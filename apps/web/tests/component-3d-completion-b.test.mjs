import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import {createCompletionLibrary,createCompletionComponent} from '../component-library/completion-registry.js';
const data=JSON.parse(readFileSync(new URL('../component-library/data/completion-b.json',import.meta.url))),lib=createCompletionLibrary(data);
const cases=[[141,2,-2.44,0,10.8,4.65,13.5,2.6],[142,2,-2.44,0,11.05,4.65,3.5,2.6],
 [143,4,-1.1,.8,3.2,2.5,.8,0],[144,4,-.85,.65,2.5,2,.5,0],[145,4,-.675,.525,2,1.6,.45,0],
 [146,4,-2.54,1.905,7,5.01,1.8,0],[147,4,-1.1,.8,3.2,2.5,.9,0],[148,3,-2.5,0,8,3.5,5.5,2.6],[149,6,-1.5,1.1,3.8,3.8,1.5,0]];
const near=(a,b)=>assert.ok(Math.abs(a-b)<2e-5,`${a} != ${b}`);
function signature(g){const a=[];g.traverse(m=>{if(m.isMesh)a.push([m.name,Array.from(m.geometry.attributes.position.array),m.position.toArray(),m.rotation.toArray(),m.material.name,m.isInstancedMesh?Array.from(m.instanceMatrix.array):null,m.userData]);});return createHash('sha256').update(JSON.stringify([a,g.userData])).digest('hex');}
test('Group B source IDs, statuses and fingerprints',()=>{
 assert.deepEqual(data.components.map(r=>r.id),cases.map(c=>`OHM-${c[0]}`));const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));assert.equal(data.source_spec_sha256,createHash('sha256').update(source).digest('hex'));
 for(const r of data.components){const raw=source.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0].match(/```yaml\s*\n([\s\S]*?)\n```/)[1];assert.equal(r.status,raw.match(/^status: (\w+)/m)[1]);assert.equal(r.source.yaml_sha256,createHash('sha256').update(raw).digest('hex'));}
});
for(const [n,count,x,y,L,W,H,tail] of cases)for(const lod of ['LOD0','LOD1','LOD2'])test(`OHM-${n} ${lod} numbering, pin1, contacts, body bounds and determinism`,()=>{
 const g=createCompletionComponent(lib,`OHM-${n}`,{lod}),u=g.userData;assert.equal(u.terminal_count,count);near(u.contacts[0].center_mm[0],x);near(u.contacts[0].center_mm[1],y);
 const expected=count===2?[[x,0],[-x,0]]:count===3?[[x,0],[0,0],[-x,0]]:count===4?[[x,y],[x,-y],[-x,-y],[-x,y]]:[[x,y],[x,0],[x,-y],[-x,-y],[-x,0],[-x,y]];
 u.contacts.forEach((c,i)=>{assert.equal(c.terminal,String(i+1));c.center_mm.slice(0,2).forEach((v,a)=>near(v,expected[i][a]));});
 g.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(g);[L,W,H+tail].forEach((v,i)=>near(b.getSize(new THREE.Vector3()).getComponent(i),v));near(b.min.z,-tail);near(b.max.z,H);
 for(const c of u.contacts){const hit=new THREE.Raycaster(new THREE.Vector3(c.center_mm[0],c.center_mm[1],-20),new THREE.Vector3(0,0,1)).intersectObject(g,true)[0];assert.ok(hit);near(hit.point.z,-tail);assert.equal(hit.object.userData.terminal??hit.object.userData.instance_terminals[hit.instanceId],c.terminal);}
 if(count>=4){const mark=g.getObjectByName('pin1-mark');assert.ok(mark.position.x<0&&mark.position.y>0);}
 g.traverse(m=>{if(m.isMesh)for(const a of Object.values(m.geometry.attributes))assert.ok(Array.from(a.array).every(Number.isFinite));});assert.equal(signature(g),signature(createCompletionComponent(lib,`OHM-${n}`,{lod})));
});
test('Abracon crystal BL numbering variant follows entry exception without moving pad sites',()=>{
 for(const id of ['OHM-143','OHM-144','OHM-145']){
  const g=createCompletionComponent(lib,id,{pin1_corner:'BL',lod:'LOD2'}),cs=g.userData.contacts;
  assert.ok(cs[0].center_mm[0]<0&&cs[0].center_mm[1]<0);assert.ok(cs[1].center_mm[0]>0&&cs[1].center_mm[1]<0);assert.ok(cs[2].center_mm[0]>0&&cs[2].center_mm[1]>0);assert.ok(g.getObjectByName('pin1-mark').position.y<0);
 }
});
test('7050 pad overhang is explicit, not silently corrected',()=>{assert.ok(lib.records['OHM-146'].library_metadata.conflicts.some(x=>x.code==='PAD_OVERHANG_005'));const g=createCompletionComponent(lib,'OHM-146');near(g.userData.contacts[0].center_mm[1],1.905);near(g.userData.parameters.pad_y,1.2);});
test('unknown footprint variants rejected',()=>{assert.throws(()=>createCompletionComponent(lib,'OHM-149',{pad_count:4}));assert.throws(()=>createCompletionComponent(lib,'OHM-146',{pin1_corner:'BL'}));});
