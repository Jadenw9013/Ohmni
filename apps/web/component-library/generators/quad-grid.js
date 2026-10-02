import * as THREE from '../../vendor/three.module.js';
import { gullWingLead, extrudedLeadProfile } from './gull-wing-lead.js';
import { addBody, addMarkings, box } from './leaded-body.js';
import { instances, leadPlacements } from './instanced-terminals.js';
import { addLeadless } from './leadless.js';
import { addGrid } from './grid-balls.js';

function jLead(p,width,lod) {
    const tip=p.lead_span/2,r=tip-p.contact_radius,c=p.lead_thickness,edge=p.body_x/2;
    const points=[[edge,p.exit_height+c/2],[tip,p.exit_height+c/2],[tip,r]];
    const segments=lod==='LOD2'?16:8;
    for(let i=1;i<=segments;i++){const a=-Math.PI*i/segments;points.push([p.contact_radius+r*Math.cos(a),r+r*Math.sin(a)]);}
    points.push([p.contact_radius-(r-c),r]);
    for(let i=1;i<=segments;i++){const a=-Math.PI+Math.PI*i/segments;points.push([p.contact_radius+(r-c)*Math.cos(a),r+(r-c)*Math.sin(a)]);}
    points.push([tip-c,p.exit_height-c/2],[edge,p.exit_height-c/2]);
    return extrudedLeadProfile(points,width);
}

function plccBody(group,p,lod,material) {
    const x=p.body_x/2,y=p.body_y/2,b=p.bevel_size;
    const shape=new THREE.Shape();shape.moveTo(-x,-y);shape.lineTo(x,-y);shape.lineTo(x,y);shape.lineTo(-x+b,y);shape.lineTo(-x,y-b);shape.closePath();
    const g=new THREE.ExtrudeGeometry(shape,{depth:p.height-p.standoff,steps:lod==='LOD2'?4:1,bevelEnabled:false});
    g.translate(0,0,p.standoff);
    // Source permits omitting an unsourced skirt/draft; preserve exact envelope.
    const mesh=new THREE.Mesh(g,material);mesh.name='beveled-body';mesh.userData.material_token=material.name;group.add(mesh);
}

export function generateQuadGrid(record,p,lod,marking,contacts,materials) {
    const group=new THREE.Group();group.name=record.id;
    const bodyMat=materials[record.body.material];
    if(['qfn','dfn'].includes(p.kind)) addLeadless(group,p,lod,contacts,materials,bodyMat);
    else if(['bga','wlcsp'].includes(p.kind)) {
        const substrate=lod==='LOD2'?p.substrate_height:0;
        if(substrate)box(group,'substrate',[p.body_x,p.body_y,substrate],[0,0,p.standoff+substrate/2],materials.MAT_BGA_SUBSTRATE);
        const body=box(group,p.kind==='wlcsp'?'silicon-die':'body',[p.body_x,p.body_y,p.body_thickness-substrate],
            [0,0,p.standoff+substrate+(p.body_thickness-substrate)/2],bodyMat);
        if(lod==='LOD2'&&p.edge_chamfer) {
            const pos=body.geometry.attributes.position,halfZ=(p.body_thickness-substrate)/2;
            for(let i=0;i<pos.count;i++)if(pos.getZ(i)>0)pos.setXYZ(i,Math.sign(pos.getX(i))*(p.body_x/2-p.edge_chamfer),Math.sign(pos.getY(i))*(p.body_y/2-p.edge_chamfer),halfZ);
            body.geometry.computeVertexNormals();
        }
        addGrid(group,p,lod,contacts,materials);
    } else {
        if(p.kind==='plcc')plccBody(group,p,lod,bodyMat);
        else addBody(group,{kind:'qfp',body_width:p.body_x,body_length:p.body_y,standoff:p.standoff,
            overall_height:p.height,draft_degrees:p.draft_degrees,parting_step:0},lod,bodyMat);
        const build=width=>p.kind==='plcc'?jLead(p,width,lod):gullWingLead({bodyEdge:p.body_x/2,
            exitHeight:p.standoff+p.body_thickness/2,tip:p.lead_span/2,footLength:p.foot_length,width,
            thickness:p.lead_thickness,radius:lod==='LOD2'?p.bend_radius:0});
        if(lod==='LOD0') {
            const width=(p.side_counts[0]-1)*p.pitch+p.lead_width;
            const mesh=instances(group,'lead-bands',build(width),materials[record.terminals.material],
                [0,1,2,3].map(s=>({side:['left','bottom','right','top'][s],position:[0,0,0],angle:[Math.PI,-Math.PI/2,0,Math.PI/2][s]})));
            mesh.userData.terminal_labels=contacts.map(c=>c.terminal);
        } else instances(group,p.kind==='plcc'?'j-leads':'gull-wing-leads',build(p.lead_width),materials[record.terminals.material],leadPlacements(contacts));
    }
    addMarkings(group,{kind:p.kind,body_width:p.body_x,body_length:p.body_y,overall_height:p.height,
        dimple_diameter:p.marker_diameter,dimple_inset:[p.marker_inset,p.marker_inset]},lod,marking,bodyMat);
    const marker=group.getObjectByName('pin1-decal');
    marker.userData.terminal=['bga','wlcsp'].includes(p.kind)?'A1':'1';
    if(p.kind==='plcc'&&p.pin1_mode==='center_top')marker.position.x=0;
    return group;
}
