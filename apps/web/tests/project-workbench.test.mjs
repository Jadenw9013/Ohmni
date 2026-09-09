import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { defaultProjectBrief, supportedBrief, parseProjectOptions, briefFitsOptions, parseProjectEnvelope, parseProjectList, parseProjectStart, sameBrief, projectRequest, briefChanges } from "../project-contract.js";
import { parseExercise, parseExerciseResult, mountProjectWorkbench, switchFamilyDraft } from "../project-workbench.js";
import { requirementResultsHtml } from "../view-model.js";

const identity = { api_version: 2, server_instance_id: "0123456789abcdef", ui_version: "a".repeat(64) };
const stamp = "2026-09-08T18:00:00+00:00";
const brief = defaultProjectBrief();
const preview = { project_name: brief.project_name, request: "sensor", asked_for: [], assumed: [], needs_clarification: [] };
const revision = { revision_id: "1".repeat(16), number: 1, created_at: stamp, brief, brief_fingerprint: "b".repeat(64), preview, job_id: null };
const project = { project_id: "2".repeat(16), created_at: stamp, updated_at: stamp, revisions: [revision] };
const envelope = (projectValue = project) => ({ ...identity, project: projectValue });
const response = (status, payload) => ({ ok: status >= 200 && status < 300, status, json: async () => payload });
// Captured from the authoritative project_options() Python projection.
const options = JSON.parse(readFileSync(new URL("./fixtures/project-options.json", import.meta.url), "utf8"));

test("all offered family defaults and legacy sensor briefs have an editable transport", () => {
    assert.equal(supportedBrief(brief), true);
    assert.equal(supportedBrief({ ...brief, sensors: [{ part_id: "BME280", address: null }] }), true);
    for (const family of options.families) {
        assert.equal(supportedBrief(family.defaults), true);
        assert.equal(briefFitsOptions(family.defaults, options), true);
    }
    assert.equal(supportedBrief({ ...brief, input_voltage_v: 4.8 }), true);
    for (const change of [
        { archetype: "unsupported" }, { status_led_count: "1" }, { button_count: -1 },
        { input_voltage_v: 12 }, { sensors: [{ part_id: "BME280", address: 256 }] },
        { include_programming_header: "false" }, { project_name: " " },
    ]) assert.equal(supportedBrief({ ...brief, ...change }), false);
    for (const change of [{ sensors: [{ part_id: "UNKNOWN_SENSOR", address: 118 }] },
        { status_led_count: 3 }, { sensors: [{ part_id: "BME280", address: 99 }] }]) {
        assert.equal(briefFitsOptions({ ...brief, ...change }, options), false);
    }
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
    assert.equal(sameBrief(brief, { ...brief, sensors: [{ part_id: "BME280", address: null }] }), false,
        "automatic allocation and an explicit address are different saved requests");
    assert.equal(sameBrief(brief, { ...brief, button_count: 0, spi_devices: [] }), true,
        "legacy omitted optional slots match their schema defaults");
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
        "Status lights: 1 → 0", "Sensors: BME280 (0x77)",
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
            replaceWith(replacement) { nodes.set(selector, replacement); },
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
        if (path === "/api/project-options") return response(200, { ...identity, options });
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

test("the exact server options contract rejects malformed, duplicate, stale, and unknown slot defaults", () => {
    assert.equal(parseProjectOptions({ ...identity, options }, identity), options);
    for (const mutate of [
        (value) => { value.families[1] = value.families[0]; },
        (value) => { value.families[0].sensor_count.max = -1; },
        (value) => { value.families[0].sensor_slot_defaults[2].part_id = "invented"; },
        (value) => { value.sensors[0].addresses = [118, 118]; },
        (value) => { value.families[2].defaults.spi_devices = []; },
    ]) {
        const changed = structuredClone(options); mutate(changed);
        assert.throws(() => parseProjectOptions({ ...identity, options: changed }, identity));
    }
    assert.throws(() => parseProjectOptions({ ...identity, options }, { ...identity, ui_version: "f".repeat(64) }));
});

test("full brief comparison preserves hidden preferences and every composed slot", () => {
    for (const update of [
        { description: "A different purpose" }, { input_voltage_v: 4.8 }, { budget_usd: null },
        { hand_solderable_preferred: false }, { button_count: 2 },
        { spi_devices: [{ part_id: "25LC256-I/SN" }] },
        { sensors: [...brief.sensors, { part_id: "TMP102AIDRLR", address: null }] },
    ]) {
        assert.equal(sameBrief(brief, { ...brief, ...update }), false);
        assert.notDeepEqual(briefChanges(brief, { ...brief, ...update }), ["The complete configuration matches the previous revision"]);
    }
});

test("family switching keeps each family's features and retains personal hidden requirements", () => {
    const saved = { ...brief, project_name: "My experiment", description: "Keep this purpose", input_voltage_v: 4.8,
        budget_usd: null, hand_solderable_preferred: false, sensors: [{ part_id: "TMP102AIDRLR", address: 73 }] };
    const drafts = new Map();
    const controller = switchFamilyDraft(saved, "a2_usb_gpio_controller", options, drafts);
    assert.equal(controller.sensors.length, 0);
    assert.equal(controller.button_count, 1);
    assert.equal(controller.project_name, saved.project_name);
    assert.equal(controller.description, saved.description);
    assert.equal(controller.input_voltage_v, 4.8);
    controller.status_led_count = 4;
    const restored = switchFamilyDraft(controller, saved.archetype, options, drafts);
    assert.deepEqual(restored.sensors, saved.sensors);
    assert.equal(restored.budget_usd, null);
    assert.equal(restored.hand_solderable_preferred, false);
    assert.equal(switchFamilyDraft(restored, controller.archetype, options, drafts).status_led_count, 4);
    assert.equal(saved.status_led_count, 1);
});

const tick = () => new Promise(setImmediate);
const formInput = (dom, values) => dom.handlers.get("input")({ target: { dataset: {},
    closest: (selector) => selector === "#project-form" ? {} : null, ...values } });

// A small DOM-lifetime harness: replacing the editor detaches its exercise
// subtree, and replaceWith moves that exact subtree back. Unlike the simple
// fixture above, clones contain different form controls and expose stale refs.
function workbenchExerciseDom() {
    const dom = workbenchDom();
    const genericQuery = dom.root.querySelector;
    let currentExercise = null;
    let markup = "";
    const makeExercise = (initial) => {
        let html = initial;
        const children = new Map();
        const container = {
            children,
            get innerHTML() { return html; },
            set innerHTML(value) {
                html = value; children.clear();
                if (value.includes('id="sensor-choice-form"')) {
                    const controls = Array.from({ length: 4 }, () => ({ disabled: false }));
                    children.set("#sensor-choice-form", { querySelectorAll: () => controls });
                    children.set("#sensor-prediction", { value: "" });
                    children.set("#sensor-result", { innerHTML: "" });
                    children.set("input[name=repair]:checked", { value: "move_both" });
                }
            },
            replaceWith(replacement) { currentExercise = replacement; },
            cloneNode() {
                const clone = makeExercise(html);
                const original = children.get("#sensor-choice-form")?.querySelectorAll();
                clone.children.get("#sensor-choice-form")?.querySelectorAll().forEach((input, i) => { input.disabled = original[i].disabled; });
                if (children.has("#sensor-prediction")) clone.children.get("#sensor-prediction").value = children.get("#sensor-prediction").value;
                return clone;
            },
        };
        container.innerHTML = initial;
        return container;
    };
    Object.defineProperty(dom.root, "innerHTML", {
        get() { return markup; },
        set(value) {
            markup = value;
            currentExercise = makeExercise(value.slice(value.indexOf('<div id="sensor-exercise"')));
        },
    });
    dom.root.querySelector = (selector) => selector === "#sensor-exercise" ? currentExercise
        : ["#sensor-choice-form", "#sensor-prediction", "#sensor-result", "input[name=repair]:checked"].includes(selector)
            ? currentExercise?.children.get(selector) || null : genericQuery(selector);
    return { ...dom, node: dom.root.querySelector };
}

const workbenchClick = (dom, selector) => dom.handlers.get("click")({ target: { closest: (value) => value === selector ? {} : null } });
const submitRepair = (dom) => dom.handlers.get("submit")({ target: { id: "sensor-choice-form" }, preventDefault() {} });

test("an in-flight repair keeps its actual form and reflection through family and count redraws", async () => {
    const dom = workbenchExerciseDom();
    let finishRepair;
    const pending = new Promise((resolve) => { finishRepair = resolve; });
    const fetcher = async (path, request) => {
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return response(200, { ...identity, options });
        if (path === "/api/exercises/sensor-rail") return request.method === "POST" ? pending : response(200, { ...identity, exercise });
        return response(200, envelope());
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openProject(project.project_id);
    workbenchClick(dom, "[data-load-exercise]"); await tick();
    const container = dom.node("#sensor-exercise");
    const form = dom.node("#sensor-choice-form");
    dom.node("#sensor-prediction").value = "Both supply pins matter.";
    submitRepair(dom); await tick();
    assert.ok(form.querySelectorAll().every((control) => control.disabled));
    formInput(dom, { name: "family", value: "a3_usb_spi_peripheral" });
    formInput(dom, { id: "project-memory-count", value: "2" });
    assert.equal(dom.node("#sensor-exercise"), container);
    assert.equal(dom.node("#sensor-choice-form"), form);
    assert.equal(dom.node("#sensor-prediction").value, "Both supply pins matter.");
    finishRepair(response(200, { ...identity, result })); await tick();
    assert.ok(form.querySelectorAll().every((control) => !control.disabled));
    assert.match(dom.node("#sensor-result").innerHTML, /Both connections now satisfy this rule/);
    controller.dispose();
});

for (const stage of ["loading", "grading"]) for (const transition of ["new project", "open project", "select revision"]) {
    test(`${transition} resets a ${stage} challenge and ignores its late response`, async () => {
        const dom = workbenchExerciseDom();
        let finish;
        let delay = true;
        const pending = new Promise((resolve) => { finish = resolve; });
        const fetcher = async (path, request) => {
            if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
            if (path === "/api/project-options") return response(200, { ...identity, options });
            if (path === "/api/exercises/sensor-rail") {
                if (delay && (stage === "loading" || request.method === "POST")) return pending;
                return response(200, { ...identity, exercise });
            }
            return response(200, envelope());
        };
        const controller = mountProjectWorkbench(dom.root, { fetcher });
        await controller.openProject(project.project_id);
        workbenchClick(dom, "[data-load-exercise]"); await tick();
        if (stage === "grading") { submitRepair(dom); await tick(); }
        if (transition === "new project") await controller.openNew();
        else if (transition === "open project") await controller.openProject(project.project_id);
        else dom.handlers.get("change")({ target: { id: "project-revision", value: revision.revision_id } });
        assert.match(dom.node("#sensor-exercise").innerHTML, /challenge has been reset.*data-load-exercise/s);
        assert.equal(dom.node("#sensor-choice-form"), null);
        finish(response(200, { ...identity, ...(stage === "loading" ? { exercise } : { result }) })); await tick();
        assert.match(dom.node("#sensor-exercise").innerHTML, /challenge has been reset/);
        assert.equal(dom.node("#sensor-result"), null, "an old response cannot publish in the reset challenge");
        delay = false;
        workbenchClick(dom, "[data-load-exercise]"); await tick();
        assert.ok(dom.node("#sensor-choice-form").querySelectorAll().every((control) => !control.disabled));
        controller.dispose();
    });
}

test("editor transitions invalidate a prior run immediately and save all hidden and restored sensor choices", async () => {
    const dom = workbenchDom();
    const custom = { ...brief, project_name: "My desk", description: "A purpose to retain", budget_usd: null,
        input_voltage_v: 4.8, hand_solderable_preferred: false };
    let live = { ...project, revisions: [{ ...revision, brief: custom, job_id: "123456789abc" }] };
    const writes = [];
    let invalidated = 0;
    const fetcher = async (path, request) => {
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return response(200, { ...identity, options });
        if (request.method === "POST") {
            const saved = JSON.parse(request.body).brief; writes.push(saved);
            live = { ...live, revisions: [...live.revisions, { ...revision, number: live.revisions.length + 1,
                revision_id: String(live.revisions.length + 2).repeat(16), brief: saved, job_id: null }] };
        }
        return response(200, envelope(live));
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher, onInvalidate: () => { invalidated += 1; } });
    await controller.openProject(project.project_id);
    assert.equal(dom.node("#project-run").disabled, false);
    const before = invalidated;
    formInput(dom, { id: "project-sensor-count", value: "3" });
    assert.equal(invalidated, before + 1);
    assert.equal(dom.node("#project-run").disabled, true);
    formInput(dom, { id: "project-address-1", dataset: { sensorAddress: "1" }, value: "73" });
    formInput(dom, { id: "project-sensor-count", value: "1" });
    formInput(dom, { id: "project-sensor-count", value: "3" });
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await tick();
    assert.equal(writes.length, 1);
    assert.deepEqual(writes[0].sensors, [custom.sensors[0], { part_id: "TMP102AIDRLR", address: 73 }, { part_id: "TMP102AIDRLR", address: null }]);
    for (const field of ["description", "budget_usd", "input_voltage_v", "hand_solderable_preferred"]) assert.equal(writes[0][field], custom[field]);
    assert.equal(dom.node("#project-run").disabled, false);
    assert.equal(live.revisions[0].brief.sensors.length, 1);
    controller.dispose();
});

test("address conflicts reach the server and cannot become a saved result in the browser", async () => {
    const dom = workbenchDom(); let writes = 0;
    const fetcher = async (path, request) => {
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return response(200, { ...identity, options });
        if (request.method === "POST") { writes += 1; return response(422, { error: "project_refused", refusal: { message: "Both sensors request the same address." } }); }
        return response(200, envelope());
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openProject(project.project_id);
    formInput(dom, { id: "project-sensor-count", value: "2" });
    formInput(dom, { id: "project-sensor-1", dataset: { sensorPart: "1" }, value: "BME280" });
    formInput(dom, { id: "project-address-1", dataset: { sensorAddress: "1" }, value: "118" });
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await tick();
    assert.equal(writes, 1, "the browser does not grade address compatibility");
    assert.match(dom.node("#project-error").textContent, /same address/);
    assert.equal(dom.node("#project-run").disabled, true);
    assert.equal(dom.node("#project-save-state").textContent, "Unsaved changes");
    controller.dispose();
});

test("options failure leaves saving disabled instead of silently offering invented defaults", async () => {
    const dom = workbenchDom();
    const controller = mountProjectWorkbench(dom.root, { fetcher: async (path) => path === "/api/health"
        ? response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" }) : response(200, {}) });
    await tick();
    assert.equal(dom.node("#project-save").disabled, true);
    assert.equal(dom.node("#project-run").disabled, true);
    assert.equal(dom.node("#project-error").hidden, false);
    controller.dispose();
});

test("retrying missing choices resumes the intended saved project instead of creating a new draft", async () => {
    const dom = workbenchDom();
    let available = false;
    let projectReads = 0;
    const fetcher = async (path) => {
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return available ? response(200, { ...identity, options }) : response(503, {});
        assert.equal(path, `/api/projects/${project.project_id}`);
        projectReads += 1;
        return response(200, envelope());
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openProject(project.project_id);
    assert.equal(projectReads, 0);
    assert.equal(dom.node("#project-save").disabled, true);
    available = true;
    dom.handlers.get("click")({ target: { closest: (selector) => selector === "[data-load-options]" ? {} : null } });
    await tick();
    assert.equal(projectReads, 1);
    assert.equal(dom.node("#project-save-state").textContent, "Revision 1 saved");
    assert.equal(dom.node("#project-run").disabled, false);
    assert.ok(dom.root.innerHTML.indexOf('id="project-run"') < dom.root.innerHTML.indexOf('id="project-preview"'),
        "the next action stays above a saved brief of any length");
    controller.dispose();
});

test("a saved-project fetch failure has a direct retry and cannot be accidentally saved as a new project", async () => {
    const dom = workbenchDom();
    let available = false;
    let writes = 0;
    const fetcher = async (path, request) => {
        if (request.method === "POST") writes += 1;
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return response(200, { ...identity, options });
        return available ? response(200, envelope()) : response(503, {});
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openProject(project.project_id);
    assert.equal(dom.node("#project-load-retry").hidden, false);
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await tick();
    assert.equal(writes, 0);
    available = true;
    dom.handlers.get("click")({ target: { closest: (selector) => selector === "[data-load-project]" ? {} : null } });
    await tick();
    assert.equal(dom.node("#project-save-state").textContent, "Revision 1 saved");
    assert.equal(dom.node("#project-load-retry").hidden, true);
    controller.dispose();
});

test("an empty project purpose gets specific guidance without losing other saved choices", async () => {
    const dom = workbenchDom();
    let writes = 0;
    const fetcher = async (path, request) => {
        if (request.method === "POST") writes += 1;
        if (path === "/api/health") return response(200, { ...identity, status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return response(200, { ...identity, options });
        return response(200, envelope());
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openProject(project.project_id);
    formInput(dom, { id: "project-description", value: "" });
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await tick();
    assert.equal(writes, 0);
    assert.match(dom.node("#project-error").textContent, /project purpose under Additional saved requirements/);
    assert.equal(dom.node("#project-run").disabled, true);
    controller.dispose();
});

test("per-choice result rendering copies server statuses and never invents missing verdicts", () => {
    const rows = [
        { field: "sensor_count", value: "3", status: "MET", detail: "Three selected sensors are present.", rule_ids: ["PB-I2C-001"] },
        { field: "firmware", value: "Not supplied", status: "UNKNOWN", detail: "Runtime behavior needs testing.", rule_ids: [] },
        { field: "description", value: "<script>alert(1)</script>", status: "VIOLATED", detail: "A recorded refusal.", rule_ids: [] },
    ];
    const html = requirementResultsHtml(rows);
    assert.match(html, /Met/); assert.match(html, /Unknown/); assert.match(html, /Violated/);
    assert.match(html, /PB-I2C-001/); assert.match(html, /&lt;script&gt;/);
    assert.equal(requirementResultsHtml([{ ...rows[0], status: undefined }]), null);
    assert.equal(requirementResultsHtml([{ ...rows[0], status: "PASS" }]), null);
    assert.equal(requirementResultsHtml([{ ...rows[0], status: ["MET"] }]), null);
    assert.equal(requirementResultsHtml([{ ...rows[0], status: { value: "MET" } }]), null);
    assert.equal(requirementResultsHtml([]), null);
});

test("readable result values and authored assumptions retain their exact server statuses", () => {
    const rows = [
        { field: "assumption", value: "internal", display_value: "Firmware still needed", origin: "assumption",
            status: "UNKNOWN", detail: "No firmware was supplied.", rule_ids: [] },
        { field: "input_voltage_v", value: "5.0", display_value: "5 V", origin: "explicit",
            status: "MET", detail: "Static range check only.", rule_ids: ["PB-PWR-001"] },
        { field: "description", value: "raw", display_value: "<img src=x>", origin: "explicit",
            status: "UNKNOWN", detail: "Retained user text.", rule_ids: [] },
    ];
    const html = requirementResultsHtml(rows);
    assert.match(html, /Input supply: 5 V/);
    assert.doesNotMatch(html, /Input supply: 5\.0/);
    assert.match(html, /&lt;img src=x&gt;/);
    assert.match(html, /<details class="requirement-assumptions"><summary>Assumptions and limits \(1\)<\/summary>.*Firmware still needed.*Unknown/s);
    assert.ok(html.indexOf("Input supply: 5 V") < html.indexOf("Assumptions and limits"));
    assert.equal(requirementResultsHtml([{ ...rows[0], display_value: {} }]), null);
});
