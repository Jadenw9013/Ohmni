import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import * as THREE from "../vendor/three.module.js";
import { ASSET_FAMILIES, ASSET_REGISTRY, createAsset, createMaterials } from "../visual-assets.js";
import { actualSceneManifest } from "../visual-board-scene.js";

const near = (a, b, tolerance = 1e-5) => assert.ok(Math.abs(a - b) <= tolerance, `${a} != ${b}`);
const ray = (group, origin, direction) => {
    group.updateMatrixWorld(true);
    return new THREE.Raycaster(new THREE.Vector3(...origin), new THREE.Vector3(...direction))
        .intersectObject(group, true);
};

test("every family builds without DOM or downloaded textures and stays above the contact plane", () => {
    const materials = createMaterials();
    for (const family of ASSET_FAMILIES) {
        const group = createAsset(family, {}, materials);
        assert.ok(group.isGroup);
        assert.equal(group.userData.appearanceOnly, true);
        assert.equal(group.userData.dimensionsAreIllustrative, true);
        assert.equal("verificationStatus" in group.userData, false);
        group.updateMatrixWorld(true);
        const bounds = new THREE.Box3().setFromObject(group);
        assert.ok(bounds.min.z > -1e-5, `${family} must not float below the contact plane`);
        assert.ok(bounds.max.z > 0);
        let drawCalls = 0, triangles = 0;
        group.traverse((object) => {
            if (!object.isMesh) return;
            drawCalls += 1;
            triangles += (object.geometry.index?.count ?? object.geometry.attributes.position.count) / 3
                * (object.isInstancedMesh ? object.count : 1);
            assert.ok(object.geometry.attributes.position.array.every(Number.isFinite));
            assert.ok(object.geometry.attributes.normal.array.every(Number.isFinite));
            assert.equal(object.castShadow, true);
            assert.equal(object.receiveShadow, true);
            assert.ok(object.material.isMeshStandardMaterial);
            assert.equal(object.material.map, null);
            assert.equal(object.material.emissive.getHex(), 0, "coated parts must not glow");
        });
        assert.ok(drawCalls <= 10, `${family}: repeat details share draw calls`);
        assert.ok(triangles < 15000, `${family}: macro detail fits a dense-scene budget`);
    }
});

test("header top opens into a real cavity while its walls occlude lateral views", () => {
    const group = createAsset("header", { contactCount: 24, width: 30, depth: 5.2, height: 6 });
    const centre = ray(group, [0, 0, 20], [0, 0, -1])[0];
    assert.equal(centre.object.name, "recess floor");
    near(centre.point.z, group.userData.cavity.floor);
    const wall = ray(group, [0, -20, 4], [0, 1, 0])[0];
    assert.match(wall.object.name, /cavity wall/);
    near(wall.point.y, -2.6, 1e-4);
    const contacts = group.getObjectByName("individual recessed gold contacts");
    assert.ok(contacts.isInstancedMesh);
    assert.equal(contacts.count, 24);
    const transform = new THREE.Matrix4();
    contacts.getMatrixAt(0, transform);
    const position = new THREE.Vector3().setFromMatrixPosition(transform);
    const hit = ray(group, [position.x, position.y, 20], [0, 0, -1])[0];
    assert.strictEqual(hit.object, contacts);
    assert.equal(hit.instanceId, 0);
    assert.ok(hit.point.z < 6 && hit.point.z > group.userData.cavity.floor);
});

test("gullwing leads have exposed shoulders, a descending knee and a flat solder foot", () => {
    const group = createAsset("qfp", { width: 14, depth: 14, height: 1.5, leadCount: 64, includeSolder: false });
    const leads = group.getObjectByName("individual gullwing leads");
    assert.equal(leads.count, 64);
    const transform = new THREE.Matrix4();
    leads.getMatrixAt(0, transform);
    const position = new THREE.Vector3().setFromMatrixPosition(transform);
    const reach = group.userData.dimensions.leadReach;
    const samples = [0.1, 0.46, 0.9].map((fraction) =>
        ray(group, [position.x + reach * fraction, position.y, 8], [0, 0, -1])
            .find((hit) => hit.object === leads));
    assert.ok(samples.every(Boolean), "each part of the bent lead is actual visible geometry");
    assert.ok(samples[0].point.z > samples[1].point.z + 0.1);
    assert.ok(samples[1].point.z > samples[2].point.z + 0.1);
    const foot = ray(group, [position.x + reach * 0.8, position.y, 8], [0, 0, -1])
        .find((hit) => hit.object === leads);
    near(samples[2].point.z, foot.point.z);
    assert.ok(samples[2].point.z < 0.3);
    assert.equal(group.getObjectByName("illustrative solder feet"), undefined);
});

test("all contact and lead submeshes resolve to the caller's one component owner", () => {
    for (const family of ASSET_FAMILIES) {
        const group = createAsset(family);
        const owner = { instanceId: `custom-${family}`, visualProvenance: "ILLUSTRATIVE_ONLY" };
        group.userData.owner = owner;
        group.traverse((object) => {
            if (!object.isMesh) return;
            let candidate = object;
            while (candidate && !candidate.userData.owner) candidate = candidate.parent;
            assert.strictEqual(candidate?.userData.owner, owner);
        });
    }
});

test("cans and axial resistors keep compound materials and modeled attachment detail", () => {
    const materials = createMaterials();
    const can = createAsset("aluminum_can", { width: 8, height: 10 }, materials);
    assert.strictEqual(can.getObjectByName("formed aluminum can wall").material, materials.aluminum);
    assert.strictEqual(can.getObjectByName("can insulator base").material, materials.plastic);
    assert.ok(can.getObjectByName("rolled can rim").geometry.isBufferGeometry);
    const resistor = createAsset("axial_resistor", { width: 7, depth: 2.4, height: 3.5 }, materials);
    assert.equal(resistor.getObjectByName("two bent axial leads").count, 2);
    assert.strictEqual(resistor.getObjectByName("rounded blue axial body").material, materials.blue);
    assert.equal(resistor.children.filter((object) => object.name.startsWith("illustrative band ")).length, 4);
    assert.equal(resistor.userData.bandsAreIllustrative, true);
    assert.equal("resistance" in resistor.userData, false);
    const custom = createAsset("qfp", { color: "#454545", label: "Q TEST", leadCount: 32 }, materials);
    assert.equal(custom.getObjectByName("individual gullwing leads").count, 32);
    assert.equal(custom.getObjectByName("beveled resin body").material.color.getHexString(), "454545");
    assert.equal(materials.resin.color.getHexString(), "25282a", "per-instance color never mutates shared material");
});

test("unsupported or impossible illustration parameters fail rather than invent details", () => {
    for (const [family, options] of [["missing", {}], ["toString", {}], ["qfp", { width: NaN }],
        ["qfp", { leadCount: 63 }], ["qfp", { width: 1, leadCount: 256 }],
        ["header", { contactCount: 3, rows: 2 }], ["axial_resistor", { height: 1 }],
        ["small_outline", { leadCount: 5 }], ["wound_inductor", { height: 0.5 }],
        ["sensor", { pads: "guessed" }], ["regulator", { pads: [{x_mm:0, y_mm:NaN, width_mm:1, height_mm:1}] }]]) {
        assert.throws(() => createAsset(family, options), RangeError);
    }
});

test("the registry records original geometry and appearance provenance without a verification claim", () => {
    assert.deepEqual(Object.keys(ASSET_REGISTRY), ASSET_FAMILIES);
    for (const family of ASSET_FAMILIES) {
        const record = ASSET_REGISTRY[family];
        assert.equal(record.modelAssetId, `ohmni-procedural/${family}@reference-packages-v1`);
        assert.equal(record.source.kind, "ORIGINAL_PROCEDURAL_SOURCE");
        assert.equal(record.source.thirdPartyGeometry, false);
        assert.equal(record.source.electricalAuthority, false);
        assert.equal(record.source.license, "Repository license unspecified");
        assert.equal(record.appearanceOnly, true);
        assert.equal(record.units, "mm");
        assert.equal(record.upAxis, "z");
        assert.equal(record.contactPlane, 0);
        assert.equal("verified" in record, false);
    }
});

test("both metal-shell apertures and the USB-C mouth are open geometry", () => {
    const shield = createAsset("shielded_connector");
    const roof = shield.getObjectByName("sheet metal roof with two open apertures");
    for (const {x,y,radius} of shield.userData.apertures) {
        for (const delta of [0, radius * 0.7]) {
            const hits = ray(shield, [x + delta, y, 20], [0,0,-1]);
            assert.ok(hits.length > 0, "the aperture reveals the interior below");
            assert.ok(hits.every((hit) => hit.object !== roof), "no roof triangle closes the opening");
            assert.ok(hits[0].point.z < shield.userData.dimensions.height - 1);
        }
    }
    assert.strictEqual(ray(shield, [0,0,20], [0,0,-1])[0].object, roof);
    assert.equal(shield.userData.electricalIdentity, "UNKNOWN");
    const usb = createAsset("usb_c");
    const opening = ray(usb, [0,20,2.4], [0,-1,0])[0];
    assert.equal(opening.object.name, "USB-C rear insert");
    assert.ok(opening.point.y < 0, "the mouth reveals a recessed insert");
    const rim = ray(usb, [0,20,3.3], [0,-1,0])[0];
    assert.equal(rim.object.name, "open oval USB-C metal shell");
    near(rim.point.y, usb.userData.cavity.openingY);
});

test("SOIC variants retain two rows of independently bent leads and white connectors retain cavities", () => {
    for (const options of [{width:5,depth:3.2,height:1.1,leadCount:8},
        {width:11,depth:8,height:2,leadCount:28}, {width:20,depth:6,height:2,leadCount:48}]) {
        const group = createAsset("small_outline", {...options, includeSolder:false});
        const leads = group.getObjectByName("individual small-outline leads");
        assert.equal(leads.count, options.leadCount);
        const transform = new THREE.Matrix4(), position = new THREE.Vector3();
        const rows = new Set();
        for (let i=0;i<leads.count;i+=1) {
            leads.getMatrixAt(i,transform);
            position.setFromMatrixPosition(transform);
            rows.add(position.y);
            near(Math.abs(position.y), options.depth / 2);
        }
        assert.equal(rows.size, 2);
        assert.equal(group.getObjectByName("illustrative small-outline solder"), undefined);
    }
    for (const [width,depth,height,contactCount] of [[7,5,4,4],[15,9,7,10]]) {
        const group = createAsset("white_connector", {width,depth,height,contactCount});
        const center = ray(group,[0,depth*.22,20],[0,0,-1])[0];
        assert.equal(center.object.name, "connector insulated floor");
        near(center.point.z, group.userData.cavity.floor);
        assert.equal(group.getObjectByName("individual interior connector contacts").count, contactCount);
    }
});

test("actual package contacts preserve arbitrary source-pad identities and coordinates without guessing missing pins", () => {
    const families = ASSET_FAMILIES.filter((family) => ASSET_REGISTRY[family].contactBasis === "source-pads");
    families.push("ceramic_chip");
    const pads = [
        {number:"A",x_mm:-12,y_mm:1.25,width_mm:1.7,height_mm:0.9,kind:"smd"},
        {number:"A",x_mm:11,y_mm:-3.5,width_mm:0.8,height_mm:1.3,kind:"thru_hole"},
        {number:"42",x_mm:0,y_mm:0,width_mm:0.6,height_mm:0.4,kind:"smd"},
        {number:"",x_mm:8,y_mm:4,width_mm:1.2,height_mm:1.2,kind:"np_thru_hole"},
    ];
    const expected = pads.slice(0,3).map(({number,x_mm,y_mm}) => ({number,x_mm,y_mm}));
    const before = structuredClone(pads);
    for (const family of families) {
        const group = createAsset(family, {pads, includeSolder:false, actual:true});
        assert.deepEqual(group.userData.sourceContacts, expected, family);
        assert.equal(group.userData.contactBasis, "source-pads");
        let contactCount = 0;
        group.traverse((object) => {
            if (!object.isMesh) return;
            assert.doesNotMatch(object.name, /illustrative.*solder|illustrative.*feet/i);
            if (/source-pad-derived|source-position gold/.test(object.name)) contactCount += object.count;
        });
        assert.equal(contactCount, 3, `${family} has exactly the three source electrical pads`);
        const empty = createAsset(family, {includeSolder:false, actual:true});
        assert.deepEqual(empty.userData.sourceContacts, [], `${family} cannot manufacture contacts without pads`);
        empty.traverse((object) => assert.doesNotMatch(object.name, /source-pad-derived|source-position gold|two metal chip terminations/));
    }
    assert.deepEqual(pads, before, "rendering cannot change source artifacts");
    const header = createAsset("pin_header", {pads});
    const contacts = header.getObjectByName("source-position gold header pins");
    for (let i=0;i<expected.length;i+=1) {
        const transform = new THREE.Matrix4(); contacts.getMatrixAt(i, transform);
        const position = new THREE.Vector3().setFromMatrixPosition(transform);
        near(position.x, expected[i].x_mm); near(position.y, expected[i].y_mm);
    }
});

test("the saved actual board preserves every terminal identity and the first-pin header origin", () => {
    const board = JSON.parse(readFileSync(new URL("../reference-board.json", import.meta.url))).board;
    const before = JSON.stringify(board), manifest = actualSceneManifest(board);
    const groups = new Map();
    for (const entry of manifest.instances) {
        const group = createAsset(entry.family, entry.options);
        const expected = entry.options.pads.filter((pad) => pad.kind !== "np_thru_hole")
            .map(({number,x_mm,y_mm}) => ({number,x_mm,y_mm}));
        assert.deepEqual(group.userData.sourceContacts, expected, entry.id);
        assert.equal(group.userData.contactBasis, "source-pads");
        assert.equal("pinRoles" in group.userData, false, "appearance does not infer electrical pin roles");
        groups.set(entry.id, group);
    }
    assert.equal(JSON.stringify(board), before);
    const header = groups.get("J2");
    header.updateMatrixWorld(true);
    const housing = new THREE.Box3().setFromObject(header.getObjectByName("source-position header insulators"));
    near(housing.min.y, -1.27); near(housing.max.y, 13.97);
    const pins = header.getObjectByName("source-position gold header pins");
    assert.equal(pins.count, 6);
    for (let i=0;i<6;i+=1) {
        const transform = new THREE.Matrix4(); pins.getMatrixAt(i, transform);
        const position = new THREE.Vector3().setFromMatrixPosition(transform);
        near(position.x, 0); near(position.y, i * 2.54);
    }
    const usb = groups.get("J1");
    assert.equal(usb.userData.sourceContacts.length, 20, "all16 signal identities and4 source SH identities remain");
    assert.equal(usb.userData.sourceContacts.filter((pad) => pad.number === "SH").length, 4);
    assert.equal(usb.userData.sourceContacts.filter((pad) => pad.number === "").length, 0, "mechanical holes are not contacts");
    assert.equal(usb.userData.renderedSourceTerminalCount, 16, "four coincident A/B lands draw once without deleting identity");
    assert.equal(groups.get("C1").getObjectByName("two metal chip terminations"), undefined);
    assert.equal(groups.get("C1").getObjectByName("source-pad-derived terminations").count, 2);
});

test("tan chip and rounded axial variants remain distinct and cannot invent actual-board contacts", () => {
    const materials = createMaterials();
    const chip = createAsset("ceramic_chip", {bodyShape:"chip"}, materials);
    const axial = createAsset("ceramic_chip", {bodyShape:"axial",width:4,depth:1.5,height:2.6}, materials);
    assert.equal(chip.userData.bodyShape, "chip");
    assert.equal(axial.userData.bodyShape, "axial");
    assert.strictEqual(axial.getObjectByName("rounded tan axial body").material, materials.tan);
    assert.equal(axial.getObjectByName("two bent axial leads").count, 2);
    assert.equal(axial.children.filter((item) => item.name.startsWith("illustrative band ")).length, 0);
    for (const options of [{bodyShape:"unknown"}, {bodyShape:"axial",actual:true},
        {bodyShape:"axial",pads:[]}]) assert.throws(() => createAsset("ceramic_chip",options), RangeError);
});

test("sleeved cans, winding turns, coated parts and unknown patches have distinct material geometry", () => {
    const materials = createMaterials();
    for (const height of [8,12,17]) {
        const group = createAsset("electrolytic_can", {height}, materials);
        assert.strictEqual(group.getObjectByName("formed aluminum can wall").material, materials.sleeve);
        assert.strictEqual(group.getObjectByName("inset aluminum lid").material, materials.aluminum);
        assert.equal(group.userData.sleeveMarkingsAreIllustrative, true);
        near(group.userData.dimensions.height, height);
    }
    const coil = createAsset("wound_inductor", {turnCount:7}, materials);
    const winding = coil.getObjectByName("continuous helical winding");
    assert.strictEqual(winding.material, materials.winding);
    const curve = winding.geometry.parameters.path;
    const lower = curve.getPoint(0), turn = curve.getPoint(1/7), halfway = curve.getPoint(.5/7);
    near(lower.x, turn.x); near(lower.y, turn.y);
    assert.ok(turn.z > lower.z);
    assert.ok(halfway.x < 0 && lower.x > 0, "one turn actually winds around the core");
    const unbanded = createAsset("coated_axial");
    assert.equal(unbanded.children.filter((item) => item.name.startsWith("illustrative band ")).length, 0);
    assert.equal(unbanded.getObjectByName("two bent axial leads").count, 2);
    const red = createAsset("coated_red", {}, materials);
    assert.strictEqual(red.getObjectByName("chip dielectric body").material, materials.red);
    assert.equal(materials.red.emissive.getHex(), 0);
    const patch = createAsset("unresolved_patch");
    assert.equal(patch.userData.isComponent, false);
    assert.equal(patch.userData.electricalIdentity, "UNKNOWN");
    assert.equal(patch.children.length, 1);
});
