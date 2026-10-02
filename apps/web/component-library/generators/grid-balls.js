import * as THREE from '../../vendor/three.module.js';
import { box } from './leaded-body.js';
import { instances } from './instanced-terminals.js';

// Symmetric truncated sphere, exact overall diameter and seating planes. At
// height=diameter (WLCSP defaults), poles remain points: no invented flattening.
export function collapsedBall(diameter,height,segments,rings) {
    const R=diameter/2,positions=[],normals=[],indices=[],rows=[];
    for(let j=0;j<=rings;j++) {
        const z=height*j/rings,dy=z-height/2,r=Math.sqrt(Math.max(0,R*R-dy*dy));
        const row=[];
        for(let i=0;i<(r<1e-9?1:segments);i++) {
            const a=2*Math.PI*i/segments;row.push(positions.length/3);
            positions.push(r*Math.cos(a),r*Math.sin(a),z);normals.push(r*Math.cos(a)/R,r*Math.sin(a)/R,dy/R);
        }
        rows.push(row);
    }
    for(let j=0;j<rings;j++)for(let i=0;i<segments;i++) {
        const a=rows[j],b=rows[j+1],k=(i+1)%segments;
        if(a.length===1)indices.push(a[0],b[k],b[i]);
        else if(b.length===1)indices.push(a[i],a[k],b[0]);
        else indices.push(a[i],a[k],b[k],a[i],b[k],b[i]);
    }
    for(const [row,z,sign] of [[rows[0],0,-1],[rows.at(-1),height,1]])if(row.length>1) {
        const center=positions.length/3;positions.push(0,0,z);normals.push(0,0,sign);
        const cap=row.map(index=>{const i=positions.length/3;positions.push(...positions.slice(index*3,index*3+3));normals.push(0,0,sign);return i;});
        for(let i=0;i<segments;i++)indices.push(center,cap[sign>0?i:(i+1)%segments],cap[sign>0?(i+1)%segments:i]);
    }
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
    geometry.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));geometry.setIndex(indices);geometry.computeBoundingBox();geometry.computeBoundingSphere();return geometry;
}

export function addGrid(group,p,lod,contacts,materials) {
    if(lod!=='LOD0') {
        const geometry=collapsedBall(p.ball_diameter,p.standoff,p.ball_segments[lod],p.ball_rings[lod]);
        return instances(group,'solder-balls',geometry,materials.MAT_SOLDER_BALL,
            contacts.map(c=>({terminal:c.terminal,position:[c.center_mm[0],c.center_mm[1],0]})));
    }
    // One slab, one draw call. Its deterministic texture retains the actual
    // populated grid/depopulation pattern, rather than a featureless metal box.
    const width=(p.nx-1)*p.pitch+p.ball_diameter,height=(p.ny-1)*p.pitch+p.ball_diameter,n=p.proxy_texture_size;
    const pixels=new Uint8Array(n*n*4);
    const populated=new Set(contacts.map(c=>`${c.row},${c.column}`));
    for(let y=0;y<n;y++)for(let x=0;x<n;x++) {
        const wx=(x+.5)/n*width-width/2+p.array_offset[0],wy=(y+.5)/n*height-height/2+p.array_offset[1];
        const col=Math.round((wx-p.array_offset[0])/p.pitch+(p.nx-1)/2),row=Math.round((p.ny-1)/2-(wy-p.array_offset[1])/p.pitch);
        const cx=(col-(p.nx-1)/2)*p.pitch+p.array_offset[0],cy=((p.ny-1)/2-row)*p.pitch+p.array_offset[1];
        const hit=populated.has(`${row},${col}`)&&Math.hypot(wx-cx,wy-cy)<=p.ball_diameter/2;
        const k=(y*n+x)*4;pixels.set(hit?[255,255,255,255]:[24,28,25,255],k);
    }
    const texture=new THREE.DataTexture(pixels,n,n,THREE.RGBAFormat);texture.colorSpace=THREE.SRGBColorSpace;
    texture.magFilter=THREE.NearestFilter;texture.minFilter=THREE.NearestFilter;texture.needsUpdate=true;
    const material=materials.MAT_SOLDER_BALL.clone();material.map=texture;
    const slab=box(group,'ball-layer-proxy',[width,height,p.standoff],[...p.array_offset,p.standoff/2],material);
    const positions=slab.geometry.attributes.position,uv=slab.geometry.attributes.uv;
    for(let i=0;i<positions.count;i++)uv.setXY(i,positions.getX(i)/width+.5,positions.getY(i)/height+.5);
    uv.needsUpdate=true;
    slab.userData={role:'LOD0_GRID_PROXY',terminal_labels:contacts.map(c=>c.terminal),grid_texture:true,
        note:'Visual slab proxy, not electrically connected metal; dots encode actual populated ball positions.'};
    return slab;
}
