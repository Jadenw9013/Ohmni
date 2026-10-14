import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { TELEMETRY_CONFIG } from "../telemetry-config.js";
import {
    TELEMETRY_BUNDLE, resetTelemetryForTests, startTelemetry, telemetryState, traceRequest, validateConfig,
} from "../telemetry.js";
import { projectRequest } from "../project-contract.js";
import { pollHeaders } from "../client-contract.js";
import * as bundle from "../vendor/sentry-telemetry.js";

const ORIGIN = "http://127.0.0.1:8000";
const DSN = `https://${"0123456789abcdef".repeat(2)}@o0.ingest.sentry.io/42`;
const enabled = (overrides = {}) => ({
    enabled: true, dsn: DSN, environment: "local", release: "ohmni@0000000", apiOrigin: "", traceSampleRate: 1, ...overrides,
});
const TRACE = `${"a".repeat(32)}-${"b".repeat(16)}-1`;
const identity = { api_version: 2, server_instance_id: "a".repeat(16), ui_version: "b".repeat(64) };
const PLAN_PATH = "/api/project-plans";

function fakeAdapter({ throwing = false } = {}) {
    const log = { started: [], requests: [], ended: [], failed: [] };
    return {
        log,
        module: {
            start(config) { log.started.push(config); },
            request(route) {
                if (throwing) throw new Error("adapter broke");
                log.requests.push(route);
                return {
                    traceHeader: TRACE,
                    end(status) { log.ended.push([route, status]); },
                    fail(site, code) { log.failed.push([route, site, code]); },
                };
            },
        },
    };
}

async function enable(adapter, config = enabled()) {
    resetTelemetryForTests();
    globalThis.location = { href: `${ORIGIN}/`, origin: ORIGIN };
    const loaded = [];
    const state = await startTelemetry({ config, origin: ORIGIN, load: async (path) => { loaded.push(path); return adapter.module; } });
    return { state, loaded };
}

test("the committed public config is disabled and the default start loads nothing", async () => {
    assert.equal(TELEMETRY_CONFIG.enabled, false);
    assert.ok(Object.isFrozen(TELEMETRY_CONFIG));
    resetTelemetryForTests();
    let loads = 0;
    assert.equal(await startTelemetry({ load: async () => { loads += 1; } }), "disabled");
    assert.equal(loads, 0);
    const handle = traceRequest("POST", "/api/demo", "/api/demo");
    assert.deepEqual({ ...handle.headers }, {});
    handle.end(202); handle.fail("timeout");
});

test("invalid or unsafe configs never load the bundle", async () => {
    const cases = [
        { dsn: "" }, { dsn: DSN.replace("o0.ingest.sentry.io", "evil.example") }, { dsn: DSN.replace("https", "http") },
        { environment: "dev" }, { release: "" }, { release: "a b" }, { apiOrigin: "https://x.example/path" },
        { traceSampleRate: 2 }, { traceSampleRate: Number.NaN }, { traceSampleRate: "1" }, { enabled: "true" },
    ];
    for (const overrides of cases) {
        resetTelemetryForTests();
        let loads = 0;
        const state = await startTelemetry({ config: enabled(overrides), origin: ORIGIN, load: async () => { loads += 1; } });
        assert.equal(loads, 0, JSON.stringify(overrides));
        assert.ok(["invalid", "disabled"].includes(state), JSON.stringify(overrides));
    }
    assert.equal(validateConfig(enabled(), "null"), null, "an opaque page origin needs an explicit API origin");
    assert.equal(validateConfig(enabled({ apiOrigin: ORIGIN }), "null").apiOrigin, ORIGIN);
});

test("a missing, slow, malformed or throwing bundle leaves the facade inert", async () => {
    const loaders = {
        missing: async () => { throw new TypeError("Failed to fetch dynamically imported module"); },
        slow: () => new Promise(() => {}),
        malformed: async () => ({ start: 1 }),
        throwing: async () => ({ start() { throw new Error("init"); }, request() {} }),
        syncThrow: () => { throw new Error("sync"); },
    };
    for (const [name, load] of Object.entries(loaders)) {
        resetTelemetryForTests();
        const state = await startTelemetry({ config: enabled(), origin: ORIGIN, load, timeoutMs: 20 });
        assert.equal(state, "unavailable", name);
        assert.equal(telemetryState(), "unavailable", name);
        assert.deepEqual({ ...traceRequest("POST", "/api/demo", "/api/demo").headers }, {}, name);
    }
});

test("start is idempotent and loads only the local bundle path", async () => {
    const adapter = fakeAdapter();
    const { state, loaded } = await enable(adapter);
    assert.equal(state, "enabled");
    assert.deepEqual(loaded, [TELEMETRY_BUNDLE]);
    assert.equal(TELEMETRY_BUNDLE, "./vendor/sentry-telemetry.js");
    await startTelemetry({ config: enabled(), load: async () => assert.fail("loaded twice") });
    assert.equal(adapter.log.started.length, 1);
    assert.deepEqual(Object.keys(adapter.log.started[0]).sort(), ["apiOrigin", "dsn", "environment", "release", "traceSampleRate"]);
});

test("only exact-origin API targets receive a trace header, and only for traced routes", async () => {
    const adapter = fakeAdapter();
    await enable(adapter);
    const hex = "0123456789abcdef";
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "/api/demo").headers }, { "sentry-trace": TRACE });
    assert.deepEqual({ ...traceRequest("POST", "/api/brief", `${ORIGIN}/api/brief`).headers }, { "sentry-trace": TRACE });
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "https://ohmni-demo.fly.dev/api/demo").headers }, {});
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "http://127.0.0.1:9000/api/demo").headers }, {});
    assert.deepEqual({ ...traceRequest("POST", `/api/projects/${hex}/revisions/${hex}/run`, `/api/projects/${hex}/revisions/${hex}/run`).headers },
        { "sentry-trace": TRACE });
    for (const [method, path] of [["GET", "/api/health"], ["GET", PLAN_PATH], ["POST", "/api/projects"],
        ["POST", "/api/projects/XYZ/revisions/1/run"], ["POST", "/api/behavior/design/run"], ["POST", "/api/demo?x=1"]]) {
        assert.deepEqual({ ...traceRequest(method, path, path).headers }, {}, `${method} ${path}`);
    }
    assert.deepEqual(adapter.log.requests, [
        "POST /api/demo", "POST /api/brief", "POST /api/demo", "POST /api/demo",
        "POST /api/projects/{project}/revisions/{revision}/run",
    ]);
});

test("a configured cross-origin API is the only origin that receives the header", async () => {
    const adapter = fakeAdapter();
    await enable(adapter, enabled({ apiOrigin: "https://ohmni-demo.fly.dev" }));
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "https://ohmni-demo.fly.dev/api/demo").headers }, { "sentry-trace": TRACE });
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "/api/demo").headers }, {});
    assert.deepEqual({ ...traceRequest("POST", "/api/demo", "https://ohmni-demo.fly.dev/other").headers }, {});
});

test("handles settle once, forward only the fixed site, and swallow adapter errors", async () => {
    const adapter = fakeAdapter();
    await enable(adapter);
    const handle = traceRequest("POST", "/api/demo", "/api/demo");
    handle.fail("timeout");
    handle.fail("transport_unreachable");
    handle.end(202);
    assert.deepEqual(adapter.log.failed, [["POST /api/demo", "browser.demo_start", "timeout"]]);
    assert.deepEqual(adapter.log.ended, []);
    const broken = fakeAdapter({ throwing: true });
    await enable(broken);
    const inert = traceRequest("POST", "/api/demo", "/api/demo");
    assert.deepEqual({ ...inert.headers }, {});
    inert.end(500);
});

const ok = (body, status = 200) => ({ ok: status < 400, status, json: async () => ({ ...identity, ...body }) });

test("project requests are byte-identical with telemetry disabled", async () => {
    resetTelemetryForTests();
    await startTelemetry();
    const calls = [];
    await projectRequest(PLAN_PATH, { identity, method: "POST", data: { message: "x", parent_id: null },
        fetcher: async (url, init) => { calls.push([url, init.headers]); return ok({}); } });
    assert.deepEqual(calls, [[PLAN_PATH, { ...pollHeaders(identity), "content-type": "application/json" }]]);
});

test("project request outcomes map to one bounded client failure each", async () => {
    const adapter = fakeAdapter();
    await enable(adapter);
    const calls = [];
    await projectRequest(PLAN_PATH, { identity, method: "POST", data: {},
        fetcher: async (url, init) => { calls.push(init.headers["sentry-trace"]); return ok({}); } });
    assert.deepEqual(calls, [TRACE]);
    await assert.rejects(projectRequest(PLAN_PATH, { identity, method: "POST", data: {},
        fetcher: async () => { throw new TypeError("secret-canary network detail"); } }), /unreachable/);
    await assert.rejects(projectRequest(PLAN_PATH, { identity, method: "POST", data: {},
        fetcher: async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("secret-canary"); } }) }));
    await assert.rejects(projectRequest(PLAN_PATH, { identity, method: "POST", data: {}, timeoutMs: 10,
        fetcher: () => new Promise(() => {}) }), /too long/);
    await assert.rejects(projectRequest(PLAN_PATH, { identity, method: "POST", data: {},
        fetcher: async () => ok({ error: "invalid_plan" }, 400) }), /safe plan/);
    assert.deepEqual(adapter.log.failed.map((entry) => entry[2]), ["transport_unreachable", "contract_mismatch", "timeout"]);
    assert.deepEqual(adapter.log.ended.map((entry) => entry[1]), [200, 400]);
    assert.ok(adapter.log.failed.every(([, site]) => site === "browser.project_request"));
});

test("the bundled adapter matches its metadata and rebuilds only allowlisted payloads", () => {
    const metadata = JSON.parse(readFileSync(new URL("../vendor/sentry-telemetry.json", import.meta.url)));
    const bytes = readFileSync(new URL("../vendor/sentry-telemetry.js", import.meta.url));
    assert.equal(metadata.sdk_version, "11.7.0");
    assert.equal(bundle.VERSION, "11.7.0");
    assert.equal(metadata.bytes, bytes.length);
    assert.equal(metadata.sha256, createHash("sha256").update(bytes).digest("hex"));
    assert.doesNotMatch(bytes.toString("utf8"), /\/(home|tmp|Users)\//);
    const trace = { trace_id: "a".repeat(32), span_id: "b".repeat(16), op: "http.client", status: "ok", data: { "http.response.status_code": 202, "http.url": "secret-canary" } };
    const event = bundle.filterEvent({
        event_id: "e".repeat(32), exception: { values: [{ type: "OhmniClientFailure", value: "browser.demo_start.timeout", stacktrace: { frames: [] } }] },
        request: { url: "secret-canary" }, user: { id: "secret-canary" }, breadcrumbs: [{ message: "secret-canary" }],
        extra: { x: "secret-canary" }, tags: { x: "secret-canary" }, contexts: { trace, browser: { name: "secret-canary" } },
    });
    assert.deepEqual(event.tags, { "ohmni.site": "browser.demo_start", "ohmni.code": "timeout" });
    assert.doesNotMatch(JSON.stringify(event), /secret-canary|stacktrace/);
    for (const hostile of [
        { exception: { values: [{ type: "TypeError", value: "secret-canary" }] } },
        { exception: { values: [{ type: "OhmniClientFailure", value: "browser.demo_start.secret-canary" }] } },
        { exception: { values: [{ type: "OhmniClientFailure", value: "browser.other.timeout" }] } },
        { message: "secret-canary" }, { type: "transaction" }, null,
        { get exception() { throw new Error("hostile"); } },
    ]) assert.equal(bundle.filterEvent(hostile), null);
    const transaction = bundle.filterTransaction({ type: "transaction", transaction: "POST /api/demo", contexts: { trace },
        spans: [{ description: "secret-canary" }], request: { url: "secret-canary" }, measurements: {} });
    assert.equal(transaction.contexts.trace.data["http.response.status_code"], 202);
    assert.doesNotMatch(JSON.stringify(transaction), /secret-canary/);
    assert.equal(bundle.filterTransaction({ type: "transaction", transaction: "GET /secret-canary", contexts: { trace } }), null);
    assert.equal(bundle.filterTransaction({ type: "transaction", transaction: "POST /api/demo", contexts: { trace: { ...trace, op: "pageload" } } }), null);
});

test("a project response is a telemetry success only after its identity check", async () => {
    const cases = {
        identity: async () => ok({ server_instance_id: "c".repeat(16) }),
        body: async () => ({ ok: true, status: 200, json: async () => ["not", "an", "envelope"] }),
        json: async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("x"); } }),
    };
    for (const [kind, fetcher] of Object.entries(cases)) {
        const adapter = fakeAdapter();
        await enable(adapter);
        await assert.rejects(projectRequest(PLAN_PATH, { identity, method: "POST", data: {}, fetcher }), undefined, kind);
        assert.deepEqual(adapter.log.failed.map((entry) => entry[2]), ["contract_mismatch"], kind);
        assert.deepEqual(adapter.log.ended, [], `${kind} is never also a success`);
    }
    const adapter = fakeAdapter();
    await enable(adapter);
    await projectRequest(PLAN_PATH, { identity, method: "POST", data: {}, fetcher: async () => ok({}) });
    assert.deepEqual(adapter.log.ended, [["POST /api/project-plans", 200]]);
    assert.deepEqual(adapter.log.failed, []);
});

test("an enabled config whose bundle file is really absent stays inert and changes no request", async () => {
    resetTelemetryForTests();
    const absent = new URL("../vendor/ohmni-absent-telemetry-bundle.js", import.meta.url).href;
    const state = await startTelemetry({ config: enabled(), origin: ORIGIN, load: () => import(absent) });
    assert.equal(state, "unavailable");
    const calls = [];
    await projectRequest(PLAN_PATH, { identity, method: "POST", data: { message: "x", parent_id: null },
        fetcher: async (url, init) => { calls.push([url, init.headers]); return ok({}); } });
    assert.deepEqual(calls, [[PLAN_PATH, { ...pollHeaders(identity), "content-type": "application/json" }]]);
});

test("the real bundle starts every request in a new trace", () => {
    const realFetch = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error("network is forbidden in this test"); };
    try {
        // Uninitialized (no DSN, so no client and nothing can be sent), the
        // SDK still assigns trace IDs: sequential and overlapping handles alike.
        const first = bundle.request("POST /api/demo");
        const second = bundle.request("POST /api/brief");
        const third = bundle.request("POST /api/demo");
        const ids = [first, second, third].map((handle) => handle.traceHeader.split("-")[0]);
        assert.ok(ids.every((id) => /^[0-9a-f]{32}$/.test(id)));
        assert.equal(new Set(ids).size, 3);
        for (const handle of [first, second, third]) handle.end(200);
        assert.equal(bundle.request("GET /secret-canary"), null);
    } finally { globalThis.fetch = realFetch; }
});
