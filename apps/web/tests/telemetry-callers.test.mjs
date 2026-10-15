// Project telemetry outcomes through the real callers and the real bundled SDK.
//
// The committed @sentry/browser bundle is started with a synthetic DSN. Its
// transport uses globalThis.fetch, which this file replaces with an in-memory
// recorder before the SDK loads: nothing leaves the process, and any other
// destination is refused. Each test drives a real caller (conversation,
// assistant, guided workbench) with a fake API and then reads the envelopes the
// SDK actually produced. A caller that rejects the server's response must never
// leave behind a successful ("ok") request transaction.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { mock } from "node:test";
import { mountConversation } from "../conversation.js";
import { mountProjectAssistant } from "../project-assistant.js";
import { mountProjectWorkbench } from "../project-workbench.js";
import { defaultProjectBrief } from "../project-contract.js";
import { resetTelemetryForTests, startTelemetry, telemetryState } from "../telemetry.js";

const INGEST = "https://o0.ingest.sentry.io/";
const sent = [];
let refused = 0;
globalThis.fetch = async (url, init = {}) => {
    if (!String(url).startsWith(INGEST)) { refused += 1; throw new TypeError("external traffic denied"); }
    const body = init.body;
    sent.push(typeof body === "string" ? body : new TextDecoder().decode(body));
    return new Response("{}", { status: 200 });
};

const ORIGIN = "http://127.0.0.1:8000";
const DSN = `https://${"0123456789abcdef".repeat(2)}@o0.ingest.sentry.io/42`;
const CONFIG = { enabled: true, dsn: DSN, environment: "local", release: "ohmni@0000000", apiOrigin: "", traceSampleRate: 1 };
const CANARY = "secret-canary-7f3a";
const BUNDLE = new URL("../vendor/sentry-telemetry.js", import.meta.url).href;

async function useTelemetry(mode) {
    resetTelemetryForTests();
    globalThis.location = { href: `${ORIGIN}/`, origin: ORIGIN };
    const load = { real: () => import(BUNDLE), missing: () => { throw new TypeError("bundle 404"); } }[mode];
    const state = mode === "disabled" ? await startTelemetry()
        : await startTelemetry({ config: CONFIG, origin: ORIGIN, load });
    assert.equal(state, { real: "enabled", missing: "unavailable", disabled: "disabled" }[mode]);
    return state;
}

// Envelope items produced since `mark`, reduced to the bounded facts asserted here.
function items(mark) {
    return sent.slice(mark).flatMap((envelope) => {
        const lines = envelope.split("\n").filter(Boolean).slice(1);
        const out = [];
        for (let i = 0; i + 1 < lines.length; i += 2) out.push({ type: JSON.parse(lines[i]).type, payload: JSON.parse(lines[i + 1]) });
        return out;
    });
}
function outcomes(mark) {
    const all = items(mark);
    return {
        transactions: all.filter((item) => item.type === "transaction")
            .map(({ payload }) => [payload.transaction, payload.contexts.trace.status]).sort(),
        issues: all.filter((item) => item.type === "event").map(({ payload }) => payload.exception.values[0].value).sort(),
        other: all.filter((item) => !["transaction", "event"].includes(item.type)).map((item) => item.type),
    };
}
// The SDK sends asynchronously. Wait (bounded) for the expected item count, then
// a little longer so an unexpected extra item would also be seen.
async function settle(mark, expected) {
    const deadline = Date.now() + 3000;
    while (items(mark).length < expected && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 10));
    await new Promise((resolve) => setTimeout(resolve, 400));
    return outcomes(mark);
}

const identity = { api_version: 2, server_instance_id: "a".repeat(16), ui_version: "b".repeat(64) };
const reply = (body, status = 200) => ({ ok: status < 400, status, json: async () => ({ ...identity, ...body }) });
const health = () => reply({ status: "ready", fixture_id: "esp32-bme280-environmental-logger", free_text: true });
const brief = () => ({ ...defaultProjectBrief(), project_name: `Board ${CANARY}`, button_count: 0, spi_devices: [], board_width_mm: 100, board_height_mm: 70 });
const PLAN_ID = "c".repeat(16), PROJECT_ID = "e".repeat(16), REVISION_ID = "f".repeat(16), TURN_ID = "9".repeat(16);
const plan = () => ({ plan_id: PLAN_ID, brief_fingerprint: "d".repeat(64), messages: [`A USB board ${CANARY}`], brief: brief(),
    stated: [], assumed_fields: Object.keys(brief()).filter((key) => key !== "schema_version"), questions: [], ready: true, preview: {} });
const revisionOf = (value, overrides = {}) => ({ revision_id: REVISION_ID, number: 1, created_at: "now", brief: value.brief,
    brief_fingerprint: value.brief_fingerprint, preview: { asked_for: [], assumed: [], needs_clarification: [] }, job_id: null, ...overrides });
const projectOf = (revisions) => ({ project_id: PROJECT_ID, created_at: "now", updated_at: "now", revisions });

function conversationDom() {
    const nodes = new Map();
    const root = { innerHTML: "", setAttribute() {}, querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, { innerHTML: "", textContent: "", value: "", hidden: false, disabled: false,
            focus() {}, addEventListener() {} });
        return nodes.get(selector);
    } };
    return { root, node: (selector) => root.querySelector(selector) };
}

/** Plan, then confirm, through mountConversation. `confirmReply` is the server's confirm response. */
async function runConfirm(confirmReply) {
    const ui = conversationDom(), saved = [], headers = [];
    const p = plan();
    const fetcher = async (url, init = {}) => {
        headers.push(init.headers || {});
        if (url === "/api/health") return health();
        if (url.endsWith("/confirm")) return confirmReply(p);
        return reply({ plan: p });
    };
    const controller = mountConversation(ui.root, { fetcher, onOpen() {}, onSaved: async (project) => { saved.push(project); } });
    await controller.begin(p.messages[0]);
    await controller.confirm();
    return { error: ui.node("#conversation-error"), saved, headers };
}

const PLAN_ROUTE = "POST /api/project-plans";
const CONFIRM_ROUTE = "POST /api/project-plans/{plan}/confirm";
const APPLY_ROUTE = "POST /api/projects/{project}/revisions/{revision}/assistant/{turn}/apply";
const ASK_ROUTE = "POST /api/projects/{project}/revisions/{revision}/assistant";
const MISMATCH = "browser.project_request.contract_mismatch";

test("confirming a plan whose saved brief matches records success", async () => {
    await useTelemetry("real");
    const mark = sent.length;
    const result = await runConfirm((p) => reply({ project: projectOf([revisionOf(p)]) }, 201));
    assert.equal(result.saved.length, 1);
    assert.equal(result.error.textContent, "");
    assert.ok(result.headers.some((h) => /^[0-9a-f]{32}-[0-9a-f]{16}-1$/.test(h["sentry-trace"] || "")), "traced requests carry a header");
    const seen = await settle(mark, 2);
    assert.deepEqual(seen, { transactions: [[PLAN_ROUTE, "ok"], [CONFIRM_ROUTE, "ok"]].sort(), issues: [], other: [] });
});

test("confirming a plan whose returned saved brief differs is never a success", async () => {
    await useTelemetry("real");
    const mark = sent.length;
    const result = await runConfirm((p) => reply({ project: projectOf([revisionOf({ ...p, brief: { ...p.brief, status_led_count: 0 } })]) }, 201));
    assert.equal(result.saved.length, 0, "the mismatched revision never reaches generation");
    assert.match(result.error.textContent, /differs from the reviewed plan/);
    const seen = await settle(mark, 3);
    assert.deepEqual(seen.transactions, [[PLAN_ROUTE, "ok"], [CONFIRM_ROUTE, "internal_error"]].sort());
    assert.deepEqual(seen.issues, [MISMATCH], "exactly one owned issue for the rejected operation");
    assert.deepEqual(seen.other, []);
});

test("a confirm whose fingerprint differs, or whose contract is malformed, is a mismatch", async () => {
    for (const [kind, confirmReply] of Object.entries({
        fingerprint: (p) => reply({ project: projectOf([revisionOf({ ...p, brief_fingerprint: "0".repeat(64) })]) }, 201),
        malformed: () => reply({ project: { project_id: PROJECT_ID, revisions: [] } }, 201),
        notjson: () => ({ ok: true, status: 201, json: async () => { throw new SyntaxError(CANARY); } }),
        identity: (p) => ({ ok: true, status: 201, json: async () => ({ ...identity, server_instance_id: "1".repeat(16), project: projectOf([revisionOf(p)]) }) }),
    })) {
        await useTelemetry("real");
        const mark = sent.length;
        const result = await runConfirm(confirmReply);
        assert.equal(result.saved.length, 0, kind);
        assert.notEqual(result.error.textContent, "", kind);
        const seen = await settle(mark, 3);
        assert.deepEqual(seen.transactions, [[PLAN_ROUTE, "ok"], [CONFIRM_ROUTE, "internal_error"]].sort(), kind);
        assert.deepEqual(seen.issues, [MISMATCH], kind);
    }
});

test("a confirm that times out records a timeout and keeps the plan", async () => {
    await useTelemetry("real");
    const mark = sent.length;
    const ui = conversationDom(), saved = [];
    const p = plan();
    let confirmCalled;
    const confirmed = new Promise((resolve) => { confirmCalled = resolve; });
    const fetcher = async (url) => {
        if (url === "/api/health") return health();
        if (url.endsWith("/confirm")) { confirmCalled(); return new Promise(() => {}); }
        return reply({ plan: p });
    };
    const controller = mountConversation(ui.root, { fetcher, onOpen() {}, onSaved: async (project) => { saved.push(project); } });
    await controller.begin(p.messages[0]);
    mock.timers.enable({ apis: ["setTimeout"] });
    let pending;
    try {
        pending = controller.confirm();
        await confirmed;
        mock.timers.tick(20000);
    } finally { mock.timers.reset(); }
    await pending;
    assert.equal(saved.length, 0);
    assert.match(ui.node("#conversation-error").textContent, /took too long/);
    assert.equal(ui.node("#conversation-confirm").hidden, false, "the reviewed plan is still offered");
    const seen = await settle(mark, 3);
    assert.deepEqual(seen.transactions, [[PLAN_ROUTE, "ok"], [CONFIRM_ROUTE, "deadline_exceeded"]].sort());
    assert.deepEqual(seen.issues, ["browser.project_request.timeout"]);
});

function assistantDom() {
    const nodes = new Map();
    const root = { innerHTML: "", setAttribute() {}, querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, { innerHTML: "", textContent: "", value: "", hidden: false, disabled: false, focus() {}, addEventListener() {} });
        return nodes.get(selector);
    } };
    return { root, node: (selector) => root.querySelector(selector) };
}
const baseRevision = () => revisionOf({ brief: brief(), brief_fingerprint: "d".repeat(64) });
const assistantContext = () => ({ projectId: PROJECT_ID, revision: baseRevision(), dirty: false });
const changeTurn = () => ({ turn_id: TURN_ID, project_id: PROJECT_ID, revision_id: REVISION_ID, revision_number: 1,
    base_brief_fingerprint: "d".repeat(64), context_fingerprint: "1".repeat(64), messages: [`Make it 80 mm wide ${CANARY}`], kind: "change",
    facts: [], brief: { ...brief(), board_width_mm: 80 }, changes: [{ field: "board_width_mm", before: 100, after: 80 }], questions: [],
    ready: true, invalidation: "New checks are needed; existing results stay with revision 1." });

async function runApply(appliedRevision, project = (revisions) => projectOf(revisions)) {
    const ui = assistantDom(), turn = changeTurn();
    let applied = null;
    const fetcher = async (url) => {
        if (url === "/api/health") return health();
        if (url.endsWith("/apply")) return reply({ project: project([baseRevision(), appliedRevision(turn)]) });
        return reply({ turn });
    };
    const controller = mountProjectAssistant(ui.root, { fetcher, onApplied: (project) => { applied = project; } });
    controller.setContext(assistantContext());
    await controller.ask(turn.messages[0]);
    await controller.apply();
    return { applied, error: ui.node("#assistant-error") };
}
const nextRevision = (turn, overrides = {}) => ({ ...baseRevision(), revision_id: "2".repeat(16), number: 2, brief: turn.brief,
    brief_fingerprint: "3".repeat(64), ...overrides });

test("applying a proposal whose returned revision matches records success", async () => {
    await useTelemetry("real");
    const mark = sent.length;
    const result = await runApply((turn) => nextRevision(turn));
    assert.equal(result.applied.revisions[1].brief.board_width_mm, 80);
    const seen = await settle(mark, 2);
    assert.deepEqual(seen, { transactions: [[APPLY_ROUTE, "ok"], [ASK_ROUTE, "ok"]].sort(), issues: [], other: [] });
});

test("applying a proposal whose returned revision differs is never a success", async () => {
    const cases = {
        brief: (turn) => nextRevision(turn, { brief: { ...turn.brief, board_width_mm: 90 } }),
        job: (turn) => nextRevision(turn, { job_id: "a".repeat(12) }),
        project: [(turn) => nextRevision(turn), (revisions) => ({ ...projectOf(revisions), project_id: "8".repeat(16) })],
        stale: [(turn) => nextRevision(turn), (revisions) => projectOf(revisions.slice(0, 1))],
    };
    for (const [kind, scenario] of Object.entries(cases)) {
        await useTelemetry("real");
        const mark = sent.length;
        const result = await runApply(...(Array.isArray(scenario) ? scenario : [scenario]));
        assert.equal(result.applied, null, kind);
        assert.match(result.error.textContent, /does not match this proposal/, kind);
        assert.equal(result.error.hidden, false, kind);
        const seen = await settle(mark, 3);
        assert.deepEqual(seen.transactions, [[APPLY_ROUTE, "internal_error"], [ASK_ROUTE, "ok"]].sort(), kind);
        assert.deepEqual(seen.issues, [MISMATCH], kind);
    }
});

// Guided saves (POST /api/projects and /revisions) are not traced routes: they
// produce no telemetry at all, so a mismatch can never be recorded as success.
const options = JSON.parse(readFileSync(new URL("./fixtures/project-options.json", import.meta.url), "utf8"));
function workbenchDom() {
    const nodes = new Map(), handlers = new Map();
    const node = (selector) => {
        if (!nodes.has(selector)) nodes.set(selector, { innerHTML: "", textContent: "", hidden: false, disabled: false,
            focus() {}, querySelector: node, querySelectorAll: () => [], setAttribute() {},
            addEventListener(name, handler) { handlers.set(`${selector}:${name}`, handler); }, replaceWith() {} });
        return nodes.get(selector);
    };
    const root = { innerHTML: "", querySelector: node, querySelectorAll: () => [],
        addEventListener: (name, handler) => handlers.set(name, handler), removeEventListener: (name) => handlers.delete(name) };
    return { root, node, handlers };
}

test("saving guided choices with a mismatched returned brief records nothing and keeps the edit", async () => {
    await useTelemetry("real");
    const mark = sent.length;
    const dom = workbenchDom();
    const posted = [];
    const fetcher = async (path, request = {}) => {
        if (path === "/api/health") return reply({ status: "ready", fixture_id: "esp32-bme280-environmental-logger" });
        if (path === "/api/project-options") return reply({ options });
        posted.push(JSON.parse(request.body).brief);
        const saved = { ...JSON.parse(request.body).brief, board_width_mm: 90 };
        return reply({ project: projectOf([revisionOf({ brief: saved, brief_fingerprint: "4".repeat(64) })]) }, 201);
    };
    const controller = mountProjectWorkbench(dom.root, { fetcher });
    await controller.openNew();
    dom.handlers.get("input")({ target: { dataset: {}, closest: (selector) => selector === "#project-form" ? {} : null, id: "project-board_width_mm", value: "80" } });
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await new Promise(setImmediate); await new Promise(setImmediate);
    assert.equal(posted.length, 1, dom.node("#project-error").textContent);
    assert.equal(posted[0].board_width_mm, 80);
    assert.equal(dom.node("#project-error").hidden, false, "the mismatch is shown, not accepted");
    assert.match(dom.root.innerHTML, /Save/);
    // The user's unsaved choice survives: saving again sends the same edit.
    dom.handlers.get("submit")({ target: { id: "project-form" }, preventDefault() {} });
    await new Promise(setImmediate); await new Promise(setImmediate);
    assert.equal(posted.length, 2);
    assert.equal(posted[1].board_width_mm, 80);
    controller.dispose();
    const seen = await settle(mark, 0);
    assert.deepEqual(seen, { transactions: [], issues: [], other: [] });
});

test("disabled or unavailable telemetry leaves every caller outcome unchanged and sends nothing", async () => {
    const reference = {};
    for (const mode of ["real", "missing", "disabled"]) {
        await useTelemetry(mode);
        const mark = sent.length;
        const good = await runConfirm((p) => reply({ project: projectOf([revisionOf(p)]) }, 201));
        const bad = await runConfirm((p) => reply({ project: projectOf([revisionOf({ ...p, brief: { ...p.brief, status_led_count: 0 } })]) }, 201));
        const apply = await runApply((turn) => nextRevision(turn, { brief: { ...turn.brief, board_width_mm: 90 } }));
        const observed = { good: [good.saved.length, good.error.textContent], bad: [bad.saved.length, bad.error.textContent],
            apply: [apply.applied, apply.error.textContent] };
        if (mode === "real") Object.assign(reference, observed);
        else {
            assert.deepEqual(observed, reference, mode);
            assert.equal(telemetryState(), mode === "missing" ? "unavailable" : "disabled");
            assert.ok([...good.headers, ...bad.headers].every((h) => !("sentry-trace" in h)), `${mode} adds no header`);
            await new Promise((resolve) => setTimeout(resolve, 400));
            assert.equal(sent.length, mark, `${mode} sends no envelope`);
        }
    }
});

test("no envelope carries project content, ids, prompts, bodies or raw errors", async () => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    assert.ok(sent.length > 0, "the scenarios above produced envelopes");
    const all = sent.join("\n");
    for (const forbidden of [CANARY, PLAN_ID, PROJECT_ID, TURN_ID, "differs from the reviewed plan", "does not match this proposal",
        "SyntaxError", "status_led_count", "127.0.0.1", "/api/project-plans/c", "stack"]) {
        assert.ok(!all.includes(forbidden), `envelope leaked ${forbidden}`);
    }
    assert.equal(refused, 0, "the SDK never tried a destination other than the recorder");
    const types = new Set(sent.flatMap((envelope) => envelope.split("\n").filter(Boolean).slice(1)
        .filter((_, i) => i % 2 === 0).map((line) => JSON.parse(line).type)));
    assert.deepEqual([...types].sort(), ["event", "transaction"]);
});
