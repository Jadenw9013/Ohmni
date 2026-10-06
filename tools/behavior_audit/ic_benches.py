"""Package-bound IC probes, using unchanged authored analytical contracts."""

from __future__ import annotations

import json
import re

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation, PWLExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point, parse_transient

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes
from .benches import numeric_contract


def ic_cases(behavior, recipe=None):
    if recipe and recipe.reference_function and recipe.reference_function.value == "SN74HC245":
        return ["a_to_b", "b_to_a", "disabled"]
    if behavior == "BEH-FREQ-XO":
        return ["frequency", "current"]
    return ["high", "low"] if behavior == "BEH-IC-LOGIC-HC" else ["default"]


def _pwl(text):
    units = {"": 1.0, "n": 1e-9, "u": 1e-6, "m": 1e-3}
    values = []
    for token in text.split():
        match = re.fullmatch(r"([+-]?(?:[0-9]*\.)?[0-9]+)([num]?)", token, re.IGNORECASE)
        if not match:
            raise ValueError("Unrecognized locked PWL literal")
        values.append(float(match[1]) * units[match[2].lower()])
    if len(values) % 2:
        raise ValueError("Incomplete locked PWL pair")
    return [
        {"time": Quantity(value=t, unit="s"), "value": Quantity(value=v, unit="V")}
        for t, v in zip(values[::2], values[1::2], strict=True)
    ]


def ic_definition(audit, entry_id, case="default"):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    r = recipes.entries[entry_id]
    behavior = r.behavior_id
    contracts = {
        "BEH-IC-TIMER555": "B4",
        "BEH-IC-LOGIC-HC": "B1",
        "BEH-IC-LOGIC-SEQ": "B1",
        "BEH-IC-OPAMP": "B5",
        "BEH-IC-LDO-SOT235": "B1",
        "BEH-IC-OPTO-DIP6": "B2",
        "BEH-FREQ-XO": "B1",
    }
    contract_id = behavior + "/" + contracts[behavior]
    contract = audit._bench_contracts()[contract_id]
    raw = (audit.root / contract["file"]).read_bytes()
    if _sha_bytes(raw) != contract["netlist_sha256"]:
        raise ValueError("Locked IC source bench changed")
    deck = raw.decode("utf-8")
    roles = {role: role for role in r.terminal_roles.values()}
    supplies = {}
    excitations = []
    resistors = []
    comparisons = []
    analysis = "op"
    observe = []
    step = "1n"
    stop = "3200n"

    def dc(pos, neg, value):
        excitations.append(
            DCExcitation(positive_net=pos, negative_net=neg, value=Quantity(value=value, unit="A"))
        )

    if behavior == "BEH-IC-TIMER555":
        if "100m" not in deck or "15" not in deck:
            raise ValueError("Authored 555 stimulus changed")
        roles.update(GND="return", TRIG="return", THRES="return", RESET="supply", VCC="supply")
        supplies = {"supply": 15}
        dc("OUT", "return", 0.1)
        band = re.fullmatch(r"TI band ([0-9.]+)\.\.([0-9.]+)", contract["expected"][0]["tolerance"])
        if not band:
            raise ValueError("555 source interval missing")
        comparisons = [
            {
                "kind": "interval",
                "node": "OUT",
                "minimum": float(band[1]),
                "maximum": float(band[2]),
            }
        ]
    elif (
        behavior == "BEH-IC-LOGIC-HC"
        and r.reference_function
        and r.reference_function.value == "SN74HC245"
    ):
        roles.update(
            GND="return",
            VCC="supply",
            OE="supply" if case == "disabled" else "return",
            DIR="return" if case == "b_to_a" else "supply",
        )
        supplies = {"supply": 4.5}
        source, destination = ("B", "A") if case == "b_to_a" else ("A", "B")
        for i in range(1, 9):
            high = i % 2 == 1
            roles[source + str(i)] = "supply" if high else "return"
            node = destination + str(i)
            if case == "disabled":
                resistors.extend([(node, "return", 10000), (node, "supply", 10000)])
                leak = next(
                    f
                    for f in registry.entry(entry_id).research.field_updates
                    if f.field == "off_state_output_leakage_max"
                )
                bound = leak.value * 1e-6 * 5000
                comparisons.append(
                    {
                        "kind": "interval",
                        "node": node,
                        "minimum": 2.25 - bound,
                        "maximum": 2.25 + bound,
                        "source_fact": leak.model_dump(mode="json"),
                        "derivation": "Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.",
                    }
                )
            else:
                dc(node, "return", 0.004) if high else dc("supply", node, 0.004)
                row = next(
                    x
                    for x in contract["expected"]
                    if x["measure"] == ("VOH_4mA" if high else "VOL_4mA")
                )
                comparisons.append(dict(numeric_contract(row), kind="absolute", node=node))
    elif behavior == "BEH-IC-LOGIC-HC":
        roles.update(GND="return", VCC="supply")
        supplies = {"supply": 4.5}
        row = next(
            x
            for x in contract["expected"]
            if x["measure"] == ("VOH_4mA" if case == "high" else "VOL_4mA")
        )
        expected = numeric_contract(row)
        for i in range(1, 5):
            roles["A" + str(i)] = roles["B" + str(i)] = "return" if case == "high" else "supply"
            output = "Y" + str(i)
            dc(output, "return", 0.004) if case == "high" else dc("supply", output, 0.004)
            comparisons.append(dict(expected, kind="absolute", node=output))
    elif behavior == "BEH-IC-OPAMP":
        roles.update(Vminus="return", Vplus="supply")
        supplies = {"supply": 5, "input": 2}
        for i in (1, 2):
            roles["IN" + str(i) + "_plus"] = "input"
            roles["IN" + str(i) + "_minus"] = "OUT" + str(i)
            resistors.append(("OUT" + str(i), "return", 1000))
        expected = numeric_contract(contract["expected"][0])
        comparisons = [
            {
                "kind": "absolute",
                "supply": "supply",
                "scale": 1000,
                "expected": 2 * expected["expected"],
                "tolerance": 2 * expected["tolerance"],
                "derivation": "Two identical channels: sum of two unchanged B5 single-amplifier current contracts. Recipe retains its authored input offset rather than silently setting it to zero.",
            }
        ]
    elif behavior == "BEH-IC-LDO-SOT235":
        roles.update(GND="return", IN="supply", EN="supply")
        supplies = {"supply": 3}
        dc("OUT", "return", 0.1)
        comparisons = [dict(numeric_contract(contract["expected"][0]), kind="absolute", node="OUT")]
    elif behavior == "BEH-IC-OPTO-DIP6":
        roles.update(K="return", E="return")
        supplies = {"supply": 5}
        # Source B2 collector supply and100ohm load, LED5mA point.
        resistors.append(("supply", "C", 100))
        dc("return", "A", 0.005)
        comparisons = [
            dict(
                numeric_contract(contract["expected"][0]),
                kind="absolute",
                supply="supply",
                scale=1000,
            )
        ]
    elif behavior == "BEH-FREQ-XO":
        roles.update(GND="return", VDD="supply", OE="supply")
        supplies = {"supply": 3.3}
        if case == "frequency":
            analysis = "tran"
            observe = ["OUT"]
            step = "100u"
            stop = "5.02ms"
            source_frequency = next(
                f
                for f in registry.entry(entry_id).research.field_updates
                if f.field == "quiescent_current_test_frequency"
            )
            factor = (
                source_frequency.value
                * 1e6
                / float(
                    registry.behavior_class(behavior).canonical_payload["parameters"]["f0"][
                        "default"
                    ]
                )
            )
            expected = numeric_contract(contract["expected"][0])
            comparisons = [
                {
                    "kind": "frequency",
                    "node": "OUT",
                    "threshold": 1.65,
                    "after": 0.005,
                    "rise_start": 10,
                    "rise_end": 210,
                    "expected": expected["expected"] * factor,
                    "tolerance": expected["tolerance"],
                    "source_fact": source_frequency.model_dump(mode="json"),
                    "derivation": "Same f0*(1+ppm) contract at explicit20MHz variant; unchanged1Hz absolute tolerance. Source B1 measures200 periods from rise10 to210. Startup is5ms source maximum instead of5us bench demonstration.",
                }
            ]
        else:
            fact = next(
                f
                for f in registry.entry(entry_id).research.field_updates
                if f.field == "quiescent_current_max"
            )
            comparisons = [
                {
                    "kind": "interval",
                    "supply": "supply",
                    "scale": 1000,
                    "minimum": 0,
                    "maximum": fact.value,
                    "source_fact": fact.model_dump(mode="json"),
                }
            ]
    else:
        roles.update(GND="return", VCC="supply")
        supplies = {"supply": 4.5}
        analysis = "tran"
        names = {"ser": "SER", "srclk": "SRCLK", "srclr": "SRCLR", "rclk": "RCLK", "oe": "OE"}
        for name, role in names.items():
            row = re.search(
                r"^V\S+\s+" + name + r"\s+0\s+pwl\(([^)]*)\)", deck, re.IGNORECASE | re.MULTILINE
            )
            if not row:
                raise ValueError("Missing authored sequential stimulus " + name)
            excitations.append(
                PWLExcitation(positive_net=role, negative_net="return", points=_pwl(row[1]))
            )
        pattern = [int(x) for x in contract["expected"][0]["value"].split(",")]
        if contract["expected"][0]["tolerance"] != "exact":
            raise ValueError("Shift contract no longer exact")
        for i, bit in enumerate(pattern):
            role = "Q" + chr(65 + i)
            resistors.extend([(role, "return", 10000), (role, "supply", 10000)])
            observe.append(role)
            comparisons.append(
                {
                    "kind": "logic",
                    "node": role,
                    "time": 2.4e-6,
                    "expected": bit,
                    "supply_voltage": 4.5,
                    "low_fraction": 0.3,
                    "high_fraction": 0.7,
                    "derivation": "Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.",
                }
            )
    comps = [CircuitComponent(ref="U1", part_id=entry_id, package=r.package)]
    nets = {n: [] for n in set(roles.values()) | supplies.keys()}
    nets.setdefault("return", [])
    for pin, role in r.terminal_roles.items():
        nets[roles[role]].append(PinRef(component="U1", pin=pin))
    choices = {"U1": BehaviorSelection(entry_id=entry_id)}
    for i, (pos, neg, value) in enumerate(resistors, 1):
        ref = "R" + str(i)
        comps.append(
            CircuitComponent(ref=ref, part_id="OHM-004", package="0603", value=Quantity.ohms(value))
        )
        choices[ref] = BehaviorSelection(entry_id="OHM-004")
        nets[pos].append(PinRef(component=ref, pin="1"))
        nets[neg].append(PinRef(component=ref, pin="2"))
    circuit = CircuitIR(
        ir_id="runtime-" + entry_id + "-" + case,
        name="Authored package-bound IC comparison",
        components=comps,
        nets=[
            Net(
                name=n,
                kind="ground" if n == "return" else "power" if n in supplies else "signal",
                connections=pins,
                external_source=ExternalSource(
                    kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(supplies[n]))
                )
                if n in supplies
                else None,
            )
            for n, pins in sorted(nets.items())
        ],
    )
    compiled = compile_circuit(
        circuit, registry, recipes, choices, analysis=analysis, excitations=excitations
    )
    identity = {
        "run_id": audit._state()["run_id"],
        "entry_id": entry_id,
        "analysis": analysis,
        "variant": case,
        "netlist_sha256": compiled.netlist_sha256,
        "circuit_hash": compiled.circuit_hash,
        "recipe_source_sha256": recipes.source.document_sha256,
        "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
        "class_source_sha256": registry.behavior_class(behavior).source.document_sha256,
        "analytical_source": contract_id,
        "source_deck_sha256": contract["netlist_sha256"],
        "comparison": comparisons,
        "observe_nets": observe,
        "tstep": step,
        "tstop": stop,
        "limits": "Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.",
    }
    return compiled, identity


def _observations(compiled, identity, output):
    point = parse_operating_point(output) if identity["analysis"] == "op" else None
    curve = (
        parse_transient(output, analysis="tran", limit=100000)
        if identity["analysis"] == "tran"
        else None
    )
    values = []
    for row in identity["comparison"]:
        if point and "supply" in row:
            current = point.branch_currents.get(compiled.source_elements[row["supply"]])
            values.append(-current.value * row["scale"] if current else None)
        elif point:
            voltage = point.node_voltages.get(compiled.node_names[row["node"]])
            values.append(voltage.value if voltage else None)
        else:
            series = next(
                (
                    x
                    for x in curve.series
                    if x.name == "v(" + compiled.node_names[row["node"]] + ")"
                ),
                None,
            )
            if row["kind"] == "frequency":
                crossings = []
                if series:
                    for t0, t1, v0, v1 in zip(
                        curve.time_s, curve.time_s[1:], series.values, series.values[1:]
                    ):
                        if t0 >= row["after"] and v0 < row["threshold"] <= v1:
                            crossings.append(t0 + (t1 - t0) * (row["threshold"] - v0) / (v1 - v0))
                start, end = row["rise_start"] - 1, row["rise_end"] - 1
                values.append(
                    (end - start) / (crossings[end] - crossings[start])
                    if len(crossings) > end
                    else None
                )
                continue
            if (
                series is None
                or not curve.time_s
                or not curve.time_s[0] <= row["time"] <= curve.time_s[-1]
            ):
                values.append(None)
            else:
                values.append(
                    series.values[
                        min(
                            range(len(curve.time_s)),
                            key=lambda k: abs(curve.time_s[k] - row["time"]),
                        )
                    ]
                )
    return values


def _matches(row, value):
    if value is None:
        return False
    if row["kind"] in {"absolute", "frequency"}:
        return abs(value - row["expected"]) <= row["tolerance"]
    if row["kind"] == "interval":
        return row["minimum"] <= value <= row["maximum"]
    bit = (
        0
        if value <= row["low_fraction"] * row["supply_voltage"]
        else 1
        if value >= row["high_fraction"] * row["supply_voltage"]
        else None
    )
    return bit == row["expected"]


def run_ic_recipes(audit, entry_ids):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    receipts = []
    for key in entry_ids:
        for case in ic_cases(recipes.entries[key].behavior_id, recipes.entries[key]):
            compiled, identity = ic_definition(audit, key, case)
            relative = f"runtime-bench-output/{key}-ic-{case}"
            result = NgspiceAdapter().behavior_circuit(
                compiled,
                work_dir=audit.run_dir / relative,
                analysis=identity["analysis"],
                tstep=identity["tstep"],
                tstop=identity["tstop"],
                observe_nets=identity["observe_nets"] or None,
            )
            output = result.get("stdout", "") + result.get("stderr", "")
            values = (
                _observations(compiled, identity, output)
                if result["status"] == "ran"
                else [None] * len(identity["comparison"])
            )
            passed = result["status"] == "ran" and all(
                _matches(row, v) for row, v in zip(identity["comparison"], values, strict=True)
            )
            _atomic_text(audit.run_dir / relative / "output.txt", output)
            _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
            receipt = dict(
                identity,
                ran_at=_now(),
                run_status="passed" if passed else "failed",
                observation_status=result["status"],
                observed=values,
                product_code_path=result.get("product_code_path"),
                problems=result["problems"],
                output_sha256=_sha_bytes(output.encode()),
                raw_output=relative + "/output.txt",
                version_output=result["version_output"],
                version_file=relative + "/version.txt",
                version_sha256=_sha_bytes(result["version_output"].encode()),
            )
            _atomic_json(audit.run_dir / f"runtime-bench-results/{key}-ic-{case}.json", receipt)
            receipts.append(receipt)
    return receipts


def ic_receipt_errors(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipe = load_recipes(registry, audit.root).entries[entry_id]
    errors = []
    for case in ic_cases(recipe.behavior_id, recipe):
        compiled, identity = ic_definition(audit, entry_id, case)
        path = audit.run_dir / f"runtime-bench-results/{entry_id}-ic-{case}.json"
        if not path.is_file():
            errors.append(f"{entry_id}: IC receipt missing")
            continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        required = dict(
            identity,
            run_status="passed",
            observation_status="ran",
            product_code_path="ohmni.eda.simulation.NgspiceAdapter.behavior_circuit",
        )
        errors.extend(
            f"{entry_id}: stale or failed IC receipt {k}"
            for k, v in required.items()
            if receipt.get(k) != v
        )
        raw = audit._safe_run_path(receipt["raw_output"]).read_bytes()
        observed = _observations(compiled, identity, raw.decode("utf-8"))
        if (
            _sha_bytes(raw) != receipt["output_sha256"]
            or observed != receipt["observed"]
            or not all(
                _matches(r, v) for r, v in zip(identity["comparison"], observed, strict=True)
            )
        ):
            errors.append(f"{entry_id}: raw IC observations fail comparison")
        version = audit._safe_run_path(receipt["version_file"]).read_bytes()
        if (
            _sha_bytes(version) != receipt["version_sha256"]
            or version.decode("utf-8") != receipt["version_output"]
            or not re.search(r"\bngspice-42\b", version.decode("utf-8"))
        ):
            errors.append(f"{entry_id}: IC ngspice42 evidence invalid")
    return errors
