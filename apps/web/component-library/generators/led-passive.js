import * as THREE from '../../vendor/three.module.js';
import { markingGeometry } from '../../visual-assets.js';
import { box } from './leaded-body.js';
import { mesh, cylinder, decal, textDecal } from './discrete-primitives.js';
import { chipSurface } from './chip-2t.js';
import { roundBentLead } from './axial-lead.js';
import { polygon, prism, outline, roundOutline, revolved, cap, ringDecal, sidePatch } from './led-passive-shapes.js';

const meta=(terminal,extra={})=>({terminal:String(terminal),...extra});
function leadBox(g,name,size,center,mat,terminal){const m=box(g,name,size,center,mat);m.userData.terminal=String(terminal);return m;}
function lensMaterial(p,mats){const m=mats[p.lens==='clear'?'MAT_PLASTIC_CLEAR':'MAT_PLASTIC_DIFFUSED'].clone();m.opacity=p.lens==='clear'?p.clear_opacity:p.lens_opacity;if(p.lens!=='clear')m.color.set(p.led_color);m.userData={...m.userData,led_color:p.led_color,role:'lens',pickable:true};return m;}
function marker(g,p,center,size,mat,role='cathode_mark'){return decal(g,role,new THREE.PlaneGeometry(...size),center,mat,false,{role,terminal:'1',side:'-X'});}
function roundLeads(g,p,cs,mats,top=p.standoff){for(const c of cs){const m=cylinder(g,`terminal-${c.terminal}`,p.lead_diameter,top+p.tail,'Z',[c.center_mm[0],c.center_mm[1],(top-p.tail)/2],mats[p.lead_material],12,meta(c.terminal));
    // Exact cap centers avoid sub-ULP cracks in ray tests after the Y-to-Z rotation.
    const a=m.geometry.attributes.position;for(let i=0;i<a.array.length;i++)if(Math.abs(a.array[i])<1e-12)a.array[i]=0;
}}

function axial(g,p,lod,mats) {
    const seg=p.segments[lod],z=p.standoff+p.body_h/2;
    if(p.cement) {
        chipSurface(g,mats,{L:p.body_x,W:p.body_y,H:p.body_h,radius:lod==='LOD0'?0:p.edge_radius,offset:[0,0,p.standoff],classify:()=>['body',p.body_material]});
    } else {
        const len=p.body_x-2*p.cap_length;
        if(lod==='LOD2'&&!p.cap_length){
            const r=p.body_h/2,e=p.edge_radius,prof=[[0,-p.body_x/2],[r-e,-p.body_x/2],[r,-p.body_x/2+e],[r,p.body_x/2-e],[r-e,p.body_x/2],[0,p.body_x/2]];
            const m=revolved(g,'body',prof,seg,mats[p.body_material]);m.rotation.y=Math.PI/2;m.position.z=z;
        }else cylinder(g,'body',p.body_h,len,'X',[0,0,z],mats[p.body_material],seg);
        if(p.cap_length)for(const sign of [-1,1])cylinder(g,'end-cap',p.body_h*2*p.cap_radius_ratio,p.cap_length,'X',[sign*(p.body_x-p.cap_length)/2,0,z],mats.MAT_STEEL_STAINLESS,seg);
        if(lod!=='LOD0'||p.family==='PKG-AXIAL_IND')for(let i=0;i<p.bands.length;i++){
            const [a,b]=p.bands[i];ringDecal(g,`band-${i+1}`,p.body_h/2,(b-a)*p.body_x,'X',[(a+b-1)*p.body_x/2,0,z],mats[`MAT_BAND_${p.band_colors[i]}`],seg,{role:'color_band_decal',band_index:i,content_basis:'CALLER_OR_DEMO_COLOR_CODE'});
        }
    }
    for(const sign of [-1,1]){const m=mesh(g,`terminal-${sign<0?1:2}`,roundBentLead({bodyEdge:p.body_x/2,holeX:p.pitch/2,axisHeight:z,diameter:p.lead_diameter,tail:p.tail,radius:p.bend_radius,lod,segments:lod==='LOD2'?16:8}),mats[p.lead_material],[0,0,0],meta(sign<0?1:2));if(sign<0)m.rotation.z=Math.PI;}
}
function vent(g,p,z,r,mats,seg) {
    const s=new THREE.Shape();s.absarc(0,0,r,0,2*Math.PI,false);
    const w=p.vent_width/2,l=p.diameter*p.vent_span/2;
    const h=polygon([[-w,-l],[w,-l],[w,-w],[l,-w],[l,w],[w,w],[w,l],[-w,l],[-w,w],[-l,w],[-l,-w],[-w,-w]]);s.holes.push(h);
    prism(g,'vent-scored-top',s,p.vent_depth,z-p.vent_depth,mats.MAT_ALUMINUM_CAN,seg,{role:'vent_score',depth_mm:p.vent_depth});
    const floor=mats.MAT_ALUMINUM_CAN.clone();floor.color.multiplyScalar(.3);
    decal(g,'vent-groove-floor',new THREE.ShapeGeometry(h),[0,0,z-p.vent_depth],floor,false,{role:'vent_score_floor',geometry_basis:'recessed metal with cosmetic darkening'});
}
function can(g,p,lod,cs,mats) {
    const seg=p.segments[lod],smd=p.kind==='can_smd',seat=smd?p.base_height:p.seat_height,z=p.standoff+seat,top=z+p.body_h,r=p.diameter/2;
    if(smd){prism(g,'positive-chamfer-base',outline(p.base,p.base,p.chamfer,true),p.base_height-p.lead_thickness,p.lead_thickness,mats.MAT_PLASTIC_BLACK,seg,{role:'positive_base_chamfer',side:'-X',terminal:'1'});
        for(const c of cs){const [x,y]=c.center_mm;leadBox(g,`terminal-${c.terminal}`,[p.foot,p.lead_width,p.lead_thickness],[x,y,p.lead_thickness/2],mats[p.lead_material],c.terminal);
            const sign=Math.sign(x);leadBox(g,'terminal-upbend',[p.lead_thickness,p.lead_width,p.upbend],[x+sign*(p.foot-p.lead_thickness)/2,0,p.upbend/2],mats[p.lead_material],c.terminal);}
    }else {if(seat)cylinder(g,'seat-disc',p.diameter-1,seat,'Z',[0,0,p.standoff+seat/2],mats.MAT_PLASTIC_BLACK,seg);roundLeads(g,p,cs,mats,z);}
    const wall=new THREE.CylinderGeometry(r,r,p.body_h-p.vent_depth,seg,1,true);wall.rotateX(Math.PI/2);
    mesh(g,'can-metal',wall,mats.MAT_ALUMINUM_CAN,[0,0,z+(p.body_h-p.vent_depth)/2]);
    mesh(g,'can-top-floor',new THREE.CircleGeometry(r,seg),mats.MAT_ALUMINUM_CAN,[0,0,top-p.vent_depth]);
    const rim=mesh(g,'can-bottom-rim',new THREE.RingGeometry(r*.82,r,seg),mats.MAT_ALUMINUM_CAN,[0,0,z]);rim.rotation.x=Math.PI;
    cylinder(g,'seal',p.diameter*.82,p.seal_height,'Z',[0,0,z+p.seal_height/2],mats.MAT_RUBBER_SEAL,seg,{role:'bottom_seal'});
    // The rubber seal occupies the bottom opening; no coincident metal cap.
    const sleeve=ringDecal(g,'sleeve-decal',r,p.body_h-p.seal_height,'Z',[0,0,z+(p.body_h+p.seal_height)/2],mats[p.sleeve_material],seg,{role:'sleeve_decal'});sleeve.renderOrder=1;
    const ring=decal(g,'sleeve-top-overlap',new THREE.RingGeometry(Math.max(r-p.top_rim,r*.65),r,seg),[0,0,top],mats[p.sleeve_material],false,{role:'sleeve_decal'});ring.renderOrder=1;
    if(p.diameter>=p.vent_min_diameter)vent(g,p,top,r,mats,seg);else cylinder(g,'can-top',p.diameter,p.vent_depth,'Z',[0,0,top-p.vent_depth/2],mats.MAT_ALUMINUM_CAN,seg);
    const stripe=sidePatch(g,'negative-stripe',r,z+p.seal_height,top-p.vent_depth,p.stripe_angle,mats.MAT_SILKSCREEN_WHITE,8,{role:'negative_stripe',terminal:'2',side:'+X'});stripe.material.polygonOffsetFactor=-4;stripe.material.polygonOffsetUnits=-4;stripe.renderOrder=2;
    if(smd){const s=new THREE.Shape();s.moveTo(0,0);s.absarc(0,0,Math.max(r-p.top_rim,r*.65),-Math.PI/2,Math.PI/2,false);s.closePath();decal(g,'negative-top-segment',new THREE.ShapeGeometry(s,seg/4),[0,0,top],mats.MAT_EPOXY_BLACK,false,{role:'negative_mark',terminal:'2',side:'+X'});}
    if(lod==='LOD2')ringDecal(g,'crimp-groove',r,p.bead_width,'Z',[0,0,z+p.bead_z],mats.MAT_RUBBER_SEAL,seg,{role:'groove_appearance',geometry_basis:'cosmetic seam; outer envelope unchanged'});
}
function tantalum(g,p,lod,mats) {
    const L=p.body_x,W=p.body_y,H=p.body_h,b=p.bevel;
    chipSurface(g,mats,{L,W,H,xCuts:[-L/2+p.foot,L/2-p.foot,-L/2+b],yCuts:[-p.lead_width/2,p.lead_width/2],zCuts:[p.lead_thickness,H*p.wrap_height_fraction,H-b],classify:(q,side)=>{
        const end=Math.abs(q[0])>L/2-p.foot+1e-9;
        if(Math.abs(q[1])<=p.lead_width/2+1e-9&&((side==='bottom'&&end)||(side==='end'&&q[2]<H*p.wrap_height_fraction)))return [`terminal-${q[0]<0?1:2}`,p.lead_material];
        return ['body',p.body_material];
    }});
    for(const m of g.children){const a=m.geometry.attributes.position;for(let i=0;i<a.count;i++){
        let x=a.getX(i),y=a.getY(i),z=a.getZ(i);if(x<-L/2+b&&z>H-b){if(Math.abs(z-H)<1e-6)x=-L/2+b;else z=H-b;}
        if(lod==='LOD2'&&z>H/2){const shrink=(z-H/2)*Math.tan(p.draft_degrees*Math.PI/180);x*=1-2*shrink/L;y*=1-2*shrink/W;}
        a.setXYZ(i,x,y,z);
    }m.geometry.computeVertexNormals();}
    marker(g,p,[-L/2+b+p.stripe_width/2,0,H],[p.stripe_width,W*.75],mats.MAT_SILKSCREEN_WHITE,'positive_bar');
}
function radialBody(g,p,lod,cs,mats) {
    const seg=p.segments[lod],z=p.standoff;
    if(p.kind==='disc'){
        cylinder(g,'body',p.body_x,p.body_y,'Y',[0,0,z+p.body_h/2],mats[p.body_material],seg);
        // Exit at the actual lower circle, not an unattached lead at its tangent.
        const exit=z+p.body_h/2-Math.sqrt((p.body_x/2)**2-(p.pitch/2)**2)+p.lead_diameter/2;roundLeads(g,p,cs,mats,exit);
    }else if(p.kind==='mica'){
        const s=roundOutline(p.body_x,p.body_h,p.edge_radius),m=prism(g,'body',s,p.body_y,0,mats[p.body_material],seg);m.rotation.x=Math.PI/2;m.position.set(0,p.body_y/2,z+p.body_h/2);roundLeads(g,p,cs,mats);
    }else {
        chipSurface(g,mats,{L:p.body_x,W:p.body_y,H:p.body_h,radius:lod==='LOD0'?0:p.edge_radius,offset:[0,0,z],classify:(q,side)=>side==='bottom'?['resin-face','MAT_RUBBER_SEAL']:['body',p.body_material]});roundLeads(g,p,cs,mats);
    }
}
function ledTht(g,p,lod,cs,mats) {
    const seg=p.segments[lod],mat=lensMaterial(p,mats),z=p.standoff,H=p.body_h;
    if(p.kind==='led_rect') {
        const L=p.body_x,b=p.bevel,s=polygon([[-L/2,0],[L/2,0],[L/2,H],[-L/2+b,H],[-L/2,H-b]]);
        const m=prism(g,'lens',s,p.body_y,0,mat,seg,{role:'lens',cathode_flat_side:'-X'});m.rotation.x=Math.PI/2;m.position.set(0,p.body_y/2,z);
    }else {
        const r=p.body_x/2,f=p.flange_diameter/2,t=p.flange_thickness,base=z+H-r;
        const profile=[[0,z],[f,z],[f,z+t],[r,z+t],[r,base]];
        for(let i=1;i<=seg/4;i++){const a=Math.PI/2*i/(seg/4);profile.push([r*Math.cos(a),base+r*Math.sin(a)]);}
        revolved(g,'lens',profile,seg,mat,-f+p.flat_depth,{role:'lens',cathode_flat_side:'-X'});
    }
    for(const c of cs){const tail=p.tail+(c.terminal==='2'&&lod==='LOD2'?p.anode_extra:0);leadBox(g,`terminal-${c.terminal}`,[p.lead_width,p.lead_thickness,z+tail],[c.center_mm[0],0,(z-tail)/2],mats[p.lead_material],c.terminal);}
    if(lod==='LOD2'&&p.lens==='clear'){
        cylinder(g,'cathode-cup',p.cup_diameter,p.cup_height,'Z',[p.pitch*p.cup_x_fraction,0,z+p.body_h*.35],mats.MAT_NICKEL,seg,{role:'internal_reflector',terminal:'1',provisional:true});
        for(const c of cs)leadBox(g,'internal-frame',[p.lead_width,p.lead_thickness,p.body_h*.35],[c.center_mm[0],0,z+p.body_h*.175],mats[p.lead_material],c.terminal);
    }
}
function ledChip(g,p,lod,mats) {
    const L=p.body_x,W=p.body_y,H=p.body_h-p.lens_height,F=p.foot;
    chipSurface(g,mats,{L,W,H,xCuts:[-L/2+F,L/2-F],zCuts:[p.wrap_height],classify:(q,side)=>{
        if((side==='bottom'&&Math.abs(q[0])>L/2-F+1e-9)||(side==='end'&&q[2]<p.wrap_height))return [`terminal-${q[0]<0?1:2}`,p.lead_material];
        return ['body',p.body_material];
    }});
    const mat=lensMaterial(p,mats),w=L*p.window_x_fraction,h=W*p.window_y_fraction;
    if(lod==='LOD2'){const m=cap(g,'lens',((w/2)**2+p.lens_height**2)/(2*p.lens_height),p.lens_height,H,p.segments[lod],mat,{role:'lens'});m.scale.y=h/w;}
    else box(g,'lens',[w,h,p.lens_height],[0,0,H+p.lens_height/2],mat).userData.role='lens';
    marker(g,p,[-L/2+F/2,0,H],[p.stripe_width,W*.7],mats.MAT_EPOXY_BLACK);
}
function ledCavity(g,p,lod,cs,mats) {
    const seg=p.segments[lod],H=p.body_h,z0=p.lead_thickness,base=H-p.cavity_depth;
    // Partition the lower case surface into plastic and metal. A metal box
    // over an identical plastic end face would produce depth-fighting stripes.
    const lower=new THREE.Group();
    chipSurface(lower,mats,{L:p.body_x,W:p.body_y,H:base-z0,xCuts:[-p.body_x/2+p.chamfer],yCuts:[p.body_y/2-p.chamfer,...new Set(cs.flatMap(c=>[c.center_mm[1]-p.lead_width/2,c.center_mm[1]+p.lead_width/2]))],zCuts:[p.wrap_height-z0],offset:[0,0,z0],classify:(q,side)=>{
        const c=side==='end'&&q[2]<p.wrap_height-z0?cs.find(c=>Math.sign(c.center_mm[0])===Math.sign(q[0])&&Math.abs(q[1]-c.center_mm[1])<p.lead_width/2+1e-9):null;
        return c?[`terminal-${c.terminal}`,p.lead_material]:['body-base',p.body_material];
    }});
    for(const m of lower.children){const a=m.geometry.attributes.position;for(let i=0;i<a.count;i++){const x=a.getX(i),y=a.getY(i),dx=x+p.body_x/2,dy=p.body_y/2-y;if(dx+dy<p.chamfer-1e-6){if(dx<1e-6)a.setY(i,p.body_y/2-p.chamfer);else a.setX(i,-p.body_x/2+p.chamfer);}}m.geometry.computeVertexNormals();}g.add(lower);
    const s=outline(p.body_x,p.body_y,p.chamfer),h=new THREE.Path();h.absarc(0,0,p.cavity_diameter/2,0,2*Math.PI,true);s.holes.push(h);prism(g,'cavity-wall',s,p.cavity_depth,base,mats[p.body_material],seg,{role:'pin1_chamfer',terminal:'1',side:'-X'});
    const mat=lensMaterial(p,mats),r=p.cavity_diameter/2;
    // Single transparent closed resin surface, with optional cap curvature.
    const prof=[[0,base],[r,base],[r,H-p.lens_height]];
    if(lod==='LOD2') {const R=(r*r+p.lens_height*p.lens_height)/(2*p.lens_height),a=Math.asin(r/R);for(let i=0;i<=seg/4;i++){const q=a*(1-i/(seg/4));prof.push([R*Math.sin(q),H-R+R*Math.cos(q)]);}}
    else prof.push([r,H],[0,H]);
    revolved(g,'lens',prof,seg,mat,null,{role:'lens'});
    for(const c of cs){const [x,y]=c.center_mm;leadBox(g,`terminal-${c.terminal}`,[p.foot,p.lead_width,p.lead_thickness],[x,y,p.lead_thickness/2],mats[p.lead_material],c.terminal);}
    if(lod==='LOD2'&&p.count>2)for(let i=0;i<3;i++){const m=mats.MAT_PLASTIC_DIFFUSED.clone();m.color.set(p.die_colors[i]);m.transparent=false;m.depthWrite=true;box(g,'rgb-die',[p.die_size,p.die_size,p.lead_thickness],[(i-1)*p.die_size*1.5,0,base+p.lead_thickness/2],m).userData.role='cosmetic_die';}
}
function ledPower(g,p,lod,mats) {
    box(g,'body',[p.body_x,p.body_y,p.base_h-p.lead_thickness],[0,0,(p.base_h+p.lead_thickness)/2],mats[p.body_material]);
    const phosphor=mats.MAT_PLASTIC_WHITE.clone();phosphor.color.set(p.led_color);decal(g,'phosphor',new THREE.PlaneGeometry(p.phosphor_size,p.phosphor_size),[0,0,p.base_h],phosphor,false,{role:'emitter_window'});
    cap(g,'lens',p.lens_radius,p.lens_h,p.base_h,p.segments[lod],lensMaterial(p,mats),{role:'lens'});
    for(const sign of [-1,1])leadBox(g,`terminal-${sign<0?1:2}`,[p.foot,p.lead_width,p.lead_thickness],[sign*Math.abs(p.pin1[0]),0,p.lead_thickness/2],mats[p.lead_material],sign<0?1:2);
    leadBox(g,'thermal-pad',[...p.thermal_size,p.lead_thickness],[0,0,p.lead_thickness/2],mats[p.lead_material],3).userData.role='thermal_pad';
    marker(g,p,[-p.body_x/2+p.marker_size/2,p.body_y/2-p.marker_size/2,p.base_h],[p.marker_size,p.marker_size],mats.MAT_EPOXY_BLACK);
}
function ledStar(g,p,lod,cs,mats,profiles) {
    const r=p.across_flats/Math.sqrt(3),s=polygon(Array.from({length:6},(_,i)=>[r*Math.cos(i*Math.PI/3),r*Math.sin(i*Math.PI/3)]));
    prism(g,'mcpcb',s,p.board_thickness,0,mats.MAT_COPPER,p.segments[lod]);decal(g,'mask',new THREE.ShapeGeometry(s),[0,0,p.board_thickness],mats.MAT_MCPCB_MASK_WHITE,false,{role:'solder_mask_decal'});
    const emitter=new THREE.Group();ledPower(emitter,{...profiles[p.emitter_profile],led_color:p.led_color,lens:p.lens},lod,mats);emitter.position.z=p.board_thickness;emitter.name='emitter-instance';emitter.userData={geometry_source_id:p.emitter_profile,electrical_authority:false};g.add(emitter);
    for(const c of cs){const [x,y,z]=c.center_mm;leadBox(g,`terminal-${c.terminal}`,[...p.wire_pad_size,p.lead_thickness],[x,y,z-p.lead_thickness/2],mats.MAT_GOLD,c.terminal);}
    const padX=Math.abs(p.wire_pad_xy[0][0]);
    for(const sign of [-1,1]){decal(g,'wire-pad-minus',new THREE.PlaneGeometry(.9,.18),[sign*padX,0,p.board_thickness],mats.MAT_EPOXY_BLACK,false,{role:sign<0?'cathode_mark':'anode_mark',side:sign<0?'-X':'+X'});if(sign>0)decal(g,'wire-pad-plus',new THREE.PlaneGeometry(.18,.9),[padX,0,p.board_thickness],mats.MAT_EPOXY_BLACK);}
}
export function generateLedPassive(p,lod,marking,contacts,mats,profiles) {
    const g=new THREE.Group();
    if(p.kind==='axial')axial(g,p,lod,mats);
    else if(p.kind.startsWith('can'))can(g,p,lod,contacts,mats);
    else if(p.kind==='tantalum')tantalum(g,p,lod,mats);
    else if(['disc','mica','film'].includes(p.kind))radialBody(g,p,lod,contacts,mats);
    else if(['led_tht','led_rect'].includes(p.kind))ledTht(g,p,lod,contacts,mats);
    else if(p.kind==='led_chip')ledChip(g,p,lod,mats);
    else if(p.kind==='led_cavity')ledCavity(g,p,lod,contacts,mats);
    else if(p.kind==='led_power')ledPower(g,p,lod,mats);
    else if(p.kind==='led_star')ledStar(g,p,lod,contacts,mats,profiles);
    else throw new RangeError('Unknown Stage 5 geometry');
    if(lod!=='LOD0'&&marking&&!p.kind.startsWith('led')&&!(p.kind==='axial'&&!p.cement)) {
        const front=['disc','mica'].includes(p.kind),canBody=p.kind.startsWith('can'),top=p.standoff+p.body_h+(p.base_height??p.seat_height??0);
        if(canBody){
            const geometry=markingGeometry(marking,p.body_x*p.mark_width_fraction,p.body_y*p.mark_height_fraction),a=geometry.attributes.position,r=p.diameter/2;
            for(let i=0;i<a.count;i++){const angle=a.getX(i)/r,z=a.getY(i)+p.standoff+(p.base_height??p.seat_height??0)+p.body_h*.55;a.setXYZ(i,r*Math.sin(angle),-r*Math.cos(angle),z);}
            geometry.computeVertexNormals();const label=decal(g,'sleeve-text-decal',geometry,[0,0,0],mats[p.mark_color],false,{role:'printed_sleeve_decal',content_basis:'CALLER_SUPPLIED_VISUAL_TEXT'});label.renderOrder=3;label.material.polygonOffsetFactor=-5;label.material.polygonOffsetUnits=-5;
        }else {const center=front?[0,-p.body_y/2,p.standoff+p.body_h*.6]:[0,0,top];textDecal(g,marking,p.body_x*p.mark_width_fraction,p.body_y*p.mark_height_fraction,center,mats[p.mark_color],front);}
    }
    return g;
}
