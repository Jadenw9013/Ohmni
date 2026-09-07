import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { createLessons, discoveryOutcome, validateLearningSource } from "../learning-model.js";

// Different identifiers and systems from the saved room sensor protect against
// a lesson sequence that accidentally encodes only the golden board.
function fixture({ reference = false } = {}) {
    const value = {
        board: {
            artifact_fingerprint: "a".repeat(64),
            routing_plan_fingerprint: "b".repeat(64),
            net_names: ["INPUT_RAIL", "MEASUREMENT"],
            components: [
                { ref: "J7", net_names: ["INPUT_RAIL"] },
                { ref: "A11", net_names: ["INPUT_RAIL", "MEASUREMENT"] },
                { ref: "R42", net_names: ["MEASUREMENT"] },
            ],
            tracks: [{ net_name: "INPUT_RAIL" }, { net_name: "MEASUREMENT" }],
        },
        systems: [
            { system: "measure", label: "Take a measurement", summary: "The projected measurement group.",
                component_refs: ["A11", "R42"], anchor_refs: ["A11"] },
            { system: "supply", label: "Bring in power", summary: "The projected supply group.",
                component_refs: ["J7"], anchor_refs: ["J7"] },
        ],
        components: [
            { ref: "J7", name: { human: "Supply connector", technical: "J7" }, system: "supply", purpose: "Component detail for the connector." },
            { ref: "A11", name: { human: "Measurement part", technical: "A11" }, system: "measure", purpose: "Component detail for the measurement part." },
            { ref: "R42", name: { human: "Helper resistor", technical: "R42" }, system: "measure", purpose: "Component detail for the resistor." },
        ],
        flows: [{
            flow_id: "measurement-path", component_refs: ["A11", "R42"], net_names: ["MEASUREMENT"],
            stages: [{ component_refs: ["A11"], net_names: ["MEASUREMENT"] }],
        }],
    };
    if (reference) {
        value.schema_version = 1;
        value.source = {
            kind: "previously_generated_reference_preview",
            artifact_fingerprint: value.board.artifact_fingerprint,
            routing_plan_fingerprint: value.board.routing_plan_fingerprint,
        };
    }
    return value;
}

function deepFreeze(value) {
    if (value && typeof value === "object") {
        Object.values(value).forEach(deepFreeze);
        Object.freeze(value);
    }
    return value;
}

test("validating a projected learning source preserves its identity", () => {
    const source = fixture();
    assert.strictEqual(validateLearningSource(source), source);
    const reference = fixture({ reference: true });
    assert.strictEqual(validateLearningSource(reference, { reference: true }), reference);
});

test("saved references require both artifact and routing lineage", () => {
    for (const field of ["artifact_fingerprint", "routing_plan_fingerprint"]) {
        const source = fixture({ reference: true });
        source.source[field] = "c".repeat(64);
        assert.throws(() => validateLearningSource(source, { reference: true }), Error, field);
        assert.throws(() => createLessons(source), Error, "lesson creation validates reference provenance too");
    }
});

test("matching fingerprint strings must still be real fingerprint shapes", () => {
    for (const invalid of ["", "abcd", "z".repeat(64)]) {
        for (const field of ["artifact_fingerprint", "routing_plan_fingerprint"]) {
            const source = fixture({ reference: true });
            source.source[field] = invalid;
            source.board[field] = invalid;
            assert.throws(() => validateLearningSource(source, { reference: true }), Error);
        }
    }
});

test("reference metadata cannot silently become a current project", () => {
    for (const mutate of [
        (source) => { source.schema_version = 2; },
        (source) => { source.source.kind = "current_verified_project"; },
        (source) => { delete source.source; },
    ]) {
        const source = fixture({ reference: true });
        mutate(source);
        assert.throws(() => validateLearningSource(source, { reference: true }), Error);
    }
});

test("missing structural arrays fail before lessons can be built", () => {
    for (const mutate of [
        (source) => { source.systems = null; },
        (source) => { source.components = {}; },
        (source) => { source.board.components = null; },
        (source) => { source.board.tracks = {}; },
        (source) => { source.board.net_names = null; },
        (source) => { source.systems[0].component_refs = null; },
        (source) => { source.systems[0].anchor_refs = null; },
    ]) {
        const source = fixture();
        mutate(source);
        assert.throws(() => validateLearningSource(source), Error);
    }
    assert.throws(() => validateLearningSource(null), Error);
});

test("duplicate geometry refs, cards, and system identifiers are ambiguous", () => {
    for (const mutate of [
        (source) => { source.board.components.push({ ...source.board.components[0] }); },
        (source) => { source.components.push({ ...source.components[0] }); },
        (source) => { source.systems.push({ ...source.systems[0] }); },
        (source) => { source.systems[0].component_refs.push("A11"); },
    ]) {
        const source = fixture();
        mutate(source);
        assert.throws(() => validateLearningSource(source), Error);
    }
});

test("cards and placed parts must describe the same set of components", () => {
    const missingCard = fixture();
    missingCard.components.pop();
    assert.throws(() => validateLearningSource(missingCard), Error);
    const unplacedCard = fixture();
    unplacedCard.components.push({ ref: "GHOST", name: { human: "Absent part" }, system: "measure" });
    assert.throws(() => validateLearningSource(unplacedCard), Error);
    const renamedCard = fixture();
    renamedCard.components[0].ref = "UNPLACED";
    assert.throws(() => validateLearningSource(renamedCard), Error);
});

test("system members and anchors remain consistent with projected cards", () => {
    for (const mutate of [
        (source) => { source.systems[0].component_refs.push("GHOST"); },
        (source) => { source.systems[0].component_refs.push("J7"); },
        (source) => { source.components[1].system = "supply"; },
        (source) => { source.systems[0].anchor_refs = ["J7"]; },
        (source) => { source.systems[0].anchor_refs = ["GHOST"]; },
    ]) {
        const source = fixture();
        mutate(source);
        assert.throws(() => validateLearningSource(source), Error);
    }
});

test("flow and stage highlights cannot name absent refs or nets", () => {
    for (const target of ["flow", "stage"]) {
        for (const field of ["component_refs", "net_names"]) {
            const source = fixture();
            const record = target === "flow" ? source.flows[0] : source.flows[0].stages[0];
            record[field] = ["GHOST"];
            assert.throws(() => validateLearningSource(source), Error, `${target}.${field}`);
        }
    }
});

test("flows are optional and their absence does not invent a connection lesson", () => {
    const source = fixture();
    delete source.flows;
    const lessons = createLessons(source);
    assert.equal(lessons.length, source.systems.length);
    assert.deepEqual(lessons.map((lesson) => lesson.refs), source.systems.map((system) => system.component_refs));
});

test("lesson order, language and highlighted parts come from the projected systems", () => {
    const source = fixture();
    const lessons = createLessons(source);
    assert.deepEqual(lessons.map((lesson) => lesson.title), source.systems.map((system) => system.label));
    assert.deepEqual(lessons.map((lesson) => lesson.description), source.systems.map((system) => system.summary));
    assert.deepEqual(lessons.map((lesson) => lesson.refs), [["A11", "R42"], ["J7"]]);
    assert.deepEqual(lessons.map((lesson) => lesson.anchorRefs), [["A11"], ["J7"]]);
    assert.deepEqual(lessons[0].parts, [
        { ref: "A11", name: "Measurement part" },
        { ref: "R42", name: "Helper resistor" },
    ]);
    assert.equal(new Set(lessons.map((lesson) => lesson.id)).size, lessons.length);
    assert.ok(lessons.every((lesson) => typeof lesson.id === "string" && lesson.id.length > 0));
});

test("part names fall back to their ref without turning identifiers into invented names", () => {
    const source = fixture();
    source.components[1].name = {};
    assert.equal(createLessons(source)[0].parts[0].name, "A11");
});

test("component-purpose copy is not promoted into a system lesson", () => {
    const source = fixture();
    source.components[1].purpose = "A deliberately unsupported component explanation.";
    const lessons = createLessons(source);
    assert.equal(lessons[0].description, source.systems[0].summary);
    assert.ok(!JSON.stringify(lessons).includes(source.components[1].purpose));
});

test("building and using lessons never mutates the authoritative source", () => {
    const source = fixture();
    const before = structuredClone(source);
    deepFreeze(source);
    const lessons = createLessons(source);
    assert.notStrictEqual(lessons[0].refs, source.systems[0].component_refs);
    assert.notStrictEqual(lessons[0].anchorRefs, source.systems[0].anchor_refs);
    lessons[0].refs.push("PRESENTATION_ONLY");
    lessons[0].anchorRefs.pop();
    lessons[0].parts[0].name = "Changed label";
    assert.deepEqual(source, before);
});

test("discovery feedback is exact lesson membership rather than an engineering verdict", () => {
    const lesson = createLessons(fixture())[0];
    assert.equal(discoveryOutcome(lesson, "A11"), "match");
    assert.equal(discoveryOutcome(lesson, "R42"), "match", "helpers are members too");
    assert.equal(discoveryOutcome(lesson, "J7"), "other");
    assert.equal(discoveryOutcome(lesson, "GHOST"), "other");
    assert.equal(discoveryOutcome(lesson, "a11"), "other", "identifiers are not fuzzy matched");
});

test("the shipped saved board supports truthful lessons with its own provenance", () => {
    const source = JSON.parse(readFileSync(new URL("../reference-board.json", import.meta.url), "utf8"));
    assert.strictEqual(validateLearningSource(source, { reference: true }), source);
    const lessons = createLessons(source);
    assert.equal(lessons.length, source.systems.length);
    for (let index = 0; index < lessons.length; index += 1) {
        assert.equal(lessons[index].description, source.systems[index].summary);
        assert.deepEqual(lessons[index].refs, source.systems[index].component_refs);
    }
});
