import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildScene, highlightMatcher } from "../board-model.js";
import { BoardView, createCamera, project } from "../board-view.js";
import { buildRenderGeometry, displayPackageKind, pointOnFootprint,
    trackRibbon, VERTEX_STRIDE } from "../board-renderer-geometry.js";
import { WebGLBoardRenderer } from "../board-renderer-webgl.js";

const reference = JSON.parse(readFileSync(new URL("../reference-board.json", import.meta.url))).board;
const near = (a, b, tolerance = 1e-6) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);
function freeze(value) {
    Object.values(value).forEach((item) => { if (item && typeof item === "object") freeze(item); });
    return Object.freeze(value);
}

test("display geometry leaves authoritative geometry and membership untouched", () => {
    const board = structuredClone(reference);
    const scene = buildScene(board);
    const before = JSON.stringify({ board, scene });
    freeze(board); freeze(scene);
    const geometry = buildRenderGeometry(scene, { matcher: highlightMatcher({ nets: ["SDA"] }), selected: "U3", xray: true });
    assert.equal(JSON.stringify({ board, scene }), before);
    assert.equal(geometry.parts.length, reference.components.length);
    for (const part of geometry.parts) {
        const original = scene.parts.find((item) => item.ref === part.ref);
        assert.deepEqual(part.points, original.points);
        assert.deepEqual(part.nets, original.nets);
        assert.deepEqual(part.centre, original.centre);
        assert.equal(part.geometryIsDisplayOnly, true);
        assert.ok(part.displayHeight > 0);
    }
});

test("package silhouettes use explicit identifiers with a generic fallback", () => {
    const geometry = buildRenderGeometry(buildScene(reference));
    assert.equal(geometry.parts.find((p) => p.ref === "U1").displayKind, "module");
    assert.equal(geometry.parts.find((p) => p.ref === "J1").displayKind, "usb");
    assert.equal(geometry.parts.find((p) => p.ref === "J2").displayKind, "header");
    assert.equal(geometry.parts.find((p) => p.ref === "U3").displayKind, "sensor");
    assert.equal(displayPackageKind({ partId: "UNKNOWN_PART", ref: "U1", system: "compute" }), "chip");
});

test("rotated and back-side display bodies preserve footprint XY and extrude outward", () => {
    const board = structuredClone(reference);
    board.components = [{ ...board.components.find((p) => p.ref === "U3"), rotation_deg: 71, side: "B.Cu" }];
    const scene = buildScene(board);
    const part = scene.parts[0];
    const origin = pointOnFootprint(part, 0, 0, 0);
    assert.deepEqual(origin, part.points[0]);
    const centre = pointOnFootprint(part, 0.5, 0.5, 2);
    near(centre.x, part.centre.x); near(centre.y, part.centre.y);
    near(centre.z, part.centre.z - 2);
    const rendered = buildRenderGeometry(scene).parts[0];
    assert.ok(rendered.top.every((point, index) => point.z < rendered.bottom[index].z));
    assert.deepEqual(rendered.top.map(({ x, y }) => [x, y]), part.points.map(({ x, y }) => [x, y]));
});

test("copper ribbons retain exact centreline endpoints and emitted widths", () => {
    for (const track of buildScene(reference).tracks) {
        const quad = trackRibbon(track);
        if (!quad.length) continue;
        near((quad[0].x + quad[3].x) / 2, track.a.x);
        near((quad[0].y + quad[3].y) / 2, track.a.y);
        near((quad[1].x + quad[2].x) / 2, track.b.x);
        near((quad[1].y + quad[2].y) / 2, track.b.y);
        near(Math.hypot(quad[0].x - quad[3].x, quad[0].y - quad[3].y), track.width);
        assert.equal(Math.sign(quad[0].z), track.layer === "F.Cu" ? 1 : -1);
    }
    assert.deepEqual(trackRibbon({ a: { x: 2, y: 3, z: 1 }, b: { x: 2, y: 3, z: 1 }, width: 0.25, layer: "F.Cu" }), []);
});

test("highlighting and X-ray change materials, never mesh positions or normals", () => {
    const scene = buildScene(reference);
    const plain = buildRenderGeometry(scene);
    const highlighted = buildRenderGeometry(scene, { selected: "U3", matcher: highlightMatcher({ nets: ["SDA"] }), xray: true });
    let differentMaterials = 0;
    for (const group of ["substrate", "objects", "shadows"]) {
        assert.equal(plain[group].length, highlighted[group].length);
        for (let i = 0; i < plain[group].length; i += VERTEX_STRIDE) {
            assert.deepEqual(plain[group].slice(i, i + 6), highlighted[group].slice(i, i + 6));
            if (plain[group][i + 6] !== highlighted[group][i + 6]) differentMaterials += 1;
        }
    }
    assert.ok(differentMaterials > 0);
    assert.ok(highlighted.substrate[11] < 0.2);
});

test("reference board geometry is finite, has unit normals and a bounded GPU budget", () => {
    for (const explode of [0, 1]) {
        const geometry = buildRenderGeometry(buildScene(reference, { explode }));
        assert.ok(geometry.vertexCount < 60000, "keep beveled packages, pad fillets and source labels below 60k vertices");
        for (const group of ["substrate", "objects", "shadows"]) {
            assert.equal(geometry[group].length % (VERTEX_STRIDE * 3), 0);
            assert.ok(geometry[group].every(Number.isFinite));
            for (let i = 0; i < geometry[group].length; i += VERTEX_STRIDE) {
                near(Math.hypot(...geometry[group].slice(i + 3, i + 6)), 1, 2e-6);
            }
        }
    }
});

test("solder fillets add sloped metal surfaces inside each authoritative pad", () => {
    const scene = buildScene(reference);
    for (const pad of scene.pads) {
        const geometry = buildRenderGeometry({ ...scene, parts: [], tracks: [], vias: [], pads: [pad] });
        const [a, b, , d] = pad.points;
        const ux = b.x - a.x, uy = b.y - a.y;
        const vx = d.x - a.x, vy = d.y - a.y;
        let raised = false;
        let slopedMetal = false;
        for (let index = 0; index < geometry.objects.length; index += VERTEX_STRIDE) {
            const dx = geometry.objects[index] - a.x, dy = geometry.objects[index + 1] - a.y;
            const u = (dx * ux + dy * uy) / (ux * ux + uy * uy);
            const v = (dx * vx + dy * vy) / (vx * vx + vy * vy);
            assert.ok(u >= -1e-4 && u <= 1.0001 && v >= -1e-4 && v <= 1.0001, `${pad.ref}: solder must stay inside the real pad`);
            if (Math.abs(geometry.objects[index + 2] - a.z) > 0.15) raised = true;
            const nz = Math.abs(geometry.objects[index + 5]);
            const metallic = Math.floor((geometry.objects[index + 9] % 4) / 2);
            if (metallic === 1 && nz > 0.01 && nz < 0.99) slopedMetal = true;
        }
        assert.ok(raised && slopedMetal, `${pad.ref}: solder has a real beveled surface`);
    }
});

test("unavailable graphics is safe with the minimal DOM used by app tests", () => {
    const view = new BoardView({ getContext() { return null; } });
    assert.equal(view.available, false);
    view.setBoard(reference);
    view.setOptions({ autoRotate: true, xray: true });
    view.frame(); view.focus("U3"); view.render();
    assert.equal(view.canAnimate(), false);
    view.dispose(); view.dispose();
});

function makeEventTarget() {
    const handlers = new Map();
    return {
        handlers,
        addEventListener(name, callback) {
            if (!handlers.has(name)) handlers.set(name, new Set());
            handlers.get(name).add(callback);
        },
        removeEventListener(name, callback) { handlers.get(name)?.delete(callback); },
        dispatchEvent(event) { for (const callback of handlers.get(event.type) || []) callback(event); },
    };
}

function makeSoftwareCanvas() {
    const context = new Proxy({ measureText: (value) => ({ width: value.length * 6 }) }, {
        get(target, name) { return target[name] ?? (() => {}); },
    });
    return { ...makeEventTarget(), dataset: {}, style: {}, hidden: false,
        getContext: (kind) => kind === "2d" ? context : null,
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 600, height: 400 }),
    };
}

test("back-side picking excludes occluded front parts; X-ray makes them inspectable", () => {
    const canvas = makeSoftwareCanvas();
    const view = new BoardView(canvas);
    view.setBoard(reference);
    assert.equal(view.hitRegions.length, reference.components.length);
    const sensor = view.hitRegions.find((part) => part.ref === "U3");
    assert.equal(view.pick({ clientX: sensor.centre.x, clientY: sensor.centre.y })?.ref, "U3");
    view.setOptions({ showBack: true });
    assert.equal(view.hitRegions.length, 0);
    view.setOptions({ xray: true });
    assert.equal(view.hitRegions.length, reference.components.length);
    view.dispose();
});

test("focus centres real selected bodies and frame recovers the complete board", () => {
    const view = new BoardView(makeSoftwareCanvas());
    view.setBoard(reference);
    const before = view.camera.zoom;
    view.focus("U3");
    assert.ok(view.camera.zoom > before);
    const focused = view.hitRegions.find((region) => region.ref === "U3").bounds;
    near(focused.cx, 300, 1e-4); near(focused.cy, 200, 1e-4);
    view.frame();
    near(view.camera.zoom, before);
    for (const corner of view.scene.substrate[0].points) {
        const point = project(corner, view.camera, view.viewport());
        assert.ok(point.x > 0 && point.x < 600 && point.y > 0 && point.y < 400);
    }
    view.dispose();
});

test("animation pauses for hidden/reduced-motion views and disposal removes work", (t) => {
    let sequence = 0;
    const callbacks = new Map();
    const originalRequest = globalThis.requestAnimationFrame;
    const originalCancel = globalThis.cancelAnimationFrame;
    globalThis.requestAnimationFrame = (callback) => { callbacks.set(++sequence, callback); return sequence; };
    globalThis.cancelAnimationFrame = (id) => callbacks.delete(id);
    t.after(() => {
        if (originalRequest) globalThis.requestAnimationFrame = originalRequest;
        else delete globalThis.requestAnimationFrame;
        if (originalCancel) globalThis.cancelAnimationFrame = originalCancel;
        else delete globalThis.cancelAnimationFrame;
    });
    const canvas = makeSoftwareCanvas();
    const view = new BoardView(canvas);
    view.setBoard(reference);
    view.setOptions({ autoRotate: true });
    assert.equal(callbacks.size, 1);
    view.reducedMotion = true; view.render();
    assert.equal(callbacks.size, 0);
    view.reducedMotion = false; view.render();
    assert.equal(callbacks.size, 1);
    canvas.hidden = true; view.render();
    assert.equal(callbacks.size, 0);
    canvas.hidden = false; view.render();
    assert.equal(callbacks.size, 1);
    view.dispose();
    assert.equal(callbacks.size, 0);
    assert.ok([...canvas.handlers.values()].every((set) => set.size === 0));
    view.setOptions({ autoRotate: true });
    assert.equal(callbacks.size, 0);
});

function makeGL() {
    let nextId = 0;
    const calls = { uploads: 0, draws: 0, deletedBuffers: 0, deletedPrograms: 0 };
    const gl = { calls, drawingBufferWidth: 600, drawingBufferHeight: 400,
        createShader: () => ++nextId, createProgram: () => ++nextId, createBuffer: () => ++nextId,
        getShaderParameter: () => true, getProgramParameter: () => true,
        getAttribLocation: () => nextId++ % 4, getUniformLocation: (_, name) => name,
        isContextLost: () => false, bufferData: () => { calls.uploads += 1; },
        drawArrays: () => { calls.draws += 1; }, deleteBuffer: () => { calls.deletedBuffers += 1; },
        deleteProgram: () => { calls.deletedPrograms += 1; },
    };
    for (const method of ["shaderSource", "compileShader", "deleteShader", "attachShader", "linkProgram",
        "enable", "disable", "depthFunc", "blendFunc", "clearColor", "bindBuffer", "enableVertexAttribArray",
        "vertexAttribPointer", "viewport", "depthMask", "clear", "useProgram", "uniform4f", "uniform2f", "uniform3f"]) gl[method] = () => {};
    return gl;
}

test("orbiting uses existing GPU buffers and disposal releases every resource", () => {
    const gl = makeGL();
    const renderer = new WebGLBoardRenderer({ getContext: () => gl });
    renderer.setGeometry(buildRenderGeometry(buildScene(reference)));
    assert.equal(gl.calls.uploads, 3);
    for (let index = 0; index < 20; index += 1) renderer.render(createCamera({ yaw: index * 0.1 }), { width: 600, height: 400 });
    assert.equal(gl.calls.uploads, 3, "camera motion must not rebuild/upload static mesh data");
    assert.equal(gl.calls.draws, 60, "three bounded batches per normal frame");
    renderer.dispose();
    assert.equal(gl.calls.deletedBuffers, 3);
    assert.equal(gl.calls.deletedPrograms, 1);
});
