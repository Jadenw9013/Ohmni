import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import * as THREE from '../vendor/three.module.js';
import {LIBRARY_DATASETS,createFullLibrary,createFullComponent,libraryCoverage} from '../component-library/full-registry.js';
import {createCompletionMaterials} from '../component-library/completion-materials.js';
const data=Object.fromEntries(LIBRARY_DATASETS.map(key=>[key,JSON.parse(readFileSync(new URL(`../component-library/data/${key}.json`,import.meta.url)))])),lib=createFullLibrary(data),materials=createCompletionMaterials();
const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url),'utf8');
test('Exactly OHM-001..180 resolve, unique, with a family/member/generator and all three LODs',()=>{
 assert.deepEqual(Object.keys(lib.records),Array.from({length:180},(_,i)=>`OHM-${String(i+1).padStart(3,'0')}`));assert.equal(libraryCoverage(lib).length,180);
 for(const r of lib.components){assert.ok(r.package_family.startsWith('PKG-'));assert.ok(r.package_member);assert.ok(r.generator.startsWith('GEN-'));assert.deepEqual(r.lod_supported,['LOD0','LOD1','LOD2']);}
});
for(const record of lib.components)test(`${record.id} all LODs build; source status and implementation flag stay distinct`,()=>{
 const raw=source.split(`# [${record.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0].match(/```yaml\s*\n([\s\S]*?)\n```/)[1],status=raw.match(/^status:\s*["']?(\w+)/m)[1];assert.equal(record.status,status);assert.equal(record.library_metadata.implementation_status,'IMPLEMENTED');
 if(status==='partial'){assert.equal(record.library_metadata.provisional,true);assert.ok(record.library_metadata.uncertain_values.length);}
 for(const lod of ['LOD0','LOD1','LOD2']){const g=createFullComponent(lib,record.id,{lod},materials);assert.equal(g.userData.lod,lod);assert.equal(g.userData.component_id,record.id);assert.equal(g.userData.implementation_status,'IMPLEMENTED');assert.ok(g.userData.model_asset_id);assert.ok(g.userData.contacts.length>0);const b=new THREE.Box3().setFromObject(g);assert.ok([...b.min.toArray(),...b.max.toArray()].every(Number.isFinite));assert.equal(g.userData.source_spec_sha256,lib.source_spec_sha256);}
});
test('Missing, duplicate and proposed-extra IDs are rejected',()=>{
 for(const mode of ['missing','duplicate','extra']){const bad=structuredClone(data);if(mode==='missing')bad['completion-e'].components.pop();else if(mode==='duplicate')bad['completion-e'].components.push(structuredClone(bad['completion-e'].components[0]));else {const r=structuredClone(bad['completion-e'].components[0]);r.id='OHM-201';bad['completion-e'].components.push(r);}assert.throws(()=>createFullLibrary(bad));}
});
test('A source partial entry cannot lose its implementation flag unnoticed',()=>{const bad=structuredClone(data);delete bad['completion-c'].components[0].library_metadata.implementation_status;assert.throws(()=>createFullLibrary(bad));});
