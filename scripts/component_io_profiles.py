"""Group C profiles transcribed from entry defaults, including explicit uncertainties."""


def group_c(r, d, cosmetic):
    n=int(r['id'][4:]);t=r['terminals'];pcb=r['pcb_interface']
    p={'kind': 'io','layout': 'explicit','family': r['package_family'],'count': t['count'],
           'width': d.get('overall_width',d.get('flange_square')),'length': d.get('overall_length',d.get('flange_square')),
           'height': d['overall_height'],'offset': pcb.get('body_offset_mm',[0,0]),
           'body_material': r.get('body',{}).get('material','MAT_PLASTIC_BLACK'),'lead_material': t.get('material','MAT_TIN_BRIGHT'),
           'source_pin1': t['pin1_xy_mm'],'source_parameters': r.get('parametric',{}).get('parameters',[]),
           'mating': [0,0,1] if n in [175,176] else [0,1,0],'tail': 2.6,'contacts': [],'mounts': [],
           'segments': {'LOD0':12,'LOD1':24,'LOD2':48}}
    conflicts=[]
    def conflict(code,choice):conflicts.append({'code': code,'geometry_choice': choice})
    def contacts(coords,size,kind='smd',names=None):
        for i,xy in enumerate(coords):p['contacts'].append({'terminal': names[i] if names else str(i+1),'center_mm': [*xy,0] if len(xy)==2 else xy,'size': size.copy(),'type': kind})
    def mount(x,y,sx,sy,kind='smd',z=0):p['mounts'].append({'center_mm': [x,y,z],'size': [sx,sy],'type': kind})
    if n in range(162,169):
        p.update(shape='shell',shell_material='MAT_NICKEL',profile='rect')
        if n==162:
            contacts([[x,-1.355] for x in [3.5,1,-1,-3.5]],[.5,.5],'tht')
            for x in [-6.57,6.57]:mount(x,1.355,2.3,2.3,'hole')
            p.update(cavity=[12.5,4.9,13.5],tongue=[12,1.9],tongue_side='lower')
        elif n==163:
            contacts([[-1.25,-2.43],[1.25,-2.43],[1.25,-.43],[-1.25,-.43]],[.5,.5],'tht')
            for x in [-6,6]:mount(x,2.43,2.3,2.3,'hole')
            p.update(profile='top-chamfer',chamfer=2,tongue_side='upper')
        elif n==164:
            contacts([[1.3-i*.65,-1.35] for i in range(5)],[.4,1.35])
            for x,s in [(-1,1.5),(1,1.5),(-2.9,1.2),(2.9,1.2)]:mount(x,1.35,s,1.55)
            for x in [-2.5,2.5]:mount(x,-1.35,.85,.55,'hole')
            for x in [-3.5,3.5]:mount(x,1.35,.5,1.15,'hole')
            p.update(profile='bottom-chamfer',chamfer=.7,cavity=[6.85,1.8,4],tongue_side='upper')
        elif n==165:
            contacts([[2.75-i*.5,-3.93] for i in range(12)]+[[-2.5+i*.5,-2.23] for i in range(12)],[.3,.7],names=[f'A{i}' for i in range(1,13)]+[f'B{i}' for i in range(1,13)])
            for x in [-4.49,4.49]:mount(x,3.93,.5,1.1,'hole')
            for x in [-4.13,4.13]:mount(x,-2.02,.5,1.1,'hole')
            mount(-3.6,-3.27,.95,.65,'locator');mount(3.6,-3.27,.65,.65,'locator')
            p.update(profile='rounded',radius=1,cavity=[8.34,2.56,6.5],tongue=[8,.7],tongue_side='center')
            conflict('USB_C_DEPTH','Use default L=7.35 at offset Y=1.1 (front 4.775); PCB prose fab depth 10.45/front 6.3 disagree. Keep explicit A/B tail and shield coordinates even outside shell.')
        elif n==166:
            contacts([[1.6-i*.8,-2.75] for i in range(5)],[.5,2.5])
            for x in [-4.4,4.4]:
                for y in [-2.75,2.75]:mount(x,y,2,2.5)
            for x in [-2.2,2.2]:mount(x,-.15,.9,.9,'locator')
            p.update(profile='bottom-chamfer',tongue_side='upper')
        elif n==167:
            contacts([[4.5-i*.5,-.05,0 if i%2==0 else -1.6] for i in range(19)],[.5,2.8])
            for x in [-6.775,6.775]:
                for z in [0,-1.6]:mount(x,.05,.6,2.6,z=z)
            p.update(profile='trapezoid',tongue_side='center',board_thickness=1.6)
            conflict('HDMI_HEIGHT_AND_SHIELD','Use YAML H=6.5 vs procedure 6.0; explicit shield X=6.775 vs formula 6.825; odd contacts Z=0, even contacts Z=-1.6 per straddle mounting and Section 2 board default.')
            conflict('HDMI_CAVITY_WIDTH','14 mm cavity equals 14 mm shell width; derive cosmetic cavity inside stated shell instead of a zero-wall cavity.')
        else:
            contacts([[3.6-i*.4,0] for i in range(19)],[.2,.5])
            p.update(profile='trapezoid',cavity=[10.42,2.42,8],tongue_side='center')
            cosmetic(p,'contact_visual_width',.2,'Half stated 0.4 pitch; visual terminal width only, no footprint binding; row positions unchanged.')
            conflict('MINI_HDMI_MOUNT_COORDINATES','Shield pad X=+/-5 is given without Y; omit unlocated shield pads. Keep explicit single-row placeholder 19 signal contacts; no footprint admission.')
        cosmetic(p,'wall',min(p['width'],p['height'])/20,'One twentieth of smaller shell face dimension, inward from sourced outer envelope.')
        if 'chamfer' not in p and p['profile'] in ['top-chamfer','bottom-chamfer','trapezoid']:cosmetic(p,'chamfer',p['height']/5,'One fifth face height, inward corner removal.')
        if 'cavity' not in p:cosmetic(p,'cavity',[p['width']-2*p['wall'],p['height']-2*p['wall'],p['length']*.8],'Outer face minus twice cosmetic wall; cavity depth 80 percent of body length.')
        if 'tongue' not in p:cosmetic(p,'tongue',[p['cavity'][0]*.8,p['cavity'][1]/4],'80 percent of cavity width and one quarter of cavity height, inside opening.')
        cosmetic(p,'tongue_recess',min(.5,p['length']/10),'Front recess bounded by one tenth of sourced length and 0.5 mm.')
        cosmetic(p,'contact_visual_height',p['height']/100,'One hundredth shell height; internal mating strips only.')
    elif n in [169,170]:
        p.update(shape='jack',cavity=[11.7,7,14] if n==169 else [10,7,14],profile='rect')
        contacts([[4.445-i*1.27,-1.905 if i%2==0 else -4.445] for i in range(8)] if n==169 else [[1.53-i*1.02,-1.5 if i%2==0 else -3.5] for i in range(4)],[.45,.45],'tht')
        cosmetic(p,'tail_visual_width',.45,'Visual tail stock below the stated 0.76 mm RJ45 hole; RJ11 borrows sibling stock. Hole positions unchanged, no drill inference.')
        if n==169:
            for x in [-5.715,5.715]:mount(x,4.445,3.2,3.2,'locator')
        else:conflict('RJ11_UNSPECIFIED_DRILL','NPTH centers +/-4,+3.5 are stated, diameter is absent; retain metadata only, omit pegs rather than infer fit.')
        p['unmodeled_mounts']=[{'xy':[-4,3.5],'diameter':None},{'xy':[4,3.5],'diameter':None}] if n==170 else []
        cosmetic(p,'latch',[p['cavity'][0]*.38,p['height']/8],'Latch width 38 percent cavity width, depth one eighth housing height; inward removal.')
        cosmetic(p,'internal_contact',[p['cavity'][0]/(p['count']*3),p['height']/100],'Internal spring strip width from cavity/contact count; height 1 percent envelope.')
    elif n in [171,172]:
        p.update(shape='bore',bore=3.8 if n==171 else 5.5,bore_x=-.3 if n==171 else 2.35,bore_z=3 if n==171 else 5.5,bore_depth=8 if n==171 else 9)
        if n==171:
            p.update(length=14.3,nose=[-.3,7.4,11,6],bore_front=11)
            contacts([[-4.9,1.7],[-4.4,-5.6],[2.2,-1.2],[4.9,-2.4],[-.3,5.6]],[.3,.9],'tht',names=['T','TN','RN','R','S'])
        else:
            contacts([[2.35,-3],[2.35,3],[-2.35,0]],[.5,1],'tht');p.update(bore_front=10.7,center_pin=2)
            conflict('DC_JACK_ENVELOPE','Retain second-pass 10.7 width, 14.4 length and 11 height; 9.0-wide KiCad outline and 6.5 callout remain unresolved. Bore axis 5.5 is stated placeholder.')
    elif n in [173,174]:
        p.update(shape='xt',profile='top-chamfer',chamfer=1 if n==173 else 1.85)
        contacts([[-2.5,-4.825],[2.5,-4.825]] if n==173 else [[-3.6,0],[3.6,0]],[1.5,1.5] if n==173 else [1.7,.6],'tht')
        if n==173:
            for x in [-5.5,5.5]:mount(x,5.175,1,1,'locator')
            conflict('XT30_LENGTH_ARITHMETIC','Use 13.95 length at stated +1.3 offset, giving -5.675..8.275. Prose front 9.275 implies 14.95 and is not used. Explicit peg centers lie outside 9.9 body; retain detached locator geometry and report missing attachment outline.')
        cosmetic(p,'wall',p['height']/8,'One eighth body height inward, leaves keyed shroud within sourced body.')
        cosmetic(p,'bullet_diameter',p['height']/3,'Internal mating bullet diameter one third body height; board tail shape and coordinates unchanged.')
        cosmetic(p,'recess_depth',p['length']/3,'Front recess one third sourced length, within housing.')
    elif n in [175,176,177]:
        p.update(shape='rf',vertical=n!=177)
        if n==175:
            contacts([[-1.05,0]],[1.05,1],names=['SIG']);contacts([[.475,1.475],[.475,-1.475]],[2.2,1.05],names=['GND1','GND2']);p['diameter']=2
        elif n==176:
            contacts([[0,0],[-2.54,2.54],[-2.54,-2.54],[2.54,-2.54],[2.54,2.54]],[1,1],'tht');p.update(diameter=6.35,hex_flats=7.87)
        else:
            contacts([[0,.6875]],[1.78,4.19],names=['SIG'])
            contacts([[-3.4925,.6875,0],[3.4925,.6875,0],[-3.4925,.6875,-1.57],[3.4925,.6875,-1.57]],[2.665,4.19],names=['GND1','GND2','GND3','GND4'])
            p.update(diameter=6.35,hex_flats=7.87,axis_z=-.785,barrel_front=15.2325,rear_depth=3.81,slot=1.57)
            conflict('SMA_EDGE_WIDTH','Hex across flats 7.87 implies wider than YAML 6.35 barrel diameter; model barrel diameter 6.35 and explicit 7.87 hex, report combined envelope. Axis Z=-0.785 remains stated provisional slot-center assumption.')
            p['unmodeled_mounts']=[{'xy':[x,y],'size':s} for x in [-3.4925,3.4925] for y,s in [(-1.8525,[.46,.89]),(-2.2975,[.97,.97])]]
        cosmetic(p,'base_fraction',.25,'Base/flange occupies lower quarter of sourced height; total height unchanged.')
        cosmetic(p,'dielectric_ratio',.6,'Dielectric opening 60 percent of interface diameter, inside metal ring.')
        cosmetic(p,'socket_ratio',.2,'Female recess 20 percent of interface diameter, inside dielectric.')
        cosmetic(p,'thread_depth',p['diameter']/80,'Cosmetic thread recess one eightieth diameter, never outside barrel envelope.')
    elif n==178:
        p.update(shape='zif',width=d['overall_length'],length=d['overall_width'],N=10,pitch=.5)
        contacts([[-2.25+i*.5,1.85] for i in range(10)],[.3,1.3])
        for x in [-4.15,4.15]:mount(x,-1.4,1.8,2.2)
        cosmetic(p,'slot_height',p['height']/4,'FPC opening one quarter body height, inside housing.')
        cosmetic(p,'actuator_depth',p['length']/4,'Rear flip bar occupies one quarter body depth, separate sub-body.')
    else:
        p.update(shape='card',shell_material='MAT_STEEL_STAINLESS',profile='rect')
        xs=[-7.065,-4.565,-1.265,.435,2.935,5.435,7.865,9.565,-9.565] if n==179 else [3.105,2.005,.905,-.195,-1.295,-2.395,-3.495,-4.545]
        contacts([[x,0 if n==179 else -4.9] for x in xs],[.8,2] if n==179 else [.85,1.1])
        if n==180:
            p['contacts'][-1]['size'][0]=.75
            for x in [-5.74,5.74]:
                for y in [1.25,4.95]:mount(x,y,1.2,1)
        cosmetic(p,'wall',p['height']/12,'Sheet stock one twelfth envelope height, entirely inward.')
        cosmetic(p,'base_height',p['height']/4,'Plastic support lower quarter of envelope.')
        cosmetic(p,'contact_reach',p['length']/3,'Internal spring reach one third envelope length; PCB pad centers unchanged.')
        if n==179:conflict('SD_INCOMPLETE_FCO','Use stated provisional body offset and exemplar signal row. Unknown shell tabs, locator posts and detect/write-protect contacts omitted; FCO remains signal-row-only provisional.')
    cosmetic(p,'pad_thickness',min(p['height']/20,.15),'Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.')
    cosmetic(p,'detail_ratios',{'shield_stock':.8,'locator_tail':.5,'tongue_strip_width':.45,'tongue_strip_length':.7,'tongue_strip_center':.4,'jack_cavity_center':.55,'jack_strip_length':.75,'bullet_length':.8,'bullet_center':.6,'zif_slot_width':.8,'zif_slot_depth':.5,'actuator_height':.4},'Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.')
    return p,conflicts
