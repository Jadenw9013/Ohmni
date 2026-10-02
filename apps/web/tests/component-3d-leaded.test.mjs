import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import { createLeadedLibrary, createLeadedComponent } from '../component-library/leaded-registry.js';
import { createLibraryMaterials } from '../component-library/materials.js';
import { placeInViewer } from '../component-library/transforms.js';

const data = JSON.parse(readFileSync(new URL('../component-library/data/leaded.json', import.meta.url)));
const library = createLeadedLibrary(data);
// Independent acceptance values from the spec's family pin-1 tables.
const cases = [
    ['070',3,-.95,-1,.95],['094',3,-.95,-1,.95],
    ['103',6,-3.81,2.54,2.54],['104',8,-3.81,3.81,2.54],['105',14,-3.81,7.62,2.54],
    ['106',16,-3.81,8.89,2.54],['107',20,-3.81,11.43,2.54],['108',28,-7.62,16.51,2.54],['109',40,-7.62,24.13,2.54],
    ['110',8,-2.58,1.905,1.27],['111',14,-2.58,3.81,1.27],['112',16,-2.58,4.445,1.27],['113',20,-4.73,5.715,1.27],
    ['114',8,-2.9,.975,.65],['115',14,-2.9,1.95,.65],['116',16,-2.9,2.275,.65],['117',20,-2.9,2.925,.65],
    ['118',16,-3.525,2.275,.65],['119',8,-2.175,.975,.65],['120',5,-.95,-1.2,.95],['121',6,-.95,-1.2,.95],
];
const near = (a,b,tol=1e-5) => assert.ok(Math.abs(a-b)<=tol, `${a} != ${b}`);
const bounds = o => { o.updateWorldMatrix(true,true); return new THREE.Box3().setFromObject(o); };
const ray = (o, x,y,z, direction) => {
    o.updateMatrixWorld(true);
    return new THREE.Raycaster(new THREE.Vector3(x,y,z), new THREE.Vector3(...direction)).intersectObject(o,true);
};
function signature(model) {
    const meshes=[]; model.updateMatrixWorld(true);
    model.traverse(n => { if (n.isMesh) meshes.push({name:n.name, matrix:n.matrixWorld.toArray(),
        attrs:Object.fromEntries(Object.entries(n.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),
        index:n.geometry.index ? Array.from(n.geometry.index.array) : null,
        material:[n.material.name,n.material.color.getHexString(),n.material.metalness,n.material.roughness], metadata:n.userData}); });
    return createHash('sha256').update(JSON.stringify({metadata:model.userData,meshes})).digest('hex');
}

test('Stage 2 IDs match the 21 explicit spec entries and retain raw source status/fingerprints',()=>{
    assert.deepEqual(Object.keys(library.records),cases.map(c=>'OHM-'+c[0]));
    const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));
    assert.equal(createHash('sha256').update(source).digest('hex'),data.source_spec_sha256);
    for(const r of Object.values(library.records)) {
        const section=source.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0];
        const raw=section.match(/```yaml\s*\n([\s\S]*?)\n```/)[1];
        assert.equal(createHash('sha256').update(raw).digest('hex'),r.source.yaml_sha256);
        assert.equal(r.status, raw.match(/^status: (\w+)/m)[1]);
        assert.equal(r.library_metadata.footprint_binding,null);
    }
});

for (const [number,count,x,y,pitch] of cases) for (const lod of ['LOD0','LOD1','LOD2']) {
    const id='OHM-'+number;
    test(`${id} ${lod}: count, orientation, order, physical contact, bounds and determinism`,()=>{
        const model=createLeadedComponent(library,id,{lod}),p=model.userData.parameters, contacts=model.userData.contacts;
        assert.equal(contacts.length,count); near(contacts[0].center_mm[0],x); near(contacts[0].center_mm[1],y);
        const expected = p.kind==='sot23' ? count===3 ? [[-.95,-1],[.95,-1],[0,1]] : count===5
            ? [[-.95,-1.2],[0,-1.2],[.95,-1.2],[.95,1.2],[-.95,1.2]]
            : [[-.95,-1.2],[0,-1.2],[.95,-1.2],[.95,1.2],[0,1.2],[-.95,1.2]]
            : Array.from({length:count},(_,i)=>i<count/2 ? [x,y-i*pitch] : [-x,-y+(i-count/2)*pitch]);
        const terminalLabels=[];
        model.traverse(n=> { if(n.userData.terminal && !n.name.includes('decal')) terminalLabels.push(n.userData.terminal);
            if(n.userData.terminals) terminalLabels.push(...n.userData.terminals); });
        assert.deepEqual(terminalLabels.sort((a,b)=>+a-+b),Array.from({length:count},(_,i)=>String(i+1)));
        for(let i=0;i<count;i++) {
            const c=contacts[i]; assert.equal(c.terminal,String(i+1));
            expected[i].forEach((v,j)=>near(c.center_mm[j],v)); near(c.center_mm[2],0);
            if(p.kind!=='dip') {
                const hit=ray(model,c.center_mm[0],c.center_mm[1],-1,[0,0,1])[0]; assert.ok(hit,'missing physical contact'); near(hit.point.z,0);
                if(lod!=='LOD0' || p.kind==='sot23') assert.equal(hit.object.userData.terminal,c.terminal);
                const actual=c.geometric_center_mm??c.center_mm;
                const lead=model.getObjectByName(`terminal-${c.terminal}`);
                if(lead) {
                    const b=bounds(lead), axis=p.kind==='sot23'?'y':'x';
                    near(c.side<0 ? b.min[axis] : b.max[axis],c.side*p.lead_span/2);
                    const inward=c.side*(p.lead_span/2-p.foot_length+1e-4);
                    const a=p.kind==='sot23'?[actual[0],inward]:[inward,actual[1]];
                    near(ray(lead,...a,-1,[0,0,1])[0].point.z,0);
                }
            } else {
                const lead=model.getObjectByName(`terminal-${c.terminal}`),tail=lead.getObjectByName('tail');
                const b=bounds(tail); near(b.min.z,-2.6);near(b.max.z,0);
                near((b.min.x+b.max.x)/2,c.center_mm[0]);near((b.min.y+b.max.y)/2,c.center_mm[1]);
                near(b.max.y-b.min.y,.46);near(b.max.x-b.min.x,.25);
                if(lod==='LOD1') near(bounds(lead.getObjectByName('shoulder')).getSize(new THREE.Vector3()).y,1.52);
            }
        }
        const b=bounds(model),size=b.getSize(new THREE.Vector3());
        size.toArray().forEach((v,i)=>near(v,model.userData.expected_dimensions_mm[i]));
        near(b.min.z,p.kind==='dip'?-2.6:0);near(b.max.z,p.overall_height);
        const dot=model.getObjectByName('pin1-decal');assert.ok(dot.position.x<0); assert.equal(Math.sign(dot.position.y),p.kind==='sot23'?-1:1);
        let triangles=0;
        model.traverse(n=>{if(!n.isMesh)return;const g=n.geometry; triangles+=(g.index?.count??g.attributes.position.count)/3;
            assert.ok(Array.from(g.attributes.position.array).every(Number.isFinite));
            const normals=g.attributes.normal;for(let i=0;i<normals.count;i++)near(Math.hypot(normals.getX(i),normals.getY(i),normals.getZ(i)),1,1e-4);
        });
        assert.ok(triangles<20000,`triangle budget ${triangles}`);
        assert.equal(signature(model),signature(createLeadedComponent(library,id,{lod})));
    });
}

test('documented body variants and DIP spacing/tail parameters remain explicit',()=>{
    for(const [id,options,w,span,pin] of [['OHM-112',{body_class:'wide'},7.5,10.3,[-4.73,4.445]],
        ['OHM-114',{body_width:3},3,4.9,[-2.15,.975]],['OHM-118',{variant:'qsop150'},3.9,6,[-2.58,2.2225]]]) {
        const m=createLeadedComponent(library,id,options);near(m.userData.parameters.body_width,w);near(m.userData.parameters.lead_span,span);
        pin.forEach((v,i)=>near(m.userData.contacts[0].center_mm[i],v));
    }
    near(createLeadedComponent(library,'OHM-114').userData.parameters.body_width,4.4);
    near(createLeadedComponent(library,'OHM-113').userData.parameters.body_width,7.5);
    for(const id of ['OHM-103','OHM-104','OHM-105','OHM-106','OHM-107']) near(createLeadedComponent(library,id).userData.parameters.row_spacing,7.62);
    for(const id of ['OHM-108','OHM-109']) near(createLeadedComponent(library,id).userData.parameters.row_spacing,15.24);
    const dip=createLeadedComponent(library,'OHM-104',{tail_length:3.3,corner_lead_slim:true});near(bounds(dip).min.z,-3.3);
    near(bounds(dip.getObjectByName('terminal-1').getObjectByName('shoulder')).getSize(new THREE.Vector3()).y,.9);
    assert.equal(dip.userData.library_metadata.provisional,true);
    assert.equal(createLeadedComponent(library,'OHM-120',{pin_count:6}).userData.contacts.length,6);
});

test('uncertainties and SOT contact discrepancy are visible without changing source status',()=>{
    for(const id of ['OHM-108','OHM-109','OHM-119']) {const r=library.records[id];assert.equal(r.status,'complete');assert.equal(r.library_metadata.provisional,true);assert.ok(r.library_metadata.uncertain_values.length);}
    for(const [id,delta] of [['OHM-070',.025],['OHM-094',.025],['OHM-120',.1],['OHM-121',.1]]) {
        const m=createLeadedComponent(library,id),c=m.userData.contacts[0];near(Math.abs(c.geometric_center_mm[1])-Math.abs(c.center_mm[1]),delta);
        near(m.userData.library_metadata.conflicts[0].delta_mm,delta);
    }
    assert.equal(library.records['OHM-070'].pcb_interface.standoff_mm,0);
    near(createLeadedComponent(library,'OHM-070').userData.parameters.standoff,.05);
});

test('invalid records and impossible parameter combinations fail rather than silently resizing',()=>{
    for(const options of [{pin_count:7},{pin_count:64},{lead_span:4},{body_length:1},{standoff:2},{exposed_pad:true},{foot_length:2},{pitch:0},{body_class:'wide'}]) {
        assert.throws(()=>createLeadedComponent(library,'OHM-110',options),RangeError,JSON.stringify(options));
    }
    assert.throws(()=>createLeadedComponent(library,'OHM-113',{body_class:'narrow'}));
    assert.throws(()=>createLeadedComponent(library,'OHM-104',{row_spacing:10.16}));
    assert.throws(()=>createLeadedComponent(library,'OHM-094',{configuration:'series'}));
    for(const mutate of [d=>d.profiles['OHM-110'].pin1_xy.reverse(),d=>d.profiles['OHM-120'].lead_mask.reverse(),
        d=>d.components[0].terminals.count=9,d=>d.components[0].status='partial']) {
        const d=structuredClone(data);mutate(d);assert.throws(()=>createLeadedLibrary(d));
    }
});

test('dual-diode configurations affect pin functions only; materials remain named tokens',()=>{
    const m=createLeadedComponent(library,'OHM-070',{configuration:'series'});
    assert.deepEqual(m.userData.contacts.map(c=>c.pin_function),['A1','K2','K1_A2']);
    const materials=createLibraryMaterials();assert.equal(materials.MAT_EPOXY_BLACK.color.getHexString(),'1b1b1d');
    assert.equal(materials.MAT_TIN_BRIGHT.color.getHexString(),'bfc1c4');
    assert.equal(materials.MAT_TIN_BRIGHT.metalness,1);
});

test('DIP notch, separate laser decals, explicit LOD changes and bottom adapter',()=>{
    const dip=createLeadedComponent(library,'OHM-104',{marking_text:'OHM104'});
    near(ray(dip,0,4.55,10,[0,0,-1])[0].point.z,3.38); // notch recess 0.30
    near(ray(dip,0,0,10,[0,0,-1])[0].point.z,3.68);
    assert.ok(dip.getObjectByName('laser-mark-decal').parent.name==='marking-decals');
    assert.equal(createLeadedComponent(library,'OHM-110',{lod:'LOD0'}).children.filter(n=>n.name.startsWith('merged-foot')).length,2);
    const original=signature(dip);
    const adapter=placeInViewer(dip,{side:'B.Cu',board_thickness_mm:1.6});
    adapter.updateMatrixWorld(true);
    const pos=new THREE.Vector3(...dip.userData.contacts[0].center_mm);dip.localToWorld(pos);
    near(pos.x,3.81);near(pos.y,3.81);near(pos.z,-.8);
    adapter.remove(dip); assert.equal(signature(dip),original);
});
