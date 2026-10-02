"""Import the approved Stage 2 IDs. Authoring only: PyYAML==6.0.3.

Entry YAML remains verbatim in each record. Rendering profiles normalize the
document's different dimension names; narrative-only values are explicit data
with provenance. No package dimension lives in a geometry generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/spec-tools"))
import yaml
from component_spec_metadata import library_metadata

IDS = [f"OHM-{n:03}" for n in [70, 94, *range(103, 122)]]


def extract(source):
    text = source.decode("utf-8")
    entries = {}
    for match in re.finditer(r"^# \[(OHM-\d+)\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)", text, re.MULTILINE | re.DOTALL):
        if match[1] not in IDS:
            continue
        raw = re.search(r"```yaml\s*\n(.*?)\n```", match[0], re.DOTALL)[1]
        record = yaml.safe_load(raw)
        sections = dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", match[0], re.MULTILINE | re.DOTALL))
        record["source"] = {"document": "PCB_COMPONENT_3D_LIBRARY_SPEC.md",
            "line": text[:match.start()].count("\n") + 1,
            "yaml_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "sections": {k: v.strip() for k, v in sections.items() if k != "Structured Specification"},
            "evidence_level": "SPEC_REPORTED; cited documents not reverified"}
        entries[record["id"]] = record
    assert sorted(entries) == IDS
    profiles = {}
    for identifier in IDS:
        r = entries[identifier]
        d = {k: v["default"] for k, v in r["dimensions_mm"].items()}
        t = r["terminals"]
        dip, sot = r["package_family"] == "PKG-DIP", r["package_family"] == "PKG-SOT23"
        inherited = entries["OHM-094"] if identifier == "OHM-070" else r
        sd = {k: v["default"] for k, v in inherited["dimensions_mm"].items()}
        st = inherited["terminals"]
        p = {"kind": "dip" if dip else "sot23" if sot else "dual_gullwing",
             "pin_count": t["count"], "pitch": sd["pitch"],
             "body_length": sd["overall_length"],
             "body_width": sd.get("body_width", sd.get("overall_width")),
             "overall_height": sd["overall_height"], "standoff": sd["standoff"],
             "lead_width": sd["lead_width"], "lead_thickness": sd["lead_thickness"],
             "pin1_xy": t["pin1_xy_mm"], "exposed_pad": False,
             "basis": "Entry YAML; OHM-070 inherits PKG-SOT23/OHM-094 geometry per its narrative."}
        if dip:
            p.update(row_spacing=d["row_spacing"], shoulder_width=1.52, corner_shoulder_width=0.90,
                     tail_length=r["pcb_interface"]["tail_below_board_top_mm"], untrimmed_tail_length=t["length_mm"],
                     notch_radius=1.0, notch_depth=0.3, dimple_diameter=0.8, dimple_inset=[1.0, 1.2],
                     bend_radius=0.2, parting_step=0.1, draft_degrees=5,
                     tail_basis="PKG-DIP family b1=1.52; trimmed installed tail -2.6 per entry geometry/PCB interface; drawing L=3.3 retained separately.")
        else:
            p.update(lead_span=sd.get("lead_span", sd.get("lead_tip_span", sd.get("overall_width"))),
                     foot_length=sd.get("lead_length", st.get("length_mm")),
                     dimple_diameter=0.9 if identifier == "OHM-113" else 0.6,
                     dimple_inset=[0.8, 0.8], bend_radius=0.1, draft_degrees=5, parting_step=0.02)
            if sot:
                p.update(contact_y=abs(t["pin1_xy_mm"][1]), dimple_diameter=0.24,
                         dimple_inset=[0.4, 0.3], parting_step=0,
                         lead_mask=([[-1,-1],[1,-1],[0,1]] if t["count"] == 3 else
                                    [[-1,-1],[0,-1],[1,-1],[1,1],[-1,1]] if t["count"] == 5 else
                                    [[-1,-1],[0,-1],[1,-1],[1,1],[0,1],[-1,1]]))
        p["appearance_basis"] = "Narrative Geometry/LOD Strategy and family: draft 5 deg, radii 0.1 SMD/0.2 DIP; SOT dot 0.24 and decal insets are visual defaults; SMD parting relief 0.02 is cosmetic."
        p["variants"] = {}
        if identifier == "OHM-112":
            p["variants"]["wide"] = {"body_length":10.3,"body_width":7.5,"lead_span":10.3,
                "overall_height":2.55,"standoff":0.2,"lead_thickness":0.27,"pin1_xy":[-4.73,4.445],"dimple_diameter":0.9,
                "basis":"PKG-SOIC member SOIC-16W"}
        if identifier == "OHM-114":
            p["variants"]["body_width_3"] = {"body_width":3.0,"lead_span":4.9,"pin1_xy":[-2.15,0.975],
                "basis":"PKG-TSSOP TSSOP-8 NXP SOT505-1 option"}
        if identifier == "OHM-118":
            p["variants"]["qsop150"] = {"body_length":4.89,"body_width":3.9,"lead_span":6.0,
                "pitch":0.635,"lead_width":0.22,"foot_length":0.84,"overall_height":1.6,"pin1_xy":[-2.58,2.2225],
                "basis":"PKG-SSOP variant B; A2=1.50 + A1=0.10; inferred height and foot callouts M-/L."}
        numeric = [k for k in r["parametric"]["parameters"] if k not in
                   ["configuration", "mark_dot", "corner_lead_slim", "exposed_pad"]]
        if not dip and not sot:
            numeric += ["body_thickness", "lead_width"]
        if sot and identifier != "OHM-070":
            numeric += ["body_length", "body_width", "standoff", "lead_width", "foot_length", "lead_span", "body_thickness"]
        p["parameter_policy"] = {"numeric":sorted(set(numeric)),
            "boolean":["corner_lead_slim"] if dip else ["mark_dot"],
            "enum": {"row_spacing":[7.62,15.24]} if dip else {}, "variant_selectors":{},
            "configuration_values":["common_cathode","series","common_anode"] if identifier == "OHM-070" else [],
            "configuration_default":"common_cathode" if identifier == "OHM-070" else None}
        if r["package_family"] == "PKG-SOIC":
            p["parameter_policy"]["variant_selectors"]["body_class"] = (
                {"narrow":"default","wide":"wide"} if identifier == "OHM-112" else
                {"wide":"default"} if identifier == "OHM-113" else {"narrow":"default"})
        if identifier == "OHM-114":
            p["parameter_policy"]["variant_selectors"]["body_width"] = {"4.4":"default","3":"body_width_3"}
        if identifier in ["OHM-120","OHM-121"]:
            p["parameter_policy"]["enum"]["pin_count"] = [5,6]
            p["parameter_policy"]["pin_count_masks"] = {
                "5":[[-1,-1],[0,-1],[1,-1],[1,1],[-1,1]],
                "6":[[-1,-1],[0,-1],[1,-1],[1,1],[0,1],[-1,1]]}
        uncertain = [f"{key}: {value['default']} mm ({value['basis']}/{value['confidence']})"
                     for key, value in r["dimensions_mm"].items() if value["basis"] == "UNCERTAIN" or value["confidence"] == "L"]
        if identifier == "OHM-119":
            uncertain.append("body_thickness 0.85 mm is RESEARCH_REQUIRED in the family and entry narrative; overall 0.95 = 0.10 + 0.85.")
        if identifier in ["OHM-108", "OHM-109"]:
            uncertain.append("Wide DIP length/width defaults are derived midpoints, not manufacturer nominal values.")
        conflicts = []
        if sot:
            center = p["lead_span"] / 2 - p["foot_length"] / 2
            conflicts.append({"code":"CONTACT_REFERENCE_VS_FOOT_CENTER", "spec_contact_abs_mm":p["contact_y"],
                "geometric_foot_center_abs_mm":round(center,6), "delta_mm":round(center-p["contact_y"],6),
                "policy":"Preserve mandated contact reference and physical lead span/foot length separately. Reference lies on foot; no exact footprint fit claimed."})
            if identifier == "OHM-070":
                conflicts.append({"code":"INHERITED_SOT23_STANDOFF", "entry_standoff_mm":0,
                    "family_standoff_mm":0.05,"policy":"Use owner PKG-SOT23 standoff 0.05 and overall A=1.0, per entry inheritance instruction; preserve raw YAML body_height/standoff."})
        r["library_metadata"] = library_metadata(r, uncertain, provisional_reasons=uncertain,
            conflicts=conflicts, supported_variant="default", unsupported_variants=["unresearched_exposed_pad"])
        r["profile_id"] = r["id"]
        profiles[r["id"]] = p
    return {"schema_version":1,"source_spec_sha256":hashlib.sha256(source).hexdigest(),
            "stage":2,"profiles":profiles,"components":[entries[i] for i in IDS],
            "count_note":"Implementation Order and approved IDs total 21 (10+4+7), not 22."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = extract((ROOT / "PCB_COMPONENT_3D_LIBRARY_SPEC.md").read_bytes())
    target = ROOT / "apps/web/component-library/data/leaded.json"
    encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if target.read_text(encoding="utf-8") != encoded:
            raise SystemExit("Stage 2 data is stale")
    else:
        target.write_text(encoded, encoding="utf-8", newline="\n")
    print(f"{len(IDS)} Stage 2 records {'checked' if args.check else 'imported'}")


if __name__ == "__main__":
    main()
