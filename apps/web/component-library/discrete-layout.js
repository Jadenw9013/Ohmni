import { positive, finite, validateMetadata, LODS } from './validate.js';

export const UPRIGHT=Object.freeze(['to126','to220','to247']);
export function discreteContacts(p) {
    const make=(terminal,x,y,extra={})=>({terminal,center_mm:[x,y,0],...extra});
    if(['axial','melf','sod','smx'].includes(p.kind)) {
        const x=p.kind==='axial'?p.pitch/2:p.kind==='melf'?(p.body_x-p.cap_length)/2:(p.span-p.foot)/2;
        return [make('1',-x,0,{function:p.bidirectional?'equivalent':'cathode'}),make('2',x,0,{function:p.bidirectional?'equivalent':'anode'})];
    }
    if(p.kind.startsWith('bridge'))return [make('1',-p.row_spacing/2,p.pitch/2),make('2',-p.row_spacing/2,-p.pitch/2),make('3',p.row_spacing/2,-p.pitch/2),make('4',p.row_spacing/2,p.pitch/2)].map(c=>({...c,function:'UNKNOWN'}));
    if(p.kind==='to92'||UPRIGHT.includes(p.kind))return [-1,0,1].map((v,i)=>make(String(i+1),v*p.pitch,0));
    if(['sot89','sot223'].includes(p.kind))return [make('1',-p.pitch,-p.contact_y),make('2',0,-p.contact_y),make('3',p.pitch,-p.contact_y),make(p.kind==='sot89'?'2':'4',0,p.contact_y,{role:'tab'})];
    if(['dpak','d2pak'].includes(p.kind))return [make('1',-p.pitch,-p.contact_y),make('3',p.pitch,-p.contact_y),make('2',0,p.tab_contact_y,{role:'tab',aliases:['4']})];
    if(p.kind==='powerpak')return Array.from({length:8},(_,i)=>make(String(i+1),(i<4?-1:1)*(p.span-p.foot)/2,(i<4?1.5-i:i-5.5)*p.pitch));
    throw new RangeError('Unknown discrete layout');
}
export function discreteBounds(p) {
    let x=p.body_x,y=p.body_y,z=p.height,cy=p.body_offset[1],zmin=0;
    if(p.kind==='axial')x=p.pitch+p.lead_diameter;
    if(['sod','smx'].includes(p.kind))x=p.span;
    if(p.kind==='bridge_dip')x=p.row_spacing+p.lead_diameter;
    if(['sot89','sot223','dpak','d2pak'].includes(p.kind)){y=p.span;cy=0;}
    if(p.kind==='powerpak')x=p.span;
    if(UPRIGHT.includes(p.kind))z+=p.standoff;
    if(p.tail)zmin=-p.tail;
    return {min:[-x/2,cy-y/2,zmin],max:[x/2,cy+y/2,z],size:[x,y,z-zmin]};
}
export function validateDiscrete(r,p) {
    validateMetadata(r);
    const families={axial:'PKG-DO_AXIAL',melf:'PKG-MELF',sod:'PKG-SOD',smx:'PKG-SMX',bridge_dip:'PKG-BRIDGE_DIP',bridge_round:'PKG-BRIDGE_ROUND',to92:'PKG-TO92',sot89:'PKG-SOT89',sot223:'PKG-SOT223',to126:'PKG-TO126',to220:'PKG-TO220',to247:'PKG-TO247',dpak:'PKG-DPAK',d2pak:'PKG-D2PAK',powerpak:'PKG-POWERPAK'};
    if(r.package_family!==families[p.kind])throw new RangeError('Package family/profile mismatch');
    if(!r.lod_supported.every(l=>LODS.includes(l)))throw new RangeError('Invalid LOD');
    for(const k of ['body_x','body_y','height'])positive(p[k],k);
    for(const k of ['standoff','tail','band_width']){finite(p[k],k);if(p[k]<0)throw new RangeError('Negative dimension');}
    if(p.standoff>=p.height)throw new RangeError('Standoff consumes body');
    if(p.band_width>p.body_x*.3)throw new RangeError('Band consumes body');
    if(p.kind==='axial') {
        positive(p.lead_diameter,'wire');positive(p.pitch,'pitch');
        if(p.pitch<p.body_x+2*(2*p.lead_diameter+.5)||p.lead_diameter>=p.diameter)throw new RangeError('Axial bend clearance');
    } else if(p.kind==='melf') {
        if(p.cap_diameter<p.diameter||2*p.cap_length+p.band_width>=p.body_x)throw new RangeError('MELF cap/band dimensions');
    } else if(p.kind.startsWith('bridge')) {
        if(p.kind==='bridge_dip'?(p.row_spacing<=p.body_x||p.pitch>=p.body_y):(p.pitch*Math.SQRT2+p.lead_diameter>=p.body_x))throw new RangeError('Bridge lead pattern');
    } else {
        for(const k of ['lead_width','lead_thickness'])positive(p[k],k);
        if(p.pitch&&p.lead_width>=p.pitch)throw new RangeError('Leads overlap');
        if(UPRIGHT.includes(p.kind)) {
            if(2*p.pitch+p.shoulder_width>p.body_x||p.tab_thickness>=p.body_y||p.front_y>=p.back_y-p.tab_thickness)throw new RangeError('Upright tab/lead dimensions');
            if(p.hole&&(p.hole_diameter>=p.tab_width||p.hole_from_top<=p.hole_diameter/2||p.hole_from_top+p.hole_diameter/2>=p.height))throw new RangeError('Hole exceeds tab');
        } else if(p.kind==='to92') {
            if(p.body_y<p.body_x/2||2*p.pitch+p.lead_width>=p.body_x)throw new RangeError('TO92 dome/leads');
        } else {
            const edge=['sod','smx'].includes(p.kind)?p.body_x:p.body_y;
            if(p.kind!=='powerpak'&&(p.span<=edge||p.foot<=0||p.foot>=p.span/2||p.exit_height<=p.lead_thickness))throw new RangeError('Lead profile does not fit');
            if(p.kind==='sot223'&&p.tab_width>=p.body_x)throw new RangeError('Tab exceeds body');
            if(['dpak','d2pak'].includes(p.kind)&&(p.tab_thickness<=p.standoff||p.tab_thickness>=p.height||p.ep_x>=p.body_x||p.ep_y>=p.body_y||p.stub_length<0||p.stub_length>p.stub_max))throw new RangeError('Embedded tab/stub does not fit');
            if(p.kind==='powerpak'&&(p.ep_x+2*p.foot>=p.span||p.ep_y>=p.body_y||3*p.pitch+p.lead_width>p.body_y))throw new RangeError('PowerPAK pad/lead clearance');
        }
    }
    return r;
}
