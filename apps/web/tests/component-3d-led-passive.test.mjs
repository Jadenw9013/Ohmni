import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import {createLedPassiveLibrary,createLedPassiveComponent} from '../component-library/led-passive-registry.js';
import {createLibraryMaterials,STAGE5_MATERIAL_ADDITIONS,MATERIAL_TOKENS} from '../component-library/materials.js';
import {placeInViewer} from '../component-library/transforms.js';
const data=JSON.parse(readFileSync(new URL('../component-library/data/led-passive.json',import.meta.url))),lib=createLedPassiveLibrary(data);
const cases=[
 [10,2,-5.08,0],[11,2,-5.08,0],[12,2,-12.7,0],[13,2,-13.97,0],
 [28,2,-2.5,0],[29,2,-2.5,0],[30,2,-2.4,0],[31,2,-5,0],[32,2,-2.4,0],
 [33,2,-1.2,0],[34,2,-1.35,0],[35,2,-2.35,0],[36,2,-3,0],[37,2,-5,0],[38,2,-7.5,0],[39,2,-2.95,0],[40,2,-2.5,0],[47,2,-5.08,0],
 [73,2,-1.27,0],[74,2,-1.27,0],[75,2,-1.27,0],[76,2,-1.27,0],
 [77,2,-.4,0],[78,2,-.6,0],[79,2,-.75,0],[80,2,-1.3,0],[81,2,-1.2,0],[82,4,-1.35,.95],[83,6,-2.1,1.7],[84,4,-2.1,1.6],[85,3,-1.4,0],[86,4,-8,3]];
const near=(a,b,t=2e-5)=>assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);
function bounds(m){m.updateMatrixWorld(true);return new THREE.Box3().setFromObject(m);}
function ray(m,origin,dir){m.updateMatrixWorld(true);return new THREE.Raycaster(new THREE.Vector3(...origin),new THREE.Vector3(...dir)).intersectObject(m,true);}
function signature(m){const a=[];m.updateMatrixWorld(true);m.traverse(n=>{if(n.isMesh)a.push({name:n.name,transform:n.matrixWorld.toArray(),pos:Array.from(n.geometry.attributes.position.array),normal:Array.from(n.geometry.attributes.normal.array),index:n.geometry.index?Array.from(n.geometry.index.array):null,material:[n.material.name,n.material.color.getHexString(),n.material.opacity],metadata:n.userData});});return createHash('sha256').update(JSON.stringify([a,m.userData])).digest('hex');}

test('32 Stage 5 records retain exact source fields/status/fingerprints',()=>{
 assert.deepEqual(Object.keys(lib.records),cases.map(x=>`OHM-${String(x[0]).padStart(3,'0')}`));
 const s=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));assert.equal(data.source_spec_sha256,createHash('sha256').update(s).digest('hex'));
 for(const r of Object.values(lib.records)){const raw=s.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0].match(/```yaml\s*\n([\s\S]*?)\n```/)[1];assert.equal(r.status,raw.match(/^status: (\w+)/m)[1]);assert.equal(r.source.yaml_sha256,createHash('sha256').update(raw).digest('hex'));assert.ok(r.library_metadata.provisional&&r.library_metadata.uncertain_values.length);assert.equal(r.library_metadata.footprint_binding,null);}
});
for(const [n,count,x,y] of cases)for(const lod of ['LOD0','LOD1','LOD2'])test(`OHM-${n} ${lod}: polarity, terminals, actual contact geometry, envelope and determinism`,()=>{
 const id=`OHM-${String(n).padStart(3,'0')}`,m=createLedPassiveComponent(lib,id,{lod}),u=m.userData,p=u.parameters;
 assert.equal(u.terminal_count,count);assert.equal(u.contacts[0].terminal,'1');near(u.contacts[0].center_mm[0],x);near(u.contacts[0].center_mm[1],y);
 for(const c of u.contacts){const tail=p.tail+(c.terminal==='2'&&lod==='LOD2'&&[73,74,75,76].includes(n)?p.anode_extra:0),top=n===86;
  const hit=ray(m,[c.center_mm[0],c.center_mm[1],top?c.center_mm[2]+1:-tail-1],top?[0,0,-1]:[0,0,1])[0];assert.ok(hit,`no contact ${c.terminal}`);near(hit.point.z,top?c.center_mm[2]:-tail);assert.equal(hit.object.userData.terminal,c.terminal,`contact hit ${hit.object.name}`);
 }
 if([29,30,31,32,40].includes(n)){assert.equal(u.contacts[0].function,'positive');const stripe=m.getObjectByName('negative-stripe');assert.equal(stripe.userData.side,'+X');assert.equal(stripe.userData.terminal,'2');assert.ok(bounds(stripe).min.x>0);assert.ok(m.getObjectByName('seal'));if(p.diameter>=p.vent_min_diameter)assert.ok(m.getObjectByName('vent-scored-top'));}
 if([33,34,35,36].includes(n)){assert.equal(u.contacts[0].function,'positive');assert.ok(m.getObjectByName('positive_bar').position.x<0);}
 if([73,74,75,76].includes(n)){assert.equal(u.contacts[0].function,'cathode');assert.equal(m.getObjectByName('lens').userData.cathode_flat_side,'-X');}
 if([77,78,79,80,85].includes(n)){assert.equal(u.contacts[0].function,'cathode');assert.ok(m.getObjectByName('cathode_mark').position.x<0);}
 if([81,82,83,84].includes(n))assert.equal(m.getObjectByName('cavity-wall').userData.terminal,'1');
 const b=bounds(m);b.min.toArray().forEach((v,i)=>near(v,u.expected_bounds_mm.min[i]));b.max.toArray().forEach((v,i)=>near(v,u.expected_bounds_mm.max[i]));
 let triangles=0,draws=0;m.traverse(o=>{if(!o.isMesh)return;draws++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;for(const a of Object.values(o.geometry.attributes))assert.ok(Array.from(a.array).every(Number.isFinite),o.name);assert.ok(MATERIAL_TOKENS[o.material.name]);});assert.ok(draws<=32);assert.ok(triangles<40000);
 assert.equal(signature(m),signature(createLedPassiveComponent(lib,id,{lod})));
});
test('snap-in override is 4 mm at every LOD and uncertain 3-pin variants fail',()=>{
 for(const lod of ['LOD0','LOD1','LOD2']){const m=createLedPassiveComponent(lib,'OHM-031',{lod});near(bounds(m).min.z,-4);assert.equal(m.userData.contacts.length,2);}
 assert.throws(()=>createLedPassiveComponent(lib,'OHM-031',{pins:3}));
});
test('SMD can corners are chamfered on positive -X, not negative +X',()=>{
 for(const id of ['OHM-030','OHM-032']){const m=createLedPassiveComponent(lib,id),b=m.getObjectByName('positive-chamfer-base');assert.equal(b.userData.side,'-X');assert.equal(ray(b,[-3.2,3.2,3],[0,0,-1]).length,0);assert.ok(ray(b,[3.2,3.2,3],[0,0,-1]).length);}
});
test('RGB and addressable lead order follows explicit entry mappings',()=>{
 assert.deepEqual(createLedPassiveComponent(lib,'OHM-083').userData.contacts.map(c=>c.center_mm),[[-2.1,1.7,0],[-2.1,0,0],[-2.1,-1.7,0],[2.1,-1.7,0],[2.1,0,0],[2.1,1.7,0]]);
 const w=createLedPassiveComponent(lib,'OHM-084');assert.deepEqual(w.userData.contacts.map(c=>c.function),['VDD','DOUT','VSS','DIN']);assert.ok(w.userData.library_metadata.conflicts.some(c=>c.code==='WS2812B_PIN1_FUNCTION'));
});
test('all 14 LEDs support independent lens/color materials and transparent picking',()=>{
 const shared=createLibraryMaterials();
 for(let n=73;n<=86;n++){const id=`OHM-${String(n).padStart(3,'0')}`;for(const lens of ['clear','diffused']){
  const m=createLedPassiveComponent(lib,id,{led_color:'#123456',lens},shared),l=m.getObjectByName('lens');assert.ok(l.isMesh);assert.equal(l.material.name,lens==='clear'?'MAT_PLASTIC_CLEAR':'MAT_PLASTIC_DIFFUSED');assert.equal(l.material.transparent,true);assert.equal(l.material.depthWrite,false);if(lens==='diffused')assert.equal(l.material.color.getHexString(),'123456');
  const b=bounds(l),c=b.getCenter(new THREE.Vector3()),hit=ray(m,[c.x,c.y,b.max.z+2],[0,0,-1]).find(h=>h.object===l);assert.ok(hit,`${id} ${lens} lens must be pickable`);assert.equal(hit.object.userData.component_id,id);
 }}assert.equal(shared.MAT_PLASTIC_DIFFUSED.color.getHexString(),'ff2a1a');
});
test('resistor bands are separate decals with a separated tolerance band',()=>{
 for(const [id,count] of [['OHM-010',4],['OHM-011',5],['OHM-047',4]]){const m=createLedPassiveComponent(lib,id);const bands=m.children.filter(o=>o.userData.role==='color_band_decal');assert.equal(bands.length,count);assert.ok(bands[0].position.x<0);assert.ok(bands.at(-1).position.x-bands.at(-2).position.x>bands[1].position.x-bands[0].position.x);assert.ok(bands.every(b=>b.material.polygonOffset));}
});
test('LED chip models reuse surface helper but use independent LED dimensions',()=>{
 const source=readFileSync(new URL('../component-library/generators/led-passive.js',import.meta.url),'utf8');assert.match(source,/import \{ chipSurface \} from '.\/chip-2t.js'/);assert.match(source,/import \{ roundBentLead \} from '.\/axial-lead.js'/);
 const m=createLedPassiveComponent(lib,'OHM-078');assert.deepEqual(m.userData.expected_dimensions_mm,[1.6,.8,.55]);assert.equal(m.getObjectByName('terminal-1').material.name,'MAT_GOLD');
});
test('hex module uses 20 across flats and instances the emitter profile',()=>{
 const m=createLedPassiveComponent(lib,'OHM-086'),b=bounds(m.getObjectByName('mcpcb'));near(b.max.y-b.min.y,20);near(b.max.x-b.min.x,40/Math.sqrt(3));assert.equal(m.getObjectByName('emitter-instance').userData.geometry_source_id,'OHM-085');assert.ok(m.userData.contacts.every(c=>c.provisional));
});
test('binding material addendum takes precedence and unrelated display tokens stay absent',()=>{
 assert.deepEqual(MATERIAL_TOKENS.MAT_RUBBER_SEAL,['#1A1A1A',.8,0]);assert.equal(MATERIAL_TOKENS.MAT_CAP_DISC_COATING[0],'#C8782A');assert.equal(MATERIAL_TOKENS.MAT_FILM_CASE_RED[0],'#B3261E');assert.equal(MATERIAL_TOKENS.MAT_MICA_DIP[0],'#B5651D');assert.equal(STAGE5_MATERIAL_ADDITIONS.MAT_MCPCB_MASK_WHITE[0],'#EDEDE8');assert.ok(!STAGE5_MATERIAL_ADDITIONS.MAT_LCD_POLARIZER_GRAY);
});
test('invalid and unsupported variants fail without silent resizing',()=>{
 for(const [id,o] of [['OHM-078',{led_color:'red'}],['OHM-074',{lens:'opaque'}],['OHM-029',{led_color:'#123456'}],['OHM-011',{band_colors:['BLACK']}],['OHM-011',{pitch:6}],['OHM-073',{anode_extra:-1}],['OHM-030',{diameter:12.5}],['OHM-040',{style:'EatonPB'}],['OHM-084',{lod:'auto'}]])assert.throws(()=>createLedPassiveComponent(lib,id,o));
});
test('bottom viewer transform carries capacitor stripe and LED cathode together',()=>{
 for(const id of ['OHM-029','OHM-078']){const m=createLedPassiveComponent(lib,id),cs=structuredClone(m.userData.contacts);const w=placeInViewer(m,{side:'B.Cu',board_thickness_mm:1.6});w.updateMatrixWorld(true);assert.deepEqual(m.userData.contacts,cs);const mark=m.getObjectByName(id==='OHM-029'?'negative-stripe':'cathode_mark');const b=bounds(mark);if(id==='OHM-029')assert.ok(b.max.x<0);else assert.ok(b.min.x>0);}
});
test('THT clear LOD2 variants keep the full envelope, physical flat and longer anode',()=>{
 for(const n of [73,74,75,76]){const m=createLedPassiveComponent(lib,`OHM-0${n}`,{lod:'LOD2',lens:'clear'}),p=m.userData.parameters,b=bounds(m);b.min.toArray().forEach((v,i)=>near(v,m.userData.expected_bounds_mm.min[i]));b.max.toArray().forEach((v,i)=>near(v,m.userData.expected_bounds_mm.max[i]));near(bounds(m.getObjectByName('terminal-2')).min.z,-3.6);if(n!==76)near(bounds(m.getObjectByName('lens')).min.x,-p.flange_diameter/2+p.flat_depth);}
});
test('can vent is a physical recess and the underside seal remains visible at every LOD',()=>{
 for(const lod of ['LOD0','LOD1','LOD2']){const m=createLedPassiveComponent(lib,'OHM-029',{lod});near(ray(m,[.5,0,20],[0,0,-1])[0].point.z,15.96);near(ray(m,[1,1,20],[0,0,-1])[0].point.z,16);assert.equal(ray(m,[0,0,-1],[0,0,1])[0].object.material.name,'MAT_RUBBER_SEAL');}
});
