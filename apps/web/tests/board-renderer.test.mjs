import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildScene, highlightMatcher } from "../board-model.js";
import { BoardView, createCamera, project } from "../board-view.js";
import { buildRenderGeometry, displayPackageKind, packageContacts, padContour, padHoleContour, pointOnFootprint,
    trackRibbon, VERTEX_STRIDE } from "../board-renderer-geometry.js";
import { WebGLBoardRenderer } from "../board-renderer-webgl.js";

const reference = JSON.parse(readFileSync(new URL("../reference-board.json", import.meta.url))).board;
const near = (a, b, tolerance = 1e-6) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);

test("source-sized slots rotate with the footprint and locating holes carry no copper finish", () => {
    const board = structuredClone(reference);
    board.components = [{ ...board.components[0], rotation_deg: 90, pads: [{
        number: "", net_name: null, kind: "np_thru_hole", shape: "oval",
        x_mm: 0, y_mm: 0, width_mm: 0.6, height_mm: 1.7,
        drill: { shape: "oval", width_mm: 0.6, height_mm: 1.7 },
    }] }];
    board.tracks = []; board.vias = [];
    const scene = buildScene(board);
    const pad = scene.pads[0];
    assert.equal(pad.nonPlated, true);
    assert.equal(pad.net, null);
    assert.deepEqual(pad.drill, board.components[0].pads[0].drill);
    const contour = padHoleContour(pad);
    const xs = contour.map(p => p.x), ys = contour.map(p => p.y);
    near(Math.max(...xs) - Math.min(...xs), 1.7);
    near(Math.max(...ys) - Math.min(...ys), 0.6);
    scene.parts = [];
    const mesh = buildRenderGeometry(scene).objects;
    assert.ok(mesh.length > 0);
    for (let i = 0; i < mesh.length; i += VERTEX_STRIDE) {
        near(mesh[i + 6], 0.012); near(mesh[i + 7], 0.018); near(mesh[i + 8], 0.022);
    }
    assert.deepEqual(padHoleContour({ ...pad, drill: null }), []);
});
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
    assert.equal(displayPackageKind({ partId: "VENDOR_42", footprintId: "Button_Switch_THT:SW_PUSH_6mm" }), "button");
    assert.equal(displayPackageKind({ partId: "VENDOR_42", footprintId: "Capacitor_SMD:C_0603" }), "capacitor");
    assert.equal(displayPackageKind({ partId: "VENDOR_42", package: "Module-SMD-38" }), "module");
    assert.equal(displayPackageKind({ partId: "VENDOR_42", package: "USB-C-16P-SMD" }), "usb");
    assert.equal(displayPackageKind({ partId: "UNKNOWN_PART", ref: "SW1", system: "button" }), "chip",
        "reference designators and functional grouping do not invent a package");
});

test("rotated circle and oval pads retain source perimeters instead of square corners", () => {
    for (const [shape, width, height] of [["circle", 2, 2], ["oval", 1.2, 2.8], ["oval", 2.8, 1.2]]) {
        for (const side of ["F.Cu", "B.Cu"]) {
            const board = { ...reference, tracks: [], vias: [], components: [{ ...reference.components[0],
                side, rotation_deg: 37, pads: [{ number: "A17", shape, kind: "smd", x_mm: 0, y_mm: 0,
                    width_mm: width, height_mm: height, net_name: "GND" }] }] };
            const scene = buildScene(board);
            const pad = scene.pads[0];
            const [a, b, , d] = pad.points;
            const toLocal = ({ x, y }) => ({
                x: ((x - a.x) * (b.x - a.x) + (y - a.y) * (b.y - a.y)) / width - width / 2,
                y: ((x - a.x) * (d.x - a.x) + (y - a.y) * (d.y - a.y)) / height - height / 2,
            });
            const contour = padContour(pad).map(toLocal);
            near(Math.max(...contour.map((p) => p.x)) - Math.min(...contour.map((p) => p.x)), width);
            near(Math.max(...contour.map((p) => p.y)) - Math.min(...contour.map((p) => p.y)), height);
            const radius = Math.min(width, height) / 2;
            const straight = Math.abs(width - height) / 2;
            const radialDistance = ({ x, y }) => width > height
                ? Math.hypot(Math.max(0, Math.abs(x) - straight), y)
                : Math.hypot(x, Math.max(0, Math.abs(y) - straight));
            for (const point of contour) near(radialDistance(point), radius);
            const objects = buildRenderGeometry({ ...scene, parts: [] }).objects;
            for (let i = 0; i < objects.length; i += VERTEX_STRIDE) {
                const local = toLocal({ x: objects[i], y: objects[i + 1] });
                assert.ok(radialDistance(local) <= radius + 1e-5, "solder and copper stay within the true rounded pad");
                near(Math.hypot(...objects.slice(i + 3, i + 6)), 1, 2e-6);
                assert.equal(Math.sign(objects[i + 2]), side === "F.Cu" ? 1 : -1);
            }
        }
    }
});

test("button terminals follow every real pad including repeated terminal numbers", () => {
    const button = { ...reference.components[0], ref: "K93", part_id: "UNFAMILIAR_BUTTON_VENDOR",
        package: "6mm-THT", footprint_id: "Button_Switch_THT:SW_PUSH_6mm", width_mm: 9.5, height_mm: 7.5,
        rotation_deg: 73, side: "B.Cu", pads: [["1", -3.25, -2.25], ["1", 3.25, -2.25],
            ["2", -3.25, 2.25], ["2", 3.25, 2.25]].map(([number, x_mm, y_mm]) => ({
            number, x_mm, y_mm, width_mm: 2, height_mm: 2, shape: "circle", kind: "thru_hole",
            net_name: number === "1" ? "BUTTON_INPUT" : "GND", drill: { shape: "circle", width_mm: 1.1, height_mm: 1.1 },
        })) };
    const scene = buildScene({ ...reference, components: [button], tracks: [], vias: [] });
    const contacts = packageContacts(scene.parts[0], scene.pads);
    assert.equal(contacts.length, 4, "two named terminals can have four real lands");
    assert.deepEqual(contacts.map((contact) => contact.number), ["1", "1", "2", "2"]);
    for (const [index, contact] of contacts.entries()) {
        const centre = pointOnFootprint({ points: scene.pads[index].points, side: "B.Cu" }, 0.5, 0.5);
        near(contact.a.x, centre.x); near(contact.a.y, centre.y);
        assert.equal(contact.net, scene.pads[index].net);
        assert.ok(contact.a.z < scene.parts[0].centre.z && contact.b.z < contact.a.z);
    }
    assert.equal(packageContacts(scene.parts[0], scene.pads.slice(0, 1)).length, 1,
        "missing source pads cannot become extra decorative terminals");
    const geometry = buildRenderGeometry(scene);
    assert.equal(geometry.parts[0].displayKind, "button");
    assert.deepEqual(geometry.parts[0].displayContacts, contacts);
    assert.ok(geometry.objects.every(Number.isFinite));
    for (let i = 0; i < geometry.objects.length; i += VERTEX_STRIDE) near(Math.hypot(...geometry.objects.slice(i + 3, i + 6)), 1, 2e-6);
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
        const scene = buildScene(reference, { explode });
        const geometry = buildRenderGeometry(scene);
        const budget = 1200 * scene.parts.length + 300 * scene.pads.length + 90 * scene.tracks.length + 250 * scene.vias.length;
        assert.ok(geometry.vertexCount < budget,
            "mesh budget scales with actual components, pads and copper, never decorative filler");
        for (const group of ["substrate", "objects", "shadows"]) {
            assert.equal(geometry[group].length % (VERTEX_STRIDE * 3), 0);
            assert.ok(geometry[group].every(Number.isFinite));
            for (let i = 0; i < geometry[group].length; i += VERTEX_STRIDE) {
                near(Math.hypot(...geometry[group].slice(i + 3, i + 6)), 1, 2e-6);
            }
        }
    }
});

test("pad finishes stay within source bounds and only undrilled lands receive solder fillets", () => {
    const scene = buildScene(reference);
    for (const pad of scene.pads) {
        const geometry = buildRenderGeometry({ ...scene, parts: [], tracks: [], vias: [], pads: [pad] });
        const [a, b, , d] = pad.points;
        const ux = b.x - a.x, uy = b.y - a.y;
        const vx = d.x - a.x, vy = d.y - a.y;
        let raised = false;
        let slopedMetal = false;
        let hasMetal = false;
        for (let index = 0; index < geometry.objects.length; index += VERTEX_STRIDE) {
            const dx = geometry.objects[index] - a.x, dy = geometry.objects[index + 1] - a.y;
            const u = (dx * ux + dy * uy) / (ux * ux + uy * uy);
            const v = (dx * vx + dy * vy) / (vx * vx + vy * vy);
            assert.ok(u >= -1e-4 && u <= 1.0001 && v >= -1e-4 && v <= 1.0001, `${pad.ref}: solder must stay inside the real pad`);
            if (Math.abs(geometry.objects[index + 2] - a.z) > 0.15) raised = true;
            const nz = Math.abs(geometry.objects[index + 5]);
            const metallic = Math.floor((geometry.objects[index + 9] % 4) / 2);
            if (metallic === 1) hasMetal = true;
            if (metallic === 1 && nz > 0.01 && nz < 0.99) slopedMetal = true;
        }
        const identity = `${pad.ref}.${pad.number || "locating hole"}`;
        assert.equal(hasMetal, !pad.nonPlated, `${identity}: locating holes must not acquire copper`);
        assert.equal(raised && slopedMetal, !pad.drill && !pad.nonPlated,
            `${identity}: solder fillets belong only on undrilled lands; drilled openings remain open`);
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
