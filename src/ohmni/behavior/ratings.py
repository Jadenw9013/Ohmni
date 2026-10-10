"""Deterministic, reference-scoped ratings. Missing observations stay unknown.

Class prose is retained verbatim. Only explicit translations below are executable;
neither a generic class number nor a model fit establishes a reference rating.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from .expressions import ExpressionUnavailable, evaluate


class RatingContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    ambient_c: float | None = None
    case_c: float | None = None
    # Explicit caller assertion about the source board/heatsink/test conditions.
    thermal_scope_confirmed: bool = False


@dataclass
class CheckBuilder:
    component: object
    values: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)

    def add(self, name, expression, parameters=(), reason=None, spec_names=()):
        evidence = self.component.parameter_evidence
        missing = [
            key
            for key in parameters
            if key not in evidence
            or evidence[key].get("basis") in {"ASSUMPTION", "RESEARCH_REQUIRED"}
        ]
        row = {
            "name": name,
            "expression": expression,
            "spec_names": list(spec_names),
            "evidence": {key: evidence[key] for key in parameters if key in evidence},
            "status": "unknown",
            "reason": reason,
        }
        if missing:
            row["reason"] = "Missing sourced limit: " + ", ".join(missing)
        elif not reason:
            try:
                outcome = evaluate(expression, self.values)
                if type(outcome) is not bool:
                    raise ExpressionUnavailable("A rating check must return a boolean")
                row.update(status="within_limit" if outcome else "violation", reason=None)
            except ExpressionUnavailable as exc:
                row["reason"] = str(exc)
        self.checks.append(row)
        return row


def _observations(component, point):
    values = dict(component.parameters)
    voltages = {"0": 0.0}
    for node, q in (point or {}).get("node_voltages", {}).items():
        if q.get("unit") == "V" and math.isfinite(q["value"]):
            voltages[node.lower()] = q["value"]
    currents = (point or {}).get("branch_currents", {})
    for role, node in component.role_nodes.items():
        if node.lower() in voltages:
            values["v_" + role] = voltages[node.lower()]
        probe = component.role_current_probes.get(role)
        q = currents.get(probe.lower()) if probe else None
        if q and q.get("unit") == "A" and math.isfinite(q["value"]):
            values["i_" + role] = q["value"]
    used = component.role_current_probes
    if used and all("v_" + role in values and "i_" + role in values for role in used):
        values["power"] = sum(values["v_" + role] * values["i_" + role] for role in used)
    return values


def _scoped_checks(component, point, context, overrides=None, transient=None):
    values = _observations(component, point)
    values.update(overrides or {})
    if context.ambient_c is not None:
        values["Tamb"] = context.ambient_c
    if context.case_c is not None:
        values["Tc"] = context.case_c
    b = CheckBuilder(component, values)
    cls = component.behavior_id
    thermal = (
        None
        if context.thermal_scope_confirmed
        else "Source thermal mounting/test conditions have not been confirmed"
    )
    if values.get("power", 0) < 0:
        thermal = (
            "Negative terminal power from this approximate model cannot establish dissipated heat"
        )

    def upper_only(name, expression, parameters, reason, violation_only=True):
        # A limit that can prove a violation but not a pass (transient-only or condition-incomplete ratings).
        row = b.add(name, expression, parameters)
        if row["status"] == "within_limit" and violation_only:
            row.update(status="unknown", reason=reason)
        elif row["status"] == "violation" and not violation_only:
            row.update(reason=reason)
        return row

    def derive(name, expression):
        try:
            values[name] = evaluate(expression, values)
        except ExpressionUnavailable:
            pass

    if cls in {"BEH-RES-FIXED", "BEH-RES-SENSE"}:
        a, z = ("A", "B") if cls == "BEH-RES-FIXED" else ("I1", "I2")
        derive("v", f"v_{a}-v_{z}")
        derive("P", f"v*i_{a}")
        derive("P_allowed", "p_rated*clamp((t_end-Tamb)/(t_end-t_knee),0,1)")
        b.add("power", "P <= P_allowed", ("p_rated", "t_end", "t_knee"), thermal, ("power",))
        if cls == "BEH-RES-FIXED":
            derive("Vmax", "min(u_limit,sqrt(p_rated*value))")
            b.add(
                "working voltage",
                "abs(v) <= Vmax",
                ("u_limit", "p_rated"),
                spec_names=("working voltage",),
            )
        else:
            b.add(
                "current",
                f"abs(i_{a}) <= sqrt(P_allowed/value)",
                ("p_rated", "t_end", "t_knee", "value"),
                thermal,
                ("current",),
            )
    elif cls == "BEH-RES-NETWORK":
        derive("derate", "clamp((t_end-Tamb)/(t_end-t_knee),0,1)")
        for k in range(2, 9):
            b.add(
                f"element power P{k}",
                f"(v_P{k}-v_P1)*i_P{k} <= p_element*derate",
                ("p_element", "t_end", "t_knee"),
                thermal,
            )
            b.add(f"working voltage P{k}", f"abs(v_P{k}-v_P1)<=v_max", ("v_max",))
        b.add(
            "package power", "power <= p_package*derate", ("p_package", "t_end", "t_knee"), thermal
        )
    elif cls == "BEH-DIO-PN" and {"A1", "K2", "K1A2"} <= set(component.role_nodes):
        # Series pair (BAV99, D050): D1 A1->K1A2, D2 K1A2->K2; currents are positive into a terminal.
        derive("i_d1", "i_A1")
        derive("i_d2", "-i_K2")
        b.add("reverse voltage D1", "v_K1A2-v_A1 <= vr_max", ("vr_max",))
        b.add("reverse voltage D2", "v_K2-v_K1A2 <= vr_max", ("vr_max",))
        for k in ("d1", "d2"):
            other = "i_d2" if k == "d1" else "i_d1"
            b.add(
                f"forward current {k.upper()}",
                f"i_{k} <= (if_double if {other} > 0 else if_single)",
                ("if_single", "if_double"),
                "DC ceiling only; source temperature/derating conditions need confirmation"
                if thermal
                else None,
            )
        if values.get("i_d1", 0) > 0 and values.get("i_d2", 0) > 0:
            thermal = "Source power and thermal resistance are stated for one diode loaded only"
        b.add("total power", "power <= p_tot", ("p_tot",), thermal)
    elif cls == "BEH-LED-POWER":
        derive("vr", "v_K-v_A")
        b.add("reverse voltage", "vr <= vr_max", ("vr_max",))
        b.add("forward current", "i_A <= if_max", ("if_max",), thermal)
        b.add(
            "junction temperature (all electrical power as heat)",
            "Tc + rth_js*(v_A-v_K)*i_A <= tj_max",
            ("rth_js", "tj_max"),
            thermal,
        )
    elif cls in {
        "BEH-DIO-PN",
        "BEH-DIO-SCHOTTKY",
        "BEH-LED-INDICATOR",
        "BEH-DIO-ZENER",
        "BEH-DIO-TVS",
    }:
        derive("vf", "v_A-v_K")
        derive("vr", "v_K-v_A")
        if "vr_max" in values:
            b.add("reverse voltage", "vr <= vr_max", ("vr_max",))
        if "if_max" in values:
            b.add(
                "forward current",
                "i_A <= if_max",
                ("if_max",),
                "DC ceiling only; source temperature/derating conditions need confirmation"
                if thermal
                else None,
            )
        if "p_rated" in values:
            b.add("source power ceiling", "power <= p_rated", ("p_rated",), thermal)
        if cls == "BEH-DIO-TVS":
            b.add("working standoff", "vr <= VWM", ("VWM",))
            b.add(
                "pulse survival",
                "abs(i_K) <= IPP",
                ("IPP",),
                "Pulse shape, duration and energy are not established by a DC point",
            )
    elif cls == "BEH-DIO-BRIDGE":
        b.add("average forward current at DC", "abs(i_PLUS)<=IF_AV", ("IF_AV",), thermal)
        b.add(
            "diode reverse voltage",
            "max(v_PLUS-v_AC1,v_PLUS-v_AC2,v_AC1-v_MINUS,v_AC2-v_MINUS)<=VRRM",
            ("VRRM",),
        )
    elif cls == "BEH-LED-RGB":
        for color in ("red", "green", "blue"):
            b.add(
                f"{color} die current",
                f"abs(i_{color}_cathode)<=if_max_die",
                ("if_max_die",),
                thermal,
            )
            b.add(
                f"{color} die power",
                f"-(v_common_anode-v_{color}_cathode)*i_{color}_cathode<=p_{color}",
                (f"p_{color}",),
                thermal,
            )
            b.add(
                f"{color} junction temperature",
                f"Tc+rth_js_{color}*(-(v_common_anode-v_{color}_cathode)*i_{color}_cathode)<=tj_max",
                (f"rth_js_{color}", "tj_max"),
                thermal,
            )
    elif cls == "BEH-RES-POT":
        derive("derate", "clamp((t_end-Tamb)/(t_end-t_knee),0,1)")
        b.add("track power", "power <= p_rated*derate", ("p_rated", "t_end", "t_knee"), thermal)
        b.add("track voltage", "abs(v_A-v_B) <= v_max", ("v_max",))
        if "v_W" in values:
            b.add("wiper voltage", "max(abs(v_W-v_A), abs(v_W-v_B)) <= v_max", ("v_max",))
    elif cls in {"BEH-CAP-CERAMIC", "BEH-CAP-MICA"}:
        b.add("rated DC voltage", "abs(v_T1-v_T2) <= vr", ("vr",))
    elif cls == "BEH-CAP-EDLC":
        derive("v", "v_P-v_N")
        if "Tamb" in values:
            b.add("ambient within rated range", "Tamb <= 85", ())
            b.add("rated voltage at ambient", "v <= (vr if Tamb <= 65 else vr_85)", ("vr", "vr_85"))
        else:
            row = b.add("rated voltage at ambient", "v <= vr_85 if v <= vr else False", ("vr", "vr_85"))
            if row["status"] == "violation" and values.get("v", 0) <= values.get("vr", 0):
                row.update(status="unknown", reason="Between the 85 C and 65 C voltage ratings; ambient temperature decides")
        upper_only("polarity", "v >= 0", (), "No reverse-voltage rating is sourced; reverse bias is never accepted",
                   violation_only=False)
    elif cls == "BEH-CAP-TANT":
        derive("v", "v_A-v_K")
        derive("vrev_limit", "vrev_25 if Tamb <= 25 else vrev_85 if Tamb <= 85 else vrev_125")
        b.add("rated voltage", "v <= vr", ("vr",),
              "Rated voltage is stated at 85 C; higher-temperature category voltage is not bound"
              if values.get("Tamb", 0) > 85 else None)
        guidance = b.add("application voltage (manufacturer MnO2 derating recommendation)", "v <= vapp_85", ("vapp_85",))
        if guidance["status"] == "violation":
            # A recommendation for low-impedance circuits, not a rating: above it is a judgment call, not a failure.
            guidance.update(status="unknown", reason="Above the manufacturer's application recommendation for MnO2 "
                            "tantalum (about half the rating); acceptable only where circuit impedance limits surge current")
        if values.get("v", 0) < 0:
            reverse = "-v <= vrev_limit" if "Tamb" in values else "-v <= vrev_25"
            upper_only("reverse voltage", reverse, ("vrev_25", "vrev_85", "vrev_125"),
                       "The reverse limits are transient-only; a DC operating point is continuous reverse bias")
    elif cls.startswith("BEH-CON-"):
        _connector_checks(component, values, b, thermal, upper_only)
    elif cls == "BEH-MAG-CMC":
        for winding in ("A", "B"):
            b.add(f"winding {winding} current", f"abs(i_{winding}1) <= irated", ("irated",), thermal)
        if "v_rated" in values:
            b.add("line voltage", "max(v_A1,v_A2,v_B1,v_B2)-min(v_A1,v_A2,v_B1,v_B2) <= v_rated", ("v_rated",))
    elif cls == "BEH-MAG-XFMR-SIGNAL":
        b.add("primary DC unbalance current", "abs(i_P_A) <= idc_unbalance", ("idc_unbalance",))
    elif cls == "BEH-MAG-INDUCTOR":
        b.add("heating current", "abs(i_A) <= irms", ("irms",), thermal)
        if "isat" in values:
            b.add("saturation current", "abs(i_A) <= isat", ("isat",))
        b.add(
            "part temperature",
            "Tamb+dT <= tmax_part",
            ("tmax_part",),
            "Self-heating and source thermal context are unavailable",
        )
    elif cls == "BEH-TRN-BJT":
        b.add("collector voltage", "v_C-v_E <= vce_max", ("vce_max",))
        b.add("reverse base voltage", "v_E-v_B <= veb_max", ("veb_max",))
        b.add("collector current", "abs(i_C) <= ic_max", ("ic_max",))
    elif cls == "BEH-TRN-MOSFET":
        b.add("gate voltage", "abs(v_G-v_S) <= vgs_max", ("vgs_max",))
        b.add("drain voltage", "v_D-v_S <= vds_max", ("vds_max",))
        b.add("drain current", "abs(i_D) <= id_max", ("id_max",), thermal)
        b.add(
            "case thermal",
            "power <= min(p_rated,(tj_max-Tc)/rth_jc)",
            ("p_rated", "tj_max", "rth_jc"),
            thermal,
        )
    elif cls == "BEH-IC-OPTO-DIP6":
        b.add("LED current", "i_A <= if_max", ("if_max",))
        b.add("LED reverse voltage", "v_K-v_A <= vr_max", ("vr_max",))
        b.add("collector voltage", "v_C-v_E <= vce_max", ("vce_max",))
        b.add("collector current", "abs(i_C) <= ic_max", ("ic_max",))
        b.add("input power", "(v_A-v_K)*i_A <= pin_max", ("pin_max",), thermal)
        b.add("output power", "(v_C-v_E)*i_C <= pout_max", ("pout_max",), thermal)

    supply = next(
        (
            pair
            for pair in [("VCC", "GND"), ("VDD", "GND"), ("Vplus", "Vminus"), ("IN", "GND")]
            if set(pair) <= set(component.role_nodes)
        ),
        None,
    )
    if supply:
        p, n = supply
        derive("rail", f"v_{p}-v_{n}")
        b.add(
            "recommended supply", "supply_min <= rail <= supply_max", ("supply_min", "supply_max")
        )
        b.add("absolute supply", "rail <= supply_abs_max", ("supply_abs_max",))
        if "icc_abs_max" in values:
            b.add("supply current", f"abs(i_{p})<=icc_abs_max", ("icc_abs_max",))
        for role in component.role_nodes:
            if role.startswith(("OUT", "Y", "Q")) and "iout_abs_max" in values:
                b.add(f"output current {role}", f"abs(i_{role})<=iout_abs_max", ("iout_abs_max",))
        if "iout_recommended" in values:
            b.add(
                "recommended output current", "abs(i_OUT)<=iout_recommended", ("iout_recommended",)
            )
    if "rth_ja" in values and "tj_max" in values:
        b.add(
            "junction temperature",
            "power >= 0 and Tamb+rth_ja*power <= tj_max",
            ("rth_ja", "tj_max"),
            thermal,
        )
    if cls == "BEH-DIO-SCHOTTKY" and {"ir_25", "ir_100", "vr_ir"} <= set(values):
        _schottky_runaway(values, b, thermal)
    if transient is not None:
        _transient_checks(component, values, b, thermal, upper_only, transient)
    return b


def _schottky_runaway(values, b, thermal):
    """Leakage self-heating: solve Tj = Tamb + Rth*(P + VR*IR(Tj)) from the two sourced leakage points.

    IR(T) = IR25*exp(k*(T-25)) with k from the 25 C and 100 C maxima; below the test voltage the
    test-voltage leakage is used (conservative), above it leakage scales linearly with VR.
    """
    if "Tamb" not in values or "rth_ja" not in values or "tj_max" not in values or "v_A" not in values:
        b.add("leakage thermal stability", "tj_leakage <= tj_max", ("ir_25", "ir_100", "rth_ja", "tj_max"),
              "Needs ambient temperature and observed terminal voltages")
        return
    vr = max(values["v_K"] - values["v_A"], 0.0) if "v_K" in values else 0.0
    k = math.log(values["ir_100"] / values["ir_25"]) / 75.0
    scale = max(1.0, vr / values["vr_ir"])
    forward = max(values.get("power", 0.0), 0.0) if vr == 0 else 0.0
    tj = values["Tamb"]
    stable = False
    for _ in range(200):
        leak = values["ir_25"] * scale * math.exp(k * (tj - 25.0))
        nxt = values["Tamb"] + values["rth_ja"] * (forward + vr * leak)
        if nxt > 1000:
            break
        if abs(nxt - tj) < 1e-4:
            tj, stable = nxt, True
            break
        tj = nxt
    values["tj_leakage"] = tj if stable else 1e9
    values["leakage_runaway"] = not stable
    b.add("leakage thermal stability", "tj_leakage <= tj_max", ("ir_25", "ir_100", "rth_ja", "tj_max"), thermal)


class TransientWindow:
    """Full-resolution role waveforms for one component; statistics are time-weighted."""

    def __init__(self, time, voltages, currents):
        self.t, self.v, self.i = time, voltages, currents

    def _mean(self, xs):
        span = self.t[-1] - self.t[0]
        if span <= 0:
            return xs[-1]
        area = sum((self.t[k + 1] - self.t[k]) * (xs[k] + xs[k + 1]) / 2 for k in range(len(xs) - 1))
        return area / span

    def series(self, kind, role):
        return (self.v if kind == "v" else self.i).get(role)

    def mean(self, xs):
        return self._mean(xs)

    def rms(self, xs):
        return math.sqrt(max(self._mean([x * x for x in xs]), 0.0))

    def ac_rms(self, xs):
        m = self._mean(xs)
        return self.rms([x - m for x in xs])

    def frequency(self, xs):
        m = self._mean(xs)
        crossings = [self.t[k] for k in range(len(xs) - 1) if xs[k] < m <= xs[k + 1]]
        if len(crossings) < 2:
            return None
        return (len(crossings) - 1) / (crossings[-1] - crossings[0])

    def diff(self, a, b):
        va, vb = self.v.get(a), self.v.get(b)
        if va is None or vb is None:
            return None
        return [x - y for x, y in zip(va, vb, strict=True)]


def _transient_checks(component, values, b, thermal, upper_only, w):
    """Peak, RMS, ripple and pulse checks that a single operating point cannot express."""
    cls = component.behavior_id
    roles = set(component.role_nodes)

    def stat(name, value):
        if value is not None:
            values[name] = value
        return value

    def peak(xs):
        return max(xs) if xs else None

    if {"A", "K"} <= roles and cls.startswith(("BEH-DIO-", "BEH-LED-")) and cls != "BEH-DIO-BRIDGE":
        reverse = w.diff("K", "A")
        i_a = w.series("i", "A")
        if reverse is not None and "vr_max" in values and cls not in {"BEH-DIO-ZENER", "BEH-DIO-TVS"}:
            stat("peak_vr", peak(reverse))
            b.add("peak reverse voltage", "peak_vr <= vr_max", ("vr_max",))
        if i_a is not None:
            if "if_max" in values:
                stat("avg_if", w.mean([max(x, 0.0) for x in i_a]))
                b.add("average forward current", "avg_if <= if_max", ("if_max",),
                      "Average over the simulated window; source temperature/derating conditions need confirmation"
                      if thermal else None)
            if "ifsm" in values:
                stat("peak_if", peak(i_a))
                upper_only("peak forward current against the surge rating", "peak_if <= ifsm", ("ifsm",),
                           "The surge rating is a single 8.3 ms half-sine; pulse shape, width and repetition are not compared")
        if cls == "BEH-DIO-TVS" and w.series("i", "K") is not None:
            stat("peak_ipp", peak([abs(x) for x in w.series("i", "K")]))
            upper_only("peak pulse current", "peak_ipp <= IPP", ("IPP",),
                       "IPP is rated for a 10/1000 us pulse; other pulse shapes are not compared")
    elif cls in {"BEH-CAP-CERAMIC", "BEH-CAP-MICA"}:
        v = w.diff("T1", "T2")
        if v is not None:
            stat("peak_v", peak([abs(x) for x in v]))
            b.add("peak voltage", "peak_v <= vr", ("vr",))
    elif cls == "BEH-CAP-TANT":
        v, i = w.diff("A", "K"), w.series("i", "A")
        if v is not None:
            stat("peak_v", peak(v))
            stat("peak_rev", peak([-x for x in v]))
            b.add("peak forward voltage", "peak_v <= vr", ("vr",),
                  "Rated voltage is stated at 85 C; higher-temperature category voltage is not bound"
                  if values.get("Tamb", 0) > 85 else None)
            if values["peak_rev"] > 0:
                limit = ("vrev_25 if Tamb <= 25 else vrev_85 if Tamb <= 85 else vrev_125"
                         if "Tamb" in values else "vrev_125")
                b.add("peak reverse voltage (transient limit)", f"peak_rev <= {limit}",
                      ("vrev_25", "vrev_85", "vrev_125"),
                      None if "Tamb" in values or values["peak_rev"] > values.get("vrev_25", 0) else
                      "Ambient temperature selects the reverse limit")
        if i is not None and "irip_max" in values:
            stat("ripple_rms", w.ac_rms(i))
            freq = stat("ripple_frequency", w.frequency(i))
            if freq is None or freq > 100e3:
                b.add("ripple current", "ripple_rms <= irip_max", ("irip_max",),
                      "Ripple rating is stated at 100 kHz; the frequency multiplier for this waveform is not bound")
            else:
                upper_only("ripple current", "ripple_rms <= irip_max", ("irip_max",),
                           "Below 100 kHz the allowed ripple is lower by an unbound frequency multiplier")
    elif cls == "BEH-CAP-EDLC":
        v, i = w.diff("P", "N"), w.series("i", "P")
        if v is not None:
            stat("peak_v", peak(v))
            if "Tamb" in values:
                b.add("peak voltage at ambient", "peak_v <= (vr if Tamb <= 65 else vr_85)", ("vr", "vr_85"))
            else:
                row = b.add("peak voltage at ambient", "peak_v <= vr_85 if peak_v <= vr else False", ("vr", "vr_85"))
                if row["status"] == "violation" and values["peak_v"] <= values.get("vr", 0):
                    row.update(status="unknown", reason="Between the 85 C and 65 C ratings; ambient decides")
        if i is not None and "ipk" in values:
            stat("peak_i", peak([abs(x) for x in i]))
            b.add("peak current", "peak_i <= ipk", ("ipk",))
    elif cls == "BEH-MAG-INDUCTOR":
        i = w.series("i", "A")
        if i is not None:
            if "isat" in values:
                stat("peak_i", peak([abs(x) for x in i]))
                b.add("peak current against saturation", "peak_i <= isat", ("isat",))
            if "irms" in values:
                stat("rms_i", w.rms(i))
                b.add("RMS heating current", "rms_i <= irms", ("irms",), thermal)
    elif cls == "BEH-MAG-CMC":
        for winding in ("A", "B"):
            i = w.series("i", winding + "1")
            if i is not None:
                stat(f"rms_{winding}", w.rms(i))
                b.add(f"winding {winding} RMS current", f"rms_{winding} <= irated", ("irated",), thermal)
    elif cls.startswith("BEH-CON-"):
        current = next((k for k in ("i_rated", "i_nom") if k in values), None)
        for role in sorted(roles):
            i = w.series("i", role)
            if i is None or current is None:
                continue
            stat(f"rms_{role}", w.rms(i))
            if current == "i_nom":
                upper_only(f"contact RMS current {role}", f"rms_{role} <= i_nom", ("i_nom",),
                           "Nominal current applies only up to the derating knee, which is not bound")
            else:
                b.add(f"contact RMS current {role}", f"rms_{role} <= {current}", (current,), thermal)
    elif cls == "BEH-RES-FIXED" and "u_limit" in values:
        v = w.diff("A", "B")
        if v is not None:
            stat("peak_v", peak([abs(x) for x in v]))
            b.add("peak working voltage", "peak_v <= u_limit", ("u_limit",))
    elif cls == "BEH-RES-POT":
        v = w.diff("A", "B")
        if v is not None:
            stat("peak_v", peak([abs(x) for x in v]))
            b.add("peak track voltage", "peak_v <= v_max", ("v_max",))
    supply = next((pair for pair in [("VCC", "GND"), ("VDD", "GND"), ("Vplus", "Vminus"), ("IN", "GND")]
                   if set(pair) <= roles), None)
    if supply and "supply_abs_max" in values:
        rail = w.diff(*supply)
        if rail is not None:
            stat("peak_rail", peak(rail))
            b.add("peak supply (absolute maximum)", "peak_rail <= supply_abs_max", ("supply_abs_max",))


def _connector_checks(component, values, b, thermal, upper_only):
    """Every terminal carries one contact's current; insulation is rated between any two contacts."""
    current = next((k for k in ("i_rated", "i_nom") if k in values), None)
    voltage = next((k for k in ("v_rated", "v_work", "v_III_2") if k in values), None)
    roles = [r for r in component.role_nodes if "v_" + r in values]
    if current:
        derating = ("Nominal current applies only up to the derating knee, which is not bound"
                    if current == "i_nom" else thermal)
        for role in component.role_nodes:
            if "i_" + role not in values:
                continue
            if current == "i_nom":
                upper_only(f"contact current {role}", f"abs(i_{role}) <= i_nom", ("i_nom",), derating)
            else:
                b.add(f"contact current {role}", f"abs(i_{role}) <= {current}", (current,), derating)
    if voltage and len(roles) > 1:
        spread = f"max({','.join('v_' + r for r in roles)})-min({','.join('v_' + r for r in roles)})"
        # OHM-171/172 print their rated voltage in a "typ" column; Jaden approved using it as the rating (D053).
        b.add("contact-to-contact voltage", f"{spread} <= {voltage}", (voltage,))
    if "t_amb_max" in values:
        b.add("ambient temperature", "Tamb <= t_amb_max", ("t_amb_max",))
    if "t_contact_max" in values:
        upper_only("contact temperature", "Tamb <= t_contact_max", ("t_contact_max",),
                   "The contact limit includes self-heating under current, which this model does not compute")


def _failure_modes(component, behavior, builder, ran):
    output = []
    faults = []
    for raw in behavior.canonical_payload.get("failure_modes", []):
        row = dict(
            raw,
            status="unknown",
            applied_response=None,
            reason="Trigger or response lacks an executable reference-scoped translation",
        )
        if not ran:
            row["reason"] = "Simulation did not run"
        elif component.behavior_id == "BEH-RES-FIXED" and raw["id"] in {
            "overpower_mild",
            "overvoltage",
        }:
            expression = "P > P_allowed" if raw["id"] == "overpower_mild" else "abs(v) > Vmax"
            # A derived power limit still needs the declared mounting context.
            power_row = next(x for x in builder.checks if x["name"] == "power")
            try:
                if raw["id"] == "overpower_mild" and power_row["status"] == "unknown":
                    raise ExpressionUnavailable(power_row["reason"])
                if raw["id"] == "overvoltage":
                    voltage_row = next(x for x in builder.checks if x["name"] == "working voltage")
                    if voltage_row["status"] == "unknown":
                        raise ExpressionUnavailable(voltage_row["reason"])
                triggered = evaluate(expression, builder.values)
                row.update(
                    status="triggered" if triggered else "not_triggered",
                    reason=None,
                    evaluated_trigger=expression,
                )
                if triggered:
                    row["applied_response"] = (
                        "flag WARNING" if raw["id"] == "overpower_mild" else "flag ERROR"
                    )
                    if raw["id"] == "overvoltage" and evaluate("abs(v)>2*Vmax", builder.values):
                        faults.append(
                            {
                                "ref": component.ref,
                                "kind": "open",
                                "resistance_ohm": 1e9,
                                "basis": "ASSUMPTION",
                                "source": behavior.source.model_dump(mode="json"),
                                "reason": raw["sim_response"],
                            }
                        )
                        row["applied_response"] = (
                            "flag ERROR; requested modeled open-circuit rerun (1G ohm)"
                        )
            except ExpressionUnavailable as exc:
                row["reason"] = str(exc)
        # Only flag-only responses with an unambiguous scoped predicate transfer.
        # A range such as 100..1000 ohm or an unspecified duration never becomes
        # an invented device substitution.
        mapped = {
            "BEH-TRN-BJT": {
                "vceo_exceeded": "collector voltage",
                "vebo_exceeded": "reverse base voltage",
            },
            "BEH-LED-INDICATOR": {
                "reverse_over_rating": "reverse voltage",
                "overcurrent_cont": "forward current",
            },
            "BEH-IC-TIMER555": {
                "overvoltage": "absolute supply",
                "output_overcurrent": "output current OUT",
            },
            "BEH-TRN-MOSFET": {"gate_oxide": "gate voltage"},
        }.get(component.behavior_id, {})
        if ran and raw["id"] in mapped:
            check = next((c for c in builder.checks if c["name"] == mapped[raw["id"]]), None)
            if check and check["status"] != "unknown":
                row.update(
                    status="triggered" if check["status"] == "violation" else "not_triggered",
                    evaluated_trigger="Violation of scoped check: " + check["name"],
                    reason=None,
                )
                if check["status"] == "violation":
                    row.update(
                        applied_response="Violation flag; source sim_response retained below",
                        unresolved_response="Clamp/degradation/damage substitution is not quantitatively defined for this reference",
                    )
        output.append(row)
    return output, faults


def evaluate_ratings(compilation, result, registry, context=None):
    """Evaluate observed op values only; unknown context never establishes safety."""
    context = context or RatingContext()
    ran_op = (
        result.get("status") == "ran"
        and result.get("analysis") == "op"
        and bool(result.get("operating_point"))
    )
    curve = None
    if result.get("status") == "ran" and result.get("analysis") == "tran" and result.get("stdout"):
        from ..eda.simulation import parse_transient

        curve = parse_transient(result["stdout"], analysis="tran", limit=100000)
        if not curve.time_s or len(curve.time_s) < 2:
            curve = None
    ran = ran_op or curve is not None
    components = []
    all_faults = []
    for component in compilation.components:
        behavior = registry.behavior_class(component.behavior_id)
        window = _window(component, curve) if curve is not None else None
        if curve is not None and window is None:
            b = _scoped_checks(component, None, context)
            reason = "Transient run did not print every terminal voltage and probe current of this component"
        elif window is not None:
            point, power = _average_point(component, window)
            b = _scoped_checks(component, point, context, {"power": power} if power is not None else None, window)
            for row in b.checks:
                if not row["name"].startswith(("peak", "average", "ripple", "RMS", "winding", "contact RMS")):
                    row["name"] += " (time average)"
            reason = None
        else:
            b = _scoped_checks(component, result.get("operating_point") if ran_op else None, context)
            reason = None if ran_op else "No operating-point or full transient observations"
        if reason:
            for check in b.checks:
                check.update(status="unknown", reason=reason)
        class_checks = []
        for original in behavior.canonical_payload.get("ratings", []):
            matches = [x for x in b.checks if original["name"] in x["spec_names"]]
            class_checks.append(
                dict(
                    original,
                    status=matches[0]["status"] if len(matches) == 1 else "unknown",
                    reason=matches[0]["reason"]
                    if len(matches) == 1
                    else "Class expression is not safely bound to this reference/analysis",
                    source=behavior.source.model_dump(mode="json"),
                )
            )
        # Authored failure triggers are operating-point expressions only.
        failures, faults = _failure_modes(component, behavior, b, ran_op)
        all_faults.extend(faults)
        statuses = [x["status"] for x in [*b.checks, *class_checks]]
        violated = "violation" in statuses or any(f["status"] == "triggered" for f in failures)
        status = (
            "violation"
            if violated
            else "unknown"
            if not ran or not statuses or "unknown" in statuses
            else "within_model_limits"
        )
        if curve is not None and window is None and status != "violation":
            status = "unknown"
        components.append(
            {
                "ref": component.ref,
                "entry_id": component.entry_id,
                "status": status,
                "class_checks": class_checks,
                "reference_checks": b.checks,
                "failure_modes": failures,
                "observations": b.values if ran else {},
                "context": context.model_dump(mode="json"),
                "basis": ("transient: time-averaged operating values plus peak, RMS, ripple and pulse statistics "
                          f"over {curve.time_s[0]:g} to {curve.time_s[-1]:g} s") if window is not None
                else "operating point" if ran_op else None,
            }
        )
    statuses = [c["status"] for c in components]
    overall = (
        "violation"
        if "violation" in statuses
        else "not_run"
        if result.get("status") != "ran"
        else "unknown"
        if not statuses or "unknown" in statuses
        else "within_model_limits"
    )
    return {
        "status": overall,
        "components": components,
        "fault_requests": all_faults,
        "limitations": [
            "Only the stated observations and source conditions were checked.",
            "Unsupported class expressions and failure triggers remain unknown; no damage timing is invented.",
            "An electrical limit check does not verify physical fit or safe operation.",
        ],
    }


def _window(component, curve):
    names = {series.name.lower(): series.values for series in curve.series}
    voltages, currents = {}, {}
    for role, node in component.role_nodes.items():
        if node == "0":
            voltages[role] = [0.0] * len(curve.time_s)
        elif f"v({node.lower()})" in names:
            voltages[role] = names[f"v({node.lower()})"]
        else:
            return None
    for role, probe in component.role_current_probes.items():
        if f"i({probe.lower()})" not in names:
            return None
        currents[role] = names[f"i({probe.lower()})"]
    return TransientWindow(curve.time_s, voltages, currents)


def _average_point(component, window):
    point = {"node_voltages": {}, "branch_currents": {}}
    for role, node in component.role_nodes.items():
        point["node_voltages"][node] = {"value": window.mean(window.v[role]), "unit": "V"}
    for role, probe in component.role_current_probes.items():
        point["branch_currents"][probe] = {"value": window.mean(window.i[role]), "unit": "A"}
    if not window.i:
        return point, None
    instantaneous = [sum(window.v[r][k] * window.i[r][k] for r in window.i) for k in range(len(window.t))]
    return point, window.mean(instantaneous)


def apply_open_faults(compilation, faults):
    """Explicit authored resistor-open approximation, never a physical prediction."""
    import hashlib

    if not compilation.runnable or not faults:
        raise ValueError("A runnable compilation and explicit fault requests are required")
    lines = compilation.netlist.splitlines()
    for index, fault in enumerate(faults):
        component = next(c for c in compilation.components if c.ref == fault["ref"])
        if (
            component.behavior_id != "BEH-RES-FIXED"
            or fault["kind"] != "open"
            or fault["resistance_ohm"] != 1e9
        ):
            raise ValueError("Unsupported failure substitution")
        removed = set(component.element_names)
        lines = [line for line in lines if not line.split() or line.split()[0] not in removed]
        # Probe sources remain, but replacement uses their physical nodes.
        lines.insert(
            -1, f"Rfailure{index} {component.role_nodes['A']} {component.role_nodes['B']} 1e9"
        )
    deck = "\n".join(lines) + "\n"
    return compilation.model_copy(
        update={"netlist": deck, "netlist_sha256": hashlib.sha256(deck.encode()).hexdigest()}
    )
