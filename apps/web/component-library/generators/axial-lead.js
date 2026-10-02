import * as THREE from '../../vendor/three.module.js';

// Shared axial diode/resistor wire, local +X exit then down -Z. Dimensions are
// caller data; the center-line radius is inner radius + wire radius.
export function roundBentLead({bodyEdge,holeX,axisHeight,diameter,tail,radius,lod,segments}) {
    const points=[[bodyEdge,axisHeight]];
    if(lod==='LOD2') {
        if(holeX-radius<=bodyEdge||axisHeight-radius < -tail)throw new RangeError('Axial bend does not fit');
        points.push([holeX-radius,axisHeight]);
        for(let i=1;i<=8;i++){const a=Math.PI/2*(1-i/8);points.push([holeX-radius+radius*Math.cos(a),axisHeight-radius+radius*Math.sin(a)]);}
    } else points.push([holeX,axisHeight]);
    points.push([holeX,-tail]);
    const pos=[],idx=[],r=diameter/2;
    points.forEach(([x,z],j)=>{
        const a=points[Math.max(0,j-1)],b=points[Math.min(points.length-1,j+1)];
        const unit=(dx,dz)=>{const l=Math.hypot(dx,dz);return [dx/l,dz/l];};
        const incoming=j?unit(x-a[0],z-a[1]):unit(b[0]-x,b[1]-z),outgoing=j<points.length-1?unit(b[0]-x,b[1]-z):incoming;
        const tangent=unit(incoming[0]+outgoing[0],incoming[1]+outgoing[1]);
        // Elliptical miter plane preserves the round stock diameter on both
        // adjoining straight segments instead of tapering toward the corner.
        const scale=1/(tangent[0]*incoming[0]+tangent[1]*incoming[1]);
        for(let i=0;i<segments;i++){const t=2*Math.PI*i/segments;pos.push(x-tangent[1]*scale*r*Math.sin(t),r*Math.cos(t),z+tangent[0]*scale*r*Math.sin(t));}
    });
    for(let j=0;j<points.length-1;j++)for(let i=0;i<segments;i++){
        const a=j*segments+i,b=j*segments+(i+1)%segments,c=b+segments,d=a+segments;idx.push(a,b,c,a,c,d);
    }
    for(const [j,reverse] of [[0,true],[points.length-1,false]]){
        const center=pos.length/3;pos.push(points[j][0],0,points[j][1]);
        for(let i=0;i<segments;i++){const a=j*segments+i,b=j*segments+(i+1)%segments;idx.push(center,reverse?b:a,reverse?a:b);}
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setIndex(idx);g.computeVertexNormals();return g;
}
