import * as THREE from '../../vendor/three.module.js';
import { markingGeometry } from '../../visual-assets.js';

export function mesh(group,name,geometry,material,center=[0,0,0],metadata={}) {
    const m=new THREE.Mesh(geometry,material);m.name=name;m.position.set(...center);m.userData={material_token:material.name,...metadata};group.add(m);return m;
}
export function cylinder(group,name,diameter,length,axis,center,material,segments,metadata={}) {
    const g=new THREE.CylinderGeometry(diameter/2,diameter/2,length,segments);
    if(axis==='X')g.rotateZ(-Math.PI/2);else if(axis==='Z')g.rotateX(Math.PI/2);
    return mesh(group,name,g,material,center,metadata);
}

// External mold faces partitioned around embedded metal. This keeps the
// plastic belly at its sourced standoff without stacking it on the tab.
export function relievedBox(group,name,bounds,metal,material) {
    const axes=bounds.map((ends,a)=>[...new Set([...ends,...metal.flatMap(b=>[b.min[a],b.max[a]]).filter(v=>v>ends[0]&&v<ends[1])])].sort((a,b)=>a-b));
    const positions=[],normals=[];
    for(const [axis,sign,u,v] of [[0,1,1,2],[0,-1,2,1],[1,1,2,0],[1,-1,0,2],[2,1,0,1],[2,-1,1,0]])
        for(let i=0;i<axes[u].length-1;i++)for(let j=0;j<axes[v].length-1;j++) {
            const vertices=[[i,j],[i+1,j],[i+1,j+1],[i,j+1]].map(([a,b])=>{const q=[0,0,0];q[axis]=bounds[axis][sign>0?1:0];q[u]=axes[u][a];q[v]=axes[v][b];return q;});
            const mid=vertices[0].map((_,k)=>(vertices[0][k]+vertices[2][k])/2);
            if(metal.some(b=>mid.every((x,k)=>x>=b.min[k]-1e-9&&x<=b.max[k]+1e-9)))continue;
            const normal=[0,0,0];normal[axis]=sign;
            for(const k of [0,1,2,0,2,3]){positions.push(...vertices[k]);normals.push(...normal);}
        }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));return mesh(group,name,g,material);
}

// XZ plate extruded along Y. A dish intersecting the top is an open notch,
// rather than an invalid hole outside the outer polygon or a resized feature.
export function holedPlate(group,name,{width,bottom,top,ymin,ymax,holeZ,holeDiameter,segments=32},material) {
    const s=new THREE.Shape(),r=holeZ-holeDiameter/2>=top||holeZ+holeDiameter/2<=bottom?0:holeDiameter/2;s.moveTo(-width/2,bottom);s.lineTo(width/2,bottom);s.lineTo(width/2,top);
    if(r&&holeZ+r>top) {
        const a=Math.asin((top-holeZ)/r),x=r*Math.cos(a);s.lineTo(x,top);s.absarc(0,holeZ,r,a,Math.PI-a,true);
    } else if(r) {const h=new THREE.Path();h.absarc(0,holeZ,r,0,2*Math.PI,true);s.holes.push(h);}
    s.lineTo(-width/2,top);s.closePath();
    const g=new THREE.ExtrudeGeometry(s,{depth:ymax-ymin,bevelEnabled:false,curveSegments:segments/2});g.rotateX(Math.PI/2);g.translate(0,ymax,0);
    return mesh(group,name,g,material,[0,0,0],{role:name.includes('tab')?'tab':'body',hole:holeDiameter?{diameter_mm:holeDiameter,center_mm:[0,(ymin+ymax)/2,holeZ],axis:'Y',fco_member:false}:null});
}

export function decal(group,name,geometry,center,material,front=false,metadata={}) {
    const mat=material.clone();mat.polygonOffset=true;mat.polygonOffsetFactor=-2;mat.polygonOffsetUnits=-2;
    const m=mesh(group,name,geometry,mat,center,{role:'separate_visual_decal',electrical_authority:false,...metadata});if(front)m.rotation.x=Math.PI/2;return m;
}
export function textDecal(group,text,width,height,center,material,front=false) {
    if(text)return decal(group,'marking-decal',markingGeometry(text,width,height),center,material,front,{content:text,content_basis:'VISUAL_ONLY'});
}
