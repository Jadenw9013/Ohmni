import assert from "node:assert/strict";
import test from "node:test";

import { CircuitLessons } from "../circuit-lessons.js";

function source() {
    return {
        board: {
            artifact_fingerprint: "a".repeat(64), routing_plan_fingerprint: "b".repeat(64),
            net_names: ["SUPPLY"], tracks: [{ net_name: "SUPPLY" }],
            components: [
                { ref: "P1", net_names: ["SUPPLY"] },
                { ref: "C1", net_names: ["SUPPLY"] },
            ],
        },
        systems: [
            { system: "power", label: "Power", summary: "The power group.", component_refs: ["P1"], anchor_refs: ["P1"] },
            { system: "compute", label: "Compute", summary: "The compute group.", component_refs: ["C1"], anchor_refs: ["C1"] },
        ],
        components: [
            { ref: "P1", system: "power", name: { human: "Power connector" } },
            { ref: "C1", system: "compute", name: { human: "Controller" } },
        ],
    };
}

// This small event surface records DOM replacement and focus. The renderer is
// represented only by the public selection/options/highlight callback contract;
// no camera, canvas, drawing, or GPU behavior is reproduced here.
function harness() {
    const listeners = new Map();
    let focused = null;
    let revision = 0;
    const container = {
        html: "",
        get innerHTML() { return this.html; },
        set innerHTML(value) { this.html = value; revision += 1; },
        addEventListener(type, handler) { listeners.set(type, handler); },
        removeEventListener(type, handler) { if (listeners.get(type) === handler) listeners.delete(type); },
        querySelector(selector) {
            if (selector !== "h3" && selector !== '[data-lesson-action="start"]') return null;
            const element = { selector, revision, setAttribute() {}, focus() { focused = element; } };
            return element;
        },
        querySelectorAll() { return []; },
    };
    let lessons;
    const view = {
        selected: null, highlight: {}, options: {}, selectionCalls: [], focusCalls: [], frameCalls: 0,
        select(ref) {
            this.selected = ref;
            this.selectionCalls.push(ref);
            lessons?.select(ref);
        },
        setHighlight(value) { this.highlight = structuredClone(value); },
        setOptions(value) { Object.assign(this.options, value); },
        focus(refs) { this.focusCalls.push(structuredClone(refs)); },
        frame() { this.frameCalls += 1; },
    };
    lessons = new CircuitLessons(container, source(), view);
    return {
        lessons, view, container,
        get focused() { return focused; },
        get revision() { return revision; },
        click(name, data = {}) {
            const action = { dataset: { lessonAction: name, ...data } };
            listeners.get("click")?.({ target: { closest: () => action } });
        },
    };
}

test("a wrong part choice keeps the tour's answer targets highlighted", () => {
    const { lessons, view, container } = harness();
    lessons.go(0);
    view.select("C1");
    assert.equal(lessons.selected, "C1", "the clicked component is still inspectable");
    assert.equal(lessons.visited.size, 0, "a different system does not complete the stop");
    assert.deepEqual(view.highlight, { refs: ["P1"] });
    assert.match(container.innerHTML, /Try one of the highlighted parts/);
    view.select("P1");
    assert.deepEqual([...lessons.visited], [0]);
    assert.deepEqual(view.highlight, { refs: ["P1"] });
    assert.match(container.innerHTML, /You found Power connector/);
});

test("clearing the board selection clears the lesson inspector too", () => {
    const { lessons, view, container } = harness();
    lessons.go(0);
    view.select("P1");
    assert.match(container.innerHTML, /class="net-inspector"/);
    view.select(null);
    assert.equal(lessons.selected, null);
    assert.doesNotMatch(container.innerHTML, /class="lab-part-detail"/);
    assert.doesNotMatch(container.innerHTML, /class="net-inspector"/);
    assert.deepEqual(view.highlight, { refs: ["P1"] }, "the tour remains ready for another choice");
});

test("moving to the next stop clears renderer selection without callback recursion", () => {
    const h = harness();
    h.lessons.go(0);
    h.view.select("P1");
    const before = h.view.selectionCalls.length;
    h.click("next");
    assert.equal(h.lessons.index, 1);
    assert.equal(h.lessons.selected, null);
    assert.equal(h.view.selected, null);
    assert.equal(h.view.selectionCalls.length, before + 1);
    assert.deepEqual(h.view.highlight, { refs: ["C1"] });
    assert.doesNotMatch(h.container.innerHTML, /class="lab-part-detail"/);
    assert.equal(h.focused.selector, "h3");
    assert.equal(h.focused.revision, h.revision, "focus lands in the newly rendered step");
});

test("returning to free exploration clears selection and restores keyboard focus", () => {
    const h = harness();
    h.lessons.go(0);
    h.view.select("P1");
    const before = h.view.selectionCalls.length;
    h.click("all");
    assert.equal(h.lessons.started, false);
    assert.equal(h.lessons.selected, null);
    assert.equal(h.view.selected, null);
    assert.equal(h.view.selectionCalls.length, before + 1);
    assert.deepEqual(h.view.highlight, {});
    assert.equal(h.view.options.animateFlow, false);
    assert.doesNotMatch(h.container.innerHTML, /class="lab-part-detail"/);
    assert.equal(h.focused.selector, '[data-lesson-action="start"]');
    assert.equal(h.focused.revision, h.revision, "focus does not stay on the removed exit button");
});

test("free exploration clears its isolated highlight when the selection is cleared", () => {
    const { lessons, view } = harness();
    view.select("C1");
    assert.deepEqual(view.highlight, { refs: ["C1"] });
    assert.equal(lessons.visited.size, 0);
    view.select(null);
    assert.deepEqual(view.highlight, {});
});

test("pausing a tour preserves discoveries and hands highlight control to the caller", () => {
    const { lessons, view, container } = harness();
    lessons.go(0);
    view.select("P1");
    view.setHighlight({ nets: ["SUPPLY"] });
    const before = view.selectionCalls.length;
    lessons.pause();
    assert.equal(lessons.started, false);
    assert.equal(lessons.selected, null);
    assert.deepEqual([...lessons.visited], [0]);
    assert.deepEqual(view.highlight, { nets: ["SUPPLY"] });
    assert.equal(view.selectionCalls.length, before);
    assert.doesNotMatch(container.innerHTML, /class="lab-part-detail"/);
});

test("tour stops focus only their projected component refs", () => {
    const { lessons, view } = harness();
    lessons.go(0);
    lessons.go(1);
    assert.deepEqual(view.focusCalls, [["P1"], ["C1"]]);
    assert.deepEqual(view.highlight, { refs: ["C1"] });
    assert.equal(lessons.visited.size, 0, "camera focus does not complete a discovery");
    lessons.go(99);
    assert.equal(view.focusCalls.length, 2, "an absent stop cannot create a camera target");
});

test("the explicit part inspector focuses the chosen part without changing the answer", () => {
    const h = harness();
    h.lessons.go(0);
    h.view.select("C1");
    assert.match(h.container.innerHTML, /aria-label="Inspect Controller on the board"/);
    h.click("inspect");
    assert.equal(h.view.focusCalls.at(-1), "C1");
    assert.deepEqual(h.view.highlight, { refs: ["P1"] }, "the tour's correct targets stay highlighted");
    assert.equal(h.lessons.selected, "C1");
    assert.equal(h.lessons.visited.size, 0);
    h.view.select(null);
    const before = h.view.focusCalls.length;
    h.click("inspect");
    assert.equal(h.view.focusCalls.length, before, "cleared selections cannot focus a stale component");
});

test("fitting the board is always available and preserves current learning state", () => {
    const h = harness();
    assert.match(h.container.innerHTML, /data-lesson-action="fit"/);
    h.lessons.go(0);
    h.view.select("P1");
    h.click("fit");
    assert.equal(h.view.frameCalls, 1);
    assert.equal(h.lessons.started, true);
    assert.equal(h.lessons.selected, "P1");
    assert.deepEqual([...h.lessons.visited], [0]);
    assert.deepEqual(h.view.highlight, { refs: ["P1"] });
});

test("disposing a lesson controller detaches delegated actions", () => {
    const h = harness();
    h.lessons.dispose();
    h.click("start");
    assert.equal(h.lessons.started, false);
    assert.equal(h.view.selectionCalls.length, 0);
});
