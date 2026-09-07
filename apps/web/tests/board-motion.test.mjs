import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { BoardView } from "../board-view.js";

const reference = JSON.parse(readFileSync(new URL("../reference-board.json", import.meta.url))).board;

function fixture(t) {
    const listeners = new Map(), frames = new Map();
    let sequence = 0, timestamp = 0;
    const saved = [globalThis.requestAnimationFrame, globalThis.cancelAnimationFrame];
    globalThis.requestAnimationFrame = (callback) => { frames.set(++sequence, callback); return sequence; };
    globalThis.cancelAnimationFrame = (id) => frames.delete(id);
    const context = new Proxy({ measureText: (text) => ({ width: text.length * 6 }) }, {
        get: (target, key) => target[key] ?? (() => {}),
    });
    const canvas = {
        dataset: {}, style: {},
        getContext: (kind) => kind === "2d" ? context : null,
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 700, height: 500 }),
        addEventListener: (name, fn) => listeners.set(name, fn),
        removeEventListener: (name) => listeners.delete(name),
    };
    const view = new BoardView(canvas);
    view.setBoard(reference);
    t.after(() => {
        view.dispose();
        for (const [index, key] of ["requestAnimationFrame", "cancelAnimationFrame"].entries()) {
            if (saved[index]) globalThis[key] = saved[index]; else delete globalThis[key];
        }
    });
    const tick = (count) => {
        for (let i = 0; i < count; i += 1) {
            timestamp += 40;
            const pending = [...frames.values()]; frames.clear();
            for (const callback of pending) callback(timestamp);
        }
    };
    return { view, frames, tick, key(key) {
        let prevented = false;
        listeners.get("keydown")({ key, preventDefault() { prevented = true; } });
        return prevented;
    } };
}

test("assembly reaches the exact assembled scene, stops work, and preserves the board", (t) => {
    const { view, tick, frames } = fixture(t);
    const original = JSON.stringify(reference);
    const assembled = JSON.stringify(view.scene);
    view.animateAssembly();
    assert.equal(view.options.explode, 1);
    tick(25);
    assert.ok(view.options.explode > 0 && view.options.explode < 1);
    tick(120);
    assert.equal(view.options.explode, 0);
    assert.equal(view.assemblyAnimation, null);
    assert.equal(view.targetCamera, null);
    assert.equal(frames.size, 0);
    assert.equal(JSON.stringify(reference), original);
    assert.equal(JSON.stringify(view.scene), assembled);
});

test("manual navigation and scrubbing interrupt assembly without snapping the layout", (t) => {
    const { view, tick, key, frames } = fixture(t);
    view.animateAssembly(); tick(20);
    const current = view.options.explode;
    key("ArrowRight");
    assert.equal(view.assemblyAnimation, null);
    tick(80);
    assert.equal(view.options.explode, current);
    assert.equal(frames.size, 0);
    view.animateAssembly(); view.setOptions({ explode: 0.35 }); tick(80);
    assert.equal(view.options.explode, 0.35);
    assert.equal(view.assemblyAnimation, null);
});

test("reduced motion gives complete static assembly and camera poses with no RAF", (t) => {
    const { view, frames } = fixture(t);
    view.reducedMotion = true;
    view.animateAssembly();
    assert.equal(view.options.explode, 0);
    view.setCameraPreset("back");
    assert.ok(view.camera.pitch < 0);
    view.focus("U3");
    assert.ok(view.camera.pitch > 0, "front component must be visible when inspected from the back");
    assert.equal(view.options.showBack, false);
    assert.equal(frames.size, 0);
});

test("camera presets animate, settle, and stop allocating frames", (t) => {
    const { view, tick, frames } = fixture(t);
    const start = view.camera.pitch;
    view.setCameraPreset("back");
    assert.equal(view.camera.pitch, start);
    tick(4);
    assert.ok(view.camera.pitch < start && view.camera.pitch > -53 * Math.PI / 180);
    tick(80);
    assert.equal(view.targetCamera, null);
    assert.ok(Math.abs(view.camera.pitch + 53 * Math.PI / 180) < 1e-8);
    assert.equal(frames.size, 0);
});

test("Escape preserves native dialog closing and backwards selection starts at the last part", (t) => {
    const { view, key } = fixture(t);
    assert.equal(key("Escape"), false);
    key("[");
    assert.equal(view.selected, view.geometry.parts.at(-1).ref);
    assert.equal(key("Escape"), true);
    assert.equal(view.selected, null);
    assert.equal(key("Escape"), false);
});

test("trace animation sleeps when copper is hidden, disconnected, or separated", (t) => {
    const { view, frames } = fixture(t);
    view.setHighlight({ nets: ["3V3"] }); view.setOptions({ animateFlow: true });
    assert.ok(view.canAnimate());
    view.setOptions({ showCopper: false });
    assert.equal(view.canAnimate(), false);
    assert.equal(frames.size, 0);
    view.setOptions({ showCopper: true, explode: 0.5 });
    assert.equal(view.canAnimate(), false);
    view.setOptions({ explode: 0 }); view.setHighlight({ nets: ["NO_SUCH_NET"] });
    assert.equal(view.canAnimate(), false);
});
