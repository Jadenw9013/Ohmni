import * as THREE from '../../vendor/three.module.js';
import { box } from './leaded-body.js';
import { gullWingLead, extrudedLeadProfile } from './gull-wing-lead.js';
import { roundBentLead } from './axial-lead.js';
import { mesh,cylinder,relievedBox,holedPlate,decal,textDecal } from './discrete-primitives.js';

const metalBounds=(size,center)=>({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});
function foldedLead(p,edge,tip,width,lod) {
    const t=p.lead_thickness,z=p.exit_height,f=p.foot;
    if(lod==='LOD0')return new THREE.BoxGeometry(f,width,t).translate(tip-f/2,0,t/2);
    const r=lod==='LOD2'?Math.min(t/2,(tip-edge)/3):0;
    const points=[[edge,z+t/2],[tip-r,z+t/2]];
    if(r)points.push([tip,z+t/2,tip,z+t/2-r]);else points.push([tip,z+t/2]);
    points.push([tip,r]);if(r)points.push([tip,0,tip-r,0]);
    points.push([tip-f,0],[tip-f,t],[tip-t,t],[tip-t,z-t/2],[edge,z-t/2]);
    return extrudedLeadProfile(points,width,r?6:1);
}
function bentFlat(p,edge,tip,width,lod) {
    if(lod==='LOD0')return new THREE.BoxGeometry(p.foot,width,p.lead_thickness).translate(tip-p.foot/2,0,p.lead_thickness/2);
    if(tip-p.foot<=edge)return foldedLead(p,edge,tip,width,lod);
    return gullWingLead({bodyEdge:edge,exitHeight:p.exit_height,tip,footLength:p.foot,width,thickness:p.lead_thickness,radius:lod==='LOD2'?p.lead_thickness/2:0});
}
function bodyBounds(p){return [[-p.body_x/2,p.body_x/2],[p.body_offset[1]-p.body_y/2,p.body_offset[1]+p.body_y/2],[p.standoff,p.height]];}

function addBand(group,p,materials,segments) {
    if(!p.band_width||p.bidirectional)return;
    const mat=materials[p.band_material];let b;
    if(['axial','melf'].includes(p.kind)) {
        const length=p.body_x-(p.kind==='melf'?2*p.cap_length:0),axis=p.kind==='melf'?p.cap_diameter/2:p.diameter/2;
        const g=new THREE.CylinderGeometry(p.diameter/2,p.diameter/2,p.band_width,segments,1,true);g.rotateZ(-Math.PI/2);
        b=decal(group,'cathode-band',g,[-length/2+p.band_width/2,0,axis],mat);
    } else b=decal(group,'cathode-band',new THREE.PlaneGeometry(p.band_width,p.body_y),[-p.body_x/2+p.band_width/2,0,p.height],mat);
    b.userData.terminal='1';b.userData.side='-X';
}
function addAxial(group,p,lod,mats) {
    const s=p.segments[lod],axis=p.diameter/2;
    cylinder(group,'body',p.diameter,p.body_x,'X',[0,0,axis],mats[p.body_material],s);
    for(const [sign,label] of [[-1,'1'],[1,'2']]){
        const g=roundBentLead({bodyEdge:p.body_x/2,holeX:p.pitch/2,axisHeight:axis,diameter:p.lead_diameter,tail:p.tail,radius:p.bend_radius,lod,segments:s});
        const lead=mesh(group,`lead-${label}`,g,mats[p.lead_material],[0,0,0],{terminal:label});if(sign<0)lead.rotation.z=Math.PI;
    }
}
function addMelf(group,p,lod,mats) {
    const s=p.segments[lod],axis=p.cap_diameter/2;
    cylinder(group,'body',p.diameter,p.body_x-2*p.cap_length,'X',[0,0,axis],mats[p.body_material],s);
    for(const [sign,label] of [[-1,'1'],[1,'2']])cylinder(group,`cap-${label}`,p.cap_diameter,p.cap_length,'X',[sign*(p.body_x-p.cap_length)/2,0,axis],mats[p.lead_material],s,{terminal:label});
}
function addSmdDiode(group,p,lod,mats) {
    const pads=[];
    for(const [sign,label] of [[-1,'1'],[1,'2']]){
        const center=[sign*(p.span-p.foot)/2,0,p.lead_thickness/2];pads.push(metalBounds([p.foot,p.lead_width,p.lead_thickness],center));
        const lead=mesh(group,`lead-${label}`,foldedLead(p,p.body_x/2,p.span/2,p.lead_width,lod),mats[p.lead_material],[0,0,0],{terminal:label});if(sign<0)lead.rotation.z=Math.PI;
    }
    relievedBox(group,'body',bodyBounds(p),pads,mats[p.body_material]);
}
function addBridge(group,p,lod,mats,contacts) {
    if(p.kind==='bridge_round')cylinder(group,'body',p.body_x,p.body_height,'Z',[0,0,p.standoff+p.body_height/2],mats[p.body_material],p.segments[lod]);
    else box(group,'body',[p.body_x,p.body_y,p.body_height],[0,0,p.standoff+p.body_height/2],mats[p.body_material]);
    for(const c of contacts){const [x,y]=c.center_mm;
        if(p.kind==='bridge_round')cylinder(group,`lead-${c.terminal}`,p.lead_diameter,p.standoff+p.tail,'Z',[x,y,(p.standoff-p.tail)/2],mats[p.lead_material],8,{terminal:c.terminal});
        else {
            const lead=mesh(group,`lead-${c.terminal}`,roundBentLead({bodyEdge:p.body_x/2,holeX:Math.abs(x),axisHeight:p.exit_height,diameter:p.lead_diameter,tail:p.tail,radius:p.bend_radius,lod,segments:lod==='LOD2'?16:8}),mats[p.lead_material],[0,y,0],{terminal:c.terminal});if(x<0)lead.rotation.z=Math.PI;
        }
    }
    // Only the '+' near pin1 is the spec's explicit placeholder. The other
    // symbols form a central legend and must not imply a researched pin map.
    const z=p.height;const plus=decal(group,'bridge-plus',new THREE.PlaneGeometry(.8,.15),[-p.body_x*.23,p.body_y*.23,z],mats.MAT_SILKSCREEN_WHITE,false,{mapping:'UNVERIFIED_VISUAL_PLACEHOLDER'});
    const cross=decal(group,'bridge-plus-cross',new THREE.PlaneGeometry(.15,.8),plus.position.toArray(),mats.MAT_SILKSCREEN_WHITE);
    cross.userData.mapping=plus.userData.mapping;
    if(p.kind==='bridge_dip'&&lod!=='LOD0') {
        decal(group,'bridge-minus',new THREE.PlaneGeometry(.6,.1),[-.9,-p.body_y*.22,z],mats.MAT_SILKSCREEN_WHITE,false,{mapping:'UNASSIGNED_SYMBOL_LEGEND'});
        for(const x of [0,.9]) {
            const shape=new THREE.Shape();
            for(let i=0;i<=16;i++){const a=-.3+.6*i/16,b=.12*Math.sin(2*Math.PI*i/16);if(i===0)shape.moveTo(a,b+.035);else shape.lineTo(a,b+.035);}
            for(let i=16;i>=0;i--)shape.lineTo(-.3+.6*i/16,.12*Math.sin(2*Math.PI*i/16)-.035);shape.closePath();
            decal(group,'bridge-ac',new THREE.ShapeGeometry(shape),[x,-p.body_y*.22,z],mats.MAT_SILKSCREEN_WHITE,false,{mapping:'UNASSIGNED_SYMBOL_LEGEND'});
        }
    }
}
function addTo92(group,p,lod,mats) {
    const w=p.body_x,t=p.body_y,r=w/2,flat=-t/2,join=t/2-r,s=new THREE.Shape();s.moveTo(-r,flat);s.lineTo(r,flat);s.lineTo(r,join);s.absarc(0,join,r,0,Math.PI,false);s.closePath();
    const bevel=lod==='LOD0'?0:p.bevel;
    const g=new THREE.ExtrudeGeometry(s,{depth:p.body_height,bevelEnabled:false,steps:lod==='LOD2'?8:2,curveSegments:p.segments[lod]/2});
    // Cosmetic small top taper stays within the exact body envelope.
    const pos=g.attributes.position;for(let i=0;i<pos.count;i++)if(pos.getZ(i)>p.body_height-bevel){pos.setXY(i,pos.getX(i)*(1-bevel/w),pos.getY(i)*(1-bevel/t));}
    g.computeVertexNormals();g.translate(0,0,p.standoff);mesh(group,'body',g,mats[p.body_material]);
    for(let i=-1;i<=1;i++)box(group,`lead-${i+2}`,[p.lead_width,p.lead_thickness,p.standoff+p.tail],[i*p.pitch,0,(p.standoff-p.tail)/2],mats[p.lead_material]).userData.terminal=String(i+2);
}
function addSotPower(group,p,lod,mats) {
    const pads=[];
    for(const [x,sign,width,label] of [[-p.pitch,-1,p.lead_width,'1'],[0,-1,p.center_lead_width,'2'],[p.pitch,-1,p.lead_width,'3'],[0,1,p.tab_width,p.kind==='sot89'?'2':'4']]) {
        const lead=mesh(group,sign>0?'tab':`lead-${label}`,bentFlat(p,p.body_y/2,p.span/2,width,lod),mats[p.lead_material],[x,0,0],{terminal:label,role:sign>0?'tab':'lead'});lead.rotation.z=sign*Math.PI/2;
        pads.push(metalBounds([width,p.foot,p.lead_thickness],[x,sign*(p.span-p.foot)/2,p.lead_thickness/2]));
    }
    relievedBox(group,'body',bodyBounds(p),pads,mats[p.body_material]);
}
function addUpright(group,p,lod,mats) {
    const top=p.standoff+p.height,holeZ=top-p.hole_from_top,split=p.back_y-p.tab_thickness,diam=p.hole?p.hole_diameter:0;
    const common={bottom:p.standoff,top:p.standoff+p.plastic_height,holeZ,holeDiameter:diam,segments:lod==='LOD0'?16:lod==='LOD1'?32:48};
    if(p.kind==='to247'&&lod!=='LOD0'&&p.dish_diameter&&p.hole){
        holedPlate(group,'body-front-dish',{...common,width:p.body_x,ymin:p.front_y,ymax:p.front_y+p.dish_depth,holeDiameter:p.dish_diameter},mats[p.body_material]);
        holedPlate(group,'body',{...common,width:p.body_x,ymin:p.front_y+p.dish_depth,ymax:split},mats[p.body_material]);
    } else holedPlate(group,'body',{...common,width:p.body_x,ymin:p.front_y,ymax:split},mats[p.body_material]);
    holedPlate(group,'tab',{...common,width:p.tab_width,bottom:p.standoff+p.tab_exposed_from,top,ymin:split,ymax:p.back_y},mats[p.tab_material]);
    if(p.kind==='to247') {
        box(group,'back-wrap-base',[p.body_x,p.tab_thickness,p.tab_exposed_from],[0,(split+p.back_y)/2,p.standoff+p.tab_exposed_from/2],mats[p.body_material]);
        const side=(p.body_x-p.tab_width)/2;
        for(const sign of [-1,1])box(group,'back-wrap-side',[side,p.tab_thickness,p.plastic_height-p.tab_exposed_from],[sign*(p.tab_width/2+side/2),(split+p.back_y)/2,p.standoff+(p.plastic_height+p.tab_exposed_from)/2],mats[p.body_material]);
    }
    for(let i=-1;i<=1;i++){
        const bottom=-p.tail,join=Math.max(bottom,p.standoff-p.shoulder_length),label=String(i+2);
        if(lod==='LOD0')box(group,`lead-${label}`,[p.lead_width,p.lead_thickness,p.standoff-bottom],[i*p.pitch,0,(p.standoff+bottom)/2],mats[p.lead_material]).userData.terminal=label;
        else {
            box(group,`shoulder-${label}`,[p.shoulder_width,p.lead_thickness,p.standoff-join],[i*p.pitch,0,(p.standoff+join)/2],mats[p.lead_material]).userData.terminal=label;
            if(join>bottom)box(group,`lead-${label}`,[p.lead_width,p.lead_thickness,join-bottom],[i*p.pitch,0,(join+bottom)/2],mats[p.lead_material]).userData.terminal=label;
        }
    }
}
function addDpak(group,p,lod,mats) {
    const cy=p.body_offset[1],back=cy+p.body_y/2,front=cy-p.body_y/2,tip=p.span/2,pads=[];
    // Exposed thermal contour and projecting tab are visible surfaces of one
    // embedded leadframe. Hidden internal metal is omitted from the render.
    const ep=box(group,'exposed-tab',[p.ep_x,p.ep_y,p.tab_thickness],[0,cy,p.tab_thickness/2],mats[p.lead_material]);ep.userData={role:'tab',terminal:'2',aliases:['4'],embedded:true};pads.push(metalBounds([p.ep_x,p.ep_y,p.tab_thickness],[0,cy,p.tab_thickness/2]));
    const ext=box(group,'tab-extension',[p.tab_width,p.tab_extension,p.tab_thickness],[0,(back+tip)/2,p.tab_thickness/2],mats[p.lead_material]);ext.userData={role:'tab',terminal:'2',aliases:['4'],embedded:true};
    for(const [x,label] of [[-p.pitch,'1'],[p.pitch,'3']]){
        const lead=mesh(group,`lead-${label}`,bentFlat(p,-front,tip,p.lead_width,lod),mats[p.lead_material],[x,0,0],{terminal:label});lead.rotation.z=-Math.PI/2;
    }
    if(p.stub_length>0)box(group,'cropped-stub',[p.lead_width,p.stub_length,p.lead_thickness],[0,front-p.stub_length/2,p.exit_height],mats[p.lead_material]).userData={terminal:'2',role:'non_contact_stub'};
    relievedBox(group,'body',bodyBounds(p),pads,mats[p.body_material]);
}
function addPowerpak(group,p,lod,mats,contacts) {
    const pads=[];
    for(const c of contacts){const [x,y]=c.center_mm,center=[x,y,p.lead_thickness/2],size=[p.foot,p.lead_width,p.lead_thickness];
        box(group,`lead-${c.terminal}`,size,center,mats[p.lead_material]).userData.terminal=c.terminal;pads.push(metalBounds(size,center));}
    box(group,'exposed-drain-pad',[p.ep_x,p.ep_y,p.lead_thickness],[0,0,p.lead_thickness/2],mats.MAT_COPPER).userData={role:'exposed_pad',tied_to:['5','6','7','8'],numbered:false};
    pads.push(metalBounds([p.ep_x,p.ep_y,p.lead_thickness],[0,0,p.lead_thickness/2]));relievedBox(group,'body',bodyBounds(p),pads,mats[p.body_material]);
    decal(group,'pin1-decal',new THREE.CircleGeometry(p.marker_diameter/2,16),[-p.body_x/2+p.marker_inset,p.body_y/2-p.marker_inset,p.height],mats.MAT_SILKSCREEN_WHITE,false,{terminal:'1'});
}

export function generateDiscrete(p,lod,marking,contacts,mats) {
    const group=new THREE.Group();
    if(p.kind==='axial')addAxial(group,p,lod,mats);
    else if(p.kind==='melf')addMelf(group,p,lod,mats);
    else if(['sod','smx'].includes(p.kind))addSmdDiode(group,p,lod,mats);
    else if(p.kind.startsWith('bridge'))addBridge(group,p,lod,mats,contacts);
    else if(p.kind==='to92')addTo92(group,p,lod,mats);
    else if(['sot89','sot223'].includes(p.kind))addSotPower(group,p,lod,mats);
    else if(['to126','to220','to247'].includes(p.kind))addUpright(group,p,lod,mats);
    else if(['dpak','d2pak'].includes(p.kind))addDpak(group,p,lod,mats);
    else if(p.kind==='powerpak')addPowerpak(group,p,lod,mats,contacts);
    else throw new RangeError('Unknown discrete package');
    addBand(group,p,mats,p.segments[lod]);
    if(lod!=='LOD0'&&marking&&!['axial','melf'].includes(p.kind)) {
        const front=['to92','to126','to220','to247'].includes(p.kind);
        const center=front?[0,p.front_y??-p.body_y/2,p.standoff+(p.plastic_height??p.body_height)*.42]:[p.band_width/2,p.body_offset[1],p.height];
        textDecal(group,marking,p.body_x*p.mark_scale,(front?(p.plastic_height??p.body_height):p.body_y)*.10,center,mats.MAT_SILKSCREEN_WHITE,front);
    }
    return group;
}
