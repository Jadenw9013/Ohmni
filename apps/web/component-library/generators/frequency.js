import * as THREE from '../../vendor/three.module.js';
import { box } from './leaded-body.js';
import { mesh, cylinder, decal, textDecal, relievedBox } from './discrete-primitives.js';
import { prism, outline } from './led-passive-shapes.js';
import { instances } from './instanced-terminals.js';

export const FREQUENCY_FAMILIES=Object.freeze(['PKG-XTAL_HC49','PKG-XTAL_SMD','PKG-OSC_SMD','PKG-RESONATOR_3PIN','PKG-SAW_SMD']);
export function frequencyContacts(p){
    if(p.tht)return Array.from({length:p.count},(_,i)=>({terminal:String(i+1),center_mm:[(i-(p.count-1)/2)*p.pitch,0,0],type:'tht'}));
    const x=Math.abs(p.source_pin1[0]),y=Math.abs(p.source_pin1[1]);
    let coords=p.count===4?[[-x,y],[-x,-y],[x,-y],[x,y]]:[[-x,y],[-x,0],[-x,-y],[x,-y],[x,0],[x,y]];
    if(p.pin1_corner==='BL')coords=[...coords.slice(1),coords[0]];
    return coords.map((xy,i)=>({terminal:String(i+1),center_mm:[...xy,0],type:'smd'}));
}
function can(g,p,lod,cs,mats){
    const L=p.body_x,W=p.body_y,H=p.height,z=p.standoff,r=W/2,s=new THREE.Shape();
    s.moveTo(-L/2+r,-r);s.lineTo(L/2-r,-r);s.absarc(L/2-r,0,r,-Math.PI/2,Math.PI/2,false);s.lineTo(-L/2+r,r);s.absarc(-L/2+r,0,r,Math.PI/2,Math.PI*1.5,false);s.closePath();
    prism(g,'metal-can',s,H,z,mats[p.body_material],p.segments[lod]);
    if(lod!=='LOD0')for(const c of cs){const d=decal(g,'lead-seal',new THREE.CircleGeometry(p.seal_diameter/2,p.segments[lod]),[...c.center_mm.slice(0,2),z],mats.MAT_RUBBER_SEAL);d.rotation.x=Math.PI;}
    if(lod==='LOD2')decal(g,'top-seam',new THREE.PlaneGeometry(L-W,p.seam_width),[0,0,z+H],mats.MAT_EPOXY_DARKGRAY);
}
function resonator(g,p,lod,mats){
    const L=p.body_x,H=p.height,r=lod==='LOD0'?0:p.radius,s=new THREE.Shape();
    s.moveTo(-L/2,0);s.lineTo(L/2,0);s.lineTo(L/2,H-r);s.quadraticCurveTo(L/2,H,L/2-r,H);s.lineTo(-L/2+r,H);s.quadraticCurveTo(-L/2,H,-L/2,H-r);s.closePath();
    const m=prism(g,'resin-body',s,p.body_y,0,mats[p.body_material],p.segments[lod]);m.rotation.x=Math.PI/2;m.position.set(0,p.body_y/2,p.standoff);
}
function smd(g,p,lod,cs,mats){
    const H=p.height,L=p.body_x,W=p.body_y,base=H*p.base_fraction;
    const pads=cs.map(c=>({min:[c.center_mm[0]-p.pad_x/2,c.center_mm[1]-p.pad_y/2,0],max:[c.center_mm[0]+p.pad_x/2,c.center_mm[1]+p.pad_y/2,p.pad_thickness]}));
    relievedBox(g,'ceramic-base',[[-L/2,L/2],[-W/2,W/2],[0,base]],pads,mats[p.body_material]);
    instances(g,'terminal-pads',new THREE.BoxGeometry(p.pad_x,p.pad_y,p.pad_thickness),mats[p.lead_material],cs.map(c=>({terminal:c.terminal,position:[...c.center_mm.slice(0,2),p.pad_thickness/2]})));
    const lid=prism(g,'metal-lid',outline(L-2*p.lid_inset,W-2*p.lid_inset,lod==='LOD2'?p.lid_chamfer:0),H-base,base,mats[p.lid_material],p.segments[lod]);
    if(p.pin1_corner==='BL')lid.rotation.x=Math.PI,lid.position.z=H+base;
    const sign=p.pin1_corner==='BL'?-1:1;
    decal(g,'pin1-mark',new THREE.CircleGeometry(p.marker_radius,p.segments[lod]),[-L/2+p.lid_inset+p.marker_radius*2,sign*(W/2-p.lid_inset-p.marker_radius*2),H],mats.MAT_EPOXY_BLACK,false,{terminal:'1',role:'pin1_mark'});
}
export function generateFrequency(p,lod,cs,mats,marking=''){
    const g=new THREE.Group();
    if(p.shape==='stadium')can(g,p,lod,cs,mats);else if(p.shape==='resonator')resonator(g,p,lod,mats);else smd(g,p,lod,cs,mats);
    if(p.tht)for(const c of cs)cylinder(g,'terminal-'+c.terminal,p.pin,p.standoff+p.tail,'Z',[...c.center_mm.slice(0,2),(p.standoff-p.tail)/2],mats[p.lead_material],p.segments[lod],{terminal:c.terminal});
    if(marking&&lod!=='LOD0')textDecal(g,marking,p.label_width,p.label_height,[0,0,p.standoff+p.height],mats.MAT_SILKSCREEN_WHITE);
    return g;
}
