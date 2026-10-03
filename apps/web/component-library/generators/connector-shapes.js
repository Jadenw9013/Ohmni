import * as THREE from '../../vendor/three.module.js';
import { mesh } from './discrete-primitives.js';

// Exact axis-aligned material boundary: no internal faces between adjoining cells.
// Bounds/voids are [min,max] vectors in mm. Also useful for shell/housing openings.
export function carvedBox(group,name,min,max,voids,material,metadata={}) {
    const axes=min.map((lo,a)=>[...new Set([lo,max[a],...voids.flatMap(v=>[v.min[a],v.max[a]]).filter(x=>x>lo&&x<max[a])])].sort((a,b)=>a-b));
    const solid=(i,j,k)=>{
        const index=[i,j,k];if(index.some((v,a)=>v<0||v>=axes[a].length-1))return false;
        const p=index.map((v,a)=>(axes[a][v]+axes[a][v+1])/2);
        return !voids.some(v=>p.every((x,a)=>x>=v.min[a]&&x<=v.max[a]));
    };
    const positions=[];
    for(let i=0;i<axes[0].length-1;i++)for(let j=0;j<axes[1].length-1;j++)for(let k=0;k<axes[2].length-1;k++)if(solid(i,j,k)){
        const idx=[i,j,k];
        for(const [a,sign,u,v] of [[0,1,1,2],[0,-1,2,1],[1,1,2,0],[1,-1,0,2],[2,1,0,1],[2,-1,1,0]]){
            const neighbor=[...idx];neighbor[a]+=sign;if(solid(...neighbor))continue;
            const verts=[[0,0],[1,0],[1,1],[0,1]].map(([du,dv])=>{const p=[0,0,0];p[a]=axes[a][idx[a]+(sign>0?1:0)];p[u]=axes[u][idx[u]+du];p[v]=axes[v][idx[v]+dv];return p;});
            for(const q of [0,1,2,0,2,3])positions.push(...verts[q]);
        }
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.computeVertexNormals();return mesh(group,name,g,material,[0,0,0],metadata);
}

export function squarePost(width,bottom,top,tip=0) {
    const positions=[],rings=tip>0?[[bottom,0],[bottom+tip,width/2],[top-tip,width/2],[top,0]]:[[bottom,width/2],[top,width/2]];
    const corners=[[-1,-1],[1,-1],[1,1],[-1,1]];
    const point=(r,c)=>[corners[c][0]*r[1],corners[c][1]*r[1],r[0]];
    for(let i=0;i<rings.length-1;i++)for(let c=0;c<4;c++){
        const q=[point(rings[i],c),point(rings[i],(c+1)%4),point(rings[i+1],(c+1)%4),point(rings[i+1],c)];
        for(const n of [0,1,2,0,2,3])positions.push(...q[n]);
    }
    for(const [r,indices] of [[rings[0],[0,2,1,0,3,2]],[rings.at(-1),[0,1,2,0,2,3]]])for(const c of indices)positions.push(...point(r,c));
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.computeVertexNormals();return g;
}

// A zero-stock surface is deliberately used when the spec gives an envelope but
// no wall stock. This does not manufacture a new physical wall dimension.
export function openEnvelope(group,name,min,max,openAxis,openSign,material,metadata={}) {
    const m=carvedBox(group,name,min,max,[],material.clone(),metadata),a=m.geometry.attributes.position;
    const out=[];
    for(let i=0;i<a.count;i+=3){const q=[0,1,2].map(k=>[a.getX(i+k),a.getY(i+k),a.getZ(i+k)]);
        if(q.every(p=>Math.abs(p[openAxis]-(openSign>0?max:min)[openAxis])<1e-6))continue;
        q.forEach(p=>out.push(...p));
    }
    m.geometry.dispose();m.geometry=new THREE.BufferGeometry();m.geometry.setAttribute('position',new THREE.Float32BufferAttribute(out,3));m.geometry.computeVertexNormals();m.material.side=THREE.DoubleSide;m.userData.unspecified_wall_stock=true;return m;
}
