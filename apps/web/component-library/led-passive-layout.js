import { positive, finite, validateMetadata, LODS } from './validate.js';
import { MATERIAL_TOKENS } from './materials.js';

const FAMILIES={axial:['PKG-AXIAL_RES','PKG-POWER_RES','PKG-AXIAL_IND'],can:['PKG-RADIAL_CAN','PKG-SNAPIN_CAN','PKG-SUPERCAP'],can_smd:['PKG-SMD_CAN'],tantalum:['PKG-TANT_MOLDED'],disc:['PKG-DISC_CAP'],mica:['PKG-MICA'],film:['PKG-FILM_BOX'],led_tht:['PKG-LED_THT'],led_rect:['PKG-LED_THT'],led_chip:['PKG-LED_CHIP'],led_cavity:['PKG-PLCC_LED','PKG-LED_5050'],led_power:['PKG-LED_POWER'],led_star:['PKG-LED_STAR']};
export function ledPassiveContacts(p) {
    const make=(terminal,x,y=0,z=0,fn='UNKNOWN')=>({terminal:String(terminal),center_mm:[x,y,z],function:fn});
    if(p.kind==='led_star')return p.wire_pad_xy.map(([x,y],i)=>({...make(i+1,x,y,p.board_thickness+p.lead_thickness,x<0?'cathode':'anode'),provisional:true,basis:'UNVERIFIED_VISUAL_PAD'}));
    if(p.kind==='led_power')return [make(1,p.pin1[0],0,0,'cathode'),make(2,-p.pin1[0],0,0,'anode'),make(3,0,0,0,'thermal')];
    if(p.kind==='led_cavity'&&p.count>2){const half=p.count/2,y=p.pin1[1],step=half>1?2*y/(half-1):0;return Array.from({length:p.count},(_,i)=>make(i+1,i<half?p.pin1[0]:-p.pin1[0],i<half?y-i*step:-y+(i-half)*step,0,p.functions?.[i]??'UNKNOWN'));}
    const x=p.pitch?p.pitch/2:Math.abs(p.pin1[0]),led=p.kind.startsWith('led'),polar=p.kind.startsWith('can')||p.kind==='tantalum';
    return [make(1,-x,0,0,led?'cathode':polar?'positive':'none'),make(2,x,0,0,led?'anode':polar?'negative':'none')];
}
export function ledPassiveBounds(p,lod) {
    let x=p.body_x,y=p.body_y,h=p.body_h+p.standoff,zmin=-p.tail,xmin=-x/2;
    if(p.kind==='axial'){x=p.pitch+p.lead_diameter;xmin=-x/2;}
    if(p.kind==='can'){x=y=p.diameter;xmin=-x/2;h+=p.seat_height;}
    if(p.kind==='can_smd'){x=Math.max(p.base,2*Math.abs(p.pin1[0])+p.foot);y=p.base;xmin=-x/2;h+=p.base_height;}
    if(p.kind==='led_tht'){x=y=p.flange_diameter;xmin=Math.min(-x/2+p.flat_depth,-p.pitch/2-p.lead_width/2);}
    if(['led_tht','led_rect'].includes(p.kind)&&lod==='LOD2')zmin-=p.anode_extra;
    return {min:[xmin,-y/2,zmin],max:[x/2,y/2,h],size:[x/2-xmin,y,h-zmin]};
}
export function validateLedPassive(r,p) {
    validateMetadata(r);
    if(!FAMILIES[p.kind]?.includes(r.package_family)||p.family!==r.package_family)throw new RangeError('Stage 5 family/profile mismatch');
    for(const k of ['body_x','body_y','body_h','lead_width','lead_thickness','lead_diameter'])positive(p[k],k);
    for(const k of ['tail','standoff']){finite(p[k],k);if(p[k]<0)throw new RangeError('Negative tail/standoff');}
    if(!r.lod_supported.every(l=>LODS.includes(l)))throw new RangeError('Invalid source LOD');
    if(p.pitch){positive(p.pitch,'pitch');if(p.pitch<=p.lead_diameter)throw new RangeError('Overlapping terminals');}
    if(p.kind==='axial'&&(p.pitch<p.body_x+4*p.lead_diameter||p.pitch/2-p.bend_radius<=p.body_x/2))throw new RangeError('Axial bend clearance');
    if(['disc','film','mica'].includes(p.kind)&&p.pitch>=p.body_x)throw new RangeError('Radial leads outside body');
    if(p.kind==='can'&&p.pitch+p.lead_diameter>=p.diameter)throw new RangeError('Can leads outside body');
    if(p.kind==='can_smd'&&(p.base<p.diameter||p.chamfer>=p.base/2||p.base_height<=p.lead_thickness))throw new RangeError('Invalid can base');
    if(p.kind==='tantalum'&&(2*p.foot>=p.body_x||p.lead_width>p.body_y||p.bevel>=p.body_h||p.lead_thickness>=p.body_h))throw new RangeError('Invalid tantalum');
    if(p.kind.startsWith('led')){
        if(!['clear','diffused'].includes(p.lens)||!/^#[0-9a-fA-F]{6}$/.test(p.led_color))throw new RangeError('Invalid LED appearance');
        if(p.kind==='led_tht'&&(p.flange_diameter<p.body_x||p.flange_thickness+p.body_x/2>=p.body_h||p.flat_depth<=0||p.flat_depth>=p.flange_diameter/2))throw new RangeError('Invalid lamp profile');
        if(p.kind==='led_chip'&&(2*p.foot>=p.body_x||p.lens_height>=p.body_h))throw new RangeError('Invalid chip LED');
        if(p.kind==='led_cavity'&&(p.cavity_diameter>=Math.min(p.body_x,p.body_y)||p.cavity_depth>=p.body_h-p.lead_thickness))throw new RangeError('Cavity does not fit');
    }
    for(const token of [p.body_material,p.lead_material,p.sleeve_material].filter(Boolean))if(!Object.hasOwn(MATERIAL_TOKENS,token))throw new RangeError('Unknown material token');
    if(p.band_colors&&p.band_colors.some(n=>!Object.hasOwn(MATERIAL_TOKENS,`MAT_BAND_${n}`)))throw new RangeError('Invalid band color');
    if(p.band_colors?.length!==p.bands?.length)throw new RangeError('Band count mismatch');
    return r;
}
