import * as THREE from '../../vendor/three.module.js';
import {box} from './leaded-body.js';
import {mesh,cylinder,decal,textDecal,relievedBox} from './discrete-primitives.js';
import {chipSurface} from './chip-2t.js';
import {instances} from './instanced-terminals.js';

export const MAGNETIC_FAMILIES=Object.freeze(['PKG-SMD_IND_WW','PKG-SMD_POWER_IND','PKG-DRUM_IND','PKG-TOROID','PKG-CMC_SMD','PKG-CMC_THT','PKG-XFMR_SIGNAL','PKG-XFMR_EE','PKG-XFMR_CT','PKG-MAGNETICS_SMD']);
function body(g,p,lod,m){
    const W=p.width,L=p.length,H=p.height,z=p.standoff,mat=m[p.body_material],seg=p.segments[lod];
    if(p.shape==='chip'){
        const cut=W/2-p.band;chipSurface(g,m,{L:W,W:L,H,xCuts:[-cut,cut],classify:([x])=>Math.abs(x)>=cut?[`terminal-${x<0?1:2}`,p.lead_material]:['body',p.body_material]});return;
    }
    if(p.shape==='toroid'){
        const outer=W/2,inner=p.inner_diameter/2,points=[];
        // Elliptical torus section keeps both stated OD and full axial thickness.
        for(let i=0;i<=seg;i++){const a=2*Math.PI*i/seg;points.push(new THREE.Vector2((outer+inner)/2+(outer-inner)/2*Math.cos(a),H/2+H/2*Math.sin(a)));}
        const geo=new THREE.LatheGeometry(points,seg);geo.rotateX(Math.PI/2);mesh(g,'coated-toroid',geo,mat,[0,0,z]);return;
    }
    if(p.shape==='cylinder'){
        cylinder(g,'sleeve',W,H-p.dome_height,'Z',[0,0,z+(H-p.dome_height)/2],mat,seg);
        const geo=new THREE.SphereGeometry(W/2,seg,Math.max(6,seg/2),0,Math.PI*2,0,Math.PI/2);geo.rotateX(Math.PI/2);geo.scale(1,1,p.dome_height/(W/2));mesh(g,'dome',geo,mat,[0,0,z+H-p.dome_height]);return;
    }
    if(p.shape==='drum'){
        const f=p.flange_height;for(const cz of [f/2,H-f/2])cylinder(g,'ferrite-flange',W,f,'Z',[0,0,z+cz],mat,seg);
        cylinder(g,'barrel',p.barrel_diameter,H-2*f,'Z',[0,0,z+H/2],mat,seg);
        cylinder(g,'winding-band',p.winding_diameter,H-2*f,'Z',[0,0,z+H/2],m.MAT_WIRE_ENAMEL_COPPER,seg);
        if(lod==='LOD2')for(let i=1;i<p.winding_turns;i++){const geo=new THREE.TorusGeometry(p.winding_diameter/2-p.pad_stock/4,p.pad_stock/4,6,seg);mesh(g,'winding-turn',geo,m.MAT_WIRE_ENAMEL_COPPER,[0,0,z+f+i*(H-2*f)/p.winding_turns]);}return;
    }
    if(p.shape==='ee'){
        const base=p.bobbin_base,fw=p.flange_stock,CW=p.core_width,CL=p.core_length,s=p.core_stock;
        box(g,'bobbin-base',[W,L,base],[0,0,z+base/2],m.MAT_PLASTIC_BLACK);
        for(const x of [-(W-fw)/2,(W-fw)/2])box(g,'bobbin-flange',[fw,L,H-base],[x,0,z+(H+base)/2],m.MAT_PLASTIC_BLACK);
        for(const cz of [base+s/2,H-s/2])box(g,'core-rail',[CW,CL,s],[0,0,z+cz],m.MAT_FERRITE_DARK);
        for(const x of [-(CW-s)/2,0,(CW-s)/2])box(g,'core-leg',[s,CL,H-base-2*s],[x,0,z+(H+base)/2],m.MAT_FERRITE_DARK);
        const window=(CW-3*s)/2;
        for(const x of [-(s+window)/2,(s+window)/2])box(g,'winding-tape',[window,p.tape_width,H-base-2*s],[x,0,z+(H+base)/2],m.MAT_TAPE_POLYESTER_YELLOW);
        return;
    }
    const pads=p.tht?[]:p.contacts.map(c=>({min:[c.center_mm[0]-c.size[0]/2,c.center_mm[1]-c.size[1]/2,0],max:[c.center_mm[0]+c.size[0]/2,c.center_mm[1]+c.size[1]/2,p.pad_stock]}));
    relievedBox(g,'housing',[[-W/2,W/2],[-L/2,L/2],[z,z+H]],pads,mat);
}
export function generateMagnetic(p,lod,cs,m,marking=''){
    const g=new THREE.Group();body(g,p,lod,m);
    if(p.shape!=='chip'){
        const s=cs[0].size,h=p.tht?p.tail+p.standoff:p.pad_stock;
        let geo=p.tht&&p.round_pin?new THREE.CylinderGeometry(s[0]/2,s[0]/2,h,p.segments[lod]):new THREE.BoxGeometry(s[0],s[1],h);
        if(p.tht&&p.round_pin)geo.rotateX(Math.PI/2);
        instances(g,'terminals',geo,m[p.lead_material],cs.map(c=>({terminal:c.terminal,position:[...c.center_mm.slice(0,2),p.tht?(p.standoff-p.tail)/2:p.pad_stock/2]})));
    }
    if(p.mark_pin1){const c=cs[0].center_mm,r=p.marker_diameter/2;
        decal(g,'pin1-mark',new THREE.CircleGeometry(r,p.segments[lod]),[Math.max(-p.width/2+2*r,c[0]),Math.min(p.length/2-2*r,c[1]),p.standoff+p.height],m.MAT_SILKSCREEN_WHITE,false,{terminal:'1',role:'pin1_mark'});
    }
    if(marking&&lod!=='LOD0')textDecal(g,marking,...p.label_size,[0,0,p.standoff+p.height],m.MAT_SILKSCREEN_WHITE);
    return g;
}
