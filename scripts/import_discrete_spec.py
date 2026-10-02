"""Authoring-only diode/power import; PyYAML 6.0.3. Raw spec remains intact."""
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

IDS = [f"OHM-{n:03}" for n in [*range(56, 70), 71, 72, 93, *range(95, 103)]]
ALIASES = {"OHM-067":"OHM-061", "OHM-068":"OHM-061", "OHM-069":"OHM-065"}


def extract(source):
    text=source.decode("utf-8"); records=[]; profiles={}
    for m in re.finditer(r"^# \[(OHM-\d+)\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)",text,re.MULTILINE|re.DOTALL):
        if m[1] not in IDS:continue
        raw=re.search(r"```yaml\s*\n(.*?)\n```",m[0],re.DOTALL)[1];r=yaml.safe_load(raw)
        sections=dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)",m[0],re.MULTILINE|re.DOTALL))
        r['source']={'document':'PCB_COMPONENT_3D_LIBRARY_SPEC.md','line':text[:m.start()].count('\n')+1,'yaml_sha256':hashlib.sha256(raw.encode()).hexdigest(),'sections':{k:v.strip() for k,v in sections.items() if k!='Structured Specification'},'evidence_level':'SPEC_REPORTED; cited sources not independently reverified'}
        d={k:v['default'] for k,v in r['dimensions_mm'].items()};n=int(r['id'][4:]);t=r['terminals']
        u=[f"{k}: {v['default']} mm ({v['basis']}/{v['confidence']})" for k,v in r['dimensions_mm'].items() if v['basis']=='UNCERTAIN' or v['confidence']=='L'];conf=[]
        p={'standoff':r['pcb_interface']['standoff_mm'],'tail':t.get('tail_below_board_top_mm',0),'lead_width':t.get('width_mm'),'lead_thickness':t.get('thickness_mm'),'source_pin1':t['pin1_xy_mm'],'source_lead_count':t['count'],'body_material':r['body']['material'],'lead_material':t['material'],'body_offset':[0,0],'segments':{'LOD0':12,'LOD1':16,'LOD2':32},'band_material':'MAT_DIODE_BAND_SILVER','band_width':0,'mark_scale':0.45,'bevel':0,'basis':'Entry YAML plus explicitly transcribed narrative geometry; cosmetic/uncertain choices listed in metadata.'}
        if n in range(56,59):
            p.update(kind='axial',body_x=d['body_length'],body_y=d['body_diameter'],height=d['body_diameter'],diameter=d['body_diameter'],pitch=d['lead_pitch'],lead_diameter=d['lead_diameter'],bend_radius=1.5*d['lead_diameter'],band_width=[.6,.9,1.5][n-56],band_material='MAT_DIODE_BAND_BLACK' if n==56 else 'MAT_DIODE_BAND_SILVER')
            u+=['Cathode band width and bend radius are OHMNI defaults; hole pitch and tail truncation are mounting choices.']
        elif n in [59,60]:
            p.update(kind='melf',body_x=d['overall_length'],body_y=d['overall_height'],height=d['overall_height'],diameter=d['body_diameter'],cap_diameter=d['overall_height'],cap_length=d['end_cap_length'],band_width=.35 if n==59 else .5,band_material='MAT_DIODE_BAND_BLACK')
            u+=['Band width/color and cap/body diameter assignment are inferred; glass/plastic appearance varies by manufacturer.']
        elif n in range(61,67):
            p.update(kind='sod' if n<64 else 'smx',body_x=d['body_length'],body_y=d['body_width'],height=d['body_height']+p['standoff'],body_height=d['body_height'],span=d['lead_span'],foot=d['foot_length'],exit_height=[.45,.4,.25,.85,.85,.9][n-61],band_width=[.35,.25,.15,.9,1,1.4][n-61])
            u+=['Lead exit height, band position/width and folded profile bend details are OHMNI defaults.']
            conf.append({'code':'BODY_HEIGHT_VS_SEATED_HEIGHT','rendered_mm':round(p['height'],5),'yaml_body_height_mm':d['body_height'],'policy':'Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values.'})
            if n<64:
                conf.append({'code':'FOOT_EXCEEDS_EXTERNAL_LEAD_RUN','external_run_mm':round((p['span']-p['body_x'])/2,5),'foot_mm':p['foot'],'policy':'Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults.'})
            else:u+=['Polarity-side body chamfer/step is RESEARCH_REQUIRED and deliberately omitted; cathode band only.']
            if n==63:u+=['SOD523 0.30 mm extracted lead thickness is unresolved; use the entry 0.12 mm default.']
        elif n in [67,68,69]:
            p=None
            if n==69:conf.append({'code':'TVS_PIN1_VS_PACKAGE','entry_pin1_x_mm':-2.425,'package_pin1_x_mm':-2.15,'policy':'User requires identical SMB package geometry; use OHM-065 contacts. Preserve raw TVS YAML and narrative unmodified.'})
        elif n in [71,72]:
            p.update(kind='bridge_dip' if n==71 else 'bridge_round',body_x=d.get('body_width',d.get('diameter')),body_y=d.get('body_length',d.get('diameter')),height=p['standoff']+d['body_height'],body_height=d['body_height'],pitch=d.get('pitch',d.get('lead_square_pitch')),row_spacing=d.get('row_spacing',d.get('lead_square_pitch')),lead_diameter=d['lead_diameter'],segments={'LOD0':12,'LOD1':24,'LOD2':48})
            u+=['Pin-to-function map RESEARCH_REQUIRED. Printed + near pin1 is only the spec visual placeholder; remaining function symbols have no positional pin assignment.','Standoff and round/flat lead form, pin1 bevel and manufacturer marking positions remain uncertain.']
            if n==71:
                p.update(exit_height=p['standoff']+.5*d['lead_diameter'],bend_radius=.5)
                conf.append({'code':'BRIDGE_TAIL_CONVENTION','modeled_bottom_z_mm':-p['tail'],'stock_length_below_body_mm':d['lead_length_below_body'],'stock_implied_bottom_z_mm':p['standoff']-d['lead_length_below_body'],'policy':'Use explicit installed tail Z=-2.6. Source prose calls 4.25-standoff-1.6 the below-board tail, mixing board-top and board-bottom conventions.'})
        elif n==93:
            p.update(kind='to92',body_x=d['body_width'],body_y=d['body_thickness'],height=p['standoff']+d['body_height'],body_height=d['body_height'],pitch=d['lead_spacing'],bevel=.08)
            u+=['Lead row/body offset, dome radius and cosmetic top bevel are inferred. Kinked/formed lead geometry is not sufficiently sourced and is not enabled.']
            conf.append({'code':'TO92_LEAD_TYPE_TEXT','policy':'Raw YAML says round_lead; narrative explicitly specifies 0.45 x 0.40 rectangular ribbon. Use narrative cross-section.'})
        elif n in [95,96]:
            p.update(kind='sot89' if n==95 else 'sot223',body_x=d['overall_length'],body_y=d['overall_width'],height=d['overall_height'],pitch=d['pitch'],span=d['lead_tip_span'],foot=t['length_mm'],tab_width=d['tab_width'],center_lead_width=.52 if n==95 else d['lead_width'],contact_y=abs(t['pin1_xy_mm'][1]),exit_height=d['overall_height']/2,bevel=.05)
            u+=['Body chamfer/radii and lead/tab exit height are cosmetic defaults; SOT89 center-lead width assignment remains uncertain.' if n==95 else 'Body chamfer/radii and lead exit height are cosmetic defaults.']
            conf.append({'code':'CONTACT_REFERENCE_VS_FOOT_CENTER','source_abs_y_mm':p['contact_y'],'geometric_abs_y_mm':round((p['span']-p['foot'])/2,5),'policy':'Preserve source contact reference and specified span/foot separately; reference lies on actual foot.'})
            if n==95:conf.append({'code':'FOOT_EXCEEDS_EXTERNAL_LEAD_RUN','external_run_mm':round((p['span']-p['body_y'])/2,5),'foot_mm':p['foot'],'policy':'Fold under body per flat-pad/tab narrative; no silent shortening of foot.'})
        elif n in [97,98,99]:
            p.update(kind='to126' if n==97 else 'to220' if n==98 else 'to247',body_x=d.get('body_width',d.get('overall_width')),body_y=d.get('body_thickness',d.get('overall_thickness')),height=d.get('body_height',d.get('overall_height')),pitch=d['pitch'],hole_diameter=d['hole_diameter'],hole_from_top=d.get('hole_center_from_top',d.get('hole_center_below_tab_top')),tab_thickness=d.get('plate_thickness',d.get('tab_thickness')),shoulder_width=1.32 if n==97 else d.get('shoulder_width',2),shoulder_length=1 if n==97 else d.get('shoulder_length',4.2),bevel=.08,tab_material='MAT_NICKEL',hole=True,dish_diameter=d.get('hole_dish_diameter',0),dish_depth=.5 if n==99 else 0,tab_exposed_from=4.4 if n==99 else 0)
            p['plastic_height']=p['height']-(d.get('tab_protrusion',2.6 if n==99 else 0))
            p['tab_width']=14 if n==99 else p['body_x'];p['back_y']=2.41 if n==99 else p['body_y']/2 if n==97 else (p['body_y']-p['tab_thickness'])/2+p['tab_thickness'];p['front_y']=p['back_y']-p['body_y'];p['body_offset']=[0,(p['back_y']+p['front_y'])/2]
            u+=['Hole position, plate/plastic split, tab contour and lead shoulder details are inferred; tab holes are body features excluded from FCO.']
            if n in [98,99]:conf.append({'code':'SHOULDER_LONGER_THAN_TRIMMED_TAIL','shoulder_length_mm':p['shoulder_length'],'available_at_default_standoff_mm':p['tail'],'policy':'Truncate at requested Z=-2.6 without shortening the shoulder. At default zero standoff no narrower tail remains visible at LOD1/2.'})
            if n==97:u+=['Shoulder length 1.0 mm is an unsourced visual default (width 1.32 from entry); optional chamfers omitted.']
            if n==99:
                p['outline']='AD';p['outlines']={'AD':{},'AC':{'body_x':15.7,'body_y':4.95,'height':20.5,'hole_from_top':5.5,'tab_thickness':1.27,'lead_thickness':.5,'shoulder_length':4.06,'plastic_height':17.9,'front_y':-2.54,'back_y':2.41,'body_offset':[0,-.065]}}
                u+=['TO247 dish depth 0.5 mm is cosmetic; plastic top 2.6 below tab top and exposed back start 4.4 are provisional.']
                conf+=[{'code':'TO247_PLASTIC_THICKNESS_ARITHMETIC','narrative_mm':3.03,'coordinate_difference_mm':3.02,'policy':'Explicit y=-2.61..0.41 wins over rounded 3.03 text.'},{'code':'TO247_DISH_TOP_INTERSECTION','dish_top_mm':18.38,'plastic_top_mm':18.35,'policy':'Preserve numeric defaults; front dish opens through plastic top by 0.03 mm rather than moving/resizing it.'}]
        elif n in [100,101]:
            p.update(kind='dpak' if n==100 else 'd2pak',body_x=d['overall_width'],body_y=d.get('plastic_length',d.get('overall_length')),height=d['overall_height'],span=d['lead_tip_span'],pitch=d['pitch'],foot=t['length_mm'],tab_thickness=d['tab_thickness'],tab_width=d.get('tab_width_tip',d['overall_width']),tab_extension=d['tab_extension'],exit_height=1.2 if n==100 else 2.2,contact_y=abs(t['pin1_xy_mm'][1]),tab_contact_y=2.5 if n==100 else 3.3,stub_length=0,stub_max=1.02 if n==100 else 0,bevel=0)
            p['body_offset']=[0,p['span']/2-p['tab_extension']-p['body_y']/2]
            p.update(ep_x=5.21 if n==100 else 6.86,ep_y=4.32 if n==100 else 6.22)
            u+=['Tab extension/symbol assignment, unsourced taper and cropped-lead stub remain uncertain. Tab is embedded at Z=0, not stacked beneath the plastic.']
            u+=['Exposed underside uses the family minimum thermal contour centered under plastic; its exact contour placement is an OHMNI visual default. Hidden internal tab metal is omitted.']
            conf.append({'code':'SOURCE_COUNT_EXCLUDES_TAB','source_lead_count':2,'modeled_distinct_terminals':3,'policy':'Raw source count means two formed leads (1,3); expose tab as terminal 2 with alias 4 separately, giving three physical terminals.'})
            conf.append({'code':'TAB_SOLID_VS_EXPOSED_CONTOUR','policy':'Procedure describes full internal plate extent; geometry shows the specified minimum exposed contour under the plastic plus projecting tab. Hidden internal metal is omitted, not exposed across the entire belly. Contour placement remains provisional.'})
            if n==100:conf.append({'code':'CONTACT_REFERENCE_VS_FOOT_CENTER','source_abs_y_mm':4.1,'geometric_abs_y_mm':4.16,'policy':'Preserve pin1 reference -4.1 and actual foot center -4.16; no footprint fit claimed.'})
            else:conf.append({'code':'D2PAK_SOURCE_OUTLINE_CONFLICT','policy':'Use second-pass plastic 9.0 + tab extension 1.5 = 10.5, versus Nexperia 11 mm title; keep corrected A1=0.1 and embedded tab.'})
        elif n==102:
            p.update(kind='powerpak',body_x=d['body_width'],body_y=d['body_length'],height=d['overall_height'],span=d['overall_width'],pitch=d['pitch'],foot=t['length_mm'],ep_x=d['pad_width'],ep_y=d['pad_length'],bevel=0)
            p.update(marker_diameter=.35,marker_inset=.5)
            u+=['A1 standoff extraction remains scrambled; unmapped end frame and dual-pad outline omitted.']
            conf += [{'code':'POWERPAK_UNMODELED_END_FRAME','source_y_mm':d['overall_length'],'modeled_y_mm':p['body_y'],'policy':'Use explicit Vishay molded-body Y=4.90; unexplained D=5.15 end frame remains unmodeled, not silently invented.'},{'code':'POWERPAK_HEIGHT_LANGUAGE','source_A_mm':p['height'],'standoff_mm':p['standoff'],'policy':'A=1.04 is seating-plane-to-top; plastic Z=.05..1.04. Procedure phrase height 1.04 from standoff would incorrectly yield 1.09.'}]
        r['profile_id']=ALIASES.get(r['id'],r['id']);r['geometry_source_id']=r['profile_id'];r['library_metadata']=library_metadata(r,u,provisional_reasons=u,conflicts=conf)
        if n in [67,68,69]:
            r['package_options']=({'SOD123':'OHM-061','SOD323':'OHM-062','SMA':'OHM-064','SMB':'OHM-065','DO-41':'OHM-057','DO-201AD':'OHM-058'} if n==67 else {'SOD123':'OHM-061','SOD323':'OHM-062','DO-35':'OHM-056','DO-41':'OHM-057','MiniMELF':'OHM-059'} if n==68 else {'SMA':'OHM-064','SMB':'OHM-065','SMC':'OHM-066'})
        if p:profiles[r['id']]=p
        records.append(r)
    byid={r['id']:r for r in records}
    for id,base in ALIASES.items():
        r=byid[id];b=byid[base];r['library_metadata']['uncertain_values']+=b['library_metadata']['uncertain_values'];r['library_metadata']['provisional']=b['library_metadata']['provisional'];r['library_metadata']['conflicts']+=b['library_metadata']['conflicts'];r['appearance_overrides']={'lead_material':r['terminals']['material']}
    assert [r['id'] for r in records]==IDS
    return {'schema_version':1,'stage':4,'source_spec_sha256':hashlib.sha256(source).hexdigest(),'profiles':profiles,'components':records}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    encoded=json.dumps(extract((ROOT/'PCB_COMPONENT_3D_LIBRARY_SPEC.md').read_bytes()),indent=2,ensure_ascii=False)+'\n';target=ROOT/'apps/web/component-library/data/discrete.json'
    if args.check:
        if target.read_text(encoding='utf-8')!=encoded:raise SystemExit('Stage 4 data is stale')
    else:target.write_text(encoded,encoding='utf-8',newline='\n')
    print(f"25 Stage 4 records {'checked' if args.check else 'imported'}; 22 package profiles")


if __name__=='__main__':main()
