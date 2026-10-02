import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import {createDiscreteLibrary,createDiscreteComponent} from '../component-library/discrete-registry.js';
import {placeInViewer} from '../component-library/transforms.js';

const data=JSON.parse(readFileSync(new URL('../component-library/data/discrete.json',import.meta.url))),library=createDiscreteLibrary(data);
const cases=[
    [56,2,-3.81,0],[57,2,-5.08,0],[58,2,-7.62,0],[59,2,-1.56,0],[60,2,-2.245,0],
    [61,2,-1.425,0],[62,2,-1.05,0],[63,2,-.625,0],[64,2,-2,0],[65,2,-2.15,0],[66,2,-3.42,0],
    [67,2,-1.425,0],[68,2,-1.425,0],[69,2,-2.15,0],[71,4,-3.81,2.54],[72,4,-2.54,2.54],
    [93,3,-1.27,0],[95,3,-1.5,-1.5],[96,4,-2.3,-3.05],[97,3,-2.28,0],[98,3,-2.54,0],[99,3,-5.45,0],
    [100,3,-2.29,-4.1],[101,3,-2.54,-6.4],[102,8,-2.77,1.905]];
const near=(a,b,t=1e-5)=>assert.ok(Math.abs(a-b)<=t,`${a} != ${b}`);
const bounds=m=>{m.updateMatrixWorld(true);return new THREE.Box3().setFromObject(m);};
function ray(m,origin,direction){m.updateMatrixWorld(true);return new THREE.Raycaster(new THREE.Vector3(...origin),new THREE.Vector3(...direction)).intersectObject(m,true);}
function signature(m,geometryOnly=false) {
    const nodes=[];m.updateMatrixWorld(true);m.traverse(n=>{if(!n.isMesh||geometryOnly&&n.userData.role==='separate_visual_decal')return;
        nodes.push({name:n.name,transform:n.matrixWorld.toArray(),attributes:Object.fromEntries(Object.entries(n.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),index:n.geometry.index?Array.from(n.geometry.index.array):null,...(geometryOnly?{}:{material:[n.material.name,n.material.color.getHexString(),n.material.opacity],metadata:n.userData})});});
    return createHash('sha256').update(JSON.stringify(geometryOnly?nodes:{nodes,metadata:m.userData})).digest('hex');
}
test('25 records retain raw source statuses, fingerprints, and 22 shared package profiles',()=>{
    assert.deepEqual(Object.keys(library.records),cases.map(c=>`OHM-${String(c[0]).padStart(3,'0')}`));assert.equal(Object.keys(library.profiles).length,22);
    const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));assert.equal(createHash('sha256').update(source).digest('hex'),data.source_spec_sha256);
    for(const r of Object.values(library.records)){
        const section=source.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0],raw=section.match(/```yaml\s*\n([\s\S]*?)\n```/)[1];
        assert.equal(createHash('sha256').update(raw).digest('hex'),r.source.yaml_sha256);assert.equal(raw.match(/^status: (\w+)/m)[1],r.status);assert.equal(r.library_metadata.footprint_binding,null);
        if(r.status==='partial')assert.ok(r.library_metadata.provisional&&r.library_metadata.uncertain_values.length);
    }
    assert.ok(!library.records['OHM-070']&&!library.records['OHM-094']);
});
for(const [n,count,x,y] of cases)for(const lod of ['LOD0','LOD1','LOD2']) {
    const id=`OHM-${String(n).padStart(3,'0')}`;
    test(`${id} ${lod}: contacts, polarity, geometry, bounds and deterministic output`,()=>{
        const m=createDiscreteComponent(library,id,{lod}),u=m.userData,p=u.parameters,cs=u.contacts;
        assert.equal(u.terminal_count,count);near(cs[0].center_mm[0],x);near(cs[0].center_mm[1],y);assert.equal(cs[0].terminal,'1');
        if(n<70){const band=m.getObjectByName('cathode-band');assert.ok(band&&band.position.x<0);assert.equal(band.userData.terminal,'1');assert.equal(cs[0].function,'cathode');assert.equal(cs[1].terminal,'2');near(cs[1].center_mm[0],-x);}
        if([71,72].includes(n)) {assert.deepEqual(cs.map(c=>c.terminal),['1','2','3','4']);assert.deepEqual(cs.map(c=>c.center_mm.slice(0,2)),[[x,y],[x,-y],[-x,-y],[-x,y]]);assert.ok(cs.every(c=>c.function==='UNKNOWN'));}
        for(const c of cs) {
            const hit=ray(m,[c.center_mm[0],c.center_mm[1],-p.tail-1],[0,0,1])[0];assert.ok(hit,`missing terminal ${c.terminal}`);
            near(hit.point.z,-p.tail);assert.equal(hit.object.userData.terminal,c.terminal,`contact hits ${hit.object.name}`);
        }
        if([97,98,99].includes(n)) {
            assert.equal(u.body_holes.length,1);const hz=u.body_holes[0].center_mm[2];assert.equal(ray(m,[0,-20,hz],[0,1,0]).length,0,'mounting hole must be open through body/tab at every LOD');
            assert.equal(u.fco_reference.body_holes_excluded,true);assert.deepEqual(u.fco_reference.mounting_holes,[]);
            assert.ok(m.getObjectByName('tab'));assert.ok(ray(m,[p.hole_diameter/2+.2,20,hz],[0,-1,0]).some(h=>h.object.name==='tab'));
        }
        if([100,101].includes(n)) {
            near(p.standoff,n===100?.08:.1);const b=bounds(m.getObjectByName('body'));near(b.min.z,p.standoff);near(b.max.z,n===100?2.29:4.3);
            const tab=m.getObjectByName('exposed-tab');near(bounds(tab).min.z,0);near(bounds(tab).max.z,p.tab_thickness);assert.ok(bounds(tab).max.z>b.min.z);assert.equal(tab.userData.embedded,true);
            assert.ok(!m.getObjectByName('lead-2'));assert.ok(m.getObjectByName('tab-extension').position.y>0);
        }
        const b=bounds(m);b.min.toArray().forEach((v,i)=>near(v,u.expected_bounds_mm.min[i]));b.max.toArray().forEach((v,i)=>near(v,u.expected_bounds_mm.max[i]));
        let triangles=0,objects=0;m.traverse(o=>{if(!o.isMesh)return;objects++;const g=o.geometry;triangles+=(g.index?.count??g.attributes.position.count)/3;
            assert.ok(Array.from(g.attributes.position.array).every(Number.isFinite));const norm=g.attributes.normal;for(let i=0;i<norm.count;i++)near(Math.hypot(norm.getX(i),norm.getY(i),norm.getZ(i)),1,1e-4);});
        assert.ok(objects<=16);assert.ok(triangles<25000);assert.equal(signature(m),signature(createDiscreteComponent(library,id,{lod})));
    });
}
test('function entries reuse exact package geometry and TVS removes only the band',()=>{
    for(const [id,base] of [['OHM-067','OHM-061'],['OHM-068','OHM-061'],['OHM-069','OHM-065']])for(const lod of ['LOD0','LOD1','LOD2']){
        const m=createDiscreteComponent(library,id,{lod}),b=createDiscreteComponent(library,base,{lod});assert.equal(m.userData.geometry_source_id,base);assert.equal(signature(m,true),signature(b,true));
        if(id==='OHM-069'){const bi=createDiscreteComponent(library,id,{lod,bidirectional:true});assert.ok(!bi.getObjectByName('cathode-band'));assert.equal(signature(m,true),signature(bi,true));assert.equal(bi.userData.contacts[0].function,'equivalent');}
    }
    assert.equal(createDiscreteComponent(library,'OHM-068',{package_member:'DO-35'}).userData.geometry_source_id,'OHM-056');
    assert.equal(createDiscreteComponent(library,'OHM-069',{package_member:'SMC'}).userData.contacts[0].center_mm[0],-3.42);
});
test('glass and epoxy materials differ; cathode never uses an unsourced SMX chamfer',()=>{
    const glass=createDiscreteComponent(library,'OHM-056'),epoxy=createDiscreteComponent(library,'OHM-057');assert.equal(glass.getObjectByName('body').material.name,'MAT_DIODE_GLASS_AMBER');assert.equal(glass.getObjectByName('body').material.opacity,.85);assert.equal(epoxy.getObjectByName('body').material.name,'MAT_EPOXY_BLACK');
    for(const id of ['OHM-064','OHM-065','OHM-066']){const m=createDiscreteComponent(library,id,{lod:'LOD2'});assert.equal(m.userData.parameters.bevel,0);assert.match(m.userData.library_metadata.uncertain_values.join(' '),/chamfer\/step.*RESEARCH_REQUIRED/);}
});
test('TO247 AD and AC preserve source outline, tab, hole and FCO offsets',()=>{
    for(const [outline,w,t,h,offset,hole,tab] of [['AD',15.9,5.02,20.95,-.1,6.17,2],['AC',15.7,4.95,20.5,-.065,5.5,1.27]])for(const lod of ['LOD0','LOD1','LOD2']){
        const m=createDiscreteComponent(library,'OHM-099',{outline,lod}),p=m.userData.parameters;near(p.body_x,w);near(p.body_y,t);near(p.height,h);near(p.body_offset[1],offset);near(p.tab_thickness,tab);near(m.userData.body_holes[0].center_mm[2],h-hole);assert.equal(ray(m,[0,-20,h-hole],[0,1,0]).length,0);
        assert.deepEqual(m.userData.contacts.map(c=>c.center_mm),[[-5.45,0,0],[0,0,0],[5.45,0,0]]);
    }
});
test('SOT223 tab is terminal 4; SOT89 has four surfaces but three terminals',()=>{
    const a=createDiscreteComponent(library,'OHM-096'),b=createDiscreteComponent(library,'OHM-095');assert.equal(a.getObjectByName('tab').userData.terminal,'4');assert.equal(a.userData.contacts.at(-1).center_mm[1],3.05);assert.equal(b.getObjectByName('tab').userData.terminal,'2');assert.equal(b.userData.contact_surface_count,4);assert.equal(b.userData.terminal_count,3);
});
test('PowerPAK is Vishay eight-pad outline with copper drain and CCW numbering',()=>{
    const m=createDiscreteComponent(library,'OHM-102'),cs=m.userData.contacts;assert.equal(cs.length,8);assert.deepEqual(cs.map(c=>c.center_mm),[[-2.77,1.905,0],[-2.77,.635,0],[-2.77,-.635,0],[-2.77,-1.905,0],[2.77,-1.905,0],[2.77,-.635,0],[2.77,.635,0],[2.77,1.905,0]]);
    const ep=m.getObjectByName('exposed-drain-pad');assert.equal(ep.material.name,'MAT_COPPER');const b=bounds(ep);near(b.max.x-b.min.x,3.66);near(b.max.y-b.min.y,3.76);near(m.userData.height_above_board_mm,1.04);
});
test('shared axial bend remains at footprint holes and tail depth when pitch changes',()=>{
    const m=createDiscreteComponent(library,'OHM-057',{pitch:12.7,tail_length:3,lod:'LOD2'});assert.deepEqual(m.userData.contacts[0].center_mm,[-6.35,0,0]);near(ray(m,[-6.35,0,-4],[0,0,1])[0].point.z,-3);
});
test('axial wire keeps its sourced diameter along both straight runs beside the miter',()=>{
    const m=createDiscreteComponent(library,'OHM-057');
    const top=ray(m,[3.5,0,4],[0,0,-1])[0].point.z,bottom=ray(m,[3.5,0,-4],[0,0,1])[0].point.z;
    near(top,1.6);near(bottom,.8);near(top-bottom,.8);
    const right=ray(m,[7,0,-1],[-1,0,0])[0].point.x,left=ray(m,[4,0,-1],[1,0,0])[0].point.x;near(right-left,.8);
});
test('parameter failures reject unsupported geometry rather than silently resizing',()=>{
    for(const [id,options] of [['OHM-057',{pitch:5}],['OHM-059',{band_width:2}],['OHM-093',{lead_form:'formed'}],['OHM-099',{outline:'4L'}],['OHM-100',{stub_length:2}],['OHM-101',{standoff:2}],['OHM-061',{bidirectional:true}],['OHM-067',{package_member:'QFN'}],['OHM-098',{tail_length:-1}],['OHM-102',{lod:'auto'}]])assert.throws(()=>createDiscreteComponent(library,id,options));
});
test('viewer bottom transform keeps cathode and band together with canonical FCO unchanged',()=>{
    const m=createDiscreteComponent(library,'OHM-061'),before=structuredClone(m.userData.contacts),wrap=placeInViewer(m,{side:'B.Cu',board_thickness_mm:1.6});wrap.updateMatrixWorld(true);assert.ok(m.getObjectByName('cathode-band').getWorldPosition(new THREE.Vector3()).x>0);assert.deepEqual(m.userData.contacts,before);
});
