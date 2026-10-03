import * as THREE from '../../vendor/three.module.js';
import { mesh } from './discrete-primitives.js';
import { carvedBox } from './connector-shapes.js';

// Shared XZ cross-section extruded toward -Y from the mating face. Inward stock;
// no overlapping box walls, and the opening is real geometry at every LOD.
export function faceProfile(w,h,kind='rect',detail=0){
    const s=new THREE.Shape(),x=w/2,c=Math.min(detail,w/3,h/2);
    if(kind==='rounded'){
        s.moveTo(-x+c,0);s.lineTo(x-c,0);s.quadraticCurveTo(x,0,x,c);s.lineTo(x,h-c);s.quadraticCurveTo(x,h,x-c,h);s.lineTo(-x+c,h);s.quadraticCurveTo(-x,h,-x,h-c);s.lineTo(-x,c);s.quadraticCurveTo(-x,0,-x+c,0);
    }else{
        const pts=kind==='top-chamfer'?[[-x,0],[x,0],[x,h-c],[x-c,h],[-x+c,h],[-x,h-c]]:
            kind==='bottom-chamfer'?[[-x+c,0],[x-c,0],[x,c],[x,h],[-x,h],[-x,c]]:
            kind==='trapezoid'?[[-x+c,0],[x-c,0],[x,h],[-x,h]]:[[-x,0],[x,0],[x,h],[-x,h]];
        pts.forEach(([a,b],i)=>i?s.lineTo(a,b):s.moveTo(a,b));
    }s.closePath();return s;
}
export function extrudeFace(g,name,shape,depth,position,material,segments=24,metadata={}){
    const geo=new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:false,curveSegments:segments});geo.rotateX(Math.PI/2);
    return mesh(g,name,geo,material,position,metadata);
}
export function bentSheetShell(g,name,p,material,lod){
    const shape=faceProfile(p.width,p.height,p.profile,p.radius??p.chamfer??0),[iw,ih,depth]=p.cavity;
    const inner=faceProfile(iw,ih,p.profile,Math.max(0,(p.radius??p.chamfer??0)-p.wall));
    const hole=new THREE.Path(inner.getPoints(p.segments[lod]).map(v=>new THREE.Vector2(v.x,v.y+(p.height-ih)/2)));shape.holes.push(hole);
    const front=p.offset[1]+p.length/2;
    extrudeFace(g,name,shape,Math.min(depth,p.length),[p.offset[0],front,0],material,p.segments[lod],{role:'bent_sheet_shell',mating:[0,1,0]});
    if(depth<p.length)extrudeFace(g,name+'-rear',faceProfile(p.width,p.height,p.profile,p.radius??p.chamfer??0),p.length-depth,[p.offset[0],front-depth,0],material,p.segments[lod]);
    if(p.contacts?.some(c=>c.type==='smd'&&c.center_mm[2]===0)){
        // Replace only the coplanar bottom faces with a partitioned pad-relieved
        // surface. The supplied pads keep their exact Z=0 contact plane.
        const bottom=[];
        for(const child of [...g.children])if(child.name===name||child.name===name+'-rear'){
            const a=child.geometry.attributes.position,out=[];let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
            for(let i=0;i<a.count;i+=3){const q=[0,1,2].map(k=>new THREE.Vector3(a.getX(i+k),a.getY(i+k),a.getZ(i+k)).add(child.position));
                if(q.every(v=>Math.abs(v.z)<1e-6)){for(const v of q){xmin=Math.min(xmin,v.x);xmax=Math.max(xmax,v.x);ymin=Math.min(ymin,v.y);ymax=Math.max(ymax,v.y);}}else for(let k=0;k<3;k++)out.push(a.getX(i+k),a.getY(i+k),a.getZ(i+k));
            }
            if(Number.isFinite(xmin))bottom.push([xmin,xmax,ymin,ymax]);
            child.geometry.dispose();child.geometry=new THREE.BufferGeometry();child.geometry.setAttribute('position',new THREE.Float32BufferAttribute(out,3));child.geometry.computeVertexNormals();
        }
        const voids=p.contacts.filter(c=>c.type==='smd'&&c.center_mm[2]===0).map(c=>({min:[c.center_mm[0]-c.size[0]/2,c.center_mm[1]-c.size[1]/2,0],max:[c.center_mm[0]+c.size[0]/2,c.center_mm[1]+c.size[1]/2,p.pad_thickness]}));
        for(const [x0,x1,y0,y1] of bottom){const patch=carvedBox(g,name+'-pad-relief',[x0,y0,0],[x1,y1,p.pad_thickness],voids,material);const a=patch.geometry.attributes.position,out=[];for(let i=0;i<a.count;i+=3)if([0,1,2].every(k=>Math.abs(a.getZ(i+k))<1e-6))for(let k=0;k<3;k++)out.push(a.getX(i+k),a.getY(i+k),a.getZ(i+k));patch.geometry.dispose();patch.geometry=new THREE.BufferGeometry();patch.geometry.setAttribute('position',new THREE.Float32BufferAttribute(out,3));patch.geometry.computeVertexNormals();}
    }
}
