"""Deterministic, reference-scoped ratings. Missing observations stay unknown.

Class prose is retained verbatim. Only explicit translations below are executable;
neither a generic class number nor a model fit establishes a reference rating.
"""

from __future__ import annotations

import math
import re
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


def _scoped_checks(component, point, context, overrides=None, transient=None, ac=None):
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
    elif cls == "BEH-DISP-LEDARRAY" and "if_max_seg" in values:
        _display_checks(component, values, b, thermal, upper_only)
    elif cls == "BEH-RES-POT":
        derive("derate", "clamp((t_end-Tamb)/(t_end-t_knee),0,1)")
        b.add("track power", "power <= p_rated*derate", ("p_rated", "t_end", "t_knee"), thermal)
        b.add("track voltage", "abs(v_A-v_B) <= v_max", ("v_max",))
        if "v_W" in values:
            b.add("wiper voltage", "max(abs(v_W-v_A), abs(v_W-v_B)) <= v_max", ("v_max",))
    elif cls in {"BEH-CAP-CERAMIC", "BEH-CAP-MICA"}:
        b.add("rated DC voltage", "abs(v_T1-v_T2) <= vr", ("vr",))
    elif cls == "BEH-CAP-FILM" and "derate_pct_per_k" in values:
        _film_checks(values, b, "abs(v_T1-v_T2)", "DC voltage")
    elif cls == "BEH-CAP-EDLC":
        derive("v", "v_P-v_N")
        if "Tamb" in values:
            b.add("ambient within rated range", "Tamb <= 85", ())
            b.add("rated voltage at ambient", "v <= (vr if Tamb <= 65 else vr_85)", ("vr", "vr_85"))
        else:
            # Without an ambient even the 85 C rating may not apply; only the highest rating proves a violation.
            upper_only("rated voltage at ambient", "v <= vr", ("vr", "vr_85"),
                       "Ambient temperature is not declared; the ratings are stated at 65 C and 85 C")
        upper_only("polarity", "v >= 0", (), "No reverse-voltage rating is sourced; reverse bias is never accepted",
                   violation_only=False)
    elif cls == "BEH-CAP-TANT":
        derive("v", "v_A-v_K")
        derive("vrev_limit", "vrev_25 if Tamb <= 25 else vrev_85 if Tamb <= 85 else vrev_125")
        hot = _tant_temperature_reason(values)
        if hot:
            upper_only("rated voltage", "v <= vr", ("vr",), hot)
        else:
            b.add("rated voltage", "v <= vr", ("vr",))
        guidance = b.add("application voltage (manufacturer MnO2 derating recommendation)", "v <= vapp_85", ("vapp_85",))
        if guidance["status"] == "violation":
            # A recommendation for low-impedance circuits, not a rating: above it is a judgment call, not a failure.
            guidance.update(status="unknown", reason="Above the manufacturer's application recommendation for MnO2 "
                            "tantalum (about half the rating); acceptable only where circuit impedance limits surge current")
        if values.get("v", 0) < 0:
            reverse = "-v <= vrev_limit" if "Tamb" in values else "-v <= vrev_25"
            upper_only("reverse voltage", reverse, ("vrev_25", "vrev_85", "vrev_125"),
                       "The reverse limits are transient-only; a DC operating point is continuous reverse bias")
    elif cls in ALUMINIUM_CAPS:
        derive("v", "v_A-v_K")
        _alcap_voltage(values, b, "v", "rated voltage")
        _alcap_reverse(values, b, "v", "")
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
    elif cls == "BEH-PWR-LOADSWITCH" and {"VIN", "VOUT", "GND", "EN_UVLO"} <= set(component.role_nodes):
        _loadswitch_checks(values, b, thermal, derive)
    elif cls == "BEH-REG-LINEAR" and {"IN", "OUT", "GND", "EN", "FB", "NR"} <= set(component.role_nodes):
        _adjustable_ldo_checks(values, b, derive)
    elif cls == "BEH-REG-BUCK-DCS" and {"VIN", "AGND", "EN", "FB", "VOS", "PG", "SW"} <= set(component.role_nodes):
        _buck_checks(values, b, thermal, derive)
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
    if ac is not None:
        _ac_checks(component, values, b, thermal, upper_only, *ac)
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
    elif cls == "BEH-CAP-FILM" and "derate_pct_per_k" in values:
        v = w.diff("T1", "T2")
        if v is not None:
            stat("peak_v", peak([abs(x) for x in v]))
            if "Tamb" in values:
                # A waveform may carry AC, whose derating starts at +75 C: a pass needs the 75 C-derated limit,
                # a violation only the 85 C-derated (DC) one; in between the waveform's content decides.
                b.add("ambient within rated range", "t_min <= Tamb <= t_max", ("t_min", "t_max"))
                row = b.add("peak voltage (derated above 75 C for AC)",
                            "peak_v <= vr*(1 - derate_pct_per_k/100*max(Tamb-75,0))", ("vr", "derate_pct_per_k"))
                if row["status"] == "violation":
                    try:
                        dc_violation = not evaluate("peak_v <= vr*(1 - derate_pct_per_k/100*max(Tamb-85,0))", values)
                    except ExpressionUnavailable:
                        dc_violation = False
                    if not dc_violation:
                        row.update(status="unknown", reason="Between the AC (+75 C) and DC (+85 C) derated limits; "
                                   "whether the waveform carries AC decides")
            else:
                _film_checks(values, b, "peak_v", "peak voltage", ac=True)
            # The 200 V rms AC rating (50 Hz, 1.4 x Urms + UDC <= Ur), its +75 C derating and the pulse dV/dt
            # limit are not evaluated on a waveform, so a transient run can never pass on the peak alone.
            b.checks.append({"name": "AC voltage, AC derating and pulse dV/dt", "expression": "", "spec_names": [],
                             "evidence": {}, "status": "unknown",
                             "reason": "The AC rating is evaluated only in an AC run at 50 Hz; pulse dV/dt is not bound"})
    elif cls == "BEH-CAP-TANT":
        v, i = w.diff("A", "K"), w.series("i", "A")
        if v is not None:
            stat("peak_v", peak(v))
            stat("peak_rev", peak([-x for x in v]))
            hot = _tant_temperature_reason(values)
            if hot:
                upper_only("peak forward voltage", "peak_v <= vr", ("vr",), hot)
            else:
                b.add("peak forward voltage", "peak_v <= vr", ("vr",))
            if values["peak_rev"] > 0:
                limit = ("vrev_25 if Tamb <= 25 else vrev_85 if Tamb <= 85 else vrev_125"
                         if "Tamb" in values else "vrev_125")
                b.add("peak reverse voltage (transient limit)", f"peak_rev <= {limit}",
                      ("vrev_25", "vrev_85", "vrev_125"),
                      None if "Tamb" in values or values["peak_rev"] > values.get("vrev_25", 0) else
                      "Ambient temperature selects the reverse limit")
        if i is not None and "irip_max" in values and _tant_esr_bound(component):
            stat("ripple_rms", w.ac_rms(i))
            b.add("ripple current", "ripple_rms <= irip_max", ("irip_max",),
                  _tant_esr_bound(component))
        elif i is not None and "irip_max" in values:
            stat("ripple_rms", w.ac_rms(i))
            freq = stat("ripple_frequency", w.frequency(i))
            if freq is None or freq > 100e3:
                b.add("ripple current", "ripple_rms <= irip_max", ("irip_max",),
                      "Ripple rating is stated at 100 kHz; the frequency multiplier for this waveform is not bound")
            else:
                upper_only("ripple current", "ripple_rms <= irip_max", ("irip_max",),
                           "Below 100 kHz the allowed ripple is lower by an unbound frequency multiplier")
    elif cls in ALUMINIUM_CAPS:
        v, i = w.diff("A", "K"), w.series("i", "A")
        if v is not None:
            stat("peak_v", peak(v))
            stat("min_v", min(v) if v else None)
            _alcap_voltage(values, b, "peak_v", "peak voltage (DC plus ripple peak)")
            _alcap_reverse(values, b, "min_v", "peak ")
        if i is not None and "irip_max" in values:
            stat("ripple_rms", w.ac_rms(i))
            b.add("ripple current", "ripple_rms <= irip_max", ("irip_max",), ALCAP_RIPPLE_REASON)
    elif cls == "BEH-CAP-EDLC":
        v, i = w.diff("P", "N"), w.series("i", "P")
        if v is not None:
            stat("peak_v", peak(v))
            if "Tamb" in values:
                b.add("peak voltage at ambient", "peak_v <= (vr if Tamb <= 65 else vr_85)", ("vr", "vr_85"))
            else:
                upper_only("peak voltage at ambient", "peak_v <= vr", ("vr", "vr_85"),
                           "Ambient temperature is not declared; the ratings are stated at 65 C and 85 C")
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
        limits, groups = contact_current_limits(values, roles)
        for role in sorted(limits):
            i = w.series("i", role)
            if i is None:
                continue
            current = limits[role]
            stat(f"rms_{role}", w.rms(i))
            if current == "i_nom":
                upper_only(f"contact RMS current {role}", f"rms_{role} <= i_nom", ("i_nom",), NOMINAL_KNEE)
            else:
                b.add(f"contact RMS current {role}", f"rms_{role} <= {current}", (current,), thermal)
        for limit, members in sorted(groups.items()):
            series = [w.series("i", r) for r in members]
            if all(x is None for x in series):
                continue
            name = f"collective contact RMS current {'+'.join(members)}"
            if any(x is None for x in series):
                b.add(name, "", (limit,), GROUP_UNOBSERVED)
                continue
            # The summed magnitude, sample by sample, then its RMS over the window.
            key = "rms_sum_" + "_".join(members)
            stat(key, w.rms([sum(abs(x) for x in sample) for sample in zip(*series)]))
            b.add(name, f"{key} <= {limit}", (limit,), thermal)
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


def _loadswitch_checks(values, b, thermal, derive):
    """TPS22810-type load switch (D074): datasheet windows, failing closed when a condition is missing."""
    derive("rail", "v_VIN-v_GND")
    b.add("recommended supply", "supply_min <= rail <= supply_max", ("supply_min", "supply_max"))
    b.add("absolute supply", "rail <= supply_abs_max", ("supply_abs_max",))
    b.add("recommended enable voltage", "0 <= v_EN_UVLO-v_GND <= en_max", ("en_max",))
    b.add("absolute enable voltage", "v_EN_UVLO-v_GND <= en_abs_max", ("en_abs_max",))
    b.add("recommended output voltage", "v_VOUT-v_VIN <= vout_rec_margin", ("vout_rec_margin",))
    b.add("absolute output voltage", "v_VOUT-v_GND <= min(rail+vout_abs_margin, vout_abs_cap)",
          ("vout_abs_margin", "vout_abs_cap"))
    # The continuous current is rated at one ambient only; without a declared ambient at or below it, unknown.
    if "Tamb" in values and "imax_ta" in values and values["Tamb"] <= values["imax_ta"]:
        b.add("continuous switch current", "abs(i_VOUT) <= imax", ("imax", "imax_ta"), thermal)
    else:
        b.add("continuous switch current", "abs(i_VOUT) <= imax", ("imax", "imax_ta"),
              "The continuous current is rated at TA = 65 C; declare an ambient at or below it")


def _adjustable_ldo_checks(values, b, derive):
    """TPS7A8001-type adjustable LDO (D074); the generic IN/GND rows add supply, output current and Tj."""
    derive("vout", "v_OUT-v_GND")
    b.add("output voltage range", "vout_min <= vout <= vout_max", ("vout_min", "vout_max"))
    b.add("absolute output voltage", "vout <= out_abs_max", ("out_abs_max",))
    b.add("absolute FB and NR voltage", "max(v_FB, v_NR)-v_GND <= fb_abs_max", ("fb_abs_max",))
    b.add("absolute enable voltage", "v_EN-v_GND <= min(v_IN-v_GND+en_abs_margin, en_abs_cap)",
          ("en_abs_margin", "en_abs_cap"))
    # Only the 1 A dropout maximum can prove headroom; below it the dropout at the actual current is not bound.
    row = b.add("dropout headroom", "v_IN-v_OUT >= vdo_max", ("vdo_max",))
    if row["status"] == "violation":
        row.update(status="unknown", reason="Below the 1 A dropout maximum; the dropout at this current is not bound")


def _buck_checks(values, b, thermal, derive):
    """TPS62160-type buck (D074): datasheet windows; currents are time averages in a transient run."""
    derive("rail", "v_VIN-v_AGND")
    b.add("recommended supply", "supply_min <= rail <= supply_max", ("supply_min", "supply_max"))
    b.add("absolute supply", "rail <= supply_abs_max", ("supply_abs_max",))
    b.add("recommended output voltage", "vout_min <= v_VOS-v_AGND <= vout_max", ("vout_min", "vout_max"))
    b.add("absolute FB, PG and VOS voltage", "max(v_FB, v_PG, v_VOS)-v_AGND <= pin_abs_max", ("pin_abs_max",))
    b.add("absolute EN voltage", "v_EN-v_AGND <= rail+en_sw_margin", ("en_sw_margin",))
    b.add("power-good sink current", "abs(i_PG) <= pg_sink_max", ("pg_sink_max",))
    b.add("recommended output current", "abs(i_SW) <= iout_recommended", ("iout_recommended",), thermal)


CONTACT_LIMIT_PREFIX = "i_rated_"
CONTACT_GROUP_PREFIX = "i_sum__"
NOMINAL_KNEE = "Nominal current applies only up to the derating knee, which is not bound"
GROUP_UNOBSERVED = "Not every contact of this collectively rated group has an observed current"


def contact_current_limits(values, roles):
    """Which sourced current limit applies to each connector contact (D068).

    The part-wide limit is ``i_rated`` (or ``i_nom``). A recipe binds a different per-contact limit for
    one role as ``i_rated_<ROLE>``. A limit the source states only collectively, over several contacts
    together, is bound as ``i_sum__<ROLE>__<ROLE>...``: it bounds the summed current magnitude of the
    listed contacts, and those contacts get no individual limit unless one is bound for them, because
    the source states none. Returns ({role: alias}, {alias: [roles]}).
    """
    groups = {k: k[len(CONTACT_GROUP_PREFIX):].split("__") for k in values if k.startswith(CONTACT_GROUP_PREFIX)}
    grouped = {role for members in groups.values() for role in members}
    default = next((k for k in ("i_rated", "i_nom") if k in values), None)
    limits = {}
    for role in roles:
        if CONTACT_LIMIT_PREFIX + role in values:
            limits[role] = CONTACT_LIMIT_PREFIX + role
        elif role not in grouped and default:
            limits[role] = default
    return limits, groups


def _display_checks(component, values, b, thermal, upper_only):
    """Per-segment LED display limits (D070); the source rates each segment or DP, never the package.

    The DC segment current applies up to the sourced derating knee ambient; above it, or with no
    declared ambient, only a violation of the flat value is proven. No common-pin or package rating
    is published, so the commons get no rating row of their own. Reverse bias is never accepted:
    the source reverse voltage is a test condition, so it can only prove a violation.
    """
    roles = set(component.role_nodes)
    segments = sorted(role for role in roles if not role.startswith("COM"))
    knee = values.get("t_knee_seg")
    ambient_ok = "Tamb" in values and knee is not None and values["Tamb"] <= knee
    for segment in segments:
        common = "COM" if "COM" in roles else "COM" + segment[-1]
        if common not in roles:
            continue
        current = f"i_{segment} <= if_max_seg"
        if ambient_ok:
            b.add(f"segment {segment} current", current, ("if_max_seg", "t_knee_seg"))
        else:
            upper_only(f"segment {segment} current", current, ("if_max_seg", "t_knee_seg"),
                       "The per-segment DC rating applies only up to the sourced derating-knee ambient; "
                       "declare an ambient at or below it (the derating above it is not encoded)")
        b.add(f"segment {segment} power", f"(v_{segment}-v_{common})*i_{segment} <= p_seg", ("p_seg",), thermal)
        if values.get(f"v_{common}", 0) - values.get(f"v_{segment}", 0) > 0:
            upper_only(f"segment {segment} reverse voltage", f"v_{common}-v_{segment} <= vr_max", ("vr_max",),
                       "The source reverse voltage is a test condition, not an application rating; "
                       "reverse bias is never accepted as within limits")


def _connector_checks(component, values, b, thermal, upper_only):
    """Every terminal carries one contact's current; insulation is rated between any two contacts."""
    voltage = next((k for k in ("v_rated", "v_work", "v_III_2") if k in values), None)
    roles = [r for r in component.role_nodes if "v_" + r in values]
    limits, groups = contact_current_limits(values, component.role_nodes)
    for role, limit in limits.items():
        if "i_" + role not in values:
            continue
        if limit == "i_nom":
            upper_only(f"contact current {role}", f"abs(i_{role}) <= i_nom", ("i_nom",), NOMINAL_KNEE)
        else:
            b.add(f"contact current {role}", f"abs(i_{role}) <= {limit}", (limit,), thermal)
    for limit, members in sorted(groups.items()):
        observed = [r for r in members if "i_" + r in values]
        if not observed:
            continue
        name = f"collective contact current {'+'.join(members)}"
        total = "+".join(f"abs(i_{r})" for r in members)
        b.add(name, f"{total} <= {limit}", (limit,),
              thermal if len(observed) == len(members) else GROUP_UNOBSERVED)
    if voltage and len(roles) > 1:
        spread = f"max({','.join('v_' + r for r in roles)})-min({','.join('v_' + r for r in roles)})"
        # OHM-171/172 print their rated voltage in a "typ" column; Jaden approved using it as the rating (D053).
        b.add("contact-to-contact voltage", f"{spread} <= {voltage}", (voltage,))
    if "t_amb_max" in values:
        b.add("ambient temperature", "Tamb <= t_amb_max", ("t_amb_max",))
    if "t_contact_max" in values:
        upper_only("contact temperature", "Tamb <= t_contact_max", ("t_contact_max",),
                   "The contact limit includes, or may include, self-heating under current, which this model "
                   "does not compute")


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
    ac_points = None
    if (result.get("status") == "ran" and result.get("analysis") == "ac" and result.get("operating_point")
            and (result.get("ac") or {}).get("points")):
        ac_points = result["ac"]["points"]
        ran_op = True  # the AC run solves and prints the same operating point first
    linear = circuit_is_linear(compilation.netlist or "")
    duals = _dual_solve_inputs(compilation, result) if ac_points is not None else {}
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
        elif ac_points is not None:
            b = _scoped_checks(component, result.get("operating_point"), context,
                               ac=(_ac_window(component, ac_points), linear, duals.get(component.ref)))
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
                else ("operating point plus sinusoidal steady state at "
                      + ", ".join(f"{p['frequency_hz']:g} Hz" for p in ac_points)
                      + ("" if linear else " (small-signal linearization)")) if ac_points is not None
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


_NONLINEAR_ELEMENTS = set("BDQMJASWUNPZ")
_CONTROLLED_ELEMENTS = set("EFGHB")


def _logical_lines(netlist):
    logical = []
    for line in netlist.splitlines():
        text = line.strip()
        if text.startswith("+") and logical:
            logical[-1] += " " + text[1:]
        elif text and not text.startswith("*"):
            logical.append(text)
    return logical


def circuit_is_linear(netlist):
    """True only when no element can make the response depend on amplitude.

    Semiconductors, switches, behavioural and digital elements are nonlinear, and so is any element
    whose value reads a circuit voltage or current (the saturating inductor card does).
    """
    for text in _logical_lines(netlist):
        if text.startswith("."):
            if re.match(r"\.(?:include|inc|lib)\b", text, re.IGNORECASE):
                return False  # an unscanned file could hold anything
            continue
        if (text[0].upper() in _NONLINEAR_ELEMENTS or re.search(r"(?<![\w.])[iv]\s*\(", text, re.IGNORECASE)
                or re.search(r"\bpoly\s*\(", text, re.IGNORECASE)):
            return False
    return bool(netlist.strip())


def circuit_is_passive(netlist):
    """Linear, with no controlled (E, F, G, H) or behavioural (B) source (D064).

    A conservative filter only: element values are not inspected (a negative resistance would still
    pass). The dual-solve bound itself needs no passivity of the network; it uses the extracted Re(Zth),
    which it requires to be positive, and the real tantalum's own passivity.
    """
    return circuit_is_linear(netlist) and not any(
        not text.startswith(".") and text[0].upper() in _CONTROLLED_ELEMENTS for text in _logical_lines(netlist))


def _terminal_node(component, role, lines):
    """The netlist node a role's element side connects to: behind its 0 V current probe when it has one."""
    probe = component.role_current_probes.get(role)
    if probe is None:
        return component.role_nodes.get(role, "").lower() or None
    found = lines.get(probe.lower(), [])
    if len(found) != 1 or len(found[0]) != 4 or found[0][1].lower() != component.role_nodes.get(role, "").lower():
        return None
    try:
        if float(found[0][3]) != 0.0:
            return None
    except ValueError:
        return None
    return found[0][2].lower()


def esr_dual_solve_elements(compilation):
    """Series-ESR elements the AC adapter shorts in its second solve (D064).

    A card qualifies only when its netlist is the T491 topology Resr -> (Cb || Rlk), checked by node:
    the *_esr resistor runs from the anode terminal to an internal node that only the card's three
    elements touch, and the capacitor and the *_lk resistor both run from that node to the cathode
    terminal. The resistor's value must be the part's sourced 100 kHz maximum ESR. Anything else is
    left out, and its ripple rows stay unknown.
    """
    lines = {}
    for text in _logical_lines(compilation.netlist or ""):
        if not text.startswith("."):
            lines.setdefault(text.split()[0].lower(), []).append(text.split())
    names = []
    for component in compilation.components:
        if not _tant_esr_bound(component):
            continue
        elements = [n.lower() for n in component.element_names]
        esr = [n for n in elements if n.startswith("r") and n.endswith("_esr")]
        cap = [n for n in elements if n.startswith("c")]
        leak = [n for n in elements if n.startswith("r") and n.endswith("_lk")]
        if len(elements) != 3 or len(esr) != 1 or len(cap) != 1 or len(leak) != 1:
            continue
        found = [lines.get(n, []) for n in (esr[0], cap[0], leak[0])]
        if any(len(f) != 1 or len(f[0]) != 4 for f in found):
            continue
        (r_line,), (c_line,), (l_line,) = found
        anode, cathode = _terminal_node(component, "A", lines), _terminal_node(component, "K", lines)
        mid = r_line[2].lower()
        if (anode is None or cathode is None or r_line[1].lower() != anode or mid in {anode, cathode}
                or {c_line[1].lower(), c_line[2].lower()} != {mid, cathode}
                or {l_line[1].lower(), l_line[2].lower()} != {mid, cathode}):
            continue
        others = [t for key, group in lines.items() if key not in {esr[0], cap[0], leak[0]}
                  for tokens in group for t in tokens[1:]]
        if mid in {t.lower() for t in others}:
            continue
        evidence = component.parameter_evidence.get("esr_max", {})
        esr_max = component.parameters.get("esr_max")
        if esr_max is None or "100 kHz" not in evidence.get("scope", ""):
            continue
        try:
            value = float(r_line[3])
        except ValueError:
            continue
        if math.isclose(value, esr_max, rel_tol=1e-12):
            names.append(next(n for n in component.element_names if n.lower() == esr[0]))
    return names


def short_elements(netlist, names):
    """The same netlist with each named two-terminal element replaced by a 0 V source (an exact short)."""
    wanted = {n.lower() for n in names}
    out, seen = [], set()
    existing = {text.split()[0].lower() for text in _logical_lines(netlist) if not text.startswith(".")}
    for line in netlist.splitlines():
        tokens = line.split()
        if tokens and tokens[0].lower() in wanted:
            short = f"Vohmni_short_{tokens[0]}"
            if tokens[0].lower() in seen or len(tokens) != 4 or short.lower() in existing:
                raise ValueError(f"Cannot short element {tokens[0]}")
            seen.add(tokens[0].lower())
            out.append(f"{short} {tokens[1]} {tokens[2]} 0")
        else:
            out.append(line)
    if seen != wanted:
        raise ValueError("Element to short not found: " + ", ".join(sorted(wanted - seen)))
    return "\n".join(out) + ("\n" if netlist.endswith("\n") else "")


def _ac_window(component, points):
    """RMS phasors per role at each solved frequency; None when any terminal is missing."""
    window = []
    for point in points:
        voltages, currents = {}, {}
        for role, node in component.role_nodes.items():
            if node == "0":
                voltages[role] = 0j
            elif node.lower() in point["node_voltages"]:
                voltages[role] = complex(*point["node_voltages"][node.lower()])
            else:
                return None
        for role, probe in component.role_current_probes.items():
            if probe.lower() not in point["branch_currents"]:
                return None
            currents[role] = complex(*point["branch_currents"][probe.lower()])
        window.append((point["frequency_hz"], voltages, currents))
    return window


RIPPLE_RATING_HZ = 100e3


def _sha256(text):
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def _dual_solve_inputs(compilation, result):
    """Per bound tantalum: the ESR-shorted second AC solve of D064, or why it is unavailable.

    The second solve is accepted only when it provably belongs to this compilation: the first solve's
    netlist hash is this compilation's netlist, the shorted elements are exactly the ones this
    compilation qualifies, and the second solve's netlist hash is this netlist with those elements shorted.
    """
    bound = [c for c in compilation.components if _tant_esr_bound(c)]
    if not bound:
        return {}
    variant = (result.get("ac") or {}).get("esr_zero")
    netlist = compilation.netlist or ""
    reason = None
    tantalums = [c for c in compilation.components if c.behavior_id == "BEH-CAP-TANT"]
    if len(tantalums) != 1:
        reason = ("the circuit has more than one tantalum capacitor, and each one's unsourced 100 kHz "
                  "impedance changes the circuit the other sees")
    elif not variant or variant.get("status") != "ran" or not variant.get("points"):
        reason = "no ESR-shorted second solve is available for this run"
    elif not circuit_is_passive(netlist):
        reason = "the circuit has a controlled or behavioural source or a nonlinear element"
    else:
        elements = esr_dual_solve_elements(compilation)
        try:
            expected = _sha256(short_elements(netlist, elements)) if elements else None
        except ValueError:
            expected = None
        if result.get("netlist_sha256") != _sha256(netlist) or variant.get("source_netlist_sha256") != _sha256(netlist):
            reason = "the first solve's netlist hash does not match this compilation"
        elif not elements or list(variant.get("elements") or []) != elements:
            reason = "the second solve did not short exactly this compilation's qualifying ESR elements"
        elif expected is None or variant.get("netlist_sha256") != expected:
            reason = "the second solve's netlist hash is not this netlist with those ESR elements shorted"
    out = {}
    for component in bound:
        shorted = {n.lower() for n in (variant or {}).get("elements", [])}
        if reason is None and not shorted & {n.lower() for n in component.element_names}:
            out[component.ref] = {"reason": "this card's series ESR was not shorted in the second solve"}
        elif reason is None:
            window = _ac_window(component, variant["points"])
            out[component.ref] = ({"window": window} if window is not None else
                                  {"reason": "the second solve did not print this part's terminal values"})
        else:
            out[component.ref] = {"reason": reason}
    return out


# Guards on the port extraction (policy, not numerics): the ESR must move the current measurably, and the
# circuit seen by the part must have real resistance.
_DUAL_MIN_SEPARATION = 1e-6
_DUAL_MIN_RESISTIVE_FRACTION = 1e-3
# Error allowed on every solved phasor, relative to its magnitude. Printing with 15 significant digits
# contributes at most 5e-15; the rest is an allowance for the solver's floating-point error. Every
# derived quantity is carried as a complex disk (centre, radius) from these inputs, so the bound below
# is an upper bound for every input within this error.
_DUAL_PHASOR_ERROR = 1e-9


def _disk_add(a, b):
    return a[0] + b[0], a[1] + b[1]


def _disk_neg(a):
    return -a[0], a[1]


def _disk_mul(a, b):
    return a[0] * b[0], abs(a[0]) * b[1] + abs(b[0]) * a[1] + a[1] * b[1]


def _disk_div(a, b):
    """a / b as a disk containing every quotient; None when b's disk contains zero."""
    centre, radius = b
    gap = abs(centre) ** 2 - radius ** 2
    if abs(centre) <= radius or gap <= 0:
        return None
    return _disk_mul(a, (centre.conjugate() / gap, radius / gap))


def _dual_solve_bound(frequency, v, i, dual, values, linear):
    """Upper bound on the real tantalum's RMS current at the rating point, or (None, reason) (D064).

    The two solves differ only in the part's series ESR, so they give two points of the linear port
    relation V = Vth - Zth*I seen by the part. A real part is passive: whatever its ESR, capacitance or
    ESL at 100 kHz, its impedance Z has Re(Z) >= 0, so |I| = |Vth| / |Zth + Z| <= |Vth| / Re(Zth). No
    lower bound exists (the part's capacitance at 100 kHz and its ESL are unsourced), so this proves a
    pass only.
    """
    if not linear:
        return None, "the circuit is nonlinear"
    if values.get("Tamb") != 25:
        return None, "the ambient is not declared as exactly 25 C, the temperature of the rating and ESR"
    if dual is None or dual.get("reason"):
        return None, (dual or {}).get("reason", "no ESR-shorted second solve is available")
    zero = next(((zv, zi) for f, zv, zi in dual["window"] if math.isclose(f, frequency, rel_tol=1e-9)), None)
    if zero is None or "A" not in i or "A" not in zero[1] or not {"A", "K"} <= set(zero[0]):
        return None, "the second solve has no value of this part at this frequency"
    eta = _DUAL_PHASOR_ERROR
    v1 = (v["A"] - v["K"], eta * (abs(v["A"]) + abs(v["K"])))
    i1 = (i["A"], eta * abs(i["A"]))
    v0 = (zero[0]["A"] - zero[0]["K"], eta * (abs(zero[0]["A"]) + abs(zero[0]["K"])))
    i0 = (zero[1]["A"], eta * abs(zero[1]["A"]))
    if i0[0] == 0 or i1[0] == 0 or abs(i1[0] - i0[0]) < _DUAL_MIN_SEPARATION * max(abs(i0[0]), abs(i1[0])):
        return None, "shorting the ESR does not measurably change this part's current, so its port is not resolved"
    # The two solves must differ by exactly the bound series resistance, seen from the part's own terminals:
    # real part equal to the maximum ESR and no reactive difference.
    step = v1[0] / i1[0] - v0[0] / i0[0]
    scale = max(abs(v1[0] / i1[0]), abs(v0[0] / i0[0]), values["esr_max"])
    if abs(step - values["esr_max"]) > 1e-6 * scale:
        return None, "the two solves do not differ by exactly the bound maximum ESR"
    delta_i = _disk_add(i1, _disk_neg(i0))
    zth = _disk_neg(_disk_div(_disk_add(v1, _disk_neg(v0)), delta_i) or (0j, math.inf))
    if not math.isfinite(zth[1]):
        return None, "the port is not resolved within the solver's numerical error"
    vth = _disk_add(v1, _disk_mul(zth, i1))
    if zth[0].real < _DUAL_MIN_RESISTIVE_FRACTION * abs(zth[0]):
        return None, ("the circuit seen by the part has almost no resistance, so the part's unsourced 100 kHz "
                      "capacitance and ESL decide its current")
    resistance = zth[0].real - zth[1]
    if resistance <= 0:
        return None, "the port is not resolved within the solver's numerical error"
    bound = (abs(vth[0]) + vth[1]) / resistance
    if bound < abs(i1[0]):
        return None, "the extracted port does not reproduce the solved current"
    return bound, None


def _ac_checks(component, values, b, thermal, upper_only, window, linear, dual=None):
    """Sinusoidal steady state: DC operating values plus RMS phasors at each requested frequency.

    For a sine on a DC bias the peak is |DC| + sqrt(2)*|AC| and the RMS is sqrt(DC^2 + |AC|^2); both
    are exact for a linear circuit. With any nonlinear element they come from a small-signal
    linearization, so no row computed from them can prove a pass or a violation.
    """
    cls = component.behavior_id
    if window is None:
        b.checks.append({"name": "AC checks", "expression": "", "spec_names": [], "evidence": {},
                         "status": "unknown",
                         "reason": "AC run did not print every terminal voltage and probe current of this component"})
        return
    root2 = math.sqrt(2.0)
    needed = [f"v_{role}" for role in component.role_nodes] + [f"i_{role}" for role in component.role_current_probes]
    if any(name not in values for name in needed):
        b.checks.append({"name": "AC checks", "expression": "", "spec_names": [], "evidence": {},
                         "status": "unknown",
                         "reason": "The operating point did not print every terminal value of this component, so "
                                   "the DC part of its AC swing is unknown"})
        return

    def dc(kind, role):
        return values[f"{kind}_{role}"]

    for frequency, v, i in window:
        tag = f" at {frequency:g} Hz"
        rows = []

        def add(name, expression, parameters, reason=None, violation_only=False, _rows=rows, _tag=tag):
            row = (upper_only(name + _tag, expression, parameters, reason) if violation_only
                   else b.add(name + _tag, expression, parameters, reason))
            _rows.append(row)
            return row

        def stat(name, value):
            values[name] = value
            return value

        def across(a, z, _v=v):
            return dc("v", a) - dc("v", z), _v[a] - _v[z]

        key = f"{frequency:g}".replace(".", "p").replace("+", "")
        if cls in {"BEH-CAP-CERAMIC", "BEH-CAP-MICA"} and {"T1", "T2"} <= set(v):
            vdc, vac = across("T1", "T2")
            stat(f"vpk_{key}", abs(vdc) + root2 * abs(vac))
            add("peak voltage (DC plus AC peak)", f"vpk_{key} <= vr", ("vr",))
        elif cls == "BEH-CAP-TANT" and {"A", "K"} <= set(v):
            vdc, vac = across("A", "K")
            stat(f"vpk_{key}", vdc + root2 * abs(vac))
            stat(f"vrev_{key}", -(vdc - root2 * abs(vac)))
            hot = _tant_temperature_reason(values)
            add("peak forward voltage (DC plus AC peak)", f"vpk_{key} <= vr", ("vr",), hot,
                violation_only=bool(hot))
            if values[f"vrev_{key}"] > 0:
                add("peak reverse voltage (transient limit)", f"vrev_{key} <= vrev_125", ("vrev_125",),
                    "A sine reverses every cycle; only transient reverse limits are sourced, so a repeated "
                    "reverse swing can prove a violation but not a pass", violation_only=True)
            if "A" in i and "irip_max" in values:
                stat(f"irip_{key}", abs(i["A"]))
                # The rating's own conditions come from its sourced scope (KEMET T491: "100 kHz, 25 C;
                # RMS current"), not from the class: a record that does not state them is never exact.
                scope = component.parameter_evidence.get("irip_max", {}).get("scope", "")
                stated = "100 kHz" in scope and "25 C" in scope and "RMS" in scope
                exact = stated and math.isclose(frequency, RIPPLE_RATING_HZ, rel_tol=1e-9)
                bound = _tant_esr_bound(component)
                limit, why = (_dual_solve_bound(frequency, v, i, dual, values, linear) if bound and exact
                              and "esr_max" in values else (None, None))
                if limit is not None:
                    # D064: the dual solve bounds the real part's current from above; a pass is proven, a
                    # violation never (the bound is not the current).
                    stat(f"irip_bound_{key}", limit)
                    heating = "esr_max" in values and "pd_max" in values
                    for name, expression, parameters in (
                            ("ripple current (rating frequency)", f"irip_bound_{key} <= irip_max", ("irip_max",)),
                            *([("ESR heating with the maximum 100 kHz ESR",
                                f"irip_bound_{key}**2*esr_max <= pd_max", ("esr_max", "pd_max"))]
                              if heating else [])):
                        row = add(name, expression, parameters, thermal)
                        if row["status"] == "violation":
                            row.update(status="unknown", reason=(
                                f"Upper bound {limit:.6g} A on the real part's current (dual solve, D064) is above "
                                "the limit; with the part's 100 kHz capacitance and ESL unsourced there is no "
                                "lower bound, so no violation is proven"))
                elif bound:
                    reason = bound + (f"; the dual solve of D064 does not apply: {why}" if why else "")
                    add("ripple current" + (" (rating frequency)" if exact else ""), f"irip_{key} <= irip_max",
                        ("irip_max",), reason)
                    if exact and "esr_max" in values and "pd_max" in values:
                        add("ESR heating with the maximum 100 kHz ESR", f"irip_{key}**2*esr_max <= pd_max",
                            ("esr_max", "pd_max"), reason)
                elif not stated:
                    add("ripple current", f"irip_{key} <= irip_max", ("irip_max",),
                        "The ripple rating's frequency, temperature or RMS basis is not stated in its source "
                        "scope", violation_only=True)
                elif exact and values.get("Tamb") is not None and values["Tamb"] <= 25:
                    add("ripple current (rating frequency)", f"irip_{key} <= irip_max", ("irip_max",), thermal)
                    if ("esr_max" in values and "pd_max" in values
                            and "100 kHz" in component.parameter_evidence.get("esr_max", {}).get("scope", "")):
                        stat(f"pesr_{key}", values[f"irip_{key}"] ** 2 * values["esr_max"])
                        add("ESR heating with the maximum 100 kHz ESR", f"pesr_{key} <= pd_max",
                            ("esr_max", "pd_max"), thermal)
                elif exact:
                    add("ripple current (rating frequency)", f"irip_{key} <= irip_max", ("irip_max",),
                        "The ripple rating is stated at 25 C; a higher or undeclared ambient needs the "
                        "temperature multiplier, which is not bound", violation_only=True)
                elif frequency < RIPPLE_RATING_HZ:
                    add("ripple current", f"irip_{key} <= irip_max", ("irip_max",),
                        "Below 100 kHz the allowed ripple is lower by an unbound frequency multiplier",
                        violation_only=True)
                else:
                    add("ripple current", f"irip_{key} <= irip_max", ("irip_max",),
                        "Ripple rating is stated at 100 kHz; the frequency multiplier is not bound")
        elif cls == "BEH-CAP-FILM" and "derate_pct_per_k" in values and {"T1", "T2"} <= set(v):
            vdc, vac = across("T1", "T2")
            stat(f"vpk_{key}", abs(vdc) + root2 * abs(vac))
            stat(f"vac_{key}", abs(vac))
            rows.append(_film_checks(values, b, f"vpk_{key}", "peak voltage (DC plus AC peak)", tag, ac=True))
            if math.isclose(frequency, 50.0, rel_tol=1e-9):
                # WIMA MKS 4 p42: AC rating at 50 Hz with 1.4 x Urms + UDC <= Ur, derated from +75 C.
                stat(f"acdc_{key}", 1.4 * abs(vac) + abs(vdc))
                derate = "(1 - derate_pct_per_k/100*max(Tamb-75,0))"
                add("AC voltage rule (1.4 x Urms + UDC)", f"acdc_{key} <= vr*{derate} and vac_{key} <= vac*{derate}",
                    ("vr", "vac", "derate_pct_per_k"),
                    None if "Tamb" in values else "The AC rating derates above 75 C; ambient temperature is needed")
            else:
                add("AC voltage", f"vac_{key} <= vac", ("vac",),
                    "The AC voltage rating is stated at 50 Hz; the permitted AC voltage at other frequencies is not bound",
                    violation_only=True)
        elif cls in ALUMINIUM_CAPS and {"A", "K"} <= set(v):
            vdc, vac = across("A", "K")
            stat(f"vpk_{key}", vdc + root2 * abs(vac))
            stat(f"vmin_{key}", vdc - root2 * abs(vac))
            rows.append(_alcap_voltage(values, b, f"vpk_{key}", "peak voltage (DC plus AC peak)", tag))
            reverse = _alcap_reverse(values, b, f"vmin_{key}", "", tag)
            if reverse is not None:
                rows.append(reverse)
            if "A" in i and "irip_max" in values:
                stat(f"irip_{key}", abs(i["A"]))
                add("ripple current", f"irip_{key} <= irip_max", ("irip_max",), ALCAP_RIPPLE_REASON)
        elif cls == "BEH-CAP-EDLC" and {"P", "N"} <= set(v):
            vdc, vac = across("P", "N")
            stat(f"vpk_{key}", vdc + root2 * abs(vac))
            if "Tamb" in values and values["Tamb"] <= 85:
                add("peak voltage at ambient (DC plus AC peak)", f"vpk_{key} <= (vr if Tamb <= 65 else vr_85)",
                    ("vr", "vr_85"))
            else:
                # vr is the sourced 65 C rating and vr_85 the 85 C rating (KYOCERA AVX SCC); nothing is rated
                # above 85 C, and without an ambient only the highest rating can prove a violation.
                add("peak voltage at ambient (DC plus AC peak)", f"vpk_{key} <= vr", ("vr", "vr_85"),
                    "Ambient temperature is undeclared or above the 85 C rated range", violation_only=True)
            if "P" in i and "ipk" in values:
                stat(f"ipk_{key}", abs(dc("i", "P")) + root2 * abs(i["P"]))
                add("peak current (DC plus AC peak)", f"ipk_{key} <= ipk", ("ipk",))
        elif cls == "BEH-MAG-INDUCTOR" and "A" in i:
            stat(f"irms_{key}", math.hypot(dc("i", "A"), abs(i["A"])))
            stat(f"ipk_{key}", abs(dc("i", "A")) + root2 * abs(i["A"]))
            if "irms" in values:
                add("RMS heating current (DC plus AC)", f"irms_{key} <= irms", ("irms",), thermal)
            if "isat" in values:
                add("peak current against saturation (DC plus AC peak)", f"ipk_{key} <= isat", ("isat",))
        elif cls == "BEH-MAG-CMC":
            for winding in ("A", "B"):
                role = winding + "1"
                if role in i:
                    stat(f"irms_{winding}_{key}", math.hypot(dc("i", role), abs(i[role])))
                    add(f"winding {winding} RMS current (DC plus AC)", f"irms_{winding}_{key} <= irated",
                        ("irated",), thermal)
        elif cls == "BEH-RES-FIXED" and {"A", "B"} <= set(v) and "A" in i:
            vdc, vac = across("A", "B")
            stat(f"vpk_{key}", abs(vdc) + root2 * abs(vac))
            stat(f"p_{key}", vdc * dc("i", "A") + (vac * i["A"].conjugate()).real)
            if "u_limit" in values:
                add("peak working voltage (DC plus AC peak)", f"vpk_{key} <= u_limit", ("u_limit",))
            if {"p_rated", "t_end", "t_knee"} <= set(values):
                add("average power (DC plus AC)", f"p_{key} <= P_allowed", ("p_rated", "t_end", "t_knee"), thermal)
        elif cls == "BEH-RES-POT" and {"A", "B"} <= set(v):
            vdc, vac = across("A", "B")
            stat(f"vpk_{key}", abs(vdc) + root2 * abs(vac))
            add("peak track voltage (DC plus AC peak)", f"vpk_{key} <= v_max", ("v_max",))
        elif cls.startswith("BEH-CON-"):
            limits, groups = contact_current_limits(values, i)
            for role in sorted(limits):
                current = limits[role]
                stat(f"irms_{role}_{key}", math.hypot(dc("i", role), abs(i[role])))
                if current == "i_nom":
                    add(f"contact RMS current {role} (DC plus AC)", f"irms_{role}_{key} <= i_nom", ("i_nom",),
                        NOMINAL_KNEE, violation_only=True)
                else:
                    add(f"contact RMS current {role} (DC plus AC)", f"irms_{role}_{key} <= {current}",
                        (current,), thermal)
            for limit, members in sorted(groups.items()):
                if not any(r in i for r in members):
                    continue
                if not all(r in i for r in members):
                    # Same rule as DC and transient: a partly observed group is unknown, never skipped.
                    add(f"collective contact RMS current {'+'.join(members)} (DC plus AC)", "", (limit,),
                        GROUP_UNOBSERVED)
                    continue
                # The RMS of a sum of magnitudes is at most the sum of the members' RMS values, so this
                # bound proves a pass; above the limit the phases decide, so it cannot prove a violation.
                bound = f"irms_sum_{'_'.join(members)}_{key}"
                stat(bound, sum(math.hypot(dc("i", r), abs(i[r])) for r in members))
                row = add(f"collective contact RMS current {'+'.join(members)} (DC plus AC)",
                          f"{bound} <= {limit}", (limit,), thermal)
                if row["status"] == "violation":
                    row.update(status="unknown", reason="The summed member RMS currents exceed the collective "
                               "limit; this sum is only an upper bound, so the phases decide")
        if not rows:
            # No translated AC rating for this class (or none of its limits is bound): the AC swing is
            # not checked, so the part cannot pass on its operating-point rows alone.
            b.checks.append({"name": "AC swing" + tag, "expression": "", "spec_names": [], "evidence": {},
                             "status": "unknown",
                             "reason": "No sinusoidal steady-state rating check is defined for this part; its "
                                       "operating-point rows do not cover the AC swing"})
        if not linear:
            for row in rows:
                if row["status"] != "unknown" or not row["reason"]:
                    row.update(status="unknown", reason=(
                        "Small-signal linearization: the circuit has a nonlinear element, so the AC amplitude "
                        "is exact only for small ripple" + (f" (computed result: {row['status']})"
                                                           if row["status"] != "unknown" else "")))


def _film_checks(values, b, observed, label, tag="", ac=False):
    """WIMA MKS 4 rating: Ur derated 1.25 %/K from +85 C for DC and from +75 C for AC voltages, within
    -55..+125 C (D059). With no declared ambient only the full rating can prove a violation (D060)."""
    start = 75 if ac else 85
    if "Tamb" in values:
        b.add("ambient within rated range" + tag, "t_min <= Tamb <= t_max", ("t_min", "t_max"))
        return b.add(label + f" (derated above {start} C)" + tag,
                     f"{observed} <= vr*(1 - derate_pct_per_k/100*max(Tamb-{start},0))", ("vr", "derate_pct_per_k"))
    row = b.add(label + f" (derated above {start} C)" + tag, f"{observed} <= vr", ("vr", "derate_pct_per_k"))
    if row["status"] == "within_limit":
        row.update(status="unknown", reason="Ambient temperature is not declared; the rating is derated above "
                   f"+{start} C and ends at +125 C")
    return row


ALUMINIUM_CAPS = {"BEH-CAP-ALEL", "BEH-CAP-ALPOLY"}
ALCAP_RIPPLE_REASON = (
    "The rated ripple current is stated at one frequency and temperature (see its scope), and the card's current is not "
    "the real part's: ESR, ESL and the 20% capacitance tolerance move it in directions the card cannot bound, so this "
    "row proves neither a pass nor a violation (D067)")


def _alcap_voltage(values, b, observed, label, tag=""):
    """Nichicon aluminium electrolytic and polymer cards (D067): DC plus ripple peak must not exceed the rated voltage,
    which applies across the category temperature range. With no declared ambient only a violation is proven."""
    if "Tamb" in values:
        b.add("ambient within category range" + tag, "t_min <= Tamb <= t_max", ("t_min", "t_max"))
        return b.add(label + tag, f"{observed} <= vr", ("vr",))
    row = b.add(label + tag, f"{observed} <= vr", ("vr",))
    if row["status"] == "within_limit":
        row.update(status="unknown", reason="Ambient temperature is not declared; the rated voltage applies only "
                   "within the category temperature range")
    return row


ALCAP_REVERSE_NOISE_V = 1e-9


def _alcap_reverse(values, b, observed, prefix, tag=""):
    """Reverse voltage is not permitted on these polarized parts (Nichicon application guidelines): any reverse
    bias is a violation. Only a reverse swing adds a row; forward bias is covered by the voltage row."""
    try:
        # 1 nV is a solver-noise floor (engine tolerance, not a datasheet value): a -1e-15 V artefact of an
        # unbiased node is not reverse bias, while any real reverse bias is far larger.
        reverse = evaluate(f"{observed} < -{ALCAP_REVERSE_NOISE_V}", values)
    except ExpressionUnavailable:
        return None
    if not reverse:
        return None
    row = b.add(prefix + "reverse voltage (not permitted)" + tag, f"{observed} >= -{ALCAP_REVERSE_NOISE_V}", ())
    row["reason"] = "Reverse voltage is not permitted on this polarized capacitor (Nichicon application guidelines)"
    return row


def _tant_temperature_reason(values):
    """The T491 rated voltage is stated up to 85 C ("rated VDC at 85 C"); above it, or with no declared
    ambient, the rating can only prove a violation."""
    if "Tamb" not in values:
        return "Ambient temperature is not declared; the rated voltage applies only up to 85 C"
    if values["Tamb"] > 85:
        return "Rated voltage is stated at 85 C; higher-temperature category voltage is not bound"
    return None


def _tant_esr_bound(component):
    """Reason text when a tantalum card carries any series element beyond its capacitance and leakage (D063).

    The T491 cards carry the sourced maximum ESR (D058). Real ESR, capacitance tolerance and the omitted
    ESL each move the part's current in a direction the card cannot bound, so with any such element its
    own ripple and ESR-heating rows prove neither a pass nor a violation. Fails closed: an element of
    any other name counts too, so only the pure Cb || Rlk card keeps the ideal-card rules.
    """
    if component.behavior_id != "BEH-CAP-TANT":
        return None
    names = [name.lower() for name in component.element_names]
    capacitors = [n for n in names if n.startswith("c")]
    leaks = [n for n in names if n.startswith("r") and n.endswith("_lk")]
    if names and len(capacitors) == 1 and len(leaks) == 1 and len(names) == 2:
        return None
    return ("The card carries a series ESR (the sourced 100 kHz maximum), and the real ESR, capacitance "
            "tolerance and omitted ESL move the part's current in directions the card cannot bound, so this "
            "row proves neither a pass nor a violation; parallel parts' currents are not bounded either (D063)")
