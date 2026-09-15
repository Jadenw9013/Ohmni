import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { actualSceneManifest } from '../visual-board-scene.js';
import { boardShape } from '../visual-renderer.js';
import { addLayers, contour } from '../visual-layers.js';
import * as THREE from '../vendor/three.module.js';
import { createMaterials } from '../visual-assets.js';

const board = JSON.parse(readFileSync(new URL('../reference-board.json', import.meta.url))).board;
test('actual visuals preserve all source owners, footprints, pads, routes and bytes', () => {
    const before = JSON.stringify(board), manifest = actualSceneManifest(board);
    assert.equal(manifest.instances.length, board.components.length);
    assert.equal(new Set(manifest.instances.map(x => x.id)).size, board.components.length);
    assert.equal(manifest.pads.length, board.components.reduce((sum, x) => sum + x.pads.length, 0));
    assert.equal(manifest.tracks.length, board.tracks.length);
    assert.equal(manifest.vias.length, board.vias.length);
    assert.equal(manifest.sourceArtifactFingerprint, board.artifact_fingerprint);
    for (const [i, entry] of manifest.instances.entries()) {
        assert.equal(entry.sourceFootprintId, board.components[i].footprint_id);
        assert.equal(entry.visualProvenance, 'PACKAGE_APPROXIMATION');
        assert.deepEqual(entry.options.pads, board.components[i].pads);
        assert.equal(entry.dimensionalSource, null);
        assert.equal(entry.options.includeSolder, false);
    }
    assert.equal(JSON.stringify(board), before);
    assert.deepEqual(manifest.silkscreen, []);
});
test('sample cannot enter actual projection or claim engineering identity', () => {
    assert.throws(() => actualSceneManifest({ ...board, kind: 'illustrative_sample' }));
    assert.throws(() => actualSceneManifest({ components: [] }));
});
test('bottom pad coordinates rotate once and remain physical x/y', () => {
    const b = { ...board, components: [{ ...board.components[0], rotation_deg: 90, side: 'B.Cu' }], tracks: [], vias: [] };
    const m = actualSceneManifest(b), p = b.components[0].pads[0];
    assert.ok(Math.abs(m.pads[0].x - (b.components[0].x_mm - b.width_mm / 2 - p.y_mm)) < 1e-9);
    assert.ok(Math.abs(m.pads[0].y - (b.components[0].y_mm - b.height_mm / 2 + p.x_mm)) < 1e-9);
    assert.equal(m.instances[0].transform.position[2], -board.display_thickness_mm / 2);
});
test('board through-openings and oval slots are geometric cutouts', () => {
    const geometry = new THREE.ExtrudeGeometry(boardShape(40, 30, [{ x: 8, y: 5, radius: 2 },
        { x: -8, y: 5, width: 1, depth: 3, shape: 'oval', rotation: 90 }]), { depth: 1.6, bevelEnabled: false });
    const object = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
    object.updateMatrixWorld();
    const ray = new THREE.Raycaster(new THREE.Vector3(8, 5, 20), new THREE.Vector3(0, 0, -1));
    assert.equal(ray.intersectObject(object).length, 0);
    ray.set(new THREE.Vector3(-8, 5, 20), new THREE.Vector3(0, 0, -1)); assert.equal(ray.intersectObject(object).length, 0);
    ray.set(new THREE.Vector3(0, 0, 20), new THREE.Vector3(0, 0, -1)); assert.ok(ray.intersectObject(object).length > 0);
});
test('copper geometry stays flat and bottom orientation is not mirrored', () => {
    const root = new THREE.Group();
    const layers = addLayers(root, { thickness: 1.6, provenance: 'ARTIFACT_DERIVED',
        tracks: [{ x1: 3, y1: 4, x2: 8, y2: 10, width_mm: .25, layer: 'B.Cu' }] }, createMaterials());
    const positions = layers.backCopper.geometry.attributes.position;
    const ys = [], zs = [];
    for (let i = 0; i < positions.count; i++) { ys.push(positions.getY(i)); zs.push(positions.getZ(i)); }
    assert.ok(Math.min(...ys) > 3.8 && Math.max(...ys) < 10.2);
    assert.ok(zs.every(z => Math.abs(z + .822) < 1e-6));
    assert.equal(contour(1, 3, 'oval').length, 36);
});
