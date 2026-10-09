import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import * as THREE from '../vendor/three.module.js';
import { createControllerLibraries, createControllerModelResolver, controllerBinding, transformContact, STM32_PACKAGE } from '../landing-pcb-controller/models.js';
import { createControllerMaterials } from '../landing-pcb-controller/presentation.js';
import { actualSceneManifest } from '../visual-board-scene.js';
import { boardShape, disposeTree } from '../visual-renderer.js';
import { normalizeControllerSource, reflectControllerBoard } from '../landing-pcb-controller/projection.js';

const libraries = createControllerLibraries(Object.fromEntries(['chip2t','leaded','quad-grid','led-passive','completion-a']
    .map(key => [key, JSON.parse(readFileSync(new URL(`../component-library/data/${key}.json`, import.meta.url)))])));
function model(part_id, footprint_id, options = {}) {
    const part = { ref: 'U1', part_id, footprint_id, pads: [] };
    const source = { board: { components: [part] }, ...options };
    return createControllerModelResolver(source, libraries)({ id: 'U1', sourceFootprintId: footprint_id, options: {} }, createControllerMaterials());
}
const near = (a, b) => assert.ok(Math.abs(a-b) < 1e-6, `${a} differs from ${b}`); // Float32 mesh bounds.

test('ST LQFP100 retains datasheet dimensions and counter-clockwise top-view pin numbering', () => {
    const m = model('STM32F103VBT6', 'Package_QFP:LQFP-100_14x14mm_P0.5mm');
    try {
        assert.equal(m.userData.contacts.length, 100);
        const expected = { 1: [-7.7,6], 25: [-7.7,-6], 26: [-6,-7.7], 50: [6,-7.7],
            51: [7.7,-6], 75: [7.7,6], 76: [6,7.7], 100: [-6,7.7] };
        for (const [number, xy] of Object.entries(expected)) {
            const c = m.userData.contacts.find(c => c.terminal === number);
            xy.forEach((value, i) => near(c.center_mm[i], value));
        }
        const size = new THREE.Box3().setFromObject(m).getSize(new THREE.Vector3());
        near(size.x,16); near(size.y,16); near(size.z,1.5);
        assert.equal(STM32_PACKAGE.body_thickness,1.4);
        const pin1 = m.getObjectByName('pin1-decal');
        const marker = pin1.getWorldPosition(new THREE.Vector3());
        assert.ok(marker.x < 0 && marker.y > 0, 'marker stays in the physical top-left pin1 corner');
        const cs=m.userData.contacts.map(c=>c.center_mm);
        const winding=cs.reduce((sum,[x,y],i)=>{const next=cs[(i+1)%cs.length];return sum+x*next[1]-y*next[0];},0);
        assert.ok(winding>0,'pin1→100 must be counter-clockwise viewed from above');
        assert.ok(m.getObjectByName('laser-mark-decal').matrixWorld.determinant()>0,
            'separate identity lettering is not mirrored by the footprint-frame conversion');
        assert.equal(libraries.quad.profiles['OHM-125'].body_thickness,1,'shared TQFP record stays unchanged');
    } finally { disposeTree(m); }
});

test('SOIC16 and SOIC8 numbering follow the normalized physical footprint rows', () => {
    for (const [id,count,firstY] of [['SN74HC595D',16,4.445],['25LC256-I/SN',8,1.905]]) {
        const m=model(id,'Package_SO:SOIC');
        try {
            const contacts=m.userData.contacts;
            assert.equal(contacts.length,count);
            near(contacts[0].center_mm[0],-2.58);near(contacts[0].center_mm[1],firstY);
            assert.ok(contacts[count/2-1].center_mm[1]<0);
            assert.ok(contacts[count/2].center_mm[0]>0 && contacts[count/2].center_mm[1]<0);
            assert.ok(contacts[count-1].center_mm[0]>0 && contacts[count-1].center_mm[1]>0);
        } finally {disposeTree(m);}
    }
});

test('two-row expansion header is centered and preserves all forty named contacts', () => {
    const m=model('TSW-120-07-G-D','Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical');
    try {
        const c=m.userData.contacts;assert.equal(c.length,40);
        near(c[0].center_mm[0],-1.27);near(c[0].center_mm[1],24.13);
        near(c[1].center_mm[0],1.27);near(c[1].center_mm[1],24.13);
        near(c[38].center_mm[1],-24.13);near(c[39].center_mm[1],-24.13);
        const bounds=new THREE.Box3().setFromObject(m);
        near(bounds.min.z,-2.54);near(bounds.max.z,8.38);
        m.traverse(node=>assert.equal(node.userData.owner,undefined,'library OHM IDs cannot intercept circuit-reference picking'));
    } finally {disposeTree(m);}
});

test('Kingbright LED is its sourced height, not the generic LED library height', () => {
    const m=model('APT1608SGC','LED_SMD:LED_0603_1608Metric');
    try {
        const size=new THREE.Box3().setFromObject(m).getSize(new THREE.Vector3());
        near(size.x,1.6);near(size.y,.8);near(size.z,.75);
        assert.equal(m.userData.contacts[0].terminal,'1');assert.ok(m.userData.contacts[0].center_mm[0]<0);
        assert.equal(libraries.led.profiles['OHM-078'].body_h,.55);
    } finally {disposeTree(m);}
});

test('AP2112 SOT23-5 pin1 and row order follow the source footprint, not SOIC convention', () => {
    const m=model('AP2112K-3.3TRG1','Package_TO_SOT_SMD:SOT-23-5');
    try {
        const c=m.userData.contacts;assert.equal(c.length,5);
        const expected=[[-1.2,.95],[-1.2,0],[-1.2,-.95],[1.2,-.95],[1.2,.95]];
        c.forEach((contact,i)=>expected[i].forEach((value,axis)=>near(contact.center_mm[axis],value)));
    } finally {disposeTree(m);}
});

test('complete display coordinate normalization is reversible and preserves original artifact geometry',()=>{
    const board={width_mm:100,height_mm:70,artifact_fingerprint:'source-identity',
        components:[{ref:'U1',x_mm:25,y_mm:15,rotation_deg:90,pads:[{number:'1',x_mm:-3,y_mm:-2,rotation_deg:90}]}],
        tracks:[{start_x_mm:3,start_y_mm:4,end_x_mm:5,end_y_mm:6}],vias:[{x_mm:8,y_mm:9}],
        mounting_holes:[{x_mm:5,y_mm:5,diameter_mm:3.2}]};
    const source={board,components:[]},before=JSON.stringify(source),display=normalizeControllerSource(source);
    assert.notStrictEqual(display.board,board);assert.equal(JSON.stringify(source),before);
    assert.deepEqual(reflectControllerBoard(display.board),board,'the affine frame conversion round-trips every physical feature');
    const d=display.board;
    assert.equal(d.components[0].y_mm,55);assert.equal(d.components[0].rotation_deg,-90);
    assert.equal(d.components[0].pads[0].y_mm,2);assert.equal(d.components[0].pads[0].rotation_deg,-90);
    assert.equal(d.tracks[0].start_y_mm,66);assert.equal(d.tracks[0].end_y_mm,64);
    assert.equal(d.vias[0].y_mm,61);assert.equal(d.mounting_holes[0].y_mm,65);
    const world=(part,pad)=>{const a=part.rotation_deg*Math.PI/180;return[part.x_mm+pad.x_mm*Math.cos(a)-pad.y_mm*Math.sin(a),part.y_mm+pad.x_mm*Math.sin(a)+pad.y_mm*Math.cos(a)];};
    const original=world(board.components[0],board.components[0].pads[0]),projected=world(d.components[0],d.components[0].pads[0]);
    near(projected[0],original[0]);near(projected[1],70-original[1]);
    assert.equal(d.artifact_fingerprint,board.artifact_fingerprint);
    assert.throws(()=>normalizeControllerSource(display),/already normalized/);
});

test('normalized USB opens off the south edge while preserving every source contact position',()=>{
    const original=JSON.parse(readFileSync(new URL('../landing-pcb-redesign/candidate-board.json',import.meta.url)));
    const source=normalizeControllerSource(original),part=source.board.components.find(p=>p.ref==='J1');
    const entry=actualSceneManifest(source.board).instances.find(p=>p.id==='J1');
    const m=createControllerModelResolver(source,libraries)(entry,createControllerMaterials());
    try{
        const contacts=m.userData.source_pad_contacts;
        for(const c of contacts){const pad=part.pads.find(p=>p.number===c.number&&Math.abs(p.x_mm-c.center_mm[0])<1e-6&&Math.abs(p.y_mm-c.center_mm[1])<1e-6);assert.ok(pad,`Lost source contact ${c.number}`);}
        assert.ok(contacts.length>=16);
        const opening=transformContact([0,m.userData.model_metadata.cavity.openingY,0],m.userData.package_binding);
        assert.ok(opening[1]<0,'cable enters from the physical south edge');
    }finally{disposeTree(m);}
});

test('unknown components cannot silently acquire a plausible but unrelated package', () => {
    assert.throws(()=>controllerBinding({part_id:'UNKNOWN',footprint_id:'UNKNOWN'}),/No declared/);
    assert.throws(()=>controllerBinding({part_id:'SN74HC595PW',footprint_id:'Package_SO:TSSOP-16'}),/No declared/);
    assert.throws(()=>controllerBinding({part_id:'25LC256-I/ST',footprint_id:'Package_SO:TSSOP-8'}),/No declared/);
});

test('Omron switch retains four physical source legs and the sourced ivory actuator envelope',()=>{
    const pads=[[-3.25,2.25,'1'],[-3.25,-2.25,'1'],[3.25,2.25,'2'],[3.25,-2.25,'2']]
        .map(([x_mm,y_mm,number])=>({x_mm,y_mm,number,kind:'thru_hole'}));
    const part={ref:'SW1',part_id:'B3F-1000',footprint_id:'Button_Switch_THT:SW_PUSH_6mm',pads};
    const m=createControllerModelResolver({board:{components:[part]}},libraries)(
        {id:'SW1',sourceFootprintId:part.footprint_id,options:{}},createControllerMaterials());
    try{
        const bounds=new THREE.Box3().setFromObject(m);
        near(bounds.min.z,-3.5);near(bounds.max.z,4.3);
        assert.equal(m.userData.source_pad_contacts.length,4);
        for(const [i,c] of m.userData.source_pad_contacts.entries()) {
            assert.equal(c.number,pads[i].number);
            near(c.center_mm[0],pads[i].x_mm);near(c.center_mm[1],pads[i].y_mm);
        }
        const actuator=m.getObjectByName('3.5 mm ivory actuator');
        const size=new THREE.Box3().setFromObject(actuator).getSize(new THREE.Vector3());
        near(size.x,3.5);near(size.y,3.5);near(size.z,.9);
    }finally{disposeTree(m);}
});

test('source mechanical holes cut the substrate without becoming copper or component models', () => {
    const board={artifact_fingerprint:'mechanical-test',width_mm:100,height_mm:70,display_thickness_mm:1.6,
        components:[],tracks:[],vias:[],mounting_holes:[{ref:'H1',kind:'np_thru_hole',x_mm:5,y_mm:5,diameter_mm:3.2,source_footprint:'MountingHole:MountingHole_3.2mm_M3'}]};
    const before=JSON.stringify(board),manifest=actualSceneManifest(board);
    assert.equal(manifest.instances.length,0);assert.equal(manifest.pads.length,0);
    assert.deepEqual([manifest.holes[0].x,manifest.holes[0].y,manifest.holes[0].radius],[-45,-30,1.6]);
    assert.equal(manifest.holes[0].annulus,undefined);
    const shape=boardShape(100,70,manifest.holes);assert.equal(shape.holes.length,1);
    assert.equal(JSON.stringify(board),before);
    assert.throws(()=>actualSceneManifest({...board,mounting_holes:[{...board.mounting_holes[0],diameter_mm:-1}]}),/Invalid source mounting hole/);
});
