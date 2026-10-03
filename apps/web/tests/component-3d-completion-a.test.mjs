import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import {createCompletionLibrary,createCompletionComponent} from '../component-library/completion-registry.js';
const data=JSON.parse(readFileSync(new URL('../component-library/data/completion-a.json',import.meta.url))),lib=createCompletionLibrary(data);
const cases=[
 [150,8,0,8.89,1,2.54,[0,0,1]], [151,10,-1.27,5.08,2,2.54,[0,0,1]],
 [152,8,0,8.89,1,2.54,[0,0,1]], [153,10,-1.27,5.08,2,2.54,[0,0,1]],
 [154,8,0,8.89,1,2.54,[1,0,0]], [155,2,0,1,1,2,[0,0,1]],
 [156,2,0,1.25,1,2.5,[0,0,1]], [157,4,2,1.5,1,1,[-1,0,0]],
 [158,2,0,1.27,1,2.54,[0,0,1]], [159,2,0,2.54,1,5.08,[1,0,0]],
 [160,3,0,5.08,1,5.08,[1,0,0]], [161,2,0,2.54,1,5.08,[1,0,0]],
];
const near=(a,b)=>assert.ok(Math.abs(a-b)<2e-5,`${a} != ${b}`);
function signature(g){const a=[];g.traverse(m=>{if(m.isMesh)a.push([m.name,Array.from(m.geometry.attributes.position.array),m.position.toArray(),m.rotation.toArray(),m.material.name,m.isInstancedMesh?Array.from(m.instanceMatrix.array):null,m.userData]);});return createHash('sha256').update(JSON.stringify([a,g.userData])).digest('hex');}
test('Group A source status and YAML fingerprints are preserved',()=>{
 const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));assert.equal(data.source_spec_sha256,createHash('sha256').update(source).digest('hex'));
 assert.deepEqual(data.components.map(r=>r.id),cases.map(c=>`OHM-${c[0]}`));
 for(const r of data.components){const raw=source.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0].match(/```yaml\s*\n([\s\S]*?)\n```/)[1];assert.equal(r.status,raw.match(/^status: (\w+)/m)[1]);assert.equal(r.source.yaml_sha256,createHash('sha256').update(raw).digest('hex'));assert.ok(r.library_metadata.uncertain_values.length);}
});
for(const [n,count,x,y,rows,pitch,mating] of cases)for(const lod of ['LOD0','LOD1','LOD2'])test(`OHM-${n} ${lod} terminal count, pin1, numbering, positions, mating and deterministic geometry`,()=>{
 const g=createCompletionComponent(lib,`OHM-${n}`,{lod}),u=g.userData;assert.equal(u.terminal_count,count);assert.deepEqual(u.mating_direction,mating);
 near(u.contacts[0].center_mm[0],x);near(u.contacts[0].center_mm[1],y);
 u.contacts.forEach((c,i)=>{assert.equal(c.terminal,String(i+1));near(c.center_mm[0],x+(i%rows)*pitch);near(c.center_mm[1],y-Math.floor(i/rows)*pitch);near(c.center_mm[2],0);});
 g.updateMatrixWorld(true);
 if(lod!=='LOD0')for(const c of u.contacts){const hits=new THREE.Raycaster(new THREE.Vector3(c.center_mm[0],c.center_mm[1],-20),new THREE.Vector3(0,0,1)).intersectObject(g,true);assert.ok(hits.length,`missing pin ${c.terminal}`);const hit=hits[0];near(hit.point.z,-u.parameters.tail);assert.equal(hit.object.userData.instance_terminals[hit.instanceId],c.terminal);}
 g.traverse(m=>{if(m.isMesh)for(const attr of Object.values(m.geometry.attributes))assert.ok(Array.from(attr.array).every(Number.isFinite),m.name);});
 assert.equal(signature(g),signature(createCompletionComponent(lib,`OHM-${n}`,{lod})));
});
test('N variants preserve row numbering and housing coupling',()=>{
 for(const [n,,,,rows,pitch] of cases)for(const N of [2,7]){
  const g=createCompletionComponent(lib,`OHM-${n}`,{N}),u=g.userData;assert.equal(u.terminal_count,N*rows);near(u.contacts[0].center_mm[1],(N-1)*pitch/2);near(u.contacts.at(-1).center_mm[1],-(N-1)*pitch/2);
 }
});
test('right-angle two-row header has odd upper pins and body offset',()=>{
 const g=createCompletionComponent(lib,'OHM-154',{rows:2,N:5});assert.equal(g.userData.terminal_count,10);near(g.getObjectByName('housing').position.x,4.04);const pins=g.children.filter(m=>m.name==='right-angle-terminals');
 assert.deepEqual(pins[0].userData.instance_terminals,['1','3','5','7','9']);pins.forEach(m=>m.geometry.computeBoundingBox());near(pins[0].geometry.boundingBox.max.z-pins[1].geometry.boundingBox.max.z,2.54);
});
test('JST-SH top entry uses its own sourced contact coordinates',()=>{
 const g=createCompletionComponent(lib,'OHM-157',{entry_direction:'top'});assert.deepEqual(g.userData.mating_direction,[0,0,1]);near(g.userData.contacts[0].center_mm[0],-1.325);near(g.userData.parameters.offset[0],.45);
});
test('unknown alternates fail explicitly',()=>{
 assert.throws(()=>createCompletionComponent(lib,'OHM-155',{entry_direction:'side'}));
 assert.throws(()=>createCompletionComponent(lib,'OHM-161',{header_orientation:'vertical'}));
 assert.throws(()=>createCompletionComponent(lib,'OHM-150',{N:0}));
 assert.throws(()=>createCompletionComponent(lib,'OHM-150',{pitch:2}));
});
test('OHM-161 cosmetic features stay inside the stated envelope at every LOD',()=>{
 for(const lod of ['LOD0','LOD1','LOD2']){
  const g=createCompletionComponent(lib,'OHM-161',{lod}),b=new THREE.Box3().setFromObject(g);
  [-3,-6.08,lod==='LOD0'?0:-3.5].forEach((v,i)=>near(b.min.getComponent(i),v));
  [19,6.08,15].forEach((v,i)=>near(b.max.getComponent(i),v));
  assert.ok(g.getObjectByName('screw-head'));assert.ok(g.getObjectByName('wire-entry-back'));
  assert.ok(lib.records['OHM-161'].cosmetic_defaults.length>=10);
  for(const c of lib.records['OHM-161'].cosmetic_defaults){assert.equal(c.tag,'COSMETIC_PROVISIONAL');assert.ok(c.derivation);assert.ok(lib.records['OHM-161'].library_metadata.uncertain_values.some(x=>x.includes(c.feature)));}
 }
});
