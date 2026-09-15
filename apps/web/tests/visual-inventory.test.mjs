import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from '../vendor/three.module.js';
import { ASSET_REGISTRY, createAsset, createMaterials } from '../visual-assets.js';
import {
    REFERENCE_LABEL, REFERENCE_EDUCATION_NOTICE, REFERENCE_INVENTORY_METADATA,
    VISUAL_INVENTORY, FAMILY_LESSONS, createIllustrativeSceneManifest, getVisualFamilyCatalog,
} from '../visual-inventory.js';

const sequence = (prefix, length) => Array.from({ length }, (_, index) => `${prefix}${String(index + 1).padStart(2, '0')}`);
const expectedIds = [
    ...sequence('IC', 10), ...sequence('S', 20), ...sequence('H', 6), ...sequence('J', 5),
    ...sequence('C', 15), ...sequence('E', 4), 'L01', 'O01', ...sequence('T', 8),
    ...sequence('M', 4), ...sequence('P', 63), ...sequence('X', 8), ...sequence('B', 10), ...sequence('V', 3),
];

test('every reference entry has exactly one disposition without becoming an electrical BOM', () => {
    assert.equal(VISUAL_INVENTORY.length, 158);
    assert.deepEqual(VISUAL_INVENTORY.map(item => item.id).sort(), expectedIds.sort());
    const counts = Object.groupBy(VISUAL_INVENTORY, item => item.disposition);
    assert.deepEqual(Object.fromEntries(Object.entries(counts).map(([key, entries]) => [key, entries.length])), {
        ILLUSTRATIVE_BODY: 124, BOARD_FEATURE: 4, PARENT_SUBDETAIL: 9,
        UNRESOLVED_PATCH: 8, SHARED_RENDER_FEATURE: 10, VIEWPORT_ONLY: 3,
    });
    const independentPassives = VISUAL_INVENTORY.filter(item => item.id.startsWith('P') && item.disposition === 'ILLUSTRATIVE_BODY');
    assert.equal(independentPassives.length, 54);
    assert.equal(REFERENCE_INVENTORY_METADATA.illustrativeBodyCount, 124);
    assert.equal(REFERENCE_INVENTORY_METADATA.sourceImageDistribution, 'PRIVATE_REFERENCE_ONLY');
    assert.match(REFERENCE_INVENTORY_METADATA.sourceImageSha256, /^[a-f0-9]{64}$/);
    assert.match(REFERENCE_INVENTORY_METADATA.sourceInventorySha256, /^[a-f0-9]{64}$/);
});

test('nine passive details select existing owners and never create extra bodies', () => {
    const scene = createIllustrativeSceneManifest();
    const expected = { P31: 'P30', P32: 'P27', P38: 'P37', P48: 'P47', P59: 'P54', P60: 'P55', P61: 'P56', P62: 'P57', P63: 'P58' };
    assert.equal(scene.parentSubdetails.length, 9);
    for (const [id, ownerId] of Object.entries(expected)) {
        const detail = VISUAL_INVENTORY.find(item => item.id === id);
        assert.equal(detail.ownerId, ownerId);
        assert.equal(scene.instances.some(item => item.id === id), false);
        assert.ok(scene.instances.find(item => item.id === ownerId).subdetailIds.includes(id));
        assert.equal(detail.ownershipBasis, ['P31', 'P32', 'P38', 'P48'].includes(id) ? 'APPROXIMATE' : 'SOURCE_DESCRIBED');
    }
});

test('sample transforms come from authored normalized art coordinates, not image pixels', () => {
    const scene = createIllustrativeSceneManifest();
    assert.equal(scene.instances.length, 124);
    for (const item of scene.instances) {
        const [u, v] = item.normalizedPosition;
        assert.ok(u > 0 && u < 1 && v > 0 && v < 1, item.id);
        assert.equal(item.x, (u - .5) * scene.width);
        assert.equal(item.y, (.5 - v) * scene.depth);
        assert.deepEqual(item.transform.position, [item.x, item.y, scene.thickness / 2]);
        assert.equal(item.dimensionalSource, 'ARTISTIC_SAMPLE_DIMENSIONS');
        assert.ok(item.knownSourceFacts.imagePointPx[0] > 1, item.id);
        assert.notDeepEqual(item.normalizedPosition, item.knownSourceFacts.imagePointPx);
        assert.equal(item.modelAssumptions.countsAreIllustrative, true);
    }
});

test('source observations, unknown roles and generic lessons stay separate from visual choices', () => {
    const scene = createIllustrativeSceneManifest();
    assert.equal(scene.label, REFERENCE_LABEL);
    for (const entry of VISUAL_INVENTORY) {
        assert.equal(entry.visualProvenance, 'ILLUSTRATIVE_ONLY');
        assert.equal(entry.circuitRole, 'UNKNOWN');
        assert.equal(entry.roleEvidenceId, null);
        assert.equal(entry.sourceComponentId, null);
        assert.equal(entry.sourceFootprintId, null);
    }
    for (const item of scene.instances) {
        assert.ok(item.name && item.description && item.knownSourceFacts.observation && item.unknownFacts, item.id);
        assert.equal(item.roleLabel, 'UNKNOWN');
        assert.equal(item.roleEvidenceId, null);
        assert.equal(item.knownSourceFacts.identity, 'UNKNOWN');
        assert.equal(item.knownSourceFacts.circuitRole, 'UNKNOWN');
        assert.equal(item.educationNotice, REFERENCE_EDUCATION_NOTICE);
        assert.equal(item.lesson, FAMILY_LESSONS[item.family]);
        assert.equal(item.selectable, true);
    }
});

test('artistic guide paths and surface features carry no circuit or release contract', () => {
    const scene = createIllustrativeSceneManifest();
    const forbidden = new Set(['nets', 'netId', 'net_id', 'net_names', 'pinId', 'verificationStatus',
        'verification_status', 'reportStatus', 'bom', 'prices', 'cost', 'exports', 'gerbers', 'fabricationReady']);
    const walk = value => {
        if (!value || typeof value !== 'object') return;
        for (const [key, child] of Object.entries(value)) {
            assert.equal(forbidden.has(key), false, `Sample must not contain ${key}`);
            walk(child);
        }
    };
    walk(scene);
    assert.equal(scene.provenance, 'ILLUSTRATIVE_ONLY');
    assert.match(scene.namespace, /illustrative-reference/);
    assert.ok(scene.illustrativeGuideGeometry.paths.length > 0);
    for (const path of scene.illustrativeGuideGeometry.paths) {
        assert.equal(path.visualProvenance, 'ILLUSTRATIVE_ONLY');
        assert.ok(path.points.length >= 2);
        assert.ok(path.points.flat().every(Number.isFinite));
    }
    assert.equal(scene.illustrativeSurfaceFeatures.items.length, 24);
    for (const feature of scene.illustrativeSurfaceFeatures.items) {
        assert.equal(feature.inventoryId, 'B04');
        assert.equal(feature.visualProvenance, 'ILLUSTRATIVE_ONLY');
        assert.equal(feature.countAsComponent, false);
        assert.ok(feature.radius > 0 && feature.annulus > feature.radius);
    }
});

test('unresolved microdetails and viewport aids do not enter the component list', () => {
    const scene = createIllustrativeSceneManifest();
    assert.equal(scene.microdetailPatches.length, 8);
    assert.equal(scene.holes.length, 4);
    assert.equal(scene.viewportFeatures.length, 3);
    assert.equal(scene.sharedFeatures.length, 10);
    for (const patch of scene.microdetailPatches) {
        assert.equal(patch.family, 'unresolved_patch');
        assert.equal(patch.countAsComponent, false);
        assert.equal(patch.selectable, false);
        assert.equal(patch.ownerId, null);
        assert.equal(scene.instances.some(item => item.id === patch.id), false);
    }
    assert.match(scene.holes.find(item => item.id === 'M04').observation, /Partly observed/);
});

test('family catalog binds all required specimen families to the local model registry', () => {
    const catalog = getVisualFamilyCatalog();
    assert.equal(catalog.length, 18);
    for (const family of catalog) {
        assert.equal(family.modelAssetId, ASSET_REGISTRY[family.family].modelAssetId);
        assert.equal(family.visualProvenance, 'ILLUSTRATIVE_ONLY');
        assert.ok(family.general && family.inspect && family.unknown);
        assert.ok(family.specimenOptions.width > 0 && family.specimenOptions.depth > 0 && family.specimenOptions.height > 0);
    }
    const beige = createIllustrativeSceneManifest().instances.filter(item => item.family === 'ceramic_chip');
    assert.equal(beige.length, 12);
    assert.deepEqual(beige.filter(item => item.options.bodyShape === 'axial').map(item => item.id), ['P13', 'P16', 'P26', 'P43', 'P45']);
    for (const item of beige.filter(item => item.options.bodyShape === 'axial')) {
        assert.ok(item.options.height > item.options.depth, item.id);
        assert.equal(item.modelAssumptions.bodyShape, 'axial');
    }
});

test('fresh manifests do not share mutable instance transforms or model options', () => {
    const a = createIllustrativeSceneManifest();
    a.instances[0].options.width = 1;
    a.instances[0].transform.position[0] = 900;
    a.illustrativeGuideGeometry.paths[0].points[0][0] = 900;
    const b = createIllustrativeSceneManifest();
    assert.notEqual(b.instances[0].options.width, 1);
    assert.notEqual(b.instances[0].transform.position[0], 900);
    assert.notEqual(b.illustrativeGuideGeometry.paths[0].points[0][0], 900);
    assert.ok(Object.isFrozen(VISUAL_INVENTORY[0].imagePointPx));
});

test('all 124 package meshes fit the artistic stage without mutual bounding-box overlap', () => {
    const scene = createIllustrativeSceneManifest(), materials = createMaterials(), boxes = [];
    for (const entry of scene.instances) {
        const group = createAsset(entry.family, entry.options, materials);
        group.position.set(entry.x, entry.y, scene.thickness / 2);
        group.rotation.z = entry.rotation * Math.PI / 180;
        group.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(group);
        assert.ok(box.min.x >= -scene.width / 2 && box.max.x <= scene.width / 2, `${entry.id} exceeds stage width`);
        assert.ok(box.min.y >= -scene.depth / 2 && box.max.y <= scene.depth / 2, `${entry.id} exceeds stage depth`);
        boxes.push([entry.id, box]);
        group.traverse(object => object.geometry?.dispose());
    }
    for (let i = 0; i < boxes.length; i += 1) for (let j = i + 1; j < boxes.length; j += 1) {
        const overlap = boxes[i][1].clone().intersect(boxes[j][1]);
        if (overlap.isEmpty()) continue;
        const size = overlap.getSize(new THREE.Vector3());
        assert.ok(size.x <= .001 || size.y <= .001, `${boxes[i][0]} overlaps ${boxes[j][0]} by ${size.toArray()}`);
    }
    Object.values(materials).forEach(material => material.dispose());
});

test('coverage document accounts for every source inventory ID', () => {
    const coverage = readFileSync(new URL('../../../docs/visual-reference/VISUAL_COVERAGE.md', import.meta.url), 'utf8');
    for (const id of expectedIds) assert.ok(coverage.includes(`| ${id} |`), id);
    assert.match(coverage, /124/);
    assert.match(coverage, /54/);
    assert.match(coverage, /not an electrically verified design/);
});
