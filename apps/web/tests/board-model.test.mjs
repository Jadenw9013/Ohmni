import assert from "node:assert/strict";
import test from "node:test";

import { buildScene, centreOf, highlightMatcher, sceneBounds } from "../board-model.js";
import { bandOf, createCamera, depthSort, project } from "../board-view.js";
import { transitionFrame, transitionTracks } from "../schematic-view.js";

const board = {
    artifact_fingerprint: "a".repeat(64),
    routing_plan_fingerprint: "b".repeat(64),
    constraints_hash: "c".repeat(64),
    width_mm: 100,
    height_mm: 70,
    layer_count: 2,
    display_thickness_mm: 1.6,
    thickness_is_display_only: true,
    layers: ["F.Cu", "B.Cu"],
    net_names: ["3V3", "GND", "SDA"],
    components: [
        {
            ref: "U3", part_id: "BME280", package: "LGA-8", footprint_id: "fp.lga8",
            system: "sense", x_mm: 80, y_mm: 50, rotation_deg: 0, side: "F.Cu",
            width_mm: 2.5, height_mm: 2.5, placement_reason: "sensor away from heat",
            net_names: ["3V3", "GND", "SDA"],
            pads: [
                { number: "1", net_name: "GND", x_mm: -0.975, y_mm: -1.025, width_mm: 0.35, height_mm: 0.5, kind: "smd", shape: "rect" },
                { number: "3", net_name: "SDA", x_mm: 0.325, y_mm: -1.025, width_mm: 0.35, height_mm: 0.5, kind: "smd", shape: "rect" },
            ],
        },
        {
            ref: "J2", part_id: "HEADER_1X6_254", package: "1x6", footprint_id: "fp.hdr",
            system: "io", x_mm: 95, y_mm: 25, rotation_deg: 90, side: "F.Cu",
            width_mm: 2.54, height_mm: 15.24, placement_reason: "header at edge",
            net_names: ["3V3"],
            pads: [
                { number: "1", net_name: "3V3", x_mm: 0, y_mm: 0, width_mm: 1.7, height_mm: 1.7, kind: "thru_hole", shape: "circle" },
            ],
        },
    ],
    tracks: [
        { net_name: "SDA", layer: "F.Cu", start_x_mm: 76, start_y_mm: 44, end_x_mm: 80, end_y_mm: 49, width_mm: 0.25 },
        { net_name: "GND", layer: "B.Cu", start_x_mm: 10, start_y_mm: 10, end_x_mm: 20, end_y_mm: 10, width_mm: 0.25 },
    ],
    vias: [{ net_name: "GND", x_mm: 15, y_mm: 10, diameter_mm: 0.8, drill_mm: 0.4 }],
};

test("the scene is centred on the board so rotation is about its middle", () => {
    assert.deepEqual(centreOf(board), { x: 50, y: 35 });
    const scene = buildScene(board);
    const u3 = scene.parts.find((p) => p.ref === "U3");
    assert.equal(u3.centre.x, 30);
    assert.equal(u3.centre.y, 15);
});

test("every primitive comes from projected data and none is invented", () => {
    const scene = buildScene(board);
    assert.equal(scene.parts.length, board.components.length);
    assert.equal(scene.pads.length, 3);
    assert.equal(scene.tracks.length, board.tracks.length);
    assert.equal(scene.vias.length, board.vias.length);
    assert.equal(scene.substrate.length, 6);
    assert.equal(scene.thickness, board.display_thickness_mm);
    assert.equal(scene.thicknessIsDisplayOnly, true);
});

test("package identity and per-pad shape and number survive the scene projection", () => {
    const scene = buildScene(board);
    for (const component of board.components) {
        const part = scene.parts.find((item) => item.ref === component.ref);
        assert.equal(part.package, component.package);
        assert.equal(part.footprintId, component.footprint_id);
        const pads = scene.pads.filter((item) => item.ref === component.ref);
        assert.deepEqual(pads.map(({ number, shape }) => ({ number, shape })),
            component.pads.map(({ number, shape }) => ({ number, shape })));
    }
});

test("copper sits on the layer the compiler emitted it on", () => {
    const scene = buildScene(board);
    const front = scene.tracks.find((t) => t.net === "SDA");
    const back = scene.tracks.find((t) => t.net === "GND");
    assert.equal(front.a.z, board.display_thickness_mm / 2);
    assert.equal(back.a.z, -board.display_thickness_mm / 2);
});

test("component rotation is applied to pads, not only to the body", () => {
    const scene = buildScene(board);
    const headerPad = scene.pads.find((p) => p.ref === "J2");
    const rotated = scene.parts.find((p) => p.ref === "J2");
    assert.ok(headerPad.through, "a through-hole pad keeps its kind");
    // A 90-degree symbol is taller than it is wide once rotated.
    const xs = rotated.points.map((p) => p.x);
    const ys = rotated.points.map((p) => p.y);
    assert.ok(Math.max(...xs) - Math.min(...xs) > Math.max(...ys) - Math.min(...ys));
});

test("hiding copper or components removes only those primitives", () => {
    const noCopper = buildScene(board, { showCopper: false });
    assert.equal(noCopper.tracks.length, 0);
    assert.equal(noCopper.vias.length, 0);
    assert.equal(noCopper.parts.length, 2);
    const noParts = buildScene(board, { showComponents: false });
    assert.equal(noParts.parts.length, 0);
    assert.equal(noParts.tracks.length, 2);
});

test("exploding moves whole systems apart without changing the board", () => {
    const flat = buildScene(board, { explode: 0 });
    const burst = buildScene(board, { explode: 1 });
    const flatU3 = flat.parts.find((p) => p.ref === "U3").centre;
    const burstU3 = burst.parts.find((p) => p.ref === "U3").centre;
    assert.notDeepEqual(flatU3, burstU3);
    assert.ok(burstU3.z > flatU3.z, "parts lift off the board");
    assert.equal(burst.width, flat.width, "the board itself does not move");
    const senseOffset = burst.offsets.sense;
    const ioOffset = burst.offsets.io;
    assert.notDeepEqual(senseOffset, ioOffset, "different systems separate differently");
});

test("highlighting is set membership, never inference", () => {
    const byNet = highlightMatcher({ nets: ["SDA"] });
    assert.ok(byNet.active);
    assert.ok(byNet.matches({ net: "SDA" }));
    assert.ok(!byNet.matches({ net: "GND" }));
    assert.ok(byNet.matches({ nets: ["3V3", "SDA"] }));
    const inactive = highlightMatcher({});
    assert.ok(!inactive.active);
    assert.ok(inactive.matches({ net: "anything" }), "no highlight means nothing is dimmed");
});

test("the top-down camera looks at the front of the board", () => {
    const camera = createCamera({ yaw: 0, pitch: Math.PI / 2 });
    const viewport = { width: 400, height: 300, cx: 200, cy: 150 };
    const origin = project({ x: 0, y: 0, z: 0 }, camera, viewport);
    const right = project({ x: 10, y: 0, z: 0 }, camera, viewport);
    const up = project({ x: 0, y: 10, z: 0 }, camera, viewport);
    assert.ok(right.x > origin.x, "board +x goes right");
    assert.ok(up.y < origin.y, "board +y goes up the screen");
    const front = project({ x: 0, y: 0, z: 1 }, camera, viewport);
    assert.ok(front.depth < origin.depth, "the front face is nearer the camera");
});

test("a negative pitch shows the back of the board", () => {
    const viewport = { width: 400, height: 300, cx: 200, cy: 150 };
    const back = createCamera({ yaw: 0, pitch: -Math.PI / 2 });
    const frontFace = project({ x: 0, y: 0, z: 1 }, back, viewport);
    const backFace = project({ x: 0, y: 0, z: -1 }, back, viewport);
    assert.ok(backFace.depth < frontFace.depth, "the back face is nearer when flipped");
});

test("perspective makes nearer geometry larger", () => {
    const camera = createCamera({ yaw: 0, pitch: 0 });
    const viewport = { width: 400, height: 300, cx: 200, cy: 150 };
    const near = project({ x: 10, y: -50, z: 0 }, camera, viewport);
    const far = project({ x: 10, y: 50, z: 0 }, camera, viewport);
    assert.ok(Math.abs(near.x - viewport.cx) > Math.abs(far.x - viewport.cx));
});

test("depth sorting draws far geometry first, within its band", () => {
    const sorted = depthSort([
        { band: 1, depth: 1 }, { band: 1, depth: 9 }, { band: 1, depth: 5 },
    ]);
    assert.deepEqual(sorted.map((p) => p.depth), [9, 5, 1]);
});

test("the substrate never hides parts sitting on the far half of the board", () => {
    // The failure this guards: the board is one large polygon whose mean depth
    // is the board centre, so a nearer-than-average part on the far edge would
    // sort behind it and vanish.
    const board = { band: 1, depth: 260 };
    const farPart = { band: 2, depth: 275 };
    const nearPart = { band: 2, depth: 240 };
    const order = depthSort([nearPart, board, farPart]);
    assert.deepEqual(order, [board, farPart, nearPart]);
});

test("bands follow which side of the board the camera is looking at", () => {
    assert.equal(bandOf(0.8, Math.PI / 4), 2, "front geometry is near when facing the front");
    assert.equal(bandOf(-0.8, Math.PI / 4), 0, "back geometry is occluded by the board");
    assert.equal(bandOf(0.8, -Math.PI / 4), 0, "flipping over swaps which side is hidden");
    assert.equal(bandOf(-0.8, -Math.PI / 4), 2);
    assert.equal(bandOf(0, Math.PI / 4), 1, "a through-board via spans both sides");
});

test("scene bounds grow to include exploded parts", () => {
    const flat = sceneBounds(buildScene(board, { explode: 0 }));
    const burst = sceneBounds(buildScene(board, { explode: 1 }));
    assert.ok(burst.radius > flat.radius);
});

const schematic = {
    artifact_fingerprint: "d".repeat(64),
    connection_method: "global_labels",
    net_names: ["3V3", "GND", "SDA"],
    symbols: [
        { ref: "U3", part_id: "BME280", system: "sense", x_mm: 10, y_mm: 10, width_mm: 20, height_mm: 12, pins: [{ pin: "3", net_name: "SDA", x_mm: 10, y_mm: 14 }] },
        { ref: "J2", part_id: "HEADER_1X6_254", system: "io", x_mm: 60, y_mm: 40, width_mm: 20, height_mm: 12, pins: [{ pin: "1", net_name: "3V3", x_mm: 60, y_mm: 44 }] },
    ],
};

test("the transition tweens between two real layouts", () => {
    const tracks = transitionTracks(schematic, board);
    assert.deepEqual(tracks.map((t) => t.ref), ["J2", "U3"]);
    const start = transitionFrame(tracks, 0);
    const end = transitionFrame(tracks, 1);
    const startU3 = start.find((f) => f.ref === "U3");
    const endU3 = end.find((f) => f.ref === "U3");
    assert.equal(startU3.symbolOpacity, 1);
    assert.equal(endU3.symbolOpacity, 0);
    assert.equal(endU3.footprintOpacity, 1);
    assert.ok(Math.abs(endU3.w - 2.5) < 1e-9, "it ends at the real footprint size");
    assert.ok(Math.abs(startU3.w - 20) < 1e-9, "it starts at the real symbol size");
});

test("a component present in only one layout is omitted, never invented", () => {
    const partial = { ...schematic, symbols: [...schematic.symbols, { ref: "GHOST", part_id: "X", system: "io", x_mm: 1, y_mm: 1, width_mm: 2, height_mm: 2, pins: [] }] };
    const tracks = transitionTracks(partial, board);
    assert.ok(!tracks.some((t) => t.ref === "GHOST"));
});

test("transition frames stay inside the interval and are monotonic", () => {
    const tracks = transitionTracks(schematic, board);
    const before = transitionFrame(tracks, -1)[0];
    const after = transitionFrame(tracks, 2)[0];
    assert.deepEqual(before, transitionFrame(tracks, 0)[0]);
    assert.deepEqual(after, transitionFrame(tracks, 1)[0]);
});
