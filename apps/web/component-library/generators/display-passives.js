import * as THREE from '../../vendor/three.module.js';
import {box} from './leaded-body.js';
import {cylinder,decal} from './discrete-primitives.js';
import {prism,outline,polygon} from './led-passive-shapes.js';
import {instances} from './instanced-terminals.js';
import {chipSurface} from './chip-2t.js';

export const DISPLAY_PASSIVE_FAMILIES=Object.freeze(['PKG-SHUNT','PKG-SIP_NET','PKG-CHIP_ARRAY','PKG-TRIMMER','PKG-TRIMMER_SMD','PKG-POT_ROTARY','PKG-7SEG','PKG-LED_MATRIX','PKG-LCD_CHARACTER','PKG-OLED_MODULE']);
function plate(g,name,W,L,h,z,holes,m,seg,offset=[0,0]){
    const s=outline(W,L);for(const [x,y,d] of holes){const hole=new THREE.Path();hole.absarc(x-offset[0],y-offset[1],d/2,0,Math.PI*2,true);s.holes.push(hole);}
    const part=prism(g,name,s,h,z,m,seg,{role:'sub_body',holes_mm:holes});part.position.x=offset[0];part.position.y=offset[1];return part;
}
function ringDecal(g,name,x,y,z,outer,inner,m,seg){const geo=new THREE.RingGeometry(inner/2,outer/2,seg);return decal(g,name,geo,[x,y,z],m);}
function shunt(g,p,lod,m){
    const block=(p.width-p.element)/2;
    box(g,'resistive-alloy',[p.element,p.length,p.height],[0,0,p.height/2],m[p.body_material]);
    for(const sign of [-1,1]){const c=p.contacts[sign<0?0:1],part=plate(g,'copper-block',block,p.length,p.height,0,[[...c.center_mm.slice(0,2),p.bolt_diameter]],m.MAT_COPPER,p.segments[lod],[sign*(p.element+block)/2,0]);part.userData.terminal=c.terminal;}
}
function array(g,p,lod,m){
    const xcut=p.width/2-p.terminal_length,ycuts=p.contacts.flatMap(c=>[c.center_mm[1]-p.terminal_width/2,c.center_mm[1]+p.terminal_width/2]);
    chipSurface(g,m,{L:p.width,W:p.length,H:p.height,xCuts:[-xcut,xcut],yCuts:ycuts,classify:([x,y],side)=>{
        const c=p.contacts.find(c=>Math.sign(c.center_mm[0])===Math.sign(x)&&Math.abs(y-c.center_mm[1])<p.terminal_width/2+1e-8);
        return c&&Math.abs(x)>=xcut?[`terminal-${c.terminal}`,p.lead_material]:['body-'+side,side==='top'?'MAT_RESISTOR_COAT_BLACK':p.body_material];
    }});
}
function trimmer(g,p,lod,m){
    const [x,y,d]=p.screw,depth=Math.max(p.rotor_depth,Math.min(p.slot[2],p.height)),H=p.height;
    const shape=outline(p.width,p.length),hole=new THREE.Path();hole.absarc(x,y,d/2,0,Math.PI*2,true);shape.holes.push(hole);
    prism(g,'housing',shape,H,0,m[p.body_material],p.segments[lod]);cylinder(g,'recess-floor',d,H-depth,'Z',[x,y,(H-depth)/2],m[p.body_material],p.segments[lod]);
    // Two clipped circular sectors leave a real screwdriver slot at every LOD.
    const points=Array.from({length:p.segments[lod]},(_,i)=>[d/2*Math.cos(i*2*Math.PI/p.segments[lod]),d/2*Math.sin(i*2*Math.PI/p.segments[lod])]);
    for(const sign of [-1,1]){const bound=p.slot[1]/2,clipped=[];
        for(let i=0;i<points.length;i++){const a=points[i],b=points[(i+1)%points.length],ina=sign*a[1]>=bound,inb=sign*b[1]>=bound;if(ina)clipped.push(a);if(ina!==inb){const f=(sign*bound-a[1])/(b[1]-a[1]);clipped.push([a[0]+f*(b[0]-a[0]),sign*bound]);}}
        const rotor=prism(g,'slotted-rotor',polygon(clipped),depth,H-depth,m[p.shape==='trimmer'&&p.tail?'MAT_BRASS':'MAT_PLASTIC_WHITE'],p.segments[lod]);rotor.position.set(x,y,0);
    }
}
function rotary(g,p,lod,m){cylinder(g,'metal-can',p.width,p.height,'Z',[0,0,p.height/2],m[p.body_material],p.segments[lod]);cylinder(g,'bushing',p.bushing,p.bushing_length,'Z',[0,0,p.height+p.bushing_length/2],m.MAT_BRASS,p.segments[lod]);cylinder(g,'shaft',p.shaft,p.shaft_length,'Z',[0,0,p.height+p.bushing_length+p.shaft_length/2],m.MAT_NICKEL,p.segments[lod]);}
function displays(g,p,lod,m){
    box(g,'display-housing',[p.width,p.length,p.height],[0,0,p.height/2],m[p.body_material]);
    const mat=m.MAT_LED_SEGMENT_WHITE,z=p.height;
    if(p.shape==='matrix'){
        const mark=mat.clone();mark.polygonOffset=true;mark.polygonOffsetFactor=-2;mark.polygonOffsetUnits=-2;
        instances(g,'dot-windows',new THREE.CircleGeometry(p.dot_diameter/2,p.segments[lod]),mark,Array.from({length:64},(_,i)=>({position:[(i%8-3.5)*p.dot_pitch,(3.5-Math.floor(i/8))*p.dot_pitch,z]}))).userData.role='separate_visual_decal';return;
    }
    const h=p.digit_height,q=p.digit_layout,stroke=p.stroke*h;
    for(let digit=0;digit<p.digits;digit++){
        const center=(p.digits-1-2*digit)*p.length/(2*p.digits),bias=q.horizontal_bias*h;
        const segments=[[0,q.bar_y*h,q.bar_length*h,stroke],[0,0,q.bar_length*h,stroke],[0,-q.bar_y*h,q.bar_length*h,stroke],...[-1,1].flatMap(a=>[-1,1].map(b=>[a*q.vertical_x*h,b*q.vertical_y*h,stroke,q.vertical_length*h]))];
        for(const [sx,sy,sw,sh] of segments){const mark=decal(g,'digit-segment',new THREE.PlaneGeometry(sw,sh),[sy,center-sx-bias,z],mat,false,{digit,role:'segment_decal',digit_up:'+X'});mark.rotation.z=-Math.PI/2;}
        decal(g,'decimal-point',new THREE.CircleGeometry(p.dp_diameter*h/2,p.segments[lod]),[q.dp_y*h,center-q.dp_x*h-bias,z],mat,false,{digit,role:'decimal_point',corner:'-X,-Y'});
    }
}
function module(g,p,lod,m){
    const z=p.standoff,t=p.pcb_thickness,holes=[...p.mounts,...p.contacts.map(c=>[...c.center_mm.slice(0,2),p.header_hole])],seg=p.segments[lod];
    const pcbGroup=new THREE.Group();pcbGroup.name='module-pcb';pcbGroup.userData.role='sub_body';g.add(pcbGroup);
    plate(pcbGroup,'pcb',p.width,p.length,t,z,holes,m[p.body_material],seg,p.offset);
    for(const c of p.contacts)for(const hz of [z,z+t]){const d=ringDecal(pcbGroup,'header-annulus',...c.center_mm.slice(0,2),hz,p.header_pad,p.header_hole,m.MAT_TIN_MATTE,seg);if(hz===z)d.rotation.x=Math.PI;}
    if(p.shape==='lcd'){
        for(const [x,y,d] of p.mounts)for(const hz of [z,z+t]){const mark=ringDecal(pcbGroup,'mounting-annulus',x,y,hz,p.mount_pad,d,m.MAT_TIN_MATTE,seg);if(hz===z)mark.rotation.x=Math.PI;}
        const top=z+p.height,polarizer=top-p.polarizer_inset,stack=new THREE.Group();stack.name='lcd-stack';stack.userData.role='sub_body';g.add(stack);
        box(stack,'glass-stack',[...p.stack,polarizer-z-t],[0,0,(polarizer+z+t)/2],m.MAT_PLASTIC_BLACK);
        const frame=outline(...p.bezel),hole=new THREE.Path(outline(...p.view).getPoints());frame.holes.push(hole);prism(g,'metal-bezel',frame,p.bezel_stock,top-p.bezel_stock,m.MAT_STEEL_STAINLESS,seg,{role:'sub_body'});
        decal(stack,'polarizer',new THREE.PlaneGeometry(...p.view),[0,0,polarizer],m.MAT_LCD_POLARIZER_GRAY);
        const pixels=[];for(let row=0;row<2;row++)for(let col=0;col<16;col++)for(let dy=0;dy<8;dy++)for(let dx=0;dx<5;dx++)pixels.push({position:[(col-7.5)*p.character_pitch[0]+(dx-2)*p.dot_pitch[0],(.5-row)*p.character_pitch[1]+(3.5-dy)*p.dot_pitch[1],polarizer]});
        const ink=m.MAT_EPOXY_DARKGRAY.clone();ink.polygonOffset=true;ink.polygonOffsetFactor=-3;ink.polygonOffsetUnits=-3;
        instances(stack,'character-pixels',new THREE.PlaneGeometry(...p.dot),ink,pixels).userData={role:'separate_visual_decal',rows:2,columns:16,text_direction:'+X',electrical_authority:false};
    }else{
        const panelY=p.offset[1]+(p.length-p.panel[1])/2,bottom=z+t+p.spacer;
        box(g,'panel-spacer',[p.panel[0],p.panel[1],p.spacer],[0,panelY,z+t+p.spacer/2],m.MAT_PLASTIC_BLACK).userData.role='sub_body';
        box(g,'oled-panel',p.panel,[0,panelY,bottom+p.panel[2]/2],m.MAT_OLED_PANEL_BLACK).userData.role='sub_body';
        decal(g,'active-window',new THREE.PlaneGeometry(...p.active),[0,panelY,z+p.height],m.MAT_GLASS);
        box(g,'header-housing',p.header,[0,p.contacts[0].center_mm[1],p.header[2]/2],m.MAT_PLASTIC_BLACK).userData.role='sub_body';
    }
}
export function generateDisplayPassive(p,lod,cs,m){
    const g=new THREE.Group();
    if(p.shape==='shunt')shunt(g,p,lod,m);else if(p.shape==='array')array(g,p,lod,m);else if(p.shape==='trimmer')trimmer(g,p,lod,m);else if(p.shape==='rotary')rotary(g,p,lod,m);else if(['lcd','oled'].includes(p.shape))module(g,p,lod,m);else if(['sevenseg','matrix'].includes(p.shape))displays(g,p,lod,m);else box(g,'sip-body',[p.width,p.length,p.height],[0,0,p.height/2],m[p.body_material]);
    if(p.shape!=='array')for(const c of cs){if(c.type==='bolt')continue;const smd=c.type==='smd',h=smd?p.pad_stock:p.tail+p.standoff+(['lcd','oled'].includes(p.shape)?p.pcb_thickness:0),pos=[...c.center_mm.slice(0,2),smd?h/2:h/2-p.tail];
        if(['trimmer','rotary','lcd','oled','shunt'].includes(p.shape)&&!smd)cylinder(g,'terminal-'+c.terminal,c.size[0],h,'Z',pos,m[p.lead_material],p.segments[lod],{terminal:c.terminal});else box(g,'terminal-'+c.terminal,[...c.size,h],pos,m[p.lead_material]).userData.terminal=c.terminal;
    }
    if(p.shape==='sip'){const d=decal(g,'pin1-mark',new THREE.CircleGeometry(p.mark_diameter/2,p.segments[lod]),[p.width/2,cs[0].center_mm[1],p.height*p.mark_height_fraction],m.MAT_SILKSCREEN_WHITE,false,{terminal:'1'});d.rotation.y=Math.PI/2;}
    return g;
}
