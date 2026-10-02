import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import { createQuadGridLibrary, createQuadGridComponent } from '../component-library/quad-grid-registry.js';
import { rowLetter, sourcePointToTop } from '../component-library/quad-grid-layout.js';
import { placeInViewer } from '../component-library/transforms.js';

const data=JSON.parse(readFileSync(new URL('../component-library/data/quad-grid.json',import.meta.url)));
const library=createQuadGridLibrary(data);
const cases=[
    [122,32,-4.2,2.8,.8],[123,44,-5.7,4,.8],[124,64,-5.7,3.75,.5],[125,100,-7.7,6,.5],[126,144,-10.7,8.75,.5],
    [127,16,-1.3,.75,.5],[128,20,-1.8,1,.5],[129,24,-1.8,1.25,.5],[130,32,-2.3,1.75,.5],[131,48,-3.3,2.75,.5],
    [132,6,-.825,.65,.65],[133,8,-1.3,.975,.65],[134,8,-.8,.75,.5],[135,28,0,5.775,1.27],
    [136,64,-2.8,2.8,.8],[137,100,-3.6,3.6,.8],[138,256,-7.5,7.5,1],[139,9,-.4,.4,.4],[140,16,-.75,.75,.5]];
const near=(a,b,tol=1e-5)=>assert.ok(Math.abs(a-b)<=tol,`${a} != ${b}`);
const bounds=o=>{o.updateWorldMatrix(true,true);return new THREE.Box3().setFromObject(o);};
function ray(model,x,y,z,direction=[0,0,1]) {
    model.updateMatrixWorld(true);return new THREE.Raycaster(new THREE.Vector3(x,y,z),new THREE.Vector3(...direction)).intersectObject(model,true);
}
function signature(model) {
    const nodes=[];model.updateMatrixWorld(true);
    model.traverse(n=>{if(!n.isMesh)return;nodes.push({name:n.name,matrix:n.matrixWorld.toArray(),
        instance:n.isInstancedMesh?Array.from(n.instanceMatrix.array):null,
        attributes:Object.fromEntries(Object.entries(n.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),
        index:n.geometry.index?Array.from(n.geometry.index.array):null,
        material:[n.material.name,n.material.color.getHexString(),n.material.roughness,n.material.metalness],
        texture:n.material.map?Array.from(n.material.map.image.data):null,metadata:n.userData});});
    return createHash('sha256').update(JSON.stringify({metadata:model.userData,nodes})).digest('hex');
}
const terminalMesh=m=>m.getObjectByName('gull-wing-leads')??m.getObjectByName('leadless-terminals')??m.getObjectByName('j-leads')??m.getObjectByName('solder-balls');

test('all 19 Stage 3 records match source fingerprints, statuses and pin1 positions',()=>{
    assert.deepEqual(Object.keys(library.records),cases.map(c=>`OHM-${c[0]}`));
    const source=readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md',import.meta.url));
    assert.equal(createHash('sha256').update(source).digest('hex'),data.source_spec_sha256);
    for(const r of Object.values(library.records)) {
        const section=source.toString().split(`# [${r.id}]`)[1].split(/\n# \[|\n## PROPOSED ADDITIONS/)[0];
        const raw=section.match(/```yaml\s*\n([\s\S]*?)\n```/)[1];
        assert.equal(createHash('sha256').update(raw).digest('hex'),r.source.yaml_sha256);
        assert.equal(raw.match(/^status: (\w+)/m)[1],r.status);assert.equal(r.library_metadata.footprint_binding,null);
    }
});

for(const [n,count,x,y,pitch] of cases)for(const lod of ['LOD0','LOD1','LOD2']) {
    const id=`OHM-${n}`;
    test(`${id} ${lod}: pin1, order, side assignment, instances, actual contacts and determinism`,()=>{
        const m=createQuadGridComponent(library,id,{lod}),u=m.userData,p=u.parameters,cs=u.contacts;
        near(cs[0].center_mm[0],x);near(cs[0].center_mm[1],y);assert.equal(cs.length,count);assert.equal(u.terminal_count,count);
        const grid=n>=136;
        if(grid) {
            const N=Math.sqrt(count),alphabet='ABCDEFGHJKLMNPRTUVWY';
            cs.forEach((c,i)=>{const r=Math.floor(i/N),col=i%N;assert.equal(c.terminal,`${alphabet[r]}${col+1}`);
                assert.equal(c.row,r);assert.equal(c.column,col);near(c.center_mm[0],x+col*pitch);near(c.center_mm[1],y-r*pitch);});
            const marker=m.getObjectByName('pin1-decal');assert.equal(marker.userData.terminal,'A1');
            assert.ok(marker.position.x<0&&marker.position.y>0&&cs[0].center_mm[0]<0&&cs[0].center_mm[1]>0,'A1 and marker must share TOP-view corner');
        } else {
            assert.equal(u.side_counts.reduce((a,b)=>a+b,0),count);
            const actual=['left','bottom','right','top'].map(side=>cs.filter(c=>c.side===side).length);assert.deepEqual(actual,u.side_counts);
            if(n===135) {
                const expectedSides=[...Array(4).fill('top'),...Array(7).fill('left'),...Array(7).fill('bottom'),...Array(7).fill('right'),...Array(3).fill('top')];
                assert.deepEqual(cs.map(c=>c.side),expectedSides);
                near(cs[3].center_mm[0],-3.81);near(cs[4].center_mm[0],-5.775);near(cs[4].center_mm[1],3.81);near(cs[27].center_mm[0],1.27);
            } else {
                const sides=n>=132?['left','right']:['left','bottom','right','top'],per=count/sides.length;
                cs.forEach((c,i)=>{const side=sides[Math.floor(i/per)],k=i%per,t=y-k*pitch;
                    const expected={left:[x,t],bottom:[-t,x],right:[-x,-t],top:[t,-x]}[side];
                    assert.equal(c.side,side);expected.forEach((v,j)=>near(c.center_mm[j],v));});
            }
            assert.deepEqual(cs.map(c=>c.terminal),Array.from({length:count},(_,i)=>String(i+1)));
        }
        if(lod!=='LOD0') {
            const mesh=terminalMesh(m);assert.ok(mesh.isInstancedMesh);assert.equal(mesh.count,count);
            assert.deepEqual(mesh.userData.instance_terminals,cs.map(c=>c.terminal));
            for(const c of cs) {
                const hit=ray(m,c.center_mm[0],c.center_mm[1],-1)[0];assert.ok(hit,`${c.terminal} contact missing`);
                near(hit.point.z,0);assert.equal(hit.object,mesh);assert.equal(mesh.userData.instance_terminals[hit.instanceId],c.terminal);
            }
        } else if(grid) {
            const slab=m.getObjectByName('ball-layer-proxy');assert.ok(slab&&!slab.isInstancedMesh&&slab.material.map);
            assert.equal(slab.userData.terminal_labels.length,count);assert.ok(new Set(slab.material.map.image.data).size>2);
        }
        if(n>=127&&n<=134) {
            const ep=m.getObjectByName('exposed-pad');assert.ok(ep);assert.equal(ep.userData.numbered,false);
            near(ray(m,0,0,-1)[0].point.z,0);assert.equal(ray(m,0,0,-1)[0].object,ep);
            const eb=bounds(ep);near(eb.max.x-eb.min.x,p.ep_x);near(eb.max.y-eb.min.y,p.ep_y);
        }
        const b=bounds(m),size=b.getSize(new THREE.Vector3()).toArray();size.forEach((v,i)=>near(v,u.expected_dimensions_mm[i]));near(b.min.z,0);near(b.max.z,p.height);
        let objects=0,triangles=0;
        m.traverse(o=>{if(!o.isMesh)return;objects++;const g=o.geometry;triangles+=(g.index?.count??g.attributes.position.count)/3*(o.isInstancedMesh?o.count:1);
            assert.ok(Array.from(g.attributes.position.array).every(Number.isFinite));
            const norm=g.attributes.normal;for(let i=0;i<norm.count;i++)near(Math.hypot(norm.getX(i),norm.getY(i),norm.getZ(i)),1,1e-4);
        });
        assert.ok(objects<=8,`mesh/draw budget ${objects}`);assert.ok(triangles<(lod==='LOD2'?250000:75000),`triangle budget ${triangles}`);
        assert.equal(signature(m),signature(createQuadGridComponent(library,id,{lod})));
    });
}

test('PLCC center_top and Section 6 modes relocate pin1 without mirroring the J-lead geometry',()=>{
    const a=createQuadGridComponent(library,'OHM-135'),b=createQuadGridComponent(library,'OHM-135',{pin1_mode:'section6_topleft'});
    assert.deepEqual(a.userData.contacts[0].center_mm,[0,5.775,0]);assert.deepEqual(b.userData.contacts[0].center_mm,[-5.775,3.81,0]);
    assert.deepEqual(b.userData.contacts.map(c=>c.side),['left','bottom','right','top'].flatMap(s=>Array(7).fill(s)));
    assert.equal(a.getObjectByName('pin1-decal').position.x,0);assert.ok(b.getObjectByName('pin1-decal').position.x<0);
    const hit=ray(a,5.775,0,-1)[0];near(hit.point.z,0);assert.equal(hit.object.name,'j-leads');
    assert.ok(a.userData.library_metadata.uncertain_values.some(s=>s.includes('secondary')));
});

test('row letters are parameterized and bottom-view inputs explicitly mirror X',()=>{
    const m=createQuadGridComponent(library,'OHM-138');assert.equal(m.userData.contacts[8*16].terminal,'J1');assert.equal(m.userData.contacts[15*16].terminal,'T1');
    const noSkip=createQuadGridComponent(library,'OHM-138',{row_letters:'ABCDEFGHIJKLMNOPQRSTUVWXYZ'});assert.equal(noSkip.userData.contacts[8*16].terminal,'I1');
    assert.equal(rowLetter(20,'ABCDEFGHJKLMNPRTUVWY'),'AA');assert.equal(rowLetter(21,'ABCDEFGHJKLMNPRTUVWY'),'AB');
    assert.deepEqual(sourcePointToTop([3.6,3.6],'BOTTOM'),[-3.6,3.6]);assert.deepEqual(sourcePointToTop([-3.6,3.6],'TOP'),[-3.6,3.6]);
    assert.throws(()=>sourcePointToTop([3.6,3.6],undefined));
});

test('depopulated centers, perimeter rows and arbitrary masks preserve coordinates and A1',()=>{
    for(const [depopulate,count] of [[{mode:'center',nx:4,ny:4},84],[{mode:'perimeter_rows',rows:1},36],[{mode:'positions',omitted:[[4,4],[4,5]]},98]]) {
        for(const lod of ['LOD0','LOD1']) {
            const m=createQuadGridComponent(library,'OHM-137',{depopulate,lod});assert.equal(m.userData.contacts.length,count);
            assert.equal(m.userData.contacts[0].terminal,'A1');assert.ok(!m.userData.contacts.some(c=>c.row===4&&c.column===4));
            assert.equal(m.userData.library_metadata.provisional,true);
        }
    }
    assert.throws(()=>createQuadGridComponent(library,'OHM-137',{depopulate:{mode:'positions',omitted:[[0,0]]}}));
    assert.throws(()=>createQuadGridComponent(library,'OHM-137',{depopulate:{mode:'center',nx:3,ny:3}}));
});

test('leadless pullback and EP clearance are visible in actual underside geometry',()=>{
    const flush=createQuadGridComponent(library,'OHM-130'),pull=createQuadGridComponent(library,'OHM-130',{terminal_pullback:.05});
    assert.equal(ray(flush,-2.49,1.75,-1)[0].object.name,'leadless-terminals');
    assert.equal(ray(pull,-2.49,1.75,-1)[0].object.name,'body');near(ray(pull,-2.49,1.75,-1)[0].point.z,.02);
    near(pull.userData.contacts[0].center_mm[0],-2.25);assert.equal(pull.userData.parameters.ep_x,3.3);
    assert.equal(ray(pull,-1.85,1.5,-1)[0].object.name,'body'); // visible gap between EP and terminals
    assert.throws(()=>createQuadGridComponent(library,'OHM-130',{terminal_pullback:.3}));
    const wson=createQuadGridComponent(library,'OHM-134');assert.ok(wson.userData.library_metadata.conflicts.some(c=>c.actual_mm===.15));
});

test('specified provisional fields and source status remain separate',()=>{
    for(const id of ['OHM-134','OHM-135','OHM-136','OHM-139'])assert.equal(library.records[id].library_metadata.provisional,true);
    assert.equal(library.records['OHM-136'].status,'complete');assert.equal(library.records['OHM-134'].status,'partial');
    assert.match(library.records['OHM-136'].library_metadata.uncertain_values.join(' '),/first-pass NXP/);
    assert.match(library.records['OHM-139'].library_metadata.uncertain_values.join(' '),/centering/);
    for(const n of [122,123,124,125,126])assert.match(library.records[`OHM-${n}`].library_metadata.uncertain_values.join(' '),/lead_thickness/);
});

test('impossible geometry and corrupted numbering data fail rather than resizing',()=>{
    for(const [id,options] of [['OHM-123',{pin_count:45}],['OHM-123',{lead_tip_span:10.5}],['OHM-130',{exposed_pad:4.5}],
        ['OHM-135',{pin1_mode:'bottom_right'}],['OHM-137',{ball_diameter:.3}],['OHM-137',{pitch:1}],
        ['OHM-137',{array_offset:[3,0]}],['OHM-137',{row_letters:'AA'}],['OHM-134',{terminal_length:.5}]])assert.throws(()=>createQuadGridComponent(library,id,options));
    for(const mutate of [d=>d.profiles['OHM-123'].side_counts[0]++,d=>d.components[0].terminals.pin1_xy_mm.reverse(),
        d=>d.profiles['OHM-136'].coordinate_view='BOTTOM',d=>d.profiles['OHM-136'].nx=7]) {
        const d=structuredClone(data);mutate(d);assert.throws(()=>createQuadGridLibrary(d));
    }
});

test('bottom placement transforms both A1 instances and markers together without changing canonical coordinates',()=>{
    const m=createQuadGridComponent(library,'OHM-137'),before=structuredClone(m.userData.contacts);
    const wrapper=placeInViewer(m,{side:'B.Cu',board_thickness_mm:1.6});wrapper.updateMatrixWorld(true);
    const marker=m.getObjectByName('pin1-decal').getWorldPosition(new THREE.Vector3());assert.ok(marker.x>0&&marker.y>0);
    const mesh=terminalMesh(m),matrix=new THREE.Matrix4();mesh.getMatrixAt(0,matrix);const p=new THREE.Vector3().setFromMatrixPosition(matrix);mesh.localToWorld(p);
    near(p.x,3.6);near(p.y,3.6);near(p.z,-.8);assert.deepEqual(m.userData.contacts,before);
});
