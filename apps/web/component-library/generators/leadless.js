import * as THREE from '../../vendor/three.module.js';
import { instances, leadPlacements } from './instanced-terminals.js';
import { box } from './leaded-body.js';

function moldSurface(group,p,pads,material) {
    const bounds=[[-p.body_x/2,p.body_x/2],[-p.body_y/2,p.body_y/2],[p.standoff,p.height]];
    const axes=bounds.map((ends,a)=>[...new Set([...ends,...pads.flatMap(b=>[b.min[a],b.max[a]]).filter(v=>v>ends[0]&&v<ends[1])])].sort((a,b)=>a-b));
    const positions=[],normals=[];
    for(const [axis,sign,u,v] of [[0,1,1,2],[0,-1,2,1],[1,1,2,0],[1,-1,0,2],[2,1,0,1],[2,-1,1,0]]) {
        for(let i=0;i<axes[u].length-1;i++)for(let j=0;j<axes[v].length-1;j++) {
            const vertices=[[i,j],[i+1,j],[i+1,j+1],[i,j+1]].map(([a,b])=>{const q=[0,0,0];q[axis]=sign>0?bounds[axis][1]:bounds[axis][0];q[u]=axes[u][a];q[v]=axes[v][b];return q;});
            const mid=vertices[0].map((_,k)=>(vertices[0][k]+vertices[2][k])/2);
            if(pads.some(b=>mid.every((x,k)=>x>=b.min[k]-1e-9&&x<=b.max[k]+1e-9)))continue;
            const normal=[0,0,0];normal[axis]=sign;
            for(const k of [0,1,2,0,2,3]){positions.push(...vertices[k]);normals.push(...normal);}
        }
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));
    const mesh=new THREE.Mesh(g,material);mesh.name='body';mesh.userData.material_token=material.name;group.add(mesh);
}

export function addLeadless(group,p,lod,contacts,materials,bodyMaterial) {
    const pads=[],placements=[];
    const targets=lod==='LOD0'?p.side_counts.flatMap((n,s)=>n?[{side_index:s,side:['left','bottom','right','top'][s],terminal:null,
        center_mm:s%2?[0,(s===1?-1:1)*(p.body_y/2-p.pullback-p.foot_length/2),0]:[(s===0?-1:1)*(p.body_x/2-p.pullback-p.foot_length/2),0,0],
        width:(n-1)*p.pitch+p.lead_width}]:[]):contacts.map(c=>({...c,width:p.lead_width}));
    for(const c of targets) {
        const size=c.side_index%2?[c.width,p.foot_length,p.lead_thickness]:[p.foot_length,c.width,p.lead_thickness];
        const center=[c.center_mm[0],c.center_mm[1],p.lead_thickness/2];
        pads.push({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});
        placements.push({terminal:c.terminal,side:c.side,position:center,angle:c.side_index%2?Math.PI/2:0});
    }
    if(lod==='LOD0') {
        // Two or four bands have different lengths for rectangular two-row parts.
        targets.forEach((c,i)=>{
            const g=new THREE.BoxGeometry(p.foot_length,c.width,p.lead_thickness);
            const mesh=instances(group,`terminal-band-${c.side}`,g,materials.MAT_TIN_MATTE,[placements[i]]);
            mesh.userData.terminal_labels=contacts.filter(t=>t.side===c.side).map(t=>t.terminal);
        });
    } else instances(group,'leadless-terminals',new THREE.BoxGeometry(p.foot_length,p.lead_width,p.lead_thickness),materials.MAT_TIN_MATTE,placements);
    pads.push({min:[-p.ep_x/2,-p.ep_y/2,0],max:[p.ep_x/2,p.ep_y/2,p.lead_thickness]});
    moldSurface(group,p,pads,bodyMaterial);
    const ep=box(group,'exposed-pad',[p.ep_x,p.ep_y,p.lead_thickness],[0,0,p.lead_thickness/2],materials.MAT_TIN_MATTE);
    ep.userData={role:'exposed_pad',numbered:false,size_mm:[p.ep_x,p.ep_y],center_mm:[0,0,0]};
    if(lod==='LOD2'&&p.pullback===0) {
        const geometry=new THREE.PlaneGeometry(p.lead_width,p.lead_thickness);geometry.rotateY(Math.PI/2);geometry.rotateX(Math.PI/2);
        const copper=materials.MAT_COPPER.clone();copper.polygonOffset=true;copper.polygonOffsetFactor=-1;copper.polygonOffsetUnits=-1;
        const placements=leadPlacements(contacts).map((a,i)=>{
            const c=contacts[i],s=c.side_index,r=(s%2?p.body_y:p.body_x)/2;
            return {...a,position:s%2?[c.center_mm[0],s===1?-r:r,p.lead_thickness/2]:[s===0?-r:r,c.center_mm[1],p.lead_thickness/2]};
        });
        const edges=instances(group,'copper-side-faces',geometry,copper,placements);
        edges.userData.role='cosmetic_sawn_edge';
    }
}
