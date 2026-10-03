"""Magnetic defaults; numbers are entry transcriptions or tagged cosmetic derivations."""


def group_d(r,d,cosmetic):
    n=int(r['id'][4:]);t=r['terminals'];p={'kind':'magnetic','layout':'explicit','family':r['package_family'],
        'width':d['body_length'],'length':d['body_width'],'height':d['overall_height'],'standoff':d['standoff'],
        'body_material':r['body']['material'],'lead_material':t['material'],'count':t['count'],'pitch':t['pitch_mm'],
        'source_parameters':[],'source_pin1':t['pin1_xy_mm'],'tail':2.5 if n==51 else 2.6,'tht':r['mounting']=='tht',
        'segments':{'LOD0':12,'LOD1':32,'LOD2':64},'contacts':[],'shape':'box'}
    conflicts=[]
    def conflict(code,choice):conflicts.append({'code':code,'geometry_choice':choice})
    coords=[]
    if n in [44,45,46,48,49,54]:coords=[[(i-(p['count']-1)/2)*p['pitch'],0] for i in range(p['count'])]
    else:
        x,y=(3.81,3.11) if n==50 else (5,2.25) if n==51 else (5.335,4.75) if n==52 else (14.62,6.25) if n==53 else (5.08,4.445)
        half=p['count']//2;coords=[[-x,y-i*p['pitch']] for i in range(half)]+[[x,-y+i*p['pitch']] for i in range(half)]
    pin={44:[.38,1.12],45:[2.5,2.5],46:[2,2],48:[.65,.65],49:[.8636,.8636],50:[1.25,1.25],51:[.8,.8],52:[.9525,.508],54:[.66,.45],55:[.6,.3]}.get(n)
    if n==53:
        pin=[p['pitch']/5]*2
        cosmetic(p,'visual_pin_diameter',pin[0],'One fifth of stated provisional 2.5 mm pitch, visual stock only; no hole diameter or footprint claim. Within body XY envelope.')
        conflict('FLYBACK_PIN1_DERIVATION','Raw pin1_xy_mm remains RESEARCH_REQUIRED. Apply Section 17.4 long-side-terminal / Section 6 dual-row convention to stated candidate row spacing 29.24 and pitch 2.5: pin1=(-14.62,+6.25), CCW, 6 per side. Entire placement remains provisional, not manufacturer-verified.')
    if n in [46,50,55]:cosmetic(p,'visual_terminal_size',pin,'Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim.')
    p['contacts']=[{'terminal':str(i+1),'center_mm':[*xy,0],'size':pin,'type':'tht' if p['tht'] else 'smd'} for i,xy in enumerate(coords)]
    p['round_pin']=n in [48,49,51,53]
    p['mark_pin1']=n in [44,50,51,52,53,54,55]
    if n==44:p.update(shape='chip',band=.38,cap_stock=.03)
    if n==45:
        p['chamfer']=.2
        conflict('POWER_INDUCTOR_TERMINALS','Keep 7.3 x 6.7 x 2.8 body; bottom contact plates 2.5 long centered +/-2.95 span 8.4, beyond body. Procedure 1.0 underfold and second-pass 1.8 terminal callout are unresolved.')
    if n==46:
        p['shape']='drum';cosmetic(p,'flange_height',p['height']/6,'Each flange occupies one sixth sourced height.')
        cosmetic(p,'barrel_diameter',p['width']*.65,'65 percent sourced flange diameter, inside envelope.')
        cosmetic(p,'winding_diameter',p['width']*.85,'85 percent flange diameter, inside sourced cylinder.')
        conflict('DRUM_PAD_SPAN','Stated provisional centers +/-2.5 and visual 2 mm terminals span 7 mm, beyond 5.8 mm drum diameter. Keep stated centers, report metal overhang.')
    if n==48:p['shape']='cylinder';cosmetic(p,'dome_height',p['height']/20,'Shallow rounded cap inside final 12 mm height, one twentieth height.')
    if n==49:
        p.update(shape='toroid',inner_diameter=12)
        conflict('TOROID_INNER_DIAMETER','Use stated 12.0 mm ID default (rounded 0.55*21.84=12.012); OD21.84/body thickness11.43, add stated1.57 standoff. Leads +/-4.064 lie inside aperture; render stated straight-down exit default without inventing unsourced attachment routes.')
    if n==51:conflict('CMC_AXES','Use YAML body X15.8/Y7.8/H18 and explicit10x4.5 pin rectangle; 10/18 drawing labels remain unresolved.')
    if n==52:conflict('SIGNAL_PIN_STOCK','Use stated 0.0375x0.020 inch rectangular stock (0.9525x0.508); alternate .042 square and 1.5 mounting-hole positions remain unresolved; no unknown mounting holes created.')
    if n==53:
        p['shape']='ee'
        cosmetic(p,'bobbin_base',p['height']/8,'Lower eighth of sourced height; full sourced plan envelope.')
        cosmetic(p,'flange_stock',p['width']/20,'One twentieth sourced X envelope; two inner flanges, do not move pin rows.')
        cosmetic(p,'core_width',p['width']*.75,'75 percent X envelope, bounded by bobbin flanges; no EFD core datasheet dimension asserted.')
        cosmetic(p,'core_length',p['length']*.9,'90 percent Y envelope, inside sourced envelope.')
        cosmetic(p,'core_stock',p['height']/5,'Core rails and center leg stock one fifth overall height.')
        cosmetic(p,'tape_width',p['length']*.45,'Tape winding band 45 percent body Y span, inside core window.')
    if n==54:conflict('CT_BODY_AND_HOLE','Use stated default17.2x9.53x20.4 and 3 rectangular0.66x0.45 pins. Alternate dimensions and PCB YAML1.4 vs prose1.0 hole remain uncertain; hole metadata never drives pin size.')
    if n==55:conflict('LAN_WIDTH_HEIGHT','Keep first-pass body X9.53/Y12.7/H6.8 and explicit10.16 contact-row spacing; alternate6.80 width/6.09 height not silently substituted.')
    cosmetic(p,'pad_stock',min(p['height']/20,.2),'Metal visual stock one twentieth height capped0.2, contact plane unchanged.')
    cosmetic(p,'marker_diameter',.2 if n==44 else min(p['width'],p['length'])/15,'OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.')
    cosmetic(p,'winding_turns',8,'Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.')
    cosmetic(p,'label_size',[p['width']*.5,p['length']*.25],'Optional separate label decal occupies half X and quarter Y of top face.')
    return p,conflicts
