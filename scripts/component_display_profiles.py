"""Group E defaults, with display orientation and module FCO kept explicit."""


def group_e(r,d,cosmetic):
    n=int(r['id'][4:]);t=r['terminals'];pcb=r['pcb_interface']
    p={'kind':'display_passive','layout':'explicit','family':r['package_family'],'width':d.get('overall_width',d.get('diameter')),
       'length':d.get('overall_length',d.get('diameter')),'height':d.get('overall_height',d.get('overall_thickness')),
       'body_material':r['body']['material'],'lead_material':t['material'],'count':t['count'],'tail':2.6,
       'source_pin1':t['pin1_xy_mm'],'source_parameters':r.get('parametric',{}).get('parameters',[]),
       'offset':pcb['body_offset_mm'],'standoff':pcb['standoff_mm'],'mounts':pcb.get('mounting_holes',[]),
       'segments':{'LOD0':12,'LOD1':32,'LOD2':64},'contacts':[]}
    conflicts=[]
    def conflict(code,choice):conflicts.append({'code':code,'geometry_choice':choice})
    def contacts(coords,size,kind='tht'):
        p['contacts']=[{'terminal':str(i+1),'center_mm':[*xy,0],'size':size,'type':kind} for i,xy in enumerate(coords)]
    if n==15:
        p.update(shape='shunt',width=d['overall_length'],length=d['overall_width'],element=d['element_length'],bolt_diameter=d['hole_diameter'],tail=3)
        contacts([[-30,0],[30,0],[-4.5,0],[4.5,0]],[1,1]);p['contacts'][0]['type']=p['contacts'][1]['type']='bolt'
        conflict('SHUNT_BLOCK_LENGTH','Use element A=15.62 and overall85, deriving each copper block34.69. Prose33.7 uses B=17.65; no gap or overlap introduced. Sense positions remain stated uncertain +/-4.5, not manufacturer-verified.')
    elif n==16:
        p.update(shape='sip',N=8,pitch=2.54,tail=2.29)
        contacts([[0,8.89-i*2.54] for i in range(8)],[.3,.3])
        cosmetic(p,'mark_height_fraction',.65,'Front-face pin1 dot at 65 percent of body height, within sourced envelope.')
    elif n==17:
        p.update(shape='array',pitch=.8,terminal_length=.65,terminal_width=.3)
        contacts([[-.475,1.2-i*.8] for i in range(4)]+[[.475,-1.2+i*.8] for i in range(4)],[.65,.3],'smd')
    elif n in [18,19]:
        p.update(shape='trimmer',screw=[1.15,3.495,2.19] if n==18 else [0,0,3.2],slot=[2.19,.56,.76] if n==18 else [2.45,.51,p['height']/10],tail=3.81 if n==18 else 0)
        contacts([[0,2.54],[0,0],[0,-2.54]] if n==18 else [[1.15,2.75],[0,-2.75],[-1.15,2.75]],[.51,.51] if n==18 else [1.3,1.3],'tht' if n==18 else 'smd')
        if n==19:p['contacts'][1]['size']=[2,1.3]
        cosmetic(p,'rotor_depth',min(p['height']/5,p['screw'][2]/3),'Recess within upper fifth of housing, limited by rotor diameter/3.')
        if n==19:cosmetic(p,'slot_depth',p['slot'][2],'One tenth housing height; inward rotor slot only.')
    elif n==20:
        p.update(shape='rotary',bushing=d['bushing_diameter'],bushing_length=d['bushing_length'],shaft=d['shaft_diameter'],shaft_length=d['shaft_length'])
        contacts([[0,5],[0,0],[0,-5]],[1,1]);conflict('ROTARY_SHAFT_CLEARANCE','Stated shaft6 and bushing7 yield equality in diameter <= bushing-1, while coupled prose says strict <; keep explicit defaults unchanged.')
    elif n in [87,88,89,90]:
        p.update(shape='matrix' if n==90 else 'sevenseg',width=d['overall_length'],length=d['overall_width'],pitch=2.54,row_spacing=d['row_spacing'])
        half=p['count']//2;x=d['row_spacing']/2;y=(half-1)*p['pitch']/2
        contacts([[-x,y-i*p['pitch']] for i in range(half)]+[[x,-y+i*p['pitch']] for i in range(half)],[.5,.25])
        if n==90:p.update(dot_pitch=d['dot_pitch'],dot_diameter=d['dot_diameter'])
        else:p.update(digits={87:1,88:2,89:4}[n],digit_height=d['digit_height'],stroke=.14,digit_width=.62,dp_diameter=.15)
        cosmetic(p,'face_depth',.1,'Entry approximate 0.1 recess; plate partition within sourced body height.')
        if n!=90:cosmetic(p,'digit_layout',{'horizontal_bias':-.06,'dp_x':.38,'dp_y':-.43,'bar_y':.43,'vertical_x':.24,'vertical_y':.215,'bar_length':.48,'vertical_length':.32},'Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face.')
    else:
        p.update(shape='lcd' if n==91 else 'oled',width=d['overall_length'],length=d['overall_width'],pcb_thickness=d['pcb_thickness'],active=d['active_area'],mating=[0,0,1],header_hole=1.,header_pad=1.8)
        contacts([[-19.05+i*2.54,15.5] for i in range(16)] if n==91 else [[-3.81+i*2.54,-12] for i in range(4)],[.64,.64])
        if n==91:
            p.update(view=d['view_area'],stack=[71,25],bezel=[70,26],character=[2.95,5.55],character_pitch=[3.55,5.95],dot=[.55,.65],dot_pitch=[.6,.7],mount_pad=5.)
            cosmetic(p,'bezel_stock',p['height']/40,'Inward bezel stock one fortieth total height, top remains13.2.')
            cosmetic(p,'polarizer_inset',p['height']/100,'Polarizer recessed one hundredth total height below bezel.')
            conflict('LCD_BEZEL_STACK','Use explicit70x26 bezel and71x25 stack; coupled strict bezel<70x26 conflicts with explicit default. Header centered X remains stated provisional; no vendor pin offset inferred.')
        else:
            p.update(panel=d['panel_size'],spacer=1.25,header=[10.16,2.54,2.5])
            conflict('OLED_FCO_COORDINATES','Keep explicit YAML header Y=-12, hole centersY=+/-11.5 and body_offsetY=+0.25 without moving pins/holes. Center-based bbox of stated coordinates is Y=-0.25; source claims these form centered FCO. Remains provisional; no silent +0.25 correction to contacts.')
            conflict('OLED_HEADER_ENVELOPE','Stated header Y=-12 and depth2.54 reaches -13.27; PCB with stated offset+0.25 reaches -13.25. Keep both dimensions; assembled outline is27.02 alongY, not silently trimmed to27.')
        cosmetic(p,'pcb_color','#2F4F3A' if n==91 else '#1E5AA8','Section7 FR4 color is variable; borrow supplied BGA substrate green / supplied plastic blue hue, keeping FR4 roughness0.5. Appearance default only.')
    cosmetic(p,'pad_stock',min(p['height']/20,.15),'Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.')
    cosmetic(p,'mark_diameter',min(p['width'],p['length'])/15,'Optional pin1 dot one fifteenth smaller body dimension, within face.')
    return p,conflicts
