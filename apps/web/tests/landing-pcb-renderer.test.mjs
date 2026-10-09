import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import * as THREE from '../vendor/three.module.js';
import { BoardView, createCamera } from '../board-view.js';
import { VisualRenderer } from '../visual-renderer.js';
import { actualSceneManifest } from '../visual-board-scene.js';
import { createMaterials } from '../visual-assets.js';
import { createLandingMaterials, LANDING_PRESENTATION } from '../landing-pcb-presentation.js';
import { createLandingModelResolver } from '../landing-pcb-models.js';

const source = JSON.parse(readFileSync(new URL('../reference-board.json', import.meta.url))).board;
const freeze = value => {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
};

const materialTextures = material => Object.values(material).filter(value => value?.isTexture);
function disposePalette(palette) {
    const textures = new Set(Object.values(palette).flatMap(materialTextures));
    for (const resource of [...textures, ...Object.values(palette)]) resource.dispose();
}

// Native GPU construction/submission is the browser gate. This harness executes
// the real scene assembly, option handling, resource disposal and picking paths.
function rendererHarness(options = {}) {
    const calls = { ratios: [], submitted: 0, disposed: 0, environments: 0 };
    const renderer = Object.create(VisualRenderer.prototype);
    Object.assign(renderer, {
        presentation: options.presentation ?? {}, materialFactory: options.materialFactory ?? createMaterials,
        instanceModelResolver: options.instanceModelResolver ?? null,
        scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera(40, 1, 1, 1200),
        underside: new THREE.DirectionalLight('#e2e9ed', options.presentation?.undersideIntensity ?? 1.7),
        owners: new Map(), frameTimes: [], canvas: { dataset: {} },
        environment: { dispose() { calls.environments++; } },
        renderer: {
            getContext: () => ({ isContextLost: () => false }),
            setPixelRatio(value) { calls.ratios.push(value); }, setSize() {}, shadowMap: {},
            info: { render: { triangles: 0, calls: 0 } },
            render() { calls.submitted++; }, dispose() { calls.disposed++; },
        },
    });
    return { renderer, calls };
}

function boardHarness(t, options = {}) {
    const handlers = new Map(), children = [], captures = [], renderers = [], contextRequests = [];
    const context = new Proxy({ measureText: text => ({ width: text.length * 6 }) }, {
        get: (target, key) => target[key] ?? (() => {}),
    });
    const canvas = {
        dataset: {}, style: {}, offsetLeft: 0, offsetTop: 0,
        getContext(kind) { contextRequests.push(kind); return kind === '2d' ? context : null; },
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 700, height: 500 }),
        setPointerCapture(id) { captures.push(id); }, releasePointerCapture() {},
        addEventListener(name, fn) { handlers.set(name, fn); },
        removeEventListener(name) { handlers.delete(name); },
        parentElement: { appendChild(child) { children.push(child); } },
        ownerDocument: { createElement() { return { style: {}, setAttribute() {}, getContext: () => context,
            remove() { this.removed = true; } }; } },
    };
    const rendererFactory = () => {
        const renderer = { disposeCalls: 0, dispose() { this.disposeCalls++; },
            render() {}, setScene() {}, pick: () => ({ ref: 'U3' }) };
        renderers.push(renderer); return renderer;
    };
    const view = new BoardView(canvas, { rendererFactory, ...options });
    t.after(() => view.dispose());
    const event = (type, extra = {}) => {
        let prevented = false;
        handlers.get(type)?.({ button: 0, pointerId: 1, pointerType: 'mouse', clientX: 100, clientY: 100,
            preventDefault() { prevented = true; }, ...extra });
        return prevented;
    };
    return { view, canvas, event, handlers, children, captures, renderers, contextRequests };
}

test('landing materials are owned per scene and never change the existing material palette', () => {
    const baseline = createMaterials(), before = Object.fromEntries(Object.entries(baseline)
        .map(([name, material]) => [name, [material.color.getHex(), material.roughness]]));
    const first = createLandingMaterials(), second = createLandingMaterials();
    for (const name of Object.keys(first)) {
        assert.notStrictEqual(first[name], second[name]);
        assert.notStrictEqual(first[name], baseline[name]);
        assert.deepEqual([baseline[name].color.getHex(), baseline[name].roughness], before[name]);
    }
    assert.notEqual(first.mask.color.getHex(), baseline.mask.color.getHex());
    first.mask.color.set('#ffffff');
    assert.notEqual(first.mask.color.getHex(), second.mask.color.getHex());
    for (const palette of [baseline, first, second]) disposePalette(palette);
});

test('landing finish textures are deterministic and separately owned, with an explicit flat-material option', () => {
    const first = createLandingMaterials(), second = createLandingMaterials(), flat = createLandingMaterials({ finish: false });
    try {
        for (const name of ['mask', 'shield']) {
            const texture = first[name].roughnessMap;
            assert.ok(texture?.isDataTexture);
            assert.strictEqual(texture, first[name].bumpMap, 'one per-material texture serves both finish channels');
            assert.notStrictEqual(texture, second[name].roughnessMap);
            assert.deepEqual(texture.image.data, second[name].roughnessMap.image.data);
            assert.equal(texture.userData.appearanceOnly, true);
            assert.equal(flat[name].roughnessMap, null);
            assert.equal(flat[name].bumpMap, null);
        }
        assert.notStrictEqual(first.mask.roughnessMap, first.shield.roughnessMap);
        assert.equal(first.aluminum.roughnessMap, null, 'sensor cap does not gain a brushed material claim');
    } finally { for (const palette of [first, second, flat]) disposePalette(palette); }
});

test('resolver preserves all source refs, footprint identity and coordinates without mutating frozen input', () => {
    const board = freeze(structuredClone(source)), before = JSON.stringify(board);
    const manifest = freeze(actualSceneManifest(board)), manifestBefore = JSON.stringify(manifest);
    const inventory = freeze({ entries: manifest.instances.map(entry => ({ ref: entry.id,
        footprintId: entry.sourceFootprintId, approximation: { family: entry.family } })) });
    const { renderer } = rendererHarness({ materialFactory: createLandingMaterials,
        instanceModelResolver: createLandingModelResolver(inventory) });
    try {
        renderer.setScene(manifest);
        assert.equal(renderer.owners.size, 29);
        assert.deepEqual([...renderer.owners.keys()], board.components.map(part => part.ref));
        for (const entry of manifest.instances) {
            const object = renderer.owners.get(entry.id);
            assert.equal(object.userData.owner, entry.sourceComponentId);
            assert.equal(object.userData.entry.sourceFootprintId, entry.sourceFootprintId);
            assert.equal(object.userData.landingBinding.ref, entry.id);
            assert.match(object.userData.geometryClaim, /approximation/i);
            assert.deepEqual(object.position.toArray(), [entry.x, entry.y,
                (entry.side === 'B.Cu' ? -1 : 1) * manifest.thickness / 2]);
            assert.equal(object.rotation.z, entry.rotation * Math.PI / 180);
            const child = object.children.find(node => node.isMesh) ?? object.children[0];
            let owner = child;
            while (owner && !owner.userData.owner) owner = owner.parent;
            assert.strictEqual(owner, object, 'descendant picking resolves to exactly one source ref');
        }
        const firstRoot = renderer.root;
        renderer.setScene(manifest);
        assert.strictEqual(renderer.root, firstRoot, 'the same scene is not rebuilt for camera work');
        assert.equal(JSON.stringify(board), before);
        assert.equal(JSON.stringify(manifest), manifestBefore);
    } finally { renderer.dispose(); }
});

test('disposing one hero releases its resources once without disposing another scene', () => {
    const manifest = actualSceneManifest(source);
    const first = rendererHarness({ materialFactory: createLandingMaterials });
    const second = rendererHarness();
    first.renderer.setScene(manifest); second.renderer.setScene(manifest);
    const counts = new Map(), untouched = [];
    first.renderer.root.traverse(node => {
        const materials = [node.material].flat().filter(Boolean);
        for (const resource of [node.geometry, ...materials, ...materials.flatMap(materialTextures)].filter(Boolean)) {
            if (counts.has(resource)) continue;
            counts.set(resource, 0); resource.addEventListener('dispose', () => counts.set(resource, counts.get(resource) + 1));
        }
    });
    second.renderer.root.traverse(node => {
        const materials = [node.material].flat().filter(Boolean);
        for (const resource of [node.geometry, ...materials, ...materials.flatMap(materialTextures)].filter(Boolean)) {
            assert.equal(counts.has(resource), false, 'scenes cannot share disposable model resources');
            resource.addEventListener('dispose', () => untouched.push(resource));
        }
    });
    first.renderer.dispose();
    assert.ok(counts.size > 0);
    assert.equal([...counts.keys()].filter(resource => resource.isTexture).length, 2);
    assert.ok([...counts.values()].every(count => count === 1));
    assert.equal(untouched.length, 0);
    assert.equal(first.calls.disposed, 1); assert.equal(first.calls.environments, 1);
    assert.equal(first.renderer.owners.size, 0);
    second.renderer.dispose();
});

test('underside inspection lighting is opt-in and restores when returning above the board', () => {
    for (const presentation of [{}, LANDING_PRESENTATION]) {
        const { renderer } = rendererHarness({ presentation });
        try {
            renderer.setScene(actualSceneManifest(source));
            const camera = createCamera(), viewport = { width: 700, height: 500, ratio: 1 };
            renderer.render({ ...camera, pitch: -.5 }, viewport);
            assert.equal(renderer.underside.intensity,
                presentation.undersideInspectionIntensity ?? presentation.undersideIntensity ?? 1.7);
            renderer.render({ ...camera, pitch: .5 }, viewport);
            assert.equal(renderer.underside.intensity, presentation.undersideIntensity ?? 1.7);
        } finally { renderer.dispose(); }
    }
});

test('landing copper color is opt-in, invalidates appearance caching and preserves exact net highlighting', () => {
    const { renderer } = rendererHarness();
    const board = freeze(structuredClone(source)), before = JSON.stringify(board);
    renderer.setScene(actualSceneManifest(board));
    const camera = createCamera(), viewport = { width: 700, height: 500, ratio: 1 };
    const copper = [renderer.layers.frontCopper, renderer.layers.backCopper];
    const topology = copper.map(mesh => Array.from(mesh.geometry.attributes.position.array));
    const rgb = hex => Array.from(new Float32Array(new THREE.Color(hex).toArray()));
    const assertColors = (hex, net = null) => {
        for (const mesh of copper) {
            const attribute = mesh.geometry.attributes.color;
            for (const range of mesh.geometry.userData.sourceRanges) {
                const expected = rgb(net && range.net === net ? '#8cecff' : hex);
                for (let vertex = range.start; vertex < range.start + range.count; vertex++)
                    assert.deepEqual(Array.from(attribute.array.slice(vertex * 3, vertex * 3 + 3)), expected);
            }
        }
    };
    try {
        renderer.render(camera, viewport);
        assertColors('#477d4d');
        renderer.presentation = LANDING_PRESENTATION;
        renderer.render(camera, viewport);
        assertColors(LANDING_PRESENTATION.maskedCopperColor);
        const versions = copper.map(mesh => mesh.geometry.attributes.color.version);
        renderer.render(camera, viewport);
        assert.deepEqual(copper.map(mesh => mesh.geometry.attributes.color.version), versions);
        renderer.render(camera, viewport, { highlight: { nets: ['SDA'] } });
        assertColors(LANDING_PRESENTATION.maskedCopperColor, 'SDA');
        renderer.render(camera, viewport, { showMask: false });
        assertColors('#b58a45');
        assert.ok(copper.every(mesh => mesh.material.metalness === 1));
        renderer.presentation = {};
        renderer.render(camera, viewport);
        assertColors('#477d4d');
        assert.ok(copper.every(mesh => mesh.material.metalness === 0));
        assert.deepEqual(copper.map(mesh => Array.from(mesh.geometry.attributes.position.array)), topology);
        assert.equal(JSON.stringify(board), before);
    } finally { renderer.dispose(); }
});

test('default quality remains compatible while landing DPR is opt-in and bounded', () => {
    for (const [presentation, expected] of [[{}, 2], [LANDING_PRESENTATION, 1.5]]) {
        const { renderer, calls } = rendererHarness({ presentation });
        renderer.setScene(actualSceneManifest(source));
        renderer.render(createCamera(), { width: 700, height: 500, ratio: 3 });
        assert.equal(calls.ratios.at(-1), expected);
        renderer.render(createCamera(), { width: 700, height: 500, ratio: 3 }, { quality: 'low' });
        assert.equal(calls.ratios.at(-1), 1);
        assert.equal(renderer.renderer.shadowMap.enabled, false);
        renderer.dispose();
    }
});

test('legacy missing-model fallback remains distinct from explicit resolver identity rejection', () => {
    const original = actualSceneManifest(source), manifest = { ...original,
        instances: [{ ...original.instances[0], family: 'not-a-supported-model' }] };
    const legacy = rendererHarness();
    try {
        legacy.renderer.setScene(manifest);
        assert.equal(legacy.renderer.owners.get(manifest.instances[0].id).userData.missingModel, true);
    } finally { legacy.renderer.dispose(); }
    const strict = rendererHarness({ instanceModelResolver() { throw new Error('Binding identity rejected'); } });
    try {
        assert.throws(() => strict.renderer.setScene(original), /Binding identity rejected/,
            'an explicit binding rejection must reach the hero failure handler, not become a ready amber box');
    } finally { strict.renderer.dispose(); }
});

test('resolver rejects missing and mismatched footprint identities before creating a model', () => {
    const instance = actualSceneManifest(source).instances[0], materials = createLandingMaterials();
    try {
        assert.throws(() => createLandingModelResolver({ entries: [] })(instance, materials), /Unaccounted landing model/);
        assert.throws(() => createLandingModelResolver({ entries: [{ ref: instance.id, footprintId: 'wrong' }] })(instance, materials),
            /Unaccounted landing model/);
    } finally { disposePalette(materials); }
});

test('default viewport still captures wheel and touch orbit while landing preserves page gestures', t => {
    const viewport = boardHarness(t), landing = boardHarness(t, { inputPolicy: 'landing' });
    assert.equal(viewport.canvas.style.touchAction, 'none');
    assert.equal(landing.canvas.style.touchAction, 'pan-y pinch-zoom');
    const wheel = { deltaY: 80, deltaMode: 0 };
    assert.equal(viewport.event('wheel', wheel), true);
    assert.notEqual(viewport.view.camera.zoom, 1);
    const before = { ...landing.view.camera };
    assert.equal(landing.event('wheel', wheel), false);
    assert.deepEqual(landing.view.camera, before);
    for (const harness of [viewport, landing]) {
        harness.event('pointerdown', { pointerType: 'touch' });
        harness.event('pointermove', { pointerType: 'touch', clientX: 145, clientY: 135 });
    }
    assert.equal(viewport.captures.length, 1);
    assert.equal(landing.captures.length, 0);
    assert.notEqual(viewport.view.camera.yaw, before.yaw);
    assert.deepEqual(landing.view.camera, before);
    landing.event('pointercancel', { pointerType: 'touch' });
    assert.equal(landing.view.dragging, null); assert.equal(landing.view.pointers.size, 0);
});

test('landing retains tap selection and mouse orbit without selecting after a scroll or cancel', t => {
    const selected = [], harness = boardHarness(t, { inputPolicy: 'landing', onSelect: ref => selected.push(ref) });
    harness.event('pointerdown', { pointerType: 'touch' });
    harness.event('pointerup', { pointerType: 'touch' });
    assert.deepEqual(selected, ['U3']);
    harness.event('pointerdown', { pointerType: 'touch' });
    harness.event('pointermove', { pointerType: 'touch', clientY: 180 });
    harness.event('pointerup', { pointerType: 'touch', clientY: 180 });
    harness.event('pointerdown', { pointerType: 'touch' });
    harness.event('pointercancel', { pointerType: 'touch' });
    assert.deepEqual(selected, ['U3']);
    const yaw = harness.view.camera.yaw;
    harness.event('pointerdown'); harness.event('pointermove', { clientX: 140 }); harness.event('pointerup');
    assert.notEqual(harness.view.camera.yaw, yaw);
    assert.deepEqual(selected, ['U3']);
});

test('construction failure opts into the poster handler without removing legacy compatibility view', t => {
    const failedFactory = () => { throw new Error('No native renderer'); };
    const failures = [];
    const legacy = boardHarness(t, { rendererFactory: failedFactory });
    const landing = boardHarness(t, { rendererFactory: failedFactory, onRendererFailure: error => failures.push(error.message) });
    assert.equal(legacy.view.available, true); assert.equal(legacy.view.rendererKind, 'canvas');
    assert.deepEqual(legacy.contextRequests, ['2d']);
    assert.equal(landing.view.available, false); assert.deepEqual(landing.contextRequests, []);
    assert.deepEqual(failures, ['No native renderer']);
    assert.equal(landing.handlers.size, 0);
});

test('context failure leaves default restore intact but opt-in failure stops and tears down once', t => {
    const legacy = boardHarness(t), failures = [];
    const landing = boardHarness(t, { onRendererFailure: error => failures.push(error.message) });
    assert.equal(legacy.event('webglcontextlost'), true);
    assert.equal(legacy.view.rendererKind, 'canvas'); assert.equal(legacy.view.available, true);
    legacy.event('webglcontextrestored');
    assert.equal(legacy.view.rendererKind, 'three'); assert.equal(legacy.renderers.length, 2);
    assert.equal(legacy.renderers[0].disposeCalls, 1);
    const childCount = landing.children.length;
    assert.equal(landing.event('webglcontextlost'), true);
    assert.equal(landing.view.available, false); assert.equal(landing.view.canAnimate(), false);
    assert.deepEqual(failures, ['3D context lost']);
    assert.equal(landing.children.length, childCount, 'poster policy does not create a compatibility canvas');
    landing.event('webglcontextrestored');
    assert.equal(landing.renderers.length, 1, 'the controller owns any deliberate retry');
    landing.view.dispose(); landing.view.dispose();
    assert.equal(landing.renderers[0].disposeCalls, 1);
    assert.equal(landing.handlers.size, 0);
    assert.ok(landing.children.every(child => child.removed));
});
