"""Authoring import for the approved completion groups; preserve raw source status."""
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
from component_io_profiles import group_c
from component_magnetic_profiles import group_d
from component_spec_metadata import library_metadata

GROUPS = {'A': list(range(150, 162)), 'B': list(range(141, 150)),
          'C': list(range(162, 181)), 'D': [44, 45, 46, *range(48, 56)],
          'E': [*range(15, 21), *range(87, 93)]}


def cosmetic(p, feature, value, derivation):
    p[feature] = value
    p.setdefault('cosmetic_defaults', []).append({'feature': feature, 'value': value,
        'tag': 'COSMETIC_PROVISIONAL', 'derivation': derivation,
        'reason': 'Noncritical appearance; does not alter contact coordinates, mating or outer envelope.'})


def group_a(r, d):
    n = int(r['id'][4:]); t = r['terminals']
    p = {'family': r['package_family'], 'count': t['count'], 'rows': 2 if n in [151,153] else 1,
             'pitch': t['pitch_mm'], 'pin': t['width_mm'], 'tail': t.get('tail_below_board_top_mm',0),
             'body_material': r['body']['material'], 'lead_material': t['material'],
             'offset': r['pcb_interface']['body_offset_mm'], 'source_pin1': t['pin1_xy_mm'],
             'segments': {'LOD0':12,'LOD1':24,'LOD2':48}, 'mating': [0,0,1],
             'source_parameters': r['parametric']['parameters']}
    conflicts=[]
    def conflict(code, choice): conflicts.append({'code':code,'geometry_choice':choice})
    if n<=154:
        p.update(kind='header',socket=n in [152,153],right_angle=n==154,
                 width=d.get('base_width',d.get('body_width',d.get('base_depth_x'))),
                 height=d.get('base_height',d.get('body_height')),end_allowance=.4 if n in [152,153] else 0,
                 above=d.get('pin_above_base',d.get('mating_length_beyond_base',0)),
                 tip=.25,base_chamfer=.2,opening=1.,opening_chamfer=.25,shallow_depth=1.,deep_depth=6.35,
                 rear_offset=d.get('rear_offset_tail_to_body',0),bend_radius=.3,n_range=[1,40])
        if n==154:p['mating']=[1,0,0]
        if n in [152,153]:conflict('SOCKET_LENGTH_RULE','Use second-pass N*pitch+0.4; older variant prose omits the end allowance.')
    elif n in [155,156]:
        p.update(kind='wire',width=d['housing_depth'],height=d['overall_height'],length_extra=d['housing_length_B']-(t['count']-1)*p['pitch'],wall=d['wall_thickness'],floor=1.,post_above=3.3 if n==155 else 3.4,n_range=[2,16],key_style='ph' if n==155 else 'xh',slot_depth=2. if n==155 else None,slot_width=1. if n==155 else 1.5,end_slot=1.3 if n==155 else None,rib=[.2,.5] if n==155 else None)
        if n==156:
            conflict('XH_WINDOW_SIDE','Entry Geometry +X wins over family -X description.')
            cosmetic(p,'slot_depth',2.,'Borrow OHM-155 PH slot depth; remains inside 7 mm XH body.')
    elif n==157:
        p.update(kind='sh',width=d['housing_depth'],height=d['overall_height'],length_extra=3.,
                 pad_length=d['pad_length'],pad_width=d['pad_width'],pad_thickness=.15,
                 tab_size=d['tab_pad'],tab_x=-1.875,tab_y_inset=.2,tab_strap=.2,
                 cavity_height=2.,cavity_length=4.2,cavity_depth=3.,floor=.4,mating=[-1,0,0],
                 pin_x=2.,n_range=[2,16],entry_direction='side',
                 top_variant={'width':2.9,'height':4.25,'offset':[.45,0],'pin_x':-1.325,'tab_x':1.2,'mating':[0,0,1]})
        conflict('SH_MATING_CONVENTION','Section 18.12 / entry -X supersedes general side-entry +Y; no mirror.')
        cosmetic(p,'end_wall',.9,'(6.0 mm default body length - 4.2 mm cavity)/2; fixed end allowance for N variants.')
        cosmetic(p,'top_wall',.5,'Borrow OHM-155 shroud wall; within BM04B 2.9 mm depth.')
    elif n==158:
        p.update(kind='kk',width=d['housing_depth'],height=d['overall_height'],length_extra=p['pitch'],
                 xmin=-2.88,xmax=2.92,wall_inner=-1.99,stub_thickness=.6,stub_width=1.6,
                 ramp_projection=.53,ramp_base=2.54,ramp_top=2.04,ramp_height=2.,post_top=9.,n_range=[2,40])
        cosmetic(p,'floor',d['overall_height']/6,'One sixth of the stated 6 mm housing height; connects walls without changing outer envelope.')
        cosmetic(p,'end_wall',.6,'Reuse the stated open-side stub thickness for end walls, inside row envelope.')
        cosmetic(p,'ramp_count',1,'One centered ramp retained for N variants; source gives one for N=2 and no N>2 rule.')
        conflict('KK_WALL_THICKNESS','Use explicit X=-2.88..-1.99 (0.89), rather than the rounded 1.0 wall prose.')
        conflict('KK_BODY_OFFSET','Use explicit outline -2.88..+2.92 (center +0.02); raw body_offset remains [0,0] as entry allows.')
        conflict('KK_STUB_POSITION','Entry +2.32..+2.92 wins over older family +2.43..+3.03.')
    elif n in [159,160]:
        p.update(kind='screw',width=d['overall_width'],height=d['overall_height'],length_extra=p['pitch'],
                 mating=[1,0,0],screw_diameter=3.,pocket_depth=1.,window_width=3.4,window_height=3.,window_z=5.,n_range=[2,12])
        conflict('SCREW_ENTRY_DIRECTION','Entry explicit +X wins over general Section 18 side-entry +Y.')
        conflict('SCREW_HEIGHT','Use adopted 13.8 above board with 3.5 tail; retain alternative 10.3 from ambiguous overall-height listings.')
    else:
        p.update(kind='plug',width=d['header_depth'],height=d['header_height'],length_extra=p['pitch']+2.,
                 plug_length=d['plug_length'],plug_height=d['plug_height'],plug_xmin=.7,plug_xmax=19.,
                 mating=[1,0,0],n_range=[2,10],header_orientation='right-angle',assembled=True,
                 screw_diameter=3.,header_rear=-3.,vertical={'width':8.6,'height':12.,'tail':3.9,'mating':[0,0,1]})
        cosmetic(p,'wall',.5,'Borrow OHM-155 0.5 mm shroud wall; keep header outer envelope fixed.')
        cosmetic(p,'internal_pin_z',d['header_height']/2,'Half of 8.6 mm header height; PCB pin axes unchanged.')
        cosmetic(p,'internal_pin_end',d['header_depth']-3.-.5,'Header front X=9.0 minus cosmetic wall; inside header.')
        cosmetic(p,'screw_x',(.7+19.)/2,'Center of specified plug X extent; Y positions follow pitch.')
        cosmetic(p,'pocket_depth',d['header_height']/8,'One eighth of header height, recessed into plug.')
        cosmetic(p,'window_width',t['pitch_mm']*2/3,'Two thirds of sourced contact pitch, centered on each row position.')
        cosmetic(p,'window_height',d['header_height']/3,'One third of header height, inside 15 mm plug.')
        cosmetic(p,'window_z',d['plug_height']/3,'One third of plug height; does not alter plug envelope.')
        cosmetic(p,'window_depth',d['header_depth']/4,'One quarter of header depth, recessed from plug +X face.')
        conflict('PLUG_INTERLOCK_UNKNOWN','Use stated overlapping assembly envelopes with explicit provisional internal features; exact mating interlock/coding remains unknown.')
        conflict('PLUG_VERTICAL_LOCATION','Vertical shroud envelope is sourced but tail/body offset and plug placement are unspecified. Default right-angle supported; vertical assembly parameter rejected until coordinates are supplied.')
    if p['kind'] in ['screw','plug']:
        if p['kind']=='screw':cosmetic(p,'window_depth',p['width']/3,'One third of stated housing depth; internal recess only.')
        cosmetic(p,'screw_head_height',p['pocket_depth']/2,'Half the pocket depth; head stays recessed.')
        cosmetic(p,'slot_width',p['screw_diameter']/8,'One eighth of specified/placeholder 3 mm head diameter.')
        cosmetic(p,'slot_length',p['screw_diameter']*.8,'80 percent of head diameter; slot stays inside head.')
    p['N']=p['count']//p['rows']
    return p, conflicts


def group_b(r, d):
    n=int(r['id'][4:]);t=r['terminals'];tht=r['mounting']=='tht'
    p={'kind':'frequency','family':r['package_family'],'body_x':d['overall_length'],'body_y':d['overall_width'],'height':d['overall_height'],
       'count':t['count'],'layout':'frequency','body_material':r['body']['material'],'lead_material':t['material'],
       'source_pin1':t['pin1_xy_mm'],'standoff':r['pcb_interface']['standoff_mm'],'tail':t.get('tail_below_board_top_mm',0),
       'tht':tht,'pin':t['width_mm'],'pitch':t.get('pitch_mm',0),'pad_x':t['width_mm'],'pad_y':t.get('length_mm',0),
       'source_parameters':r['parametric']['parameters'],'segments':{'LOD0':16,'LOD1':32,'LOD2':64},'pin1_corner':'TL'}
    conflicts=[]
    if tht:
        p['shape']='stadium' if n in [141,142] else 'resonator'
        cosmetic(p,'radius',p['body_y']/2 if n in [141,142] else .8,'HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry.')
        cosmetic(p,'seal_diameter',p['pin']*3,'Three times stated lead diameter, inside bottom plate.')
        cosmetic(p,'seam_width',p['body_y']/50,'One fiftieth of can width; surface seam inside top envelope.')
        cosmetic(p,'label_width',p['body_x']*.55,'55 percent of sourced body length; optional identity decal.')
        cosmetic(p,'label_height',min(p['body_y'],p['height'])/5,'One fifth of smaller face dimension.')
        if n in [141,142]:conflicts.append({'code':'SUPPLIED_VS_TRIMMED_LEAD','geometry_choice':'Keep explicit 2.6 mm mounted tail rather than as-supplied 12.7 mm minimum.'})
    else:
        p['shape']='smd';p['lid_material']='MAT_STEEL_STAINLESS' if n!=149 else 'MAT_EPOXY_DARKGRAY'
        cosmetic(p,'pad_thickness',t.get('thickness_mm',.02),'Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.')
        cosmetic(p,'base_fraction',.7 if n<=145 else .65,'Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.')
        cosmetic(p,'lid_inset',.1 if n<=145 else .15,'Entry lid inset; SAW borrows oscillator seam inset.')
        cosmetic(p,'marker_radius',min(p['body_x'],p['body_y'])/25,'One twenty-fifth of smaller body dimension; lid corner mark only.')
        cosmetic(p,'lid_chamfer',min(p['body_x'],p['body_y'])/10,'One tenth of smaller dimension, removes material at marked corner only.')
        cosmetic(p,'label_width',p['body_x']*.5,'Half of body length, inside lid.')
        cosmetic(p,'label_height',p['body_y']/5,'One fifth of body width, inside lid.')
        if n in [145,147]:conflicts.append({'code':'PROSE_HEIGHT_VS_YAML','geometry_choice':f'Use YAML overall height {p["height"]} mm; recompute stated fractional ceramic/lid split instead of older approximate prose heights.'})
        if n==146:conflicts.append({'code':'PAD_OVERHANG_005','geometry_choice':'Keep explicit contacts Y=+/-1.905 and pad Y size=1.2. Metal spans 5.01 mm vs ceramic body width 5.0; do not shorten pads or move terminals to enforce the contradictory pads-inside-body sentence.'})
    return p,conflicts


def extract(source, group):
    text=source.decode('utf-8');records=[];profiles={}
    for m in re.finditer(r'^# \[(OHM-(\d+))\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)',text,re.MULTILINE|re.DOTALL):
        if int(m[2]) not in GROUPS[group]:continue
        raw=re.search(r'```yaml\s*\n(.*?)\n```',m[0],re.DOTALL)[1];r=yaml.safe_load(raw)
        sections=dict(re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',m[0],re.MULTILINE|re.DOTALL))
        r['source']={'document':'PCB_COMPONENT_3D_LIBRARY_SPEC.md','line':text[:m.start()].count('\n')+1,'yaml_sha256':hashlib.sha256(raw.encode()).hexdigest(),'sections':{k:v.strip() for k,v in sections.items() if k!='Structured Specification'},'evidence_level':'SPEC_REPORTED; not independently reverified'}
        d={k:v['default'] for k,v in r['dimensions_mm'].items() if 'default' in v}
        p,conflicts={'C':group_c,'D':group_d}[group](r,d,cosmetic) if group in ['C','D'] else {'A':group_a,'B':group_b}[group](r,d)
        if p is None:raise ValueError('Group not yet implemented')
        uncertain=[f'{k}: {v.get("default",v)} ({v.get("basis")}/{v.get("confidence")})' for k,v in r['dimensions_mm'].items() if v.get('confidence')=='L' or v.get('basis') in ['UNCERTAIN','RECALLED_UNVERIFIED','RESEARCH_REQUIRED']]
        uncertain += [line.strip() for line in m[0].splitlines() if re.search(r'UNCERTAIN|RECALLED_UNVERIFIED|RESEARCH_REQUIRED|placeholder|not confirmed|not sourced|unsourced',line,re.IGNORECASE) and not line.startswith('  ')]
        uncertain += [sections.get('Research Confidence','').strip()]
        uncertain += [f"COSMETIC_PROVISIONAL {c['feature']}={c['value']}: {c['derivation']}" for c in p.get('cosmetic_defaults',[])]
        r['cosmetic_defaults']=p.get('cosmetic_defaults',[])
        r['library_metadata']=library_metadata(r,uncertain,provisional_reasons=['Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.'],conflicts=conflicts,implementation_status='IMPLEMENTED',implementation_group=group)
        r['profile_id']=r['id'];profiles[r['id']]=p;records.append(r)
    records.sort(key=lambda r:r['id'])
    return {'schema_version':1,'group':group,'source_spec_sha256':hashlib.sha256(source).hexdigest(),'components':records,'profiles':profiles}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--group',choices=GROUPS,required=True);parser.add_argument('--check',action='store_true');a=parser.parse_args()
    result=extract((ROOT/'PCB_COMPONENT_3D_LIBRARY_SPEC.md').read_bytes(),a.group)
    content=json.dumps(result,indent=2,ensure_ascii=False)+'\n';path=ROOT/f'apps/web/component-library/data/completion-{a.group.lower()}.json'
    if a.check:
        if not path.exists() or path.read_text(encoding='utf-8')!=content:raise SystemExit('Generated source records are stale')
    else:path.write_text(content,encoding='utf-8')
    print(f'{len(result["components"])} Group {a.group} records '+('checked' if a.check else 'written'))
