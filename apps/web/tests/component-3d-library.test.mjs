import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as THREE from '../vendor/three.module.js';
import { createLibrary, createComponent } from '../component-library/registry.js';
import { createLibraryMaterials, MATERIAL_TOKENS } from '../component-library/materials.js';
import { placeInViewer, footprintFCO, validateFootprintBinding, tailBottom } from '../component-library/transforms.js';

const data = JSON.parse(readFileSync(new URL('../component-library/data/chip2t.json', import.meta.url)));
const library = createLibrary(data);
const ids = [...Array.from({ length: 9 }, (_, i) => i + 1), 14,
    ...Array.from({ length: 7 }, (_, i) => i + 21), 41, 42, 43].map(n => `OHM-${String(n).padStart(3, '0')}`);
const near = (a, b, tol = 1e-5) => assert.ok(Math.abs(a - b) <= tol, `${a} != ${b}`);
const bounds = object => { object.updateMatrixWorld(true); return new THREE.Box3().setFromObject(object); };
const ray = (model, start, direction) => {
    model.updateMatrixWorld(true);
    return new THREE.Raycaster(new THREE.Vector3(...start), new THREE.Vector3(...direction)).intersectObject(model, true);
};
function signature(model) {
    const meshes = []; model.updateMatrixWorld(true);
    model.traverse(node => {
        if (!node.isMesh) return;
        meshes.push({ name: node.name, matrix: node.matrixWorld.toArray(),
            attributes: Object.fromEntries(Object.entries(node.geometry.attributes).map(([key, attr]) => [key, Array.from(attr.array)])),
            index: node.geometry.index ? Array.from(node.geometry.index.array) : null,
            material: [node.material.name, node.material.color.getHexString(), node.material.roughness, node.material.metalness],
            metadata: node.userData });
    });
    return createHash('sha256').update(JSON.stringify({ metadata: model.userData, meshes })).digest('hex');
}

test('all 20 defaults retain the supplied spec identifiers, dimensions, contacts and statuses', () => {
    assert.deepEqual(Object.keys(library.records), ids);
    const source = readFileSync(new URL('../../../PCB_COMPONENT_3D_LIBRARY_SPEC.md', import.meta.url));
    assert.equal(createHash('sha256').update(source).digest('hex'), data.source_spec_sha256);
    const text = source.toString('utf8');
    for (const id of ids) {
        const section = text.slice(text.indexOf(`# [${id}]`)).split(/\n# \[|\n## PROPOSED ADDITIONS/)[0];
        const raw = section.match(/```yaml\s*\n([\s\S]*?)\n```/)[1];
        const record = library.records[id];
        assert.equal(createHash('sha256').update(raw).digest('hex'), record.source.yaml_sha256);
        for (const [name, dimension] of Object.entries(record.dimensions_mm)) {
            const match = raw.match(new RegExp(`  ${name}:\\s*\\{default: ([\\d.]+)`));
            assert.ok(match, `${id}/${name}`); assert.equal(dimension.default, Number(match[1]));
        }
        assert.equal(record.status, raw.match(/status: (\w+)/)[1]);
        assert.equal(record.library_metadata.provisional, ['OHM-014', 'OHM-043'].includes(id));
        assert.equal(record.library_metadata.footprint_binding, null);
        assert.ok(Object.isFrozen(record.dimensions_mm));
    }
});

for (const id of ids) for (const lod of ['LOD0', 'LOD1', 'LOD2']) {
    test(`${id} ${lod}: measured envelope, two complete contact areas, finite geometry and deterministic output`, () => {
        const first = createComponent(library, id, { lod }), second = createComponent(library, id, { lod });
        const [L, W, H] = first.userData.expected_dimensions_mm, box = bounds(first);
        [-L / 2, -W / 2, 0].forEach((n, i) => near(box.min.getComponent(i), n));
        [L / 2, W / 2, H].forEach((n, i) => near(box.max.getComponent(i), n));
        assert.equal(first.userData.contacts.length, 2); assert.notEqual(first.uuid, second.uuid);
        assert.equal(signature(first), signature(second));
        let triangles = 0;
        first.traverse(mesh => {
            if (!mesh.isMesh) return;
            triangles += mesh.geometry.attributes.position.count / 3;
            for (const attribute of Object.values(mesh.geometry.attributes)) assert.ok(attribute.array.every(Number.isFinite));
            const normals = mesh.geometry.attributes.normal;
            for (let i = 0; i < normals.count; i++) near(Math.hypot(normals.getX(i), normals.getY(i), normals.getZ(i)), 1);
            assert.equal(mesh.material.name, mesh.userData.material_token);
        });
        assert.ok(triangles <= (lod === 'LOD0' ? 100 : lod === 'LOD1' ? 3000 : 20000), `${triangles} triangles`);
        for (const contact of first.userData.contacts) {
            const mesh = first.getObjectByName(`terminal-${contact.terminal}`);
            assert.ok(mesh, 'Each physical terminal remains independently identifiable');
            const p = mesh.geometry.attributes.position;
            const underside = [];
            for (let i = 0; i < p.count; i++) if (Math.abs(p.getZ(i)) < 1e-8) underside.push([p.getX(i), p.getY(i)]);
            const minX = Math.min(...underside.map(v => v[0])), maxX = Math.max(...underside.map(v => v[0]));
            near((minX + maxX) / 2, contact.center_mm[0]); near(maxX - minX, contact.size_mm[0]);
            near(Math.max(...underside.map(v => v[1])) - Math.min(...underside.map(v => v[1])), contact.size_mm[1]);
            for (const dx of [-0.4, 0, 0.4]) {
                const hit = ray(first, [contact.center_mm[0] + dx * contact.size_mm[0], W * 0.2, -1], [0, 0, 1])[0];
                assert.equal(hit.object.userData.terminal, contact.terminal); near(hit.point.z, 0);
            }
        }
        near(first.userData.contacts[0].center_mm[0], library.records[id].terminals.pin1_xy_mm[0]);
    });
}

test('five-face cap coverage and unequal top/bottom bands use actual geometry', () => {
    const model = createComponent(library, 'OHM-003'); // top=.20, bottom=.25
    assert.equal(ray(model, [-0.28, 0, 2], [0, 0, -1])[0].object.name, 'top-coat');
    assert.equal(ray(model, [-0.28, 0, -2], [0, 0, 1])[0].object.name, 'terminal-1');
    for (const [start, direction] of [[[-2, 0, .15], [1, 0, 0]], [[-.45, 2, .15], [0, -1, 0]],
        [[-.45, -2, .15], [0, 1, 0]], [[-.45, 0, 2], [0, 0, -1]], [[-.45, 0, -2], [0, 0, 1]]]) {
        assert.equal(ray(model, start, direction)[0].object.name, 'terminal-1');
    }
});

test('one generator produces distinct resistor, ceramic, ferrite and metal-strip constructions', () => {
    for (const [id, token, topToken] of [['OHM-004', 'MAT_CERAMIC_ALUMINA_WHITE', 'MAT_RESISTOR_COAT_BLACK'],
        ['OHM-023', 'MAT_MLCC_BROWN', 'MAT_MLCC_BROWN'], ['OHM-041', 'MAT_FERRITE_DARK', 'MAT_FERRITE_DARK'],
        ['OHM-014', 'MAT_ALLOY_MANGANIN', 'MAT_RESISTOR_COAT_BLACK']]) {
        const model = createComponent(library, id);
        assert.equal(ray(model, [0, -5, .25], [0, 1, 0])[0].object.material.name, token);
        const top = ray(model, [0, 0, 5], [0, 0, -1])[0]; assert.equal(top.object.material.name, topToken);
        if (id === 'OHM-014') { near(top.point.z, .7 * .85 + .05); assert.ok(top.point.z < .7); }
    }
});

test('LOD2 changes upper-edge geometry while LOD0 omits markings and LOD1 has no edge rounding', () => {
    for (const id of ids) {
        assert.notEqual(signature(createComponent(library, id, { lod: 'LOD1' })), signature(createComponent(library, id, { lod: 'LOD2' })));
        const lod2 = createComponent(library, id, { lod: 'LOD2' });
        let curved = false;
        lod2.traverse(mesh => {
            if (!mesh.isMesh) return;
            const a = mesh.geometry.attributes.normal;
            for (let i = 0; i < a.count; i++) if (Math.abs(a.getZ(i)) > .1 && Math.abs(a.getZ(i)) < .99) curved = true;
        });
        assert.ok(curved);
    }
    const materials = createLibraryMaterials();
    const marked = createComponent(library, 'OHM-004', { marking_text: '100' }, materials);
    assert.ok(marked.getObjectByName('marking-decal'));
    assert.equal(createComponent(library, 'OHM-004', { lod: 'LOD0', marking_text: '100' }, materials).getObjectByName('marking-decal'), undefined);
    assert.equal(materials.MAT_SILKSCREEN_WHITE.polygonOffset, false);
});

test('material tokens preserve exact sRGB PBR values without instance mutation', () => {
    const materials = createLibraryMaterials();
    for (const [token, [color, roughness, metalness]] of Object.entries(MATERIAL_TOKENS)) {
        assert.equal(`#${materials[token].color.getHexString()}`.toUpperCase(), color);
        assert.equal(materials[token].roughness, roughness); assert.equal(materials[token].metalness, metalness);
    }
    createComponent(library, 'OHM-023', { body_material: 'MAT_MLCC_GRAY', overall_height: .5 }, materials);
    assert.equal(library.records['OHM-023'].dimensions_mm.overall_height.default, .8);
    assert.equal(materials.MAT_MLCC_BROWN.color.getHexString(), '8c6a45');
});

test('invalid variants, missing metadata, degenerate bands and guessed terminals fail explicitly', () => {
    for (const [id, options] of [['missing', {}], ['OHM-014', { terminal_count: 4 }], ['OHM-041', { inductor_type: 'wirewound' }],
        ['OHM-023', { overall_height: NaN }], ['OHM-023', { overall_height: 1 }], ['OHM-023', { overall_height: .1 }],
        ['OHM-004', { lod: 'AUTO' }], ['OHM-001', { marking_text: '100' }], ['OHM-004', { body_material: 'MAT_MLCC_GRAY' }]]) {
        assert.throws(() => createComponent(library, id, options), RangeError);
    }
    for (const mutate of [d => d.components.push(d.components[0]), d => d.components[0].terminals.count = 3,
        d => d.components[0].terminals.pin1_xy_mm = [0, 0], d => d.components[0].body.material = 'UNSPECIFIED',
        d => d.family.profiles['R.01005I'].dimensions_mm.terminal_band_top.default = .21,
        d => d.components.find(c => c.id === 'OHM-043').library_metadata.uncertain_values = []]) {
        const clone = structuredClone(data); mutate(clone); assert.throws(() => createLibrary(clone), RangeError);
    }
});

test('viewer transform flips X and Z at the bottom surface and preserves canonical geometry', () => {
    for (const side of ['F.Cu', 'B.Cu']) for (const angle of [0, 90, 180, 270]) {
        const model = createComponent(library, 'OHM-004');
        const original = Array.from(model.children[0].geometry.attributes.position.array);
        const root = placeInViewer(model, { side, rotation_deg: angle, board_thickness_mm: 2, x_mm: 4, y_mm: 5 });
        root.updateMatrixWorld(true);
        const p = model.localToWorld(new THREE.Vector3(-.675, 0, 0));
        const sign = side === 'B.Cu' ? -1 : 1, radians = angle * Math.PI / 180;
        near(p.x, 4 - .675 * sign * Math.cos(radians)); near(p.y, 5 - .675 * sign * Math.sin(radians)); near(p.z, sign);
        assert.deepEqual(Array.from(model.children[0].geometry.attributes.position.array), original);
        near(root.matrixWorld.determinant(), 1);
    }
    near(tailBottom(), -2.6); near(tailBottom(2), -3); near(tailBottom(1.6, 4), -4);
});

test('explicit footprint bindings retain revision, axis and pad-name identity; fit remains unverified', () => {
    const model = createComponent(library, 'OHM-004');
    const footprint = { id: 'test-fixture-only', sha256: 'a'.repeat(64), pads: [
        { number: 'A', x_mm: 0, y_mm: 2, width_mm: 1, height_mm: 1 },
        { number: 'B', x_mm: 2, y_mm: 2, width_mm: 1, height_mm: 1 },
        { number: '', mechanical: true, x_mm: 5, y_mm: 0, width_mm: 2, height_mm: 2 }] };
    assert.deepEqual(footprintFCO(footprint.pads, 'KICAD_Y_DOWN'), [2.75, -.75]);
    const binding = { component_id: 'OHM-004', source_spec_sha256: data.source_spec_sha256,
        model_asset_id: model.userData.model_asset_id, model_source_sha256: model.userData.model_source_sha256,
        footprint_id: footprint.id, footprint_sha256: footprint.sha256, frame: 'KICAD_Y_DOWN',
        translation_mm: [0, 0], rotation_deg: 0, terminal_to_pad: { 1: 'A', 2: 'B' } };
    assert.deepEqual(validateFootprintBinding(binding, model, footprint), binding);
    assert.throws(() => validateFootprintBinding({ ...binding, footprint_sha256: 'b'.repeat(64) }, model, footprint));
    assert.throws(() => validateFootprintBinding({ ...binding, terminal_to_pad: { 1: '1', 2: '2' } }, model, footprint));
    assert.throws(() => footprintFCO(footprint.pads, 'guess'));
    const asymmetric = [{number:'1',x_mm:0,y_mm:0,width_mm:2,height_mm:2,shape:'circle',rotation_deg:45},
        {number:'2',x_mm:4,y_mm:0,width_mm:1,height_mm:1,shape:'rect'}];
    assert.deepEqual(footprintFCO(asymmetric, 'OHMNI_Y_UP'), [1.75, 0]);
    assert.throws(() => footprintFCO([{...asymmetric[0],shape:'roundrect'}], 'OHMNI_Y_UP'));
    assert.equal(model.userData.library_metadata.footprint_binding, null);
});
