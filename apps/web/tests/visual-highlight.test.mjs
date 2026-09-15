import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from '../vendor/three.module.js';
import { actualSceneManifest } from '../visual-board-scene.js';
import { VisualRenderer, disposeTree } from '../visual-renderer.js';

// Exercise the actual renderer option path while replacing only the native GPU
// submission. Colors are the same BufferAttributes uploaded by Three.js.
function rendererHarness(manifest) {
    const view = Object.create(VisualRenderer.prototype);
    Object.assign(view, {
        scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera(40, 1, 1, 1200),
        canvas: { dataset: {} }, owners: new Map(), frameTimes: [],
        renderer: {
            getContext: () => ({ isContextLost: () => false }),
            setPixelRatio() {}, setSize() {}, shadowMap: {},
            info: { render: { triangles: 0, calls: 0 } },
            render() {},
        },
    });
    view.setScene(manifest);
    const camera = { yaw: 0, pitch: .9, distance: 180, focal: 600, zoom: 1, panX: 0, panY: 0 };
    return { view, render: options => view.render(camera, { width: 800, height: 600 }, options) };
}

function colorsOf(view) {
    return Object.fromEntries(Object.entries(view.layers).filter(([, mesh]) => mesh.geometry.attributes.color)
        .map(([key, mesh]) => [key, Array.from(mesh.geometry.attributes.color.array)]));
}

function assertExactNetHighlight(view, before, selectedNet) {
    const matchingKinds = new Set();
    let changed = 0;
    for (const [key, mesh] of Object.entries(view.layers)) {
        const attribute = mesh.geometry.attributes.color;
        if (!attribute) continue;
        assert.equal(mesh.material.vertexColors, true);
        for (const range of mesh.geometry.userData.sourceRanges) {
            const matches = range.net === selectedNet;
            if (matches) matchingKinds.add(range.kind);
            for (let vertex = range.start; vertex < range.start + range.count; vertex++) {
                const offset = vertex * 3;
                const same = [0, 1, 2].every(channel => attribute.array[offset + channel] === before[key][offset + channel]);
                assert.equal(same, !matches, `${key}/${range.kind}/${range.net}: only exact source-net membership changes`);
                if (!same) changed++;
            }
        }
    }
    assert.ok(changed > 0, `${selectedNet} must change the GPU color buffer`);
    return matchingKinds;
}

test('render highlights only the saved net geometry and clears it without changing topology or source bytes', () => {
    const board = JSON.parse(readFileSync(new URL('../reference-board.json', import.meta.url))).board;
    const sourceBefore = JSON.stringify(board), manifest = actualSceneManifest(board);
    const { view, render } = rendererHarness(manifest);
    render({ highlight: { nets: [] } });
    const baseline = colorsOf(view);
    const topology = Object.fromEntries(Object.entries(view.layers).map(([key, mesh]) =>
        [key, { geometry: mesh.geometry, positions: Array.from(mesh.geometry.attributes.position.array),
            normals: Array.from(mesh.geometry.attributes.normal.array) }]));
    const meshCount = view.root.children.length;

    render({ highlight: { nets: ['SDA'] }, reducedMotion: true });
    assert.deepEqual(assertExactNetHighlight(view, baseline, 'SDA'), new Set(['pad', 'track']));
    const firstVersions = Object.fromEntries(Object.entries(view.layers).map(([key, mesh]) => [key, mesh.geometry.attributes.color?.version]));
    render({ highlight: { nets: ['SDA'] }, reducedMotion: true });
    for (const [key, mesh] of Object.entries(view.layers)) {
        assert.equal(mesh.geometry.attributes.color?.version, firstVersions[key], 'unchanged orbit frames do not re-upload color buffers');
    }
    render({ highlight: { nets: ['GND'] }, reducedMotion: true });
    assert.deepEqual(assertExactNetHighlight(view, baseline, 'GND'), new Set(['pad', 'via', 'track']));
    render({ highlight: { nets: ['SD'] } });
    assert.deepEqual(colorsOf(view), baseline, 'partial names cannot select SDA');
    render({ highlight: { nets: [] } });
    assert.deepEqual(colorsOf(view), baseline, 'clearing selection restores the original surface colors');
    assert.equal(view.root.children.length, meshCount, 'highlighting adds no meshes or draw calls');
    for (const [key, mesh] of Object.entries(view.layers)) {
        assert.strictEqual(mesh.geometry, topology[key].geometry);
        assert.deepEqual(Array.from(mesh.geometry.attributes.position.array), topology[key].positions);
        assert.deepEqual(Array.from(mesh.geometry.attributes.normal.array), topology[key].normals);
    }
    assert.equal(JSON.stringify(board), sourceBefore);
    disposeTree(view.root);
});

test('sample paths and unknown pads never gain electrical membership from visual input', () => {
    const manifest = { provenance: 'ILLUSTRATIVE_ONLY', width: 20, depth: 15, thickness: 1.6, instances: [],
        pads: [{ net_name: 'SDA', owner: 'ILL-1', kind: 'smd', width_mm: 1, height_mm: 1,
            shape: 'rect', x: 0, y: 0, rotation: 0, side: 'F.Cu' }],
        illustrativeGuideGeometry: { paths: [{ net_name: 'SDA', points: [[0, 0], [5, 5]], width: .3 }] } };
    const { view, render } = rendererHarness(manifest);
    render({});
    const baseline = colorsOf(view), before = JSON.stringify(manifest);
    render({ highlight: { refs: ['ILL-1'], nets: ['SDA'], systems: ['sensor'] }, reducedMotion: true });
    assert.deepEqual(colorsOf(view), baseline);
    for (const mesh of Object.values(view.layers)) assert.deepEqual(mesh.geometry.userData.sourceRanges, []);
    assert.equal(JSON.stringify(manifest), before);
    disposeTree(view.root);
});
