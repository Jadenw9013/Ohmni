import test from "node:test";
import assert from "node:assert/strict";
import { defaultProjectBrief, supportedBrief, parseProjectEnvelope, parseProjectList, parseProjectStart, sameBrief, projectRequest, briefChanges } from "../project-contract.js";
import { parseExercise, parseExerciseResult, mountProjectWorkbench } from "../project-workbench.js";

const identity = { api_version: 2, server_instance_id: "0123456789abcdef", ui_version: "a".repeat(64) };
const stamp = "2026-09-08T18:00:00+00:00";
const brief = defaultProjectBrief();
const preview = { project_name: brief.project_name, request: "sensor", asked_for: [], assumed: [], needs_clarification: [] };
const revision = { revision_id: "1".repeat(16), number: 1, created_at: stamp, brief, brief_fingerprint: "b".repeat(64), preview, job_id: null };
const project = { project_id: "2".repeat(16), created_at: stamp, updated_at: stamp, revisions: [revision] };
const envelope = (projectValue = project) => ({ ...identity, project: projectValue });
const response = (status, payload) => ({ ok: status >= 200 && status < 300, status, json: async () => payload });

test("only the bounded sensor family can be loaded into the editable workbench", () => {
    assert.equal(supportedBrief(brief), true);
    assert.equal(supportedBrief({ ...brief, sensors: [{ part_id: "BME280", address: null }] }), true);
    for (const change of [
        { sensors: [{ part_id: "UNKNOWN_SENSOR", address: 118 }] }, { status_led_count: 3 },
        { input_voltage_v: 12 }, { sensors: [{ part_id: "BME280", address: 99 }] },
        { include_programming_header: "false" }, { project_name: " " },
    ]) assert.equal(supportedBrief({ ...brief, ...change }), false);
});

test("saved revision parsing rejects stale identity, duplicate ids, malformed previews and missing fingerprints", () => {
    assert.equal(parseProjectEnvelope(envelope(), identity), project);
    const alternate = { ...identity, server_instance_id: "f".repeat(16) };
    assert.throws(() => parseProjectEnvelope(envelope(), alternate));
    for (const revisionValue of [
        { ...revision, brief_fingerprint: "" }, { ...revision, preview: {} },
        { ...revision, number: 2 }, { ...revision, job_id: "../../unrelated" },
    ]) assert.throws(() => parseProjectEnvelope(envelope({ ...project, revisions: [revisionValue] }), identity));
    assert.throws(() => parseProjectEnvelope(envelope({ ...project, revisions: [revision, { ...revision, number: 2 }] }), identity));
});

test("project list requires actual saved projects and safe ids", () => {
    assert.deepEqual(parseProjectList({ ...identity, projects: [] }, identity), []);
    assert.throws(() => parseProjectList({ ...identity, projects: [{ name: "invented" }] }, identity));
    assert.throws(() => parseProjectList({ ...identity, projects: [{ project_id: "../escape", name: "x", revision_count: 1, latest_revision_id: revision.revision_id }] }, identity));
});

test("editing any exposed circuit choice invalidates the saved revision match", () => {
    assert.equal(sameBrief(brief, structuredClone(brief)), true);
    for (const change of [{ project_name: "Changed" }, { status_led_count: 0 }, { include_programming_header: false }, { sensors: [{ part_id: "BME280", address: 119 }] }]) {
        assert.equal(sameBrief(brief, { ...brief, ...change }), false);
    }
    assert.equal(sameBrief(brief, { ...brief, sensors: [{ part_id: "BME280", address: null }] }), true);
});

test("reopening a persisted run accepts its real state and rejects guessed job ids", () => {
    for (const status of ["queued", "running", "complete", "failed"]) {
        assert.equal(parseProjectStart({ ...identity, job_id: "123456789abc", status }, identity), "123456789abc");
    }
    assert.throws(() => parseProjectStart({ ...identity, job_id: "123456789abc", status: "success" }, identity));
    assert.throws(() => parseProjectStart({ ...identity, job_id: "bad", status: "complete" }, identity));
});

test("project writes fetch fresh identity and transmit the brief without inventing evidence", async () => {
    const requests = [];
    const fetcher = async (path, options) => {
        requests.push([path, options]);
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        return response(201, envelope());
    };
    const result = await projectRequest("/api/projects", { fetcher, method: "POST", data: { brief } });
    assert.equal(requests[0][0], "/api/health");
    assert.deepEqual(JSON.parse(requests[1][1].body), { ...identity, brief });
    assert.equal(requests[1][1].headers["X-Ohmni-Server-Instance"], identity.server_instance_id);
    assert.deepEqual(result.payload, envelope());
});

test("refusal and malformed server replies cannot turn into saved success", async () => {
    await assert.rejects(projectRequest("/api/projects", { identity, method: "POST", fetcher: async () => response(422, { error: "project_refused", refusal: { message: "Sensor is unsupported." } }) }), /Sensor is unsupported/);
    await assert.rejects(projectRequest("/api/projects", { identity, fetcher: async () => response(200, {}) }));
    await assert.rejects(projectRequest("/api/projects", { identity, fetcher: async () => response(200, { ...identity, server_instance_id: "f".repeat(16) }) }));
});

const exercise = { id: "sensor-rail", title: "Can you spot the power problem?", prompt: "The sensor's two supply pins, VDD and VDDIO, are connected to USB's 5 V rail. Which change should we check?", choices: [
    { id: "leave_5v", label: "Leave both sensor supplies on 5 V" },
    { id: "move_vdd", label: "Move only VDD to the 3.3 V rail" },
    { id: "move_both", label: "Move VDD and VDDIO to the 3.3 V rail" },
], limitation: "A teaching circuit, not a physical measurement." };
const check = { circuit_hash: "c".repeat(64), rule_id: "PB-PWR-001", outcome: "FAIL", findings: [{ severity: "error", title: "Supply outside range", description: "The circuit exceeds its supported range." }] };
const result = { choice: "move_both", correct: true, explanation: "Both connections now satisfy this rule.", before: check, after: { ...check, outcome: "PASS", findings: [] }, evidence: [{ source: "BME280 datasheet", page: 6, status: "catalog_reported", value: 3.6 }], limitation: exercise.limitation };

test("the challenge displays only a server supplied exercise and matching graded response", () => {
    assert.equal(parseExercise({ ...identity, exercise }, identity), exercise);
    assert.equal(parseExerciseResult({ ...identity, result }, identity, "move_both"), result);
    assert.throws(() => parseExerciseResult({ ...identity, result }, identity, "leave_5v"));
    for (const change of [{ correct: "true" }, { after: null }, { evidence: null }, { explanation: "" }]) {
        assert.throws(() => parseExerciseResult({ ...identity, result: { ...result, ...change } }, identity, "move_both"));
    }
    assert.throws(() => parseExercise({ ...identity, exercise: { ...exercise, choices: [exercise.choices[0], exercise.choices[0]] } }, identity));
});

test("catalog assumptions with no source citation remain visible without fabricating evidence", () => {
    const assumed = { ...result, evidence: [{ source: null, page: null, status: "ASSUMED", value: "VDD maximum: 3.6 V" }] };
    assert.equal(parseExerciseResult({ ...identity, result: assumed }, identity, "move_both"), assumed);
    assert.equal(assumed.evidence[0].source, null);
});

test("revision comparison describes only choices changed in the saved briefs", () => {
    assert.deepEqual(briefChanges(brief, { ...brief, status_led_count: 0, sensors: [{ part_id: "BME280", address: 119 }] }), [
        "Omitted the status LED and its resistor", "Changed the sensor address to 0x77",
    ]);
    assert.deepEqual(briefChanges(null, brief), ["First saved configuration"]);
    assert.equal(briefChanges(brief, structuredClone(brief)).length, 1);
});

function workbenchDom() {
    const nodes = new Map();
    const handlers = new Map();
    const node = (selector) => {
        if (!nodes.has(selector)) nodes.set(selector, {
            innerHTML: "", textContent: "", hidden: false, disabled: false,
            focus() {}, querySelectorAll: () => [],
        });
        return nodes.get(selector);
    };
    const root = { innerHTML: "", querySelector: node, querySelectorAll: () => [],
        addEventListener: (name, handler) => handlers.set(name, handler),
        removeEventListener: (name) => handlers.delete(name),
    };
    return { root, node, handlers };
}

test("a first run refreshes authoritative revision metadata and keeps its reopen action after revision selection", async () => {
    const dom = workbenchDom();
    let started = false;
    let projectReads = 0;
    const fetcher = async (path) => {
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        assert.equal(path, `/api/projects/${project.project_id}`);
        projectReads += 1;
        return response(200, envelope({ ...project, revisions: [{ ...revision, job_id: started ? "123456789abc" : null }] }));
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher, onRun: async (context) => {
        assert.equal(context.projectId, project.project_id);
        assert.equal(context.revisionId, revision.revision_id);
        started = true;
    } });
    await controller.openProject(project.project_id);
    assert.equal(dom.node("#project-run").textContent, "Generate my board");
    dom.handlers.get("click")({ target: { closest: (selector) => selector === "#project-run" ? {} : null } });
    await new Promise(setImmediate);
    assert.equal(projectReads, 2, "the run action reloads the saved project from the server");
    assert.equal(dom.node("#project-run").textContent, "Open this revision's run");
    dom.handlers.get("change")({ target: { id: "project-revision", value: revision.revision_id } });
    assert.equal(dom.node("#project-run").textContent, "Open this revision's run");
    assert.equal(dom.node("#project-run").disabled, false);
    assert.equal(revision.job_id, null, "the original immutable revision object was not patched with guessed metadata");
    controller.dispose();
});
