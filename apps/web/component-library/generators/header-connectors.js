import * as THREE from '../../vendor/three.module.js';
import { box } from './leaded-body.js';
import { mesh, cylinder, decal } from './discrete-primitives.js';
import { instances } from './instanced-terminals.js';
import { extrudedLeadProfile } from './gull-wing-lead.js';
import { carvedBox, squarePost } from './connector-shapes.js';

function pinInstances(g,p,cs,bottom,top,mat,tip=0){return instances(g,'terminals',squarePost(p.pin,bottom,top,tip),mat,cs.map(c=>({position:[...c.center_mm.slice(0,2),0],terminal:c.terminal})));}
function header(g,p,lod,cs,mats){
    const L=p.N*p.pitch+p.end_allowance,W=p.width,H=p.height;
    if(p.right_angle){
        const near=(p.rows-1)*p.pitch/2,rear=near+p.rear_offset,front=rear+W;
        box(g,'housing',[W,L,H],[rear+W/2,0,H/2],mats[p.body_material]);
        for(let row=0;row<p.rows;row++){
            const x=(row-(p.rows-1)/2)*p.pitch,z=(p.rows-row-.5)*p.pitch,t=p.pin/2,tip=front+p.above;
            const r=p.bend_radius,points=lod==='LOD0'?[[x,z-t],[tip,z-t],[tip,z+t],[x,z+t]]:lod==='LOD2'?
                [[x-t,-p.tail],[x+t,-p.tail],[x+t,z-t-r],[x+t,z-t,x+t+r,z-t],[tip,z-t],[tip,z+t],[x-t+r,z+t],[x-t,z+t,x-t,z+t-r]]:
                [[x-t,-p.tail],[x+t,-p.tail],[x+t,z-t],[tip,z-t],[tip,z+t],[x-t,z+t]];
            const lead=extrudedLeadProfile(points,p.pin,lod==='LOD2'?12:1);
            instances(g,'right-angle-terminals',lead,mats[p.lead_material],cs.filter(c=>c.column===row).map(c=>({position:[0,c.center_mm[1],0],terminal:c.terminal})));
        }
    }else if(p.socket){
        const depth=lod==='LOD2'?p.deep_depth:p.shallow_depth;
        const holes=cs.map(c=>({min:[c.center_mm[0]-p.opening/2,c.center_mm[1]-p.opening/2,H-depth],max:[c.center_mm[0]+p.opening/2,c.center_mm[1]+p.opening/2,H]}));
        carvedBox(g,'socket-housing',[-W/2,-L/2,0],[W/2,L/2,H],holes,mats[p.body_material]);
        // Openings survive LOD0 as requested. Entry chamfer is a real four-face funnel.
        const verts=[];
        for(const c of cs){const [x,y]=c.center_mm;const a=p.opening/2,b=a+p.opening_chamfer;
            const low=[[-a,-a],[a,-a],[a,a],[-a,a]],high=[[-b,-b],[b,-b],[b,b],[-b,b]];
            for(let k=0;k<4;k++){const q=[low[k],low[(k+1)%4],high[(k+1)%4],high[k]].map((v,i)=>[x+v[0],y+v[1],H+(i<2?-p.opening_chamfer:0)]);for(const i of [0,1,2,0,2,3])verts.push(...q[i]);}
        }
        // Funnel top needs larger openings in the top slab, not an overlapping lid.
        g.remove(g.children.find(c=>c.name==='socket-housing'));
        carvedBox(g,'socket-housing',[-W/2,-L/2,0],[W/2,L/2,H-p.opening_chamfer],holes,mats[p.body_material]);
        carvedBox(g,'socket-rim',[-W/2,-L/2,H-p.opening_chamfer],[W/2,L/2,H],cs.map(c=>({min:[c.center_mm[0]-p.opening/2-p.opening_chamfer,c.center_mm[1]-p.opening/2-p.opening_chamfer,H-p.opening_chamfer],max:[c.center_mm[0]+p.opening/2+p.opening_chamfer,c.center_mm[1]+p.opening/2+p.opening_chamfer,H]})),mats[p.body_material]);
        const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));geo.computeVertexNormals();const m=mesh(g,'socket-entry-chamfers',geo,mats[p.body_material]);m.material=m.material.clone();m.material.side=THREE.DoubleSide;
        pinInstances(g,p,cs,lod==='LOD0'?0:-p.tail,H-depth,mats[p.lead_material]);
    }else{
        box(g,'housing',[W,L,H],[0,0,H/2],mats[p.body_material]);
        pinInstances(g,p,cs,lod==='LOD0'?0:-p.tail,H+p.above,mats[p.lead_material],lod==='LOD0'?0:p.tip);
    }
}

function wire(g,p,lod,cs,mats){
    const L=(p.N-1)*p.pitch+p.length_extra,x=p.offset[0],W=p.width,H=p.height,w=p.wall;
    const cuts=[{min:[x-W/2+w,-L/2+w,p.floor],max:[x+W/2-w,L/2-w,H]}];
    if(lod==='LOD2'&&p.key_style==='ph'){
        cuts.push({min:[x+W/2-w,-p.slot_width/2,H-p.slot_depth],max:[x+W/2,p.slot_width/2,H]});
        for(const sign of [-1,1])cuts.push({min:[-.15-p.end_slot/2,sign<0?-L/2:L/2-w,H-p.slot_depth],max:[-.15+p.end_slot/2,sign<0?-L/2+w:L/2,H]});
    }
    if(lod==='LOD2'&&p.key_style==='xh')for(const c of cs)cuts.push({min:[x+W/2-w,c.center_mm[1]-p.slot_width/2,H-p.slot_depth],max:[x+W/2,c.center_mm[1]+p.slot_width/2,H]});
    carvedBox(g,'housing',[x-W/2,-L/2,0],[x+W/2,L/2,H],cuts,mats[p.body_material]);
    pinInstances(g,p,cs,lod==='LOD0'?0:-p.tail,p.floor+p.post_above,mats[p.lead_material]);
    if(lod==='LOD2'&&p.rib)box(g,'polarizing-rib',[p.rib[0],p.rib[1],H-p.floor],[x-W/2+w+p.rib[0]/2,0,(H+p.floor)/2],mats[p.body_material]);
}
function sh(g,p,lod,cs,mats){
    const L=(p.N-1)*p.pitch+p.length_extra,x=p.offset[0],W=p.width,H=p.height;
    const cut=p.entry_direction==='side'?{min:[x-W/2,-L/2+p.end_wall,p.floor],max:[x-W/2+p.cavity_depth,L/2-p.end_wall,p.floor+p.cavity_height]}:{min:[x-W/2+p.top_wall,-L/2+p.end_wall,p.floor],max:[x+W/2-p.top_wall,L/2-p.end_wall,H]};
    carvedBox(g,'housing',[x-W/2,-L/2,0],[x+W/2,L/2,H],[cut],mats[p.body_material]);
    instances(g,'signal-tails',new THREE.BoxGeometry(p.pad_length,p.pad_width,p.pad_thickness),mats[p.lead_material],cs.map(c=>({position:[c.center_mm[0],c.center_mm[1],p.pad_thickness/2],terminal:c.terminal})));
    for(const sign of [-1,1]){
        const y=sign*(L/2-p.tab_y_inset);
        const tab=box(g,'mounting-tab',[...p.tab_size,p.pad_thickness],[p.tab_x,y,p.pad_thickness/2],mats[p.lead_material]);tab.userData={role:'mounting_contact',electrical_terminal:false};
        if(lod==='LOD2')box(g,'tab-strap',[p.tab_size[0],p.tab_strap,H],[p.tab_x,sign*L/2,H/2],mats[p.lead_material]);
    }
}
function kk(g,p,lod,cs,mats){
    const L=p.N*p.pitch,H=p.height;
    box(g,'floor',[p.xmax-p.xmin,L,p.floor],[(p.xmin+p.xmax)/2,0,p.floor/2],mats[p.body_material]);
    for(const sign of [-1,1])box(g,'end-wall',[p.xmax-p.xmin,p.end_wall,H],[(p.xmin+p.xmax)/2,sign*(L-p.end_wall)/2,H/2],mats[p.body_material]);
    box(g,'back-wall',[p.wall_inner-p.xmin,L,H],[(p.wall_inner+p.xmin)/2,0,H/2],mats[p.body_material]);
    for(const c of cs)box(g,'wall-stub',[p.stub_thickness,p.stub_width,H],[p.xmax-p.stub_thickness/2,c.center_mm[1],H/2],mats[p.body_material]);
    if(p.ramp!==false){
        const geo=extrudedLeadProfile([[p.wall_inner,H-p.ramp_height],[p.wall_inner+p.ramp_projection,H-p.ramp_height],[p.wall_inner,H]],p.ramp_base);
        mesh(g,'friction-ramp',geo,mats[p.body_material]);
    }
    pinInstances(g,p,cs,lod==='LOD0'?0:-p.tail,p.post_top,mats[p.lead_material]);
}

function screwBody(g,p,lod,cs,mats,{L,W,H,x,screwX}){
    const windows=cs.map(c=>({min:[x+W/2-p.window_depth,c.center_mm[1]-p.window_width/2,p.window_z-p.window_height/2],max:[x+W/2,c.center_mm[1]+p.window_width/2,p.window_z+p.window_height/2]}));
    carvedBox(g,'housing-base',[x-W/2,-L/2,0],[x+W/2,L/2,H-p.pocket_depth],windows,mats[p.body_material]);
    const s=new THREE.Shape();s.moveTo(x-W/2,-L/2);s.lineTo(x+W/2,-L/2);s.lineTo(x+W/2,L/2);s.lineTo(x-W/2,L/2);s.closePath();
    for(const c of cs){const h=new THREE.Path();h.absarc(screwX,c.center_mm[1],p.screw_diameter/2,0,Math.PI*2,true);s.holes.push(h);}
    const geo=new THREE.ExtrudeGeometry(s,{depth:p.pocket_depth,bevelEnabled:false,curveSegments:p.segments[lod]/2});mesh(g,'pocket-top',geo,mats[p.body_material],[0,0,H-p.pocket_depth]);
    for(const c of cs){
        const z=H-p.pocket_depth+p.screw_head_height;
        cylinder(g,'screw-head',p.screw_diameter,p.screw_head_height,'Z',[screwX,c.center_mm[1],z-p.screw_head_height/2],mats.MAT_STEEL_STAINLESS,p.segments[lod],{role:'screw',basis:'COSMETIC_PROVISIONAL'});
        decal(g,'screw-slot',new THREE.PlaneGeometry(p.slot_length,p.slot_width),[screwX,c.center_mm[1],z],mats.MAT_PLASTIC_BLACK,false,{basis:'COSMETIC_PROVISIONAL'});
        const m=decal(g,'wire-entry-back',new THREE.PlaneGeometry(p.window_width,p.window_height),[x+W/2-p.window_depth,c.center_mm[1],p.window_z],mats.MAT_PLASTIC_BLACK,false,{role:'wire_entry',basis:'COSMETIC_PROVISIONAL'});m.rotation.set(Math.PI/2,Math.PI/2,0);
    }
}
function screw(g,p,lod,cs,mats){
    screwBody(g,p,lod,cs,mats,{L:p.N*p.pitch,W:p.width,H:p.height,x:p.offset[0],screwX:0});
    pinInstances(g,p,cs,lod==='LOD0'?0:-p.tail,0,mats[p.lead_material]);
}
function plug(g,p,lod,cs,mats){
    const L=p.N*p.pitch+2,header=new THREE.Group(),plug=new THREE.Group();header.name='header';plug.name='plug';g.add(header,plug);
    carvedBox(header,'shroud',[p.header_rear,-L/2,0],[p.header_rear+p.width,L/2,p.height],[{min:[p.header_rear+p.wall,-L/2+p.wall,p.wall],max:[p.header_rear+p.width,L/2-p.wall,p.height-p.wall]}],mats[p.body_material]);
    const t=p.pin/2,z=p.internal_pin_z,end=p.internal_pin_end;
    const geo=extrudedLeadProfile([[-t,lod==='LOD0'?0:-p.tail],[t,lod==='LOD0'?0:-p.tail],[t,z-t],[end,z-t],[end,z+t],[-t,z+t]],p.pin);
    instances(header,'terminals',geo,mats[p.lead_material],cs.map(c=>({terminal:c.terminal,position:[0,c.center_mm[1],0]})));
    screwBody(plug,p,lod,cs,mats,{L:p.N*p.pitch,W:p.plug_length,H:p.plug_height,x:(p.plug_xmin+p.plug_xmax)/2,screwX:p.screw_x});
    plug.userData={role:'mating_plug',unresolved_features:['coding_profile'],cosmetic_basis:'COSMETIC_PROVISIONAL'};
    if(!p.assembled)plug.position.x=p.plug_length;
}
const GENERATORS={'PKG-HDR_PIN':header,'PKG-HDR_SOCKET':header,'PKG-JST_PH':wire,'PKG-JST_XH':wire,'PKG-JST_SH':sh,'PKG-MOLEX_KK':kk,'PKG-SCREW_TERM':screw,'PKG-PLUG_TERM':plug};
export function generateHeaderConnector(p,lod,contacts,materials){const g=new THREE.Group();GENERATOR_CHECK(p.family);GENERATORS[p.family](g,p,lod,contacts,materials);return g;}
function GENERATOR_CHECK(family){if(!GENERATORS[family])throw new RangeError('Unsupported connector family');}
export const HEADER_CONNECTOR_FAMILIES=Object.freeze(Object.keys(GENERATORS));
