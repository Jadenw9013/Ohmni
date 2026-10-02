"""Authoring-only Stage 3 spec import; requires pinned PyYAML==6.0.3.

Raw source records are retained. Profiles normalize YAML dimension names and
transcribe narrative-only geometry choices with their basis explicitly stated.
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

IDS = [f"OHM-{i}" for i in range(122, 141)]


def extract(source):
    text = source.decode("utf-8")
    entries, profiles = {}, {}
    for match in re.finditer(r"^# \[(OHM-\d+)\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)", text, re.MULTILINE | re.DOTALL):
        if match[1] not in IDS:
            continue
        raw = re.search(r"```yaml\s*\n(.*?)\n```", match[0], re.DOTALL)[1]
        r = yaml.safe_load(raw)
        sections = dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", match[0], re.MULTILINE | re.DOTALL))
        r["source"] = {"document":"PCB_COMPONENT_3D_LIBRARY_SPEC.md", "line":text[:match.start()].count("\n")+1,
            "yaml_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "sections":{k:v.strip() for k,v in sections.items() if k != "Structured Specification"},
            "evidence_level":"SPEC_REPORTED; cited sources not independently reverified"}
        d = {k:v["default"] for k,v in r["dimensions_mm"].items()}
        kind = {"PKG-QFP":"qfp","PKG-QFN":"qfn","PKG-DFN":"dfn","PKG-PLCC":"plcc","PKG-BGA":"bga","PKG-WLCSP":"wlcsp"}[r["package_family"]]
        p = {"kind":kind, "body_x":d["overall_length"], "body_y":d["overall_width"],
             "pin_count":r["terminals"]["count"],"pitch":d["pitch"],"standoff":d["standoff"],
             "source_height":d["overall_height"],"height":d["overall_height"],
             "pin1_xy":r["terminals"]["pin1_xy_mm"],"draft_degrees":5 if kind == "qfp" else 0,
             "marker_diameter":min(d["overall_length"], d["overall_width"]) * 0.08,
             "marker_inset":min(d["overall_length"], d["overall_width"]) * 0.16,
             "basis":"Dimensions from entry YAML; narrative-only defaults identified in geometry_basis.",
             "geometry_basis":"Marker size/inset are cosmetic OHMNI defaults (family index area). No fabricated footprint geometry."}
        uncertain = [f"{k}: {v['default']} mm ({v['basis']}/{v['confidence']})" for k,v in r["dimensions_mm"].items() if v["basis"] == "UNCERTAIN" or v["confidence"] == "L"]
        conflicts = []
        if kind == "qfp":
            p.update(body_thickness=d["body_thickness"],height=d["standoff"]+d["body_thickness"],
                lead_span=d["lead_tip_span"],lead_width=d["lead_width"],lead_thickness=d["lead_thickness"],foot_length=d["lead_foot_length"],
                marker_diameter=float(re.search(r"dia ([\d.]+)",r["body"]["features"][0])[1]),marker_inset=1.0,
                bend_radius=d["lead_thickness"],side_counts=[r["terminals"]["count"]//4]*4)
            uncertain.append("Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.")
        elif kind in ["qfn","dfn"]:
            p.update(lead_width=d["terminal_width"],foot_length=d["terminal_length"],lead_thickness=r["terminals"]["thickness_mm"],
                ep_x=d.get("exposed_pad",d.get("exposed_pad_x")), ep_y=d.get("exposed_pad",d.get("exposed_pad_y")),
                pullback=0, pullback_demo=0.05, min_gap=0.2, accepted_min_gap=0.2,
                corner_margin=0.4, accepted_corner_margin=0.4,ep_chamfer=0,
                side_counts=([r["terminals"]["count"]//4]*4 if kind=="qfn" else [r["terminals"]["count"]//2,0,r["terminals"]["count"]//2,0]))
            p["geometry_basis"] += " Leadframe thickness from terminals YAML. Default pullback=0 per family flush-face rule; 0.05 demonstration is a caller-requested visual variant, not sourced."
            if kind == "qfn":
                conflicts.append({"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,
                    "policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."})
            if r["id"] == "OHM-134":
                uncertain += ["Terminal size 0.40 x 0.20 mm versus 0.32 x 0.18 in another extraction of TI DSG0008A.","EP 0.90 x 1.60 mm is one option; onsemi alternative 0.80 x 1.20."]
                p.update(accepted_min_gap=0.15,accepted_corner_margin=0.3)
                conflicts += [{"code":"EP_CLEARANCE_BELOW_FAMILY_RULE","actual_mm":0.15,"family_min_mm":0.2,
                    "policy":"Preserve WSON source geometry; TI source shows no K limit. No silent resizing; only this documented exception accepted."},
                    {"code":"ROW_CORNER_MARGIN_BELOW_FAMILY_RULE","row_plus_width_mm":1.7,"body_minus_margin_mm":1.6,
                     "policy":"Preserve source values; resulting total margin is 0.30, not family 0.40."}]
        elif kind == "plcc":
            p.update(lead_span=d["lead_tip_span"],lead_width=d["lead_width"],lead_thickness=d["lead_thickness"],
                contact_radius=5.775,exit_height=2.4,bevel_size=1.0,pin1_mode="center_top",side_counts=[7,7,7,7],
                marker_diameter=0.8,marker_inset=1.0)
            p["geometry_basis"] += " Contact radius 5.775 from YAML pin1; J outer radius=HD/2-contact radius=0.45; exit z2.4 and bevel 1.0 from narrative; dimple 0.8 cosmetic."
            uncertain += ["pin1_mode center_top rests on a secondary engineering reference, not a legible primary numbering diagram.",
                "Pin-1 bevel 1.0 x 1.0 mm and dimple size are UNCERTAIN cosmetic defaults.","Contact apex radial 5.775 mm is derived from an assumed 0.45 mm curl radius."]
        else:
            grid = int(r["terminals"]["count"]**0.5)
            p.update(nx=grid,ny=grid,ball_diameter=d["ball_diameter"],body_thickness=d["body_thickness"],
                height=d["standoff"]+d["body_thickness"],row_letters="ABCDEFGHJKLMNPRTUVWY",array_offset=[0,0],
                depopulate={"mode":"none"},coordinate_view="TOP",grid_margin=0.4 if kind=="bga" else 0.1,
                substrate_height=0.1 if kind=="bga" else 0,edge_chamfer=0.01 if kind=="wlcsp" else 0,
                ball_segments={"LOD1":12,"LOD2":24},ball_rings={"LOD1":8,"LOD2":16},proxy_texture_size=256)
            p["geometry_basis"] += " Sphere truncated symmetrically at z0 and standoff. BGA optional LOD2 substrate 0.10 mm is cosmetic within body thickness; WLCSP edge break 0.01 mm cosmetic. LOD0 slab uses a grid texture to retain populated-ball positions."
            if r["id"] == "OHM-136":
                uncertain.append("Ball diameter 0.46 mm is the first-pass NXP 0.41-0.51 value; not reverified in the second pass.")
            if r["id"] == "OHM-139":
                uncertain += ["Array offset [0,0] assumes centering on the 1.50 x 1.28 die (RESEARCH_REQUIRED).",
                              "Ball diameter 0.24 mm is borrowed from other vendors' 0.4-pitch WLCSP drawings."]
            if r["id"] == "OHM-137":
                conflicts += [{"code":"BALL_MAP_EXTRACTION_CONFLICT","policy":"Full 10x10=100 array follows the family resolution; contradictory extracted 'corner balls removed' is not used."},
                    {"code":"STALE_VALIDATION_ARITHMETIC","source_text_mm":7.65,"calculated_mm":7.6,"policy":"Use 9*0.8+0.40=7.60; raw source text retained."}]
        if "body_thickness" in p and abs(p["height"]-p["source_height"])>1e-9:
            conflicts.append({"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":p["source_height"],
                "rendered_height_mm":round(p["height"],6),"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."})
        p["parameter_controls"] = {"pitch":"pitch", "body_size":"body_size", "standoff":"standoff"}
        if kind in ["qfp","qfn","dfn","plcc"]:
            p["parameter_controls"].update(pin_count="pin_count",lead_width="lead_width")
        if kind=="qfp":p["parameter_controls"].update(body_thickness="body_thickness",lead_tip_span="lead_span",lead_foot_length="foot_length")
        if kind in ["qfn","dfn"]:p["parameter_controls"].update(terminal_pullback="pullback",terminal_length="foot_length",terminal_width="lead_width",exposed_pad="ep_size",exposed_pad_x="ep_x",exposed_pad_y="ep_y",body_height="height")
        if kind=="plcc":p["parameter_controls"].update(pin1_mode="pin1_mode",bevel_size="bevel_size")
        if kind in ["bga","wlcsp"]:p["parameter_controls"].update(N_x="nx",N_y="ny",ball_diameter="ball_diameter",body_thickness="body_thickness",die_x="body_x",die_y="body_y",array_offset="array_offset",row_letters="row_letters",depopulate="depopulate")
        r["profile_id"] = r["id"]
        r["library_metadata"] = library_metadata(r,uncertain,provisional_reasons=uncertain,
            conflicts=conflicts,supported_variant="default",unsupported_variants=["unresearched_manufacturer_specific_footprints"])
        entries[r["id"]]=r;profiles[r["id"]]=p
    assert sorted(entries)==IDS
    return {"schema_version":1,"stage":3,"source_spec_sha256":hashlib.sha256(source).hexdigest(),
            "profiles":profiles,"components":[entries[i] for i in IDS]}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check",action="store_true");args=parser.parse_args()
    data=extract((ROOT/"PCB_COMPONENT_3D_LIBRARY_SPEC.md").read_bytes())
    encoded=json.dumps(data,indent=2,ensure_ascii=False)+"\n";target=ROOT/"apps/web/component-library/data/quad-grid.json"
    if args.check:
        if target.read_text(encoding="utf-8")!=encoded:raise SystemExit("Stage 3 data is stale")
    else:target.write_text(encoded,encoding="utf-8",newline="\n")
    print(f"19 Stage 3 records {'checked' if args.check else 'imported'}")


if __name__=="__main__":main()
