import * as THREE from '../../vendor/three.module.js';
import { box } from './leaded-body.js';
import { cylinder,mesh,relievedBox } from './discrete-primitives.js';
import { carvedBox } from './connector-shapes.js';
import { instances } from './instanced-terminals.js';
import { faceProfile,extrudeFace,bentSheetShell } from './bent-sheet-shell.js';

export const IO_FAMILIES=Object.freeze(['PKG-USB_A','PKG-USB_B','PKG-USB_MICRO','PKG-USB_C','PKG-USB_MINI','PKG-HDMI','PKG-HDMI_MINI','PKG-RJ45','PKG-RJ11','PKG-AUDIO_JACK','PKG-DC_JACK','PKG-XT','PKG-UFL','PKG-SMA_RF','PKG-SMA_EDGE','PKG-FFC_ZIF','PKG-SD_SOCKET','PKG-MICROSD_SOCKET']);
export function ioContacts(p){return structuredClone(p.contacts);}
function terminals(g,p,cs,m,lod){
    const groups=new Map();for(const c of cs){const z=c.center_mm[2],height=c.type==='tht'?p.tail:p.pad_thickness,key=JSON.stringify([c.size,height,z,c.type]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(c);}
    for(const cs of groups.values()){
        const c=cs[0],h=c.type==='tht'?p.tail:p.pad_thickness,sign=c.center_mm[2]<0?-1:1;
        instances(g,'contacts',new THREE.BoxGeometry(c.size[0],c.size[1],h),m[p.lead_material],cs.map(c=>({terminal:c.terminal,position:[c.center_mm[0],c.center_mm[1],c.center_mm[2]+(c.type==='tht'?-h/2:sign*h/2)]})));
    }
    for(const [i,q] of p.mounts.entries()){
        const [x,y,z]=q.center_mm,[w,d]=q.size;
        // Hole dimensions remain metadata; visible legs use inward cosmetic stock.
        if(q.type==='smd')box(g,'shield-tab',[w,d,p.pad_thickness],[x,y,z+(z<0?-1:1)*p.pad_thickness/2],m.MAT_NICKEL).userData.role='mounting';
        else if(q.type==='locator'){
            if(lod!=='LOD0'&&!p.omit_locator_geometry)cylinder(g,'locator',Math.min(w,d),p.tail*p.detail_ratios.locator_tail,'Z',[x,y,-p.tail*p.detail_ratios.locator_tail/2],m.MAT_PLASTIC_BLACK,p.segments[lod],{role:'mounting',hole:q});
        }else box(g,'shield-leg',[Math.min(w,p.pad_thickness),d*p.detail_ratios.shield_stock,p.tail],[x,y,-p.tail/2],m.MAT_NICKEL).userData={role:'mounting',hole:q};
    }
}
function shell(g,p,lod,m){
    bentSheetShell(g,'shell',p,m[p.shell_material],lod);
    const [w,h]=p.tongue,front=p.offset[1]+p.length/2,depth=p.cavity[2]-p.tongue_recess;
    const cz=p.tongue_side==='lower'?(p.height-p.cavity[1])/2+h/2:p.tongue_side==='upper'?(p.height+p.cavity[1])/2-h/2:p.height/2;
    box(g,'insulator-tongue',[w,depth,h],[p.offset[0],front-p.tongue_recess-depth/2,cz],m.MAT_PLASTIC_BLACK);
    const strip=p.contact_visual_height,r=p.detail_ratios;
    for(const c of p.contacts){const side=p.family==='PKG-USB_C'?(c.terminal.startsWith('A')?1:-1):p.family==='PKG-USB_B'?(Number(c.terminal)<=2?1:-1):p.family==='PKG-HDMI'?(Number(c.terminal)%2?1:-1):p.tongue_side==='upper'?-1:1;
        box(g,'mating-contact',[c.size[0]*r.tongue_strip_width,depth*r.tongue_strip_length,strip],[c.center_mm[0],front-p.tongue_recess-depth*r.tongue_strip_center,cz+side*(h/2+strip/2)],m.MAT_GOLD).userData.terminal=c.terminal;
    }
}
function jack(g,p,lod,m){
    const [x,y]=p.offset,W=p.width,L=p.length,H=p.height,F=y+L/2,[cw,ch,depth]=p.cavity,cz=H*p.detail_ratios.jack_cavity_center;
    carvedBox(g,'jack-housing',[x-W/2,y-L/2,0],[x+W/2,F,H],[{min:[x-cw/2,F-depth,cz-ch/2],max:[x+cw/2,F,cz+ch/2]},{min:[x-p.latch[0]/2,F-depth,cz-ch/2-p.latch[1]],max:[x+p.latch[0]/2,F,cz-ch/2]}],m.MAT_PLASTIC_BLACK);
    instances(g,'spring-contacts',new THREE.BoxGeometry(p.internal_contact[0],depth*p.detail_ratios.jack_strip_length,p.internal_contact[1]),m.MAT_GOLD,p.contacts.map(c=>({terminal:c.terminal,position:[c.center_mm[0],F-depth/2,cz+ch/2-p.internal_contact[1]/2]})));
}
function bore(g,p,lod,m){
    const [x,y]=p.offset,W=p.width,L=p.length,H=p.height,F=p.bore_front,B=y-L/2,shape=faceProfile(W,H);
    const hole=new THREE.Path();hole.absarc(p.bore_x-x,p.bore_z,p.bore/2,0,Math.PI*2,true);shape.holes.push(hole);
    extrudeFace(g,'bored-housing',shape,L,[x,y+L/2,0],m.MAT_PLASTIC_BLACK,p.segments[lod]);
    if(p.nose){const s=faceProfile(p.nose[3],H),h=new THREE.Path();h.absarc(0,p.bore_z,p.bore/2,0,Math.PI*2,true);s.holes.push(h);extrudeFace(g,'nose',s,p.nose[2]-p.nose[1],[p.nose[0],p.nose[2],0],m.MAT_PLASTIC_BLACK,p.segments[lod]);}
    box(g,'bore-rear-wall',[W,Math.max(.1,F-p.bore_depth-B),H],[x,(B+F-p.bore_depth)/2,H/2],m.MAT_PLASTIC_BLACK);
    if(p.center_pin)cylinder(g,'center-pin',p.center_pin,p.bore_depth-.5,'Y',[p.bore_x,F-(p.bore_depth+.5)/2,p.bore_z],m.MAT_NICKEL,p.segments[lod]);
}
function xt(g,p,lod,m){
    bentSheetShell(g,'keyed-shroud',{...p,cavity:[p.width-2*p.wall,p.height-2*p.wall,p.recess_depth]},m[p.body_material],lod);
    const F=p.offset[1]+p.length/2;
    for(const c of p.contacts)cylinder(g,'mating-pin',p.bullet_diameter,p.recess_depth*p.detail_ratios.bullet_length,'Y',[c.center_mm[0],F-p.recess_depth*p.detail_ratios.bullet_center,p.height/2],m.MAT_GOLD,p.segments[lod],{terminal:c.terminal});
}
function ring(g,name,outer,inner,depth,axis,pos,material,segments){
    const s=new THREE.Shape();s.absarc(0,0,outer/2,0,Math.PI*2,false);const hole=new THREE.Path();hole.absarc(0,0,inner/2,0,Math.PI*2,true);s.holes.push(hole);
    const geo=new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:false,curveSegments:segments});geo.translate(0,0,-depth/2);if(axis==='Y')geo.rotateX(Math.PI/2);return mesh(g,name,geo,material,pos);
}
function rf(g,p,lod,m){
    const H=p.height,D=p.diameter,b=H*p.base_fraction,seg=p.segments[lod],mat=m[p.body_material];
    if(p.vertical){
        const [x,y]=p.offset;box(g,'base',[p.width,p.length,b],[x,y,b/2],mat);
        ring(g,'interface-ring',D,D*p.dielectric_ratio,H-b,'Z',[x,y,(H+b)/2],mat,seg);
        ring(g,'dielectric',D*p.dielectric_ratio,D*p.socket_ratio,H-b,'Z',[x,y,(H+b)/2],m.MAT_PLASTIC_WHITE,seg);
        if(p.hex_flats){const geo=new THREE.CylinderGeometry(p.hex_flats/Math.sqrt(3),p.hex_flats/Math.sqrt(3),b,6);geo.rotateX(Math.PI/2);mesh(g,'hex-nut',geo,mat,[x,y,b*1.5]);}
    }else{
        const F=p.barrel_front,Z=p.axis_z,depth=p.length-p.rear_depth;
        carvedBox(g,'straddle-block',[-p.width/2,F-p.length,Z-H/2],[p.width/2,F-depth,Z+H/2],[{min:[-p.width/2,F-p.length,-p.slot],max:[p.width/2,F-depth,0]}],mat);
        ring(g,'barrel',D,D*p.dielectric_ratio,depth,'Y',[0,F-depth/2,Z],mat,seg);
        ring(g,'dielectric',D*p.dielectric_ratio,D*p.socket_ratio,depth,'Y',[0,F-depth/2,Z],m.MAT_PLASTIC_WHITE,seg);
        const geo=new THREE.CylinderGeometry(p.hex_flats/Math.sqrt(3),p.hex_flats/Math.sqrt(3),p.rear_depth/2,6);mesh(g,'hex-nut',geo,mat,[0,F-depth+p.rear_depth/4,Z]);
    }
    // Recessed thread indication; LOD0 retains the ring and dielectric recognition.
    if(lod==='LOD2'&&p.hex_flats)g.userData.thread_detail='Recessed thread appearance omitted; no unsourced pitch asserted';
}
function zif(g,p,lod,m){
    const [x,y]=p.offset,W=p.width,L=p.length,H=p.height,F=y+L/2;
    const r=p.detail_ratios;
    carvedBox(g,'zif-housing',[x-W/2,y-L/2,0],[x+W/2,F,H],[{min:[x-W*r.zif_slot_width/2,F-L*r.zif_slot_depth,H/2-p.slot_height/2],max:[x+W*r.zif_slot_width/2,F,H/2+p.slot_height/2]},{min:[x-W/2,y-L/2,H*(1-r.actuator_height)],max:[x+W/2,y-L/2+p.actuator_depth,H]}],m.MAT_PLASTIC_BLACK);
    box(g,'flip-actuator',[W,p.actuator_depth,H*r.actuator_height],[x,y-L/2+p.actuator_depth/2,H*(1-r.actuator_height/2)],m.MAT_PLASTIC_NATURAL).userData.role='actuator';
}
function card(g,p,lod,m){
    const W=p.width,L=p.length,H=p.height,[x,y]=p.offset,F=y+L/2,w=p.wall;
    // Open-bottom folded cover; plastic floor with real underside contact recesses.
    const s=new THREE.Shape();[[-W/2,0],[-W/2,H],[W/2,H],[W/2,0],[W/2-w,0],[W/2-w,H-w],[-W/2+w,H-w],[-W/2+w,0]].forEach(([a,b],i)=>i?s.lineTo(a,b):s.moveTo(a,b));s.closePath();
    extrudeFace(g,'bent-sheet-cover',s,L,[x,F,0],m[p.shell_material],p.segments[lod],{role:'bent_sheet_shell'});
    const pads=p.contacts.map(c=>({min:[c.center_mm[0]-c.size[0]/2,c.center_mm[1]-c.size[1]/2,0],max:[c.center_mm[0]+c.size[0]/2,c.center_mm[1]+c.size[1]/2,p.pad_thickness]}));
    relievedBox(g,'plastic-floor',[[x-W/2+w,x+W/2-w],[y-L/2,F],[0,p.base_height]],pads,m.MAT_PLASTIC_BLACK);
    for(const c of p.contacts)box(g,'card-spring',[c.size[0],p.contact_reach,p.pad_thickness],[c.center_mm[0],c.center_mm[1]+p.contact_reach/2,p.base_height+p.pad_thickness/2],m.MAT_GOLD).userData.terminal=c.terminal;
}
const BUILDERS={shell,jack,bore,xt,rf,zif,card};
export function generateIO(p,lod,cs,m){const g=new THREE.Group();BUILDERS[p.shape](g,p,lod,m);terminals(g,p,cs,m,lod);return g;}
