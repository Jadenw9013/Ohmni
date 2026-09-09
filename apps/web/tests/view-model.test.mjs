import assert from "node:assert/strict";
import test from "node:test";

import { artifactCurrent, badge, money, releaseReadiness, tone } from "../view-model.js";

const FIXTURE_ID = "esp32-bme280-environmental-logger";
const INSTANCE = "0123456789abcdef";
const OTHER_INSTANCE = "fedcba9876543210";
const UI_VERSION = "a".repeat(64);
const OTHER_UI_VERSION = "b".repeat(64);
const JOB_ID = "012345abcdef";

const response = (status, payload) => ({ ok: status >= 200 && status < 300, status, json: async () => payload });
const health = (values = {}) => ({ status: "ready", fixture_id: FIXTURE_ID, api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION, ...values });
const identity = { api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION };
const briefEnvelope = (values = {}) => ({ brief: brief(), api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION, ...values });
const startEnvelope = (values = {}) => ({ job_id: JOB_ID, status: "queued", api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION, ...values });
const jobEnvelope = (values = {}) => ({ job_id: JOB_ID, status: "running", progress: [], report: null, error: null, error_code: null, api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION, ...values });

const brief = () => ({
    project_name: "ESP32 environmental logger",
    request: "SECRET request text",
    asked_for: [{ field: "budget_usd", label: "Budget", value: "about $20", origin: "explicit", grounding: "quoted", source_text: "SECRET request text" }],
    assumed: [{ field: "assumption", label: "Ohmni assumed", value: "USB-C is a 5 V sink", origin: "assumption", grounding: "assumption", source_text: null }],
    needs_clarification: [{ field: "target_logic_voltage", label: "Voltage the chips run at", value: "3.3 V", origin: "explicit", grounding: "interpreted", source_text: "SECRET request text" }],
});

const term = (human, technical, detail = null) => ({ human, technical, detail });

// A minimal completed report. Only the shape app.js reads, with statuses that
// must survive rendering unchanged.
const experience = () => ({
    headline: "ESP32 environmental logger",
    subhead: "19 parts on a 100 x 70 mm board",
    brief: brief(),
    stages: [{ stage: "check", label: "Checking the electrical design", detail: "d", status: "FOUND_PROBLEM", outcome: "8 blocking problem(s)" }],
    systems: [{ system: "power", label: "Power", summary: "s", component_refs: ["J1", "U2"], anchor_refs: ["J1", "U2"] }],
    grouping: [{ component_ref: "U2", part_id: "AP2112K-3.3TRG1", system: "power", anchor: true, attached_to: null, basis: "regulator" }],
    flows: [{ flow_id: "power", label: "Power", question: "Where does it go?", summary: "sum", basis: "declared external source", net_names: ["VBUS"], component_refs: ["J1"], stages: [{ title: "Power arrives", detail: "d", net_names: ["VBUS"], component_refs: ["J1"], pin_labels: [] }] }],
    board: {
        artifact_fingerprint: "f".repeat(64), routing_plan_fingerprint: "e".repeat(64), constraints_hash: "d".repeat(64),
        width_mm: 100, height_mm: 70, layer_count: 2, display_thickness_mm: 1.6, thickness_is_display_only: true,
        thickness_note: "Board thickness is a display value. Ohmni does not model the layer stack-up.",
        layers: ["F.Cu", "B.Cu"], net_names: ["VBUS"], tracks: [], vias: [],
        components: [{ ref: "U2", part_id: "AP2112K-3.3TRG1", name: term("3.3 V voltage regulator", "AP2112K-3.3TRG1 U2"), package: "SOT-23-5", footprint_id: "fp", system: "power", x_mm: 20, y_mm: 58, rotation_deg: 0, side: "F.Cu", width_mm: 3, height_mm: 3.2, placement_reason: "near power input", pads: [], net_names: ["VBUS"] }],
    },
    schematic: { artifact_fingerprint: "c".repeat(64), connection_method: "global_labels", net_names: ["VBUS"], symbols: [{ ref: "U2", part_id: "AP2112K-3.3TRG1", name: term("3.3 V voltage regulator", "AP2112K-3.3TRG1 U2"), system: "power", x_mm: 10, y_mm: 10, width_mm: 20, height_mm: 12, pins: [{ pin: "1", net_name: "VBUS", x_mm: 10, y_mm: 14 }] }] },
    components: [{ ref: "U2", part_id: "AP2112K-3.3TRG1", name: term("3.3 V voltage regulator", "AP2112K-3.3TRG1 U2", "600 mA LDO"), display_name: "AP2112K", package: "SOT-23-5", system: "power", purpose: "Turns the incoming supply into a steady lower voltage.", grouping_basis: "regulator", quantity_on_board: 1, line_quantity: 1, value: null, assembly_difficulty: "moderate", assembly_reason: "Small surface-mount package. Fiddly by hand but doable.", assembly_basis: "Assembly difficulty is an Ohmni estimate from the package shape, not a manufacturer figure.", orientation_sensitive: false, price_knowledge: "UNKNOWN", unit_price: null, evidence_status: "catalog_reported" }],
    checks: [],
    check_sections: [
        { family: "ohmni", label: "Ohmni's own checks", summary: "Rules Ohmni ran.", groups: [{ group: "electrical", family: "ohmni", label: "Voltages and currents", question: "q", status: "VERIFIED", rule_count: 1, rules: [{ rule_id: "PB-PWR-001", title: "Supply rail in range", outcome: "PASS", findings: 0, limitations: ["placement is not checked"], missing_data: [] }] }] },
        { family: "external", label: "Checked independently by KiCad", summary: "Other software.", groups: [{ group: "kicad_erc", family: "external", label: "Schematic connection check", question: "q", status: "PASS_WITH_WARNINGS", rule_count: 1, rules: [{ rule_id: "KICAD-ERC", title: "KiCad electrical rule check (ERC)", outcome: "PASS_WITH_WARNINGS", findings: 21, limitations: [], missing_data: [] }] }] },
        { family: "not_analysed", label: "Not analysed", summary: "No rules exist.", groups: [{ group: "simulation", family: "not_analysed", label: "Simulation", question: "q", status: "UNSUPPORTED", rule_count: 0, rules: [] }] },
    ],
    bring_up: [
        { action: "Measure the 3.3 V power.", prediction: "3.3 V", basis: "Derived from the regulator datasheet.", rule_id: null },
        { action: "Power it from a current-limited bench supply.", prediction: null, basis: "Ohmni has no start-up current figure.", rule_id: null },
    ],
    repair: { happened: false, headline: "Ohmni found nothing that needed fixing.", plain_summary: null, part: null, from_net: null, to_net: null, operating_min_v: null, steps: [], moved_pins: [], evidence: [] },
    confidence: {
        checked: [{ label: "The electrical design", status: "CHECKED", detail: "24 rules" }],
        not_verified: [{ label: "Does it actually work?", status: "NOT_YET_VERIFIED", detail: "No physical board has been built." }],
    },
    tour: { narration_source: "deterministic_projection_not_a_language_model", steps: [{ step_id: "overview", title: "What you built", narration: "n", focus: "board", system: null, flow_id: null, component_refs: [], net_names: [], facts: ["board 100 x 70 mm"] }] },
});

const completedReport = () => ({
    experience: experience(),
    release: { status: "READY_FOR_MANUFACTURING_REVIEW", current: true, package_fingerprint: "9".repeat(64), files: [{ relative_path: "golden-F_Cu.gtl", sha256: "1".repeat(64), size_bytes: 10, kind: "F.Cu" }] },
    economics: { known_consumption_cost: "5.68", known_purchase_requirement: "23.00", fabrication: "UNKNOWN", shipping: "UNKNOWN", pricing_source: "SYNTHETIC FIXTURE - NOT LIVE SUPPLIER DATA" },
});

// ── fake DOM ────────────────────────────────────────────────────────────

function createNode(selector) {
    const node = {
        selector, innerHTML: "", textContent: "", hidden: false, disabled: false, value: "",
        style: {}, dataset: {}, children: [], attributes: {},
        setAttribute(name, value) { this.attributes[name] = value; },
        getAttribute(name) { return this.attributes[name] ?? null; },
        removeAttribute(name) { delete this.attributes[name]; },
        focus() { this.focused = true; },
        classList: {
            set: new Set(),
            add(name) { this.set.add(name); },
            remove(name) { this.set.delete(name); },
            contains(name) { return this.set.has(name); },
            toggle(name, force) { const on = force === undefined ? !this.set.has(name) : force; if (on) this.set.add(name); else this.set.delete(name); return on; },
        },
        listeners: {},
        addEventListener(type, handler) { this.listeners[type] = handler; },
        removeEventListener(type) { delete this.listeners[type]; },
        scrollIntoView(options) { node.scrollCalls.push(options); },
        scrollCalls: [],
        querySelector: () => null,
        closest: () => null,
        clientWidth: 520, clientHeight: 260,
        // A canvas whose 2D context is unavailable, so the board view takes its
        // declared no-canvas path and no rendering happens under test.
        getContext: () => null,
    };
    return node;
}

function createDom() {
    const nodes = new Map();
    const windowHandlers = {};
    const documentHandlers = {};
    const get = (selector) => {
        if (!nodes.has(selector)) nodes.set(selector, createNode(selector));
        return nodes.get(selector);
    };
    const groups = new Map();
    const group = (selector, values, field) => {
        const items = values.map((value) => {
            const node = get(`${selector}:${value}`);
            node.dataset[field] = value;
            return node;
        });
        groups.set(selector, items);
        return items;
    };
    group('[data-navigate]', ["describe", "agree", "design", "review", "build"], "navigate");
    group('[data-panel]', ["board", "learn", "checks"], "panel");
    group('[data-result-panel]', ["board", "learn", "checks"], "resultPanel");
    const downloads = group('[data-artifact-download]', ["schematic", "board"], "artifactDownload");
    for (const link of downloads) {
        link.dataset.current = "true";
        link.dataset.downloadUrl = `/api/artifacts/${JOB_ID}/golden.kicad_${link.dataset.artifactDownload === "board" ? "pcb" : "sch"}`;
    }
    const document = {
        hidden: false,
        querySelector: get,
        querySelectorAll: (selector) => groups.get(selector) || [],
        getElementById: (id) => get(`#${id}`),
        addEventListener: (type, handler) => { documentHandlers[type] = handler; },
        removeEventListener: (type, handler) => { if (documentHandlers[type] === handler) delete documentHandlers[type]; },
    };
    const window = {
        addEventListener: (type, handler) => { windowHandlers[type] = handler; },
        removeEventListener: (type, handler) => { if (windowHandlers[type] === handler) delete windowHandlers[type]; },
    };
    return { document, window, get, nodes, groups, windowHandlers, documentHandlers };
}

let importSequence = 0;
async function withApp(run) {
    const originals = {
        document: globalThis.document, window: globalThis.window, fetch: globalThis.fetch,
        matchMedia: globalThis.matchMedia, CSS: globalThis.CSS,
    };
    const dom = createDom();
    globalThis.document = dom.document;
    globalThis.window = dom.window;
    // Reduced motion is the deterministic path: no timers start under test.
    globalThis.matchMedia = () => ({ matches: true });
    globalThis.CSS = { escape: (value) => value };
    const app = await import(`../app.js?frontend-regression=${++importSequence}`);
    try { return await run(app, dom); } finally {
        app.stopCompletionMonitor();
        for (const [key, value] of Object.entries(originals)) {
            if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
        }
    }
}

// ── pure view-model ─────────────────────────────────────────────────────

test("truthful status tones remain distinct", () => {
    assert.equal(tone("PASS"), "pass");
    assert.equal(tone("VERIFIED"), "pass");
    assert.equal(tone("PASS_WITH_WARNINGS"), "warn");
    assert.equal(tone("PARTIALLY_VERIFIED"), "warn");
    assert.equal(tone("NOT_VERIFIED"), "fail");
    assert.equal(tone("FAIL"), "fail");
    assert.equal(tone("UNKNOWN"), "warn");
    assert.equal(tone("NOT_YET_VERIFIED"), "notyet");
    assert.equal(tone("UNSUPPORTED"), "notyet");
});

test("unknown money never renders as zero", () => {
    assert.equal(money(null, "UNKNOWN"), "UNKNOWN");
    assert.equal(money("0", "KNOWN"), "$0.00");
});

test("artifact freshness is explicit", () => {
    assert.equal(artifactCurrent({ current: true }), "CURRENT");
    assert.equal(artifactCurrent({ current: false }), "STALE");
});

test("badges escape untrusted labels", () => {
    assert.match(badge("<script>"), /&lt;script&gt;/);
});

test("release readiness stays truthful about staleness", () => {
    assert.deepEqual(releaseReadiness({ status: "READY_FOR_MANUFACTURING_REVIEW", current: true }),
        { status: "READY_FOR_MANUFACTURING_REVIEW", label: "Ready for manufacturing review" });
    assert.deepEqual(releaseReadiness({ status: "READY_FOR_MANUFACTURING_REVIEW", current: false }),
        { status: "STALE", label: "Release is stale or not ready" });
});

// ── envelope parsing ────────────────────────────────────────────────────

test("polling dispositions are exhaustive and fail closed", async () => withApp(async (app) => {
    assert.deepEqual(["queued", "running", "complete", "failed", "paused"].map(app.pollDisposition),
        ["continue", "continue", "complete", "failed", "invalid"]);
}));

test("health, brief, start and job envelopes are bound to one server generation", async () => withApp(async (app) => {
    assert.deepEqual(app.parseHealth(health()), identity);
    assert.throws(() => app.parseHealth(health({ fixture_id: "other" })), /fixture_rejected/);
    assert.throws(() => app.parseHealth(health({ api_version: 1 })), /api_ui_mismatch/);
    assert.throws(() => app.parseHealth({ ...health(), extra: 1 }), /api_ui_mismatch/);

    assert.equal(app.parseBrief(briefEnvelope(), identity).project_name, "ESP32 environmental logger");
    assert.throws(() => app.parseBrief(briefEnvelope({ server_instance_id: OTHER_INSTANCE }), identity), /generation_mismatch/);
    assert.throws(() => app.parseBrief(briefEnvelope({ ui_version: OTHER_UI_VERSION }), identity), /generation_mismatch/);
    assert.throws(() => app.parseBrief({ ...briefEnvelope(), brief: { asked_for: [] } }, identity), /api_ui_mismatch/);

    assert.equal(app.parseStart(startEnvelope(), identity), JOB_ID);
    assert.throws(() => app.parseStart(startEnvelope({ job_id: "nope" }), identity), /api_ui_mismatch/);
    assert.throws(() => app.parseStart(startEnvelope({ server_instance_id: OTHER_INSTANCE }), identity), /generation_mismatch/);

    assert.equal(app.parseJob(jobEnvelope(), JOB_ID, identity).status, "running");
    assert.throws(() => app.parseJob(jobEnvelope({ status: "running", report: {} }), JOB_ID, identity), /api_ui_mismatch/);
    assert.throws(() => app.parseJob(jobEnvelope({ status: "complete", report: {} }), JOB_ID, identity), /api_ui_mismatch/,
        "a completed job without an experience projection is rejected");
    assert.throws(() => app.parseJob(jobEnvelope({ status: "failed", report: null, error: "other", error_code: "pipeline_failed" }), JOB_ID, identity), /api_ui_mismatch/);
    assert.throws(() => app.parseJob(jobEnvelope({ status: "failed", error: "Demo pipeline failed", error_code: "made_up" }), JOB_ID, identity), /api_ui_mismatch/);
}));

// ── journey ─────────────────────────────────────────────────────────────

test("opening the brief performs health then a generation-bound brief request", async () => withApp(async (app, dom) => {
    const calls = [];
    globalThis.fetch = async (url, options) => {
        calls.push({ url, options });
        if (url === "/api/health") return response(200, health());
        if (url === "/api/brief") return response(200, briefEnvelope());
        throw new Error(`unexpected ${url}`);
    };
    await app.openBrief();
    assert.deepEqual(calls.map((call) => call.url), ["/api/health", "/api/brief"]);
    assert.deepEqual(JSON.parse(calls[1].options.body), {
        fixture_id: FIXTURE_ID, api_version: 2, server_instance_id: INSTANCE, ui_version: UI_VERSION,
    });
    const rendered = dom.get("#brief").innerHTML;
    assert.match(rendered, /Design choices/, "derived values lead the brief");
    assert.match(rendered, /Assumptions to know/);
    assert.match(rendered, /From the example brief/);
    assert.doesNotMatch(rendered, /your own words|what you wrote|go back and say so/);
    assert.match(dom.get("#agree-note").textContent, /2 design choices and assumptions/);
    assert.match(dom.get("#agree-note").textContent, /Editing this example is not available/);
    assert.equal(dom.get("#agree").hidden, false);
    assert.equal(dom.get("#describe").hidden, true);
}));

test("start failures map only allowlisted backend conditions to actionable copy", async () => {
    const cases = [
        [async () => { throw new Error("offline"); }, /demo backend is unavailable/],
        [async () => response(500, {}), /demo backend is unavailable/],
        [async () => response(409, { error: "server_instance_mismatch" }), /restarted or changed/],
        [async () => response(409, { error: "ui_version_mismatch" }), /restarted or changed/],
        [async () => response(400, { error: "fixture_rejected" }), /rejected the deterministic demo fixture/],
        [async () => response(503, { error: "brief_unavailable" }), /could not prepare the example brief/],
        [async () => response(418, { error: "not_in_the_allowlist" }), /does not match the running Ohmni demo server/],
    ];
    for (const [handler, expected] of cases) {
        await withApp(async (app, dom) => {
            globalThis.fetch = async (url) => (url === "/api/health" ? response(200, health()) : handler());
            await app.openBrief();
            assert.match(dom.get("#run-error").textContent, expected);
            assert.equal(dom.get("#run-error").hidden, false);
            assert.doesNotMatch(dom.get("#run-error").textContent, /SECRET|Traceback|Error:/);
        });
    }
});

test("confirming the brief starts a generation-bound job and polls it", async () => withApp(async (app, dom) => {
    const calls = [];
    globalThis.fetch = async (url, options) => {
        calls.push({ url, options });
        if (url === "/api/health") return response(200, health());
        if (url === "/api/brief") return response(200, briefEnvelope());
        if (url === "/api/demo") return response(202, startEnvelope());
        if (url === `/api/jobs/${JOB_ID}`) {
            return response(200, jobEnvelope({ progress: [{ stage: "routing", label: "Drawing the copper", status: "RUNNING", detail: "d", percent: 40 }] }));
        }
        throw new Error(`unexpected ${url}`);
    };
    await app.openBrief();
    const scheduled = [];
    await app.startRun({ pollDependencies: { schedule: (fn, delay) => scheduled.push(delay) } });
    const poll = calls.find((call) => call.url === `/api/jobs/${JOB_ID}`);
    assert.deepEqual(poll.options.headers, {
        "X-Ohmni-Server-Instance": INSTANCE, "X-Ohmni-API-Version": "2", "X-Ohmni-UI-Version": UI_VERSION,
    });
    assert.deepEqual(scheduled, [900], "an in-flight job schedules exactly one continuation");
    assert.equal(dom.get("#progress-percent").textContent, "40%");
    assert.equal(dom.get("#design").hidden, false);
}));

test("polling distinguishes restart, lost job, worker start, and pipeline failures", async () => {
    const cases = [
        [() => response(404, { error: "job_not_found" }), /no longer available/],
        [() => response(409, { error: "server_instance_mismatch" }), /restarted or changed/],
        [() => response(200, jobEnvelope({ status: "failed", error: "Demo pipeline failed", error_code: "worker_start_failed" })), /worker failed before progress began/],
        [() => response(200, jobEnvelope({ status: "failed", error: "Demo pipeline failed", error_code: "pipeline_failed" })), /engineering pipeline failed/],
    ];
    for (const [handler, expected] of cases) {
        await withApp(async (app, dom) => {
            globalThis.fetch = async () => handler();
            await app.poll(JOB_ID, identity, { schedule: () => { throw new Error("must not continue polling"); } });
            assert.match(dom.get("#run-error").textContent, expected);
        });
    }
});

test("a completed run renders settled stages with no running affordance", async () => withApp(async (app, dom) => {
    globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
    await app.poll(JOB_ID, identity, { monitorer: () => {} });
    const stages = dom.get("#stage-list").innerHTML;
    assert.match(stages, /Checking the electrical design/);
    assert.match(stages, /FOUND PROBLEM/);
    assert.doesNotMatch(stages, /RUNNING/, "a finished project shows no RUNNING status");
    assert.doesNotMatch(stages, /class="pending"/);
    assert.equal(dom.get("#progress-percent").textContent, "100%");
    assert.equal(dom.get("#progress-now").textContent, "Finished");
    assert.equal(dom.get("#review").hidden, false);
    assert.equal(dom.get("#build").hidden, true, "the completed board is the focused stage");
    assert.equal(dom.get("#design").hidden, true, "the stage record remains accessible through navigation");
}));

test("a completed run preserves unsupported and not-yet-verified statuses verbatim", async () => withApp(async (app, dom) => {
    globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
    await app.poll(JOB_ID, identity, { monitorer: () => {} });
    const confidence = dom.get("#confidence-panel").innerHTML;
    assert.match(confidence, /NOT YET VERIFIED/);
    assert.match(confidence, /No physical board has been built/);
    assert.match(dom.get("#checks").innerHTML, /UNSUPPORTED/);
    assert.match(dom.get("#checks").innerHTML, /Ohmni has no rules here/,
        "an unanalysed area explains itself rather than disappearing");
    assert.match(dom.get("#parts").innerHTML, /price UNKNOWN/, "an unknown price never becomes a number");
    assert.match(dom.get("#tour-panel").innerHTML, /deterministic_projection_not_a_language_model/,
        "the tour never claims to be a live model");
}));

test("the brief never claims the user wrote a value Ohmni worked out", async () => withApp(async (app, dom) => {
    app.renderBrief({
        project_name: "P", request: "make me a sensor",
        asked_for: [{ field: "budget_usd", label: "Budget", value: "about $20", origin: "explicit", grounding: "quoted" }],
        assumed: [{ field: "assumption", label: "Ohmni assumed", value: "USB-C is a 5 V sink", origin: "assumption", grounding: "assumption" }],
        needs_clarification: [{ field: "target_logic_voltage", label: "Voltage the chips run at", value: "3.3 V", origin: "explicit", grounding: "interpreted" }],
    });
    const html = dom.get("#brief").innerHTML;
    const quoted = html.slice(html.indexOf("brief-group asked"));
    const worked = html.slice(html.indexOf("brief-group unclear"), html.indexOf("brief-group assumed"));
    // The regression: an interpreted value shown under "straight from what you
    // wrote", beside an all-clear saying nothing needs confirming.
    assert.match(worked, /3\.3 V/, "an interpreted value goes where the user is asked to check it");
    assert.doesNotMatch(quoted, /3\.3 V/);
    assert.match(quoted, /about \$20/, "a value the user really wrote stays quoted");
    assert.doesNotMatch(html, /everything above came from what you wrote/i);
}));

test("an empty clarification column never contradicts the columns beside it", async () =>
    withApp(async (app, dom) => {
        app.renderBrief({
            project_name: "P", request: "r",
            asked_for: [{ field: "budget_usd", label: "Budget", value: "about $20", origin: "explicit", grounding: "quoted" }],
            assumed: [], needs_clarification: [],
        });
        assert.match(dom.get("#brief").innerHTML, /No additional choices were recorded/);
        assert.doesNotMatch(dom.get("#brief").innerHTML, /your own words|what you wrote/);
    }));

test("checks are grouped by who ran them, so verdicts cannot read as contradictions", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        const html = dom.get("#checks").innerHTML;
        const ohmni = html.indexOf("own checks");
        const external = html.indexOf("Checked independently by KiCad");
        const none = html.indexOf("Not analysed");
        assert.ok(ohmni >= 0 && external > ohmni && none > external, "three families, in order");
        // The regression: an empty Ohmni category labelled after the external
        // tool, sitting beside that tool's passing result.
        assert.doesNotMatch(html, /own opinion/);
        assert.doesNotMatch(html.slice(none), /KiCad/,
            "nothing in the unanalysed family is attributed to KiCad");
    }));

test("bench steps show only values Ohmni derived, and say so when it derived none", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        const html = dom.get("#bringup-panel").innerHTML;
        assert.match(html, /3\.3 V/);
        assert.match(html, /Ohmni has no prediction/,
            "a step with no derived value says so rather than inventing one");
        // The BLOCKER: engineering values hardcoded in the browser and
        // presented as things Ohmni worked out.
        assert.doesNotMatch(html, /4\.7 mA/,
            "predictions come from the projection, never from this file");
    }));

test("part cards lead with a readable name and keep the identifier disclosed", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        const html = dom.get("#parts").innerHTML;
        assert.match(html, /3\.3 V voltage regulator/, "the human name leads");
        assert.match(html, /AP2112K-3\.3TRG1/, "the identifier is still available");
        assert.doesNotMatch(html, /package-based deterministic classification/,
            "implementation language never reaches a part card");
        assert.match(html, /Small surface-mount package/, "difficulty is explained in words");
        assert.match(html, /Ohmni estimate/, "and is not passed off as a manufacturer figure");
    }));

test("system cards list named components that select on the board", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        const html = dom.get("#systems").innerHTML;
        assert.match(html, /part-pick/, "components are individually pickable");
        assert.match(html, /data-ref="U2"/);
        assert.match(html, /3\.3 V voltage regulator/, "listed by readable name");
        assert.match(html, /class="ident">U2/, "with the reference designator beside it");
    }));

test("selecting a component shows its purpose and discloses identifiers", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        app.renderSelection("U2");
        const html = dom.get("#selection").innerHTML;
        assert.match(html, /3\.3 V voltage regulator/);
        assert.match(html, /Turns the incoming supply/);
        const details = html.slice(html.indexOf("<details"));
        assert.match(details, /SOT-23-5/, "package is disclosed, not led with");
        assert.match(details, /near power input/, "and so is why it sits there");
    }));

test("the board view states that its thickness is a display value", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", progress: [], report: completedReport() }));
        await app.poll(JOB_ID, identity, { monitorer: () => {} });
        assert.match(dom.get("#board-thickness-note").textContent, /does not model the layer stack-up/,
            "the one non-derived geometric value is labelled where it is shown");
    }));

test("changed servers preserve the completed workspace but disable downloads and clean up monitoring", async () => {
    for (const payload of [health({ server_instance_id: OTHER_INSTANCE }), health({ ui_version: OTHER_UI_VERSION })]) {
        await withApp(async (app, dom) => {
            globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", report: completedReport() }));
            await app.poll(JOB_ID, identity, { monitorer: () => {} });
            globalThis.fetch = async () => response(200, payload);
            const cleared = [];
            const check = app.beginCompletionMonitor(identity, {
                setIntervalFn: () => 7, clearIntervalFn: (id) => cleared.push(id),
                windowTarget: dom.window, documentTarget: dom.document,
            });
            assert.equal(await check(), false);
            assert.equal(dom.get("#connection-banner").hidden, false);
            assert.match(dom.get("#connection-message").textContent, /earlier server/);
            assert.equal(dom.get("#review").hidden, false, "the previously completed result remains available to read");
            for (const link of dom.groups.get('[data-artifact-download]')) {
                assert.equal(link.getAttribute("href"), null);
                assert.equal(link.getAttribute("aria-disabled"), "true");
            }
            app.stopCompletionMonitor();
            assert.deepEqual(cleared, [7]);
            assert.deepEqual(Object.keys(dom.windowHandlers), []);
            assert.deepEqual(Object.keys(dom.documentHandlers), []);
        });
    }
});

test("a disconnected result stays readable and current downloads recover only with the same server", async () => withApp(async (app, dom) => {
    globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", report: completedReport() }));
    await app.poll(JOB_ID, identity, { monitorer: () => {} });
    let online = false;
    globalThis.fetch = async () => { if (!online) throw new Error("gone"); return response(200, health()); };
    const check = app.beginCompletionMonitor(identity, {
        setIntervalFn: () => 1, clearIntervalFn: () => {},
        windowTarget: dom.window, documentTarget: dom.document,
    });
    assert.equal(await check(), false);
    assert.match(dom.get("#connection-message").textContent, /Connection lost/);
    assert.equal(dom.get("#review").hidden, false);
    const [current, stale] = dom.groups.get('[data-artifact-download]');
    stale.dataset.current = "false";
    assert.equal(current.getAttribute("href"), null);
    online = true;
    assert.equal(await check(), true);
    assert.equal(dom.get("#connection-banner").hidden, true);
    assert.equal(current.getAttribute("href"), current.dataset.downloadUrl);
    assert.equal(stale.getAttribute("href"), null, "reconnecting never revives a stale artifact");
}));

test("navigation unlocks only available stages and shows one workspace at a time", async () => withApp(async (app, dom) => {
    assert.equal(app.navigate("review"), false);
    assert.equal(app.navigate("build"), false);
    globalThis.fetch = async (url) => response(200, url === "/api/health" ? health() : briefEnvelope());
    await app.openBrief();
    assert.equal(app.navigate("agree"), true);
    assert.equal(app.navigate("build"), false);
    globalThis.fetch = async () => response(200, jobEnvelope({ status: "complete", report: completedReport() }));
    await app.poll(JOB_ID, identity, { monitorer: () => {} });
    for (const stage of ["build", "design", "agree", "review", "describe"]) {
        assert.equal(app.navigate(stage), true);
        for (const other of ["describe", "agree", "design", "review", "build"]) {
            assert.equal(dom.get(`#${other}`).hidden, other !== stage);
        }
    }
}));

test("result tabs expose one panel and keep one keyboard tab stop", async () => withApp(async (app, dom) => {
    for (const panel of ["learn", "checks", "board"]) {
        assert.equal(app.selectResultPanel(panel), true);
        for (const tab of dom.groups.get('[data-panel]')) {
            const active = tab.dataset.panel === panel;
            assert.equal(tab.getAttribute("aria-selected"), String(active));
            assert.equal(tab.getAttribute("tabindex"), active ? "0" : "-1");
        }
        for (const section of dom.groups.get('[data-result-panel]')) {
            assert.equal(section.hidden, section.dataset.resultPanel !== panel);
        }
    }
    assert.equal(app.selectResultPanel("missing"), false);
}));

test("live progress shows the job's own explanation of the slow stage", async () =>
    withApp(async (app, dom) => {
        globalThis.fetch = async (url) => {
            if (url === "/api/health") return response(200, health());
            if (url === "/api/demo") return response(202, startEnvelope());
            return response(200, jobEnvelope({ progress: [{
                stage: "routing", label: "Drawing the copper connections", status: "RUNNING",
                detail: "This is the slow part. Copper paths replace what would be wires.",
                percent: 40,
            }] }));
        };
        await app.startRun({ pollDependencies: { schedule: () => {} } });
        assert.equal(dom.get("#progress-now").textContent, "Drawing the copper connections");
        assert.match(dom.get("#progress-detail").textContent, /slow part/,
            "the detail the job publishes is rendered, not discarded");
        assert.equal(dom.get("#progress-percent").textContent, "40%");
    }));

test("personal project runs use the saved revision endpoint and can reopen completed jobs", async () => withApp(async (app, dom) => {
    const calls = [];
    const fetcher = async (url, options) => {
        calls.push([url, options]);
        return response(202, startEnvelope({ status: "complete" }));
    };
    let polled;
    await app.startProjectRun({ projectId: "1".repeat(16), revisionId: "2".repeat(16), identity,
        preview: brief(), fetcher, poller: (id, generation) => { polled = { id, generation }; } });
    assert.equal(calls[0][0], `/api/projects/${"1".repeat(16)}/revisions/${"2".repeat(16)}/run`);
    assert.deepEqual(JSON.parse(calls[0][1].body), identity);
    assert.deepEqual(polled, { id: JOB_ID, generation: identity });
    assert.doesNotMatch(dom.get("#stage-list").innerHTML, /Fixing what it found/);
    assert.match(dom.get("#stage-list").innerHTML, /saved revision/);
}));

test("a persisted interrupted job is parsed as failed with no fabricated result", async () => withApp(async (app) => {
    const job = app.parseJob(jobEnvelope({ status: "failed", error: "Demo pipeline failed", error_code: "server_restarted" }), JOB_ID, identity);
    assert.equal(job.status, "failed");
    assert.equal(job.report, null);
}));

test("editing a project immediately clears result navigation and disables old artifact links", async () => withApp(async (app, dom) => {
    await app.poll(JOB_ID, identity, { fetcher: async () => response(200, jobEnvelope({ status: "complete", report: completedReport() })), monitorer: () => {} });
    assert.equal(app.canNavigate("build"), true);
    app.invalidateProjectResult();
    assert.equal(app.canNavigate("build"), false);
    assert.equal(app.canNavigate("review"), false);
    for (const link of dom.groups.get('[data-artifact-download]')) {
        assert.equal(link.getAttribute("href"), null);
        assert.equal(link.getAttribute("aria-disabled"), "true");
        assert.equal(link.dataset.current, "false");
    }
}));
