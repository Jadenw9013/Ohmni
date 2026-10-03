import * as THREE from '../../vendor/three.module.js';
import { mesh, decal } from './discrete-primitives.js';

export function polygon(points) {const s=new THREE.Shape();s.moveTo(...points[0]);for(const p of points.slice(1))s.lineTo(...p);s.closePath();return s;}
export function prism(group,name,shape,height,z,material,segments=16,metadata={}) {
    const g=new THREE.ExtrudeGeometry(shape,{depth:height,bevelEnabled:false,curveSegments:segments/4});g.translate(0,0,z);return mesh(group,name,g,material,[0,0,0],metadata);
}
export function outline(w,h,chamfer=0,both=false) {
    return polygon([[-w/2,-h/2+(both?chamfer:0)],[-w/2+(both?chamfer:0),-h/2],[w/2,-h/2],[w/2,h/2],[-w/2+chamfer,h/2],[-w/2,h/2-chamfer]]);
}
export function roundOutline(w,h,r) {
    if(!r)return outline(w,h);
    const s=new THREE.Shape();s.moveTo(-w/2+r,-h/2);s.lineTo(w/2-r,-h/2);s.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);s.lineTo(w/2,h/2-r);s.quadraticCurveTo(w/2,h/2,w/2-r,h/2);s.lineTo(-w/2+r,h/2);s.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);s.lineTo(-w/2,-h/2+r);s.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);return s;
}
// Closed surface of revolution along Z, with an optional physical -X flat.
// Rings all have the same topology: no stacked transparent internal faces.
export function revolved(group,name,profile,segments,material,flatX=null,metadata={}) {
    const pos=[],idx=[];
    for(const [r,z] of profile)for(let i=0;i<segments;i++){const a=2*Math.PI*i/segments;pos.push(flatX===null?r*Math.cos(a):Math.max(flatX,r*Math.cos(a)),r*Math.sin(a),z);}
    for(let j=0;j<profile.length-1;j++)for(let i=0;i<segments;i++){const a=j*segments+i,b=j*segments+(i+1)%segments;idx.push(a,b,b+segments,a,b+segments,a+segments);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setIndex(idx);g.computeVertexNormals();return mesh(group,name,g,material,[0,0,0],metadata);
}
export function cap(group,name,radius,height,base,segments,material,metadata={}) {
    const a=Math.acos(1-height/radius),profile=[[0,base]];
    for(let i=0;i<=segments/4;i++){const t=a*(1-i/(segments/4));profile.push([radius*Math.sin(t),base+height-radius+radius*Math.cos(t)]);}
    return revolved(group,name,profile,segments,material,null,metadata);
}
export function ringDecal(group,name,radius,length,axis,center,material,segments,metadata={}) {
    const g=new THREE.CylinderGeometry(radius,radius,length,segments,1,true);if(axis==='X')g.rotateZ(-Math.PI/2);else g.rotateX(Math.PI/2);
    return decal(group,name,g,center,material,false,metadata);
}
export function sidePatch(group,name,radius,z0,z1,angle,material,segments,metadata={}) {
    // Angle zero is +X; include it exactly for a pickable center.
    const pos=[],idx=[];for(let i=0;i<=segments;i++){const a=-angle/2+angle*i/segments;for(const z of [z0,z1])pos.push(radius*Math.cos(a),radius*Math.sin(a),z);}
    for(let i=0;i<segments;i++){const a=2*i;idx.push(a,a+2,a+3,a,a+3,a+1);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setIndex(idx);g.computeVertexNormals();return decal(group,name,g,[0,0,0],material,false,metadata);
}
