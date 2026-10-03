"""Authoring-only Stage 5 import. Raw source fields remain unchanged."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/spec-tools'))
import yaml
from component_spec_metadata import library_metadata

IDS = [*range(10, 14), *range(28, 41), 47, *range(73, 87)]
BANDS = {'4': [[.12,.20],[.26,.34],[.40,.48],[.80,.88]], '5': [[.10,.17],[.22,.29],[.34,.41],[.46,.53],[.83,.90]]}


def extract(source):
    text=source.decode('utf-8');records=[];profiles={}
    for m in re.finditer(r'^# \[(OHM-(\d+))\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)',text,re.MULTILINE|re.DOTALL):
        n=int(m[2])
        if n not in IDS:continue
        raw=re.search(r'```yaml\s*\n(.*?)\n```',m[0],re.DOTALL)[1];r=yaml.safe_load(raw)
        sections=dict(re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',m[0],re.MULTILINE|re.DOTALL))
        r['source']={'document':'PCB_COMPONENT_3D_LIBRARY_SPEC.md','line':text[:m.start()].count('\n')+1,'yaml_sha256':hashlib.sha256(raw.encode()).hexdigest(),'sections':{k:v.strip() for k,v in sections.items() if k!='Structured Specification'},'evidence_level':'SPEC_REPORTED; cited sources not independently reverified'}
        d={k:v['default'] for k,v in r['dimensions_mm'].items()};t=r['terminals']
        u=[f"{k}: {v['default']} mm ({v['basis']}/{v['confidence']})" for k,v in r['dimensions_mm'].items() if v['basis']=='UNCERTAIN' or 'L' in v['confidence']]
        c=[]
        def conflict(code,policy,_items=c,**values):_items.append({'code':code,**values,'policy':policy})
        p={'kind':None,'family':r['package_family'],'body_material':r['body']['material'],'lead_material':t['material'],'standoff':r['pcb_interface']['standoff_mm'],'tail':2.6 if r['mounting']=='tht' else 0,'lead_diameter':d.get('lead_diameter',t.get('width_mm',.5)),'lead_width':t.get('width_mm',.5),'lead_thickness':t.get('thickness_mm',.1),'count':t['count'],'pin1':t['pin1_xy_mm'],'segments':{'LOD0':16,'LOD1':32,'LOD2':64},'mark_width_fraction':.6,'mark_height_fraction':.12,'mark_color':'MAT_SILKSCREEN_WHITE'}
        if n in [10,11,12,13,47]:
            p.update(kind='axial',body_x=d['body_length'],body_y=d.get('body_diameter',d.get('body_width')),body_h=d.get('body_height',d.get('body_diameter',d.get('body_width'))),pitch=d.get('lead_pitch',d.get('pitch')),cement=n==12,cap_length=d.get('end_cap_length',0),cap_radius_ratio=.45,edge_radius=.3 if n==12 else .1)
            if n==47:p['lead_diameter']=.51;p['body_color']='#4F7A4A'
            p['bend_radius']=p['lead_diameter']*1.5;p['band_count']=5 if n==11 else 4 if n in [10,47] else 0
            p['band_colors']=['BROWN','BLACK','RED','GOLD'] if p['band_count']==4 else ['BROWN','BLACK','BLACK','RED','BROWN'] if p['band_count']==5 else []
            p['bands']=BANDS.get(str(p['band_count']),[])
            u+=['Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.']
            if n==12:conflict('CEMENT_OUTLINE_TEXT','Independent width and height columns and entry box procedure win over the conflicting cylindrical summary.');u+=['Cement lead length/pitch, edge radius and printed marking field remain provisional.']
            if n==13:
                # Keep the explicit step-1 procedure, rather than force a longer cap envelope into the bend clearance.
                conflict('WIREWOUND_CAP_EXTENT','Use explicit procedure: coating A-2*cap, caps within A. Family B=25.40 and prose saying caps beyond A conflict with that procedure; retain both, do not enlarge silently.',A_mm=22.23,B_max_mm=25.40,cap_mm=1.59)
                u+=['Wirewound B column/cap interpretation, green coating, cap taper and lead geometry are not independently resolved.']
            if n==47:u+=['Bourns 78F only distributor-supported; lead diameter .51 from narrative, coating green is an OHMNI default.']
        elif n in [29,31,40,30,32]:
            smd=n in [30,32];p.update(kind='can_smd' if smd else 'can',diameter=d['diameter'],body_h=d['body_height'],body_x=d['diameter'],body_y=d['diameter'],pitch=t['pitch_mm'],seal_height=.3,bead_z=1.5,bead_depth=.4,bead_width=.4,top_rim=1.0,vent_width=.12,vent_depth=.04,vent_span=.65,vent_min_diameter=10 if smd else 6.3,stripe_angle=.48,seat_height=2 if n==31 else 0,sleeve_material='MAT_PVC_SLEEVE_BLUE' if n==31 else 'MAT_PVC_SLEEVE_BLACK')
            u+=['Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.']
            if smd:
                p.update(base=d['base_plate'],span=d['overall_length'],base_height=1.0,chamfer=1.0,gap=d.get('terminal_gap',1.8),foot=t['length_mm'],upbend=.3)
                conflict('SMD_CAN_TERMINAL_ARITHMETIC','Preserve contact x=2.4 and 2.9-long pads (outer 3.85, inner .95). B=7.8/P=1.8 imply 3.0-long pads; do not silently stretch terminals.',source_span_mm=7.8,source_gap_mm=1.8,source_pad_length_mm=2.9,modeled_span_mm=7.7,modeled_gap_mm=1.9)
                conflict('SMD_CAN_HEIGHT_STACK','Body-height L remains cylinder height above the provisional 1 mm plate; total seating height is L+1. The plate/H/K callouts are unresolved.',can_height_mm=p['body_h'],plate_height_mm=1)
                u+=['Base thickness 1.0 and terminal thickness .1 are visual defaults; H/K meaning unresolved. Base plate D+0.3 applies only through 10 mm. 12.5 mm and larger base/pad tables are not inferred or enabled.']
                if n==30:conflict('SMD_CAN_MEMBER_NAME','Raw member D8 is retained, but the second-pass numeric default is diameter 6.3 mm.')
                if n==32:u+=['Polymer OS-CON base plate and terminals use the OHM-030 FK proxy; radial style B is outside this default record.']
            if n==31:
                p['tail']=4.0
                conflict('SNAPIN_TAIL_OVERRIDE_LOCATION','Entry YAML supplies terminal_protrusion/length=4.0 rather than the addendum tail key. Apply the explicit requested override, bottom Z=-4.0.')
                conflict('SNAPIN_SEAT_HEIGHT_STACK','Follow procedure can D x L above 2 mm seat: rendered top is 42 mm. Nominal body L=40 is retained; seat dimensions are provisional.')
                u+=['Snap-in 3-pin hole coordinates and terminal cross-section are unresolved. Only the sourced two-pin default is enabled; no third hole is invented. Seat diameter D-1 and height 2 are visual defaults.']
            if n==40:
                conflict('SUPERCAP_TAIL_LANGUAGE','Keep global 2.6 mm trimmed tail; raw length_mm=3.0 is not an explicit below-board override and is unsourced.')
                u+=['Default is Kyocera AVX SCC 10x20, not Eaton PB. Single summarized source; lead length, sleeve color and alternative styles remain uncertain.']
        elif n in range(33,37):
            p.update(kind='tantalum',body_x=d['overall_length'],body_y=d['overall_width'],body_h=d['overall_height'],foot=t['length_mm'],bevel=.4,draft_degrees=3,wrap_height_fraction=.6,stripe_width=.3)
            u+=['Tantalum bevel .4, 3-degree draft and marking layout are cosmetic; end strips partition the nominal envelope instead of extending outside it.']
        elif n in [28,37,38,39]:
            p.update(kind='disc' if n==28 else 'mica' if n==39 else 'film',body_x=d.get('overall_length',d.get('diameter')),body_y=d.get('overall_width',d.get('thickness')),body_h=d.get('overall_height',d.get('diameter')),pitch=d['pitch'],edge_radius=1.5 if n==39 else .3,resin_depth=.1,face_bulge=.2 if n==39 else 0)
            u+=['Standoff, meniscus, fillets, resin face, lead taper and print placement are visual defaults; no certification/value is asserted.']
            if n==28:conflict('DISC_COATING_ENVELOPE','Use 7 x 2.5 as finished coated envelope. Adding the procedural .4 coating on every face would contradict those dimensions; coating has material only.')
            if n in [37,38]:conflict('FILM_UNCUT_VS_TRIMMED_LEAD','Raw terminal length 6 mm is uncut/ambiguous; apply default below-board tail 2.6 mm per mounting convention.')
            if n==39:conflict('MICA_STANDOFF_AND_BULGE','Use explicit YAML .5 standoff. LOD2 face bulge stays inside the 4.3 mm finished thickness rather than adding .4 to it.')
        elif n in range(73,77):
            rect=n==76;p.update(kind='led_rect' if rect else 'led_tht',body_x=d.get('body_diameter',d.get('overall_length')),body_y=d.get('body_diameter',d.get('overall_width')),body_h=d['overall_height'],pitch=d['pitch'],flange_diameter=d.get('flange_diameter'),flange_thickness=d.get('flange_thickness'),flat_depth=.4,bevel=.5,anode_extra=1.0,lens='diffused',led_color='#FF2A1A',lens_opacity=.78,clear_opacity=.3,cup_diameter=.9,cup_height=.3,cup_x_fraction=-.25)
            u+=['Cathode flat depth .4 (rectangular chamfer .5), lead cross-section and 1 mm LOD2 anode extension are unsourced visual defaults. Dome is hemispherical.']
            if n==73:
                conflict('DOME_RADIUS_ROUNDING','Body radius 1.45 and drawing R1.4 differ by .05. Follow explicit hemisphere D/2 procedure; preserve R1.4 in source.',source_radius_mm=1.4,modeled_radius_mm=1.45)
                conflict('LED3_FLAT_VS_LEAD','Flat x=-1.2 from the provisional .4 depth cuts inside cathode lead extent -1.52. Preserve both; full assembly bounds include the projecting lead. Flat depth needs research.',flat_x_mm=-1.2,lead_outer_x_mm=-1.52)
            if n==75:u+=['10 mm LED flange thickness 1.2 mm is a placeholder with only <1.5 bound; single numeric drawing, not cross-verified.']
            if n==76:conflict('RECT_LED_VENDOR_HEIGHT','Use second-pass 5 x 2 x 7 and long axis along X; 7.05/7.5 vendor heights and axis association remain unresolved.')
        elif n in range(77,85):
            chip=n<81;p.update(kind='led_chip' if chip else 'led_cavity',body_x=d['overall_length'],body_y=d['overall_width'],body_h=d['overall_height'],foot=t['length_mm'],wrap_height=.05 if chip else .5,chamfer=0 if chip else .7 if n<83 else .6,cavity_diameter=2.4 if n<83 else 4.0,cavity_depth=.8,window_x_fraction=.5,window_y_fraction=.7,lens_height=.08 if chip else .1,lens='diffused',led_color='#FF2A1A' if n<82 else '#B9C5D0',lens_opacity=.78,clear_opacity=.3,stripe_width=.08 if chip else .2,die_colors=['#FF2A1A','#23C552','#2868E8'],die_size=.25)
            u+=['Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.']
            if chip:
                conflict('CHIP_LED_WINDOW_HEIGHT','Overall H includes the emitter window: recess the central window by its .08 cap height. The literal box-H-plus-dome procedure would exceed stated overall height.')
            if n==81:conflict('PLCC2_CONTACT_CENTER','Preserve YAML x=-1.2; the coupled 3.5/2-1/2 expression gives -1.25. Modeled feet center on the explicit YAML coordinate.')
            if n in [82,83,84]:u+=['Neutral cool diffuser tint is an OHMNI unlit appearance default, chosen to distinguish the cavity from the white case.']
            if n in [82,83]:u+=['RGB channel-to-pin functions remain UNKNOWN; CCW pin numbering is geometric only. The general two-terminal cathode rule does not assign RGB channel functions.']
            if n==84:
                p['functions']=['VDD','DOUT','VSS','DIN']
                conflict('WS2812B_LENGTH','Keep default 5 x 5 x 1.6; Worldsemi V5 5 x 5.4 x 1.57 is an explicit unresolved alternative.')
                conflict('WS2812B_PIN1_FUNCTION','Entry pin1 is VDD at top-left, not an LED cathode. Preserve VDD/DOUT/VSS/DIN and list this exception to the generic LED rule.')
                u+=['WS2812B pin1/chamfer top-left is KiCad convention, not confirmed manufacturer corner; 5.0 vs 5.4 and lead dimensions remain provisional.']
        elif n in [85,86]:
            p.update(kind='led_power' if n==85 else 'led_star',body_x=3.45 if n==85 else d['across_flats']*2/(3**.5),body_y=3.45 if n==85 else d['across_flats'],body_h=d['overall_height'],base_h=.85,lens_radius=1.53,lens_h=1.15,phosphor_size=1.8,lens='clear',led_color='#F8DC55',lens_opacity=.78,clear_opacity=.3,foot=.55,lead_width=2.0,thermal_size=[1.8,2.8],marker_size=.25)
            u+=['Emitter total height 2.0 vs 2.45, underside pad sizes, phosphor and cathode marker placement remain provisional.']
            if n==85:conflict('POWER_LED_SPHERICAL_CAP','Use sourced R1.53 and h1.15; derived diameter 2.96358 differs from rounded YAML 2.96, retained as rounding.',rounded_diameter_mm=2.96)
            else:
                p.update(board_thickness=d['board_thickness'],across_flats=d['across_flats'],wire_pad_size=[2.0,2.5],wire_pad_xy=[[-8,3],[-8,-3],[8,-3],[8,3]],emitter_profile='OHM-085')
                conflict('STAR_HEX_DIAMETER','Use second-pass regular hex 20 mm across flats. Across vertices is 23.094, so cannot also be 20 mm overall diameter.',source_diameter_mm=20,across_flats_mm=20)
                conflict('STAR_UNRESOLVED_PIN1','Raw pin1=[0,0] is an unresolved placeholder under the emitter. Visual-only wire-pad centers are explicit provisional data at +/-8,+/-3, pin1 cathode at -X per requested polarity. No footprint binding.')
                u+=['Star wire-pad sizes/positions are illustrative, not source geometry. Hole spacing 17.5 lacks diameter/coordinates; optic/mounting holes and vendor lobes omitted. Hex default has no invented holes.']
        if p['kind'] is None:raise ValueError(r['id'])
        r['profile_id']=r['id'];r['library_metadata']=library_metadata(r,u,provisional_reasons=u,conflicts=c);profiles[r['id']]=p;records.append(r)
    if len(records)!=32:raise ValueError('Expected 32 entries')
    return {'schema_version':1,'stage':5,'source_spec_sha256':hashlib.sha256(source).hexdigest(),'profiles':profiles,'components':sorted(records,key=lambda r:r['id'])}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    data=extract((ROOT/'PCB_COMPONENT_3D_LIBRARY_SPEC.md').read_bytes());p=ROOT/'apps/web/component-library/data/led-passive.json';value=json.dumps(data,indent=2,ensure_ascii=False)+'\n'
    if args.check:
        if p.read_text(encoding='utf-8')!=value:raise SystemExit('Imported data differs')
    else:p.write_text(value,encoding='utf-8')
    print(f"32 Stage 5 records {'checked' if args.check else 'written'}")


if __name__=='__main__':main()
