// No-throw browser telemetry facade.
//
// Application modules import only this file. It never imports the SDK
// statically: the locally bundled adapter (vendor/sentry-telemetry.js) is
// loaded with a bounded dynamic import, and only when the public config enables
// telemetry and validates. Until it has loaded -- or when it is disabled,
// invalid, missing or broken -- every call is an inert pass-through, so the
// application's requests and behavior are exactly what they are without it.
// Nothing is queued while the bundle loads, and no user text, URL, header,
// body or thrown value is ever handed to the adapter: only fixed route
// templates, HTTP status codes and allowlisted failure codes.
import { TELEMETRY_CONFIG } from "./telemetry-config.js";

export const TELEMETRY_BUNDLE = "./vendor/sentry-telemetry.js";
const ENVIRONMENTS = new Set(["local", "preview", "production", "hackathon"]);
const DSN = /^https:\/\/[0-9a-f]{32}@o[0-9]{1,20}\.ingest(?:\.[a-z]{2})?\.sentry\.io\/[0-9]{1,20}$/;
const RELEASE = /^[A-Za-z0-9][A-Za-z0-9._@+-]{0,79}$/;
const ORIGIN = /^https?:\/\/[a-z0-9.-]+(?::[0-9]{1,5})?$/;
const HEX16 = "[0-9a-f]{16}";
const ROUTES = [
    [new RegExp("^/api/brief$"), "POST /api/brief", "browser.brief"],
    [new RegExp("^/api/demo$"), "POST /api/demo", "browser.demo_start"],
    [new RegExp("^/api/project-plans$"), "POST /api/project-plans", "browser.project_request"],
    [new RegExp(`^/api/project-plans/${HEX16}/confirm$`), "POST /api/project-plans/{plan}/confirm", "browser.project_request"],
    [new RegExp(`^/api/projects/${HEX16}/revisions/${HEX16}/assistant$`),
        "POST /api/projects/{project}/revisions/{revision}/assistant", "browser.project_request"],
    [new RegExp(`^/api/projects/${HEX16}/revisions/${HEX16}/assistant/${HEX16}/apply$`),
        "POST /api/projects/{project}/revisions/{revision}/assistant/{turn}/apply", "browser.project_request"],
    [new RegExp(`^/api/projects/${HEX16}/revisions/${HEX16}/run$`),
        "POST /api/projects/{project}/revisions/{revision}/run", "browser.project_request"],
];

const INERT = Object.freeze({ headers: Object.freeze({}), end() {}, fail() {} });
let adapter = null;
let status = "disabled";
let allowedOrigin = null;
let pending = null;

/** "disabled" | "invalid" | "loading" | "enabled" | "unavailable". */
export const telemetryState = () => status;

/** The validated public config, or null when telemetry must stay off. */
export function validateConfig(config, origin) {
    try {
        if (!config || config.enabled !== true) return null;
        const { dsn, environment, release, apiOrigin, traceSampleRate } = config;
        if (typeof dsn !== "string" || !DSN.test(dsn)) return null;
        if (!ENVIRONMENTS.has(environment)) return null;
        if (typeof release !== "string" || !RELEASE.test(release)) return null;
        if (typeof apiOrigin !== "string" || (apiOrigin !== "" && !ORIGIN.test(apiOrigin))) return null;
        if (typeof traceSampleRate !== "number" || !(traceSampleRate >= 0 && traceSampleRate <= 1)) return null;
        const target = apiOrigin || (typeof origin === "string" && ORIGIN.test(origin) ? origin : null);
        if (!target) return null;
        return Object.freeze({ dsn, environment, release, traceSampleRate, apiOrigin: target });
    } catch { return null; }
}

/**
 * Start telemetry once. Resolves to the final state and never rejects; the
 * application does not wait for it.
 */
export function startTelemetry({
    config = TELEMETRY_CONFIG, load = (path) => import(path), timeoutMs = 3000,
    origin = globalThis.location?.origin,
} = {}) {
    if (pending) return pending;
    let valid = null;
    try {
        if (config?.enabled !== true) return (pending = Promise.resolve(status));
        valid = validateConfig(config, origin);
    } catch { valid = null; }
    if (!valid) {
        status = "invalid";
        return (pending = Promise.resolve(status));
    }
    status = "loading";
    let timer;
    const timeout = new Promise((resolve) => { timer = setTimeout(() => resolve(null), timeoutMs); });
    pending = (async () => {
        try {
            const module = await Promise.race([Promise.resolve().then(() => load(TELEMETRY_BUNDLE)), timeout]);
            if (!module || typeof module.start !== "function" || typeof module.request !== "function") throw new Error();
            module.start(valid);
            adapter = module;
            allowedOrigin = valid.apiOrigin;
            status = "enabled";
        } catch {
            adapter = null;
            status = "unavailable";
        } finally { clearTimeout(timer); }
        return status;
    })();
    return pending;
}

const routeFor = (method, path) => {
    if (method !== "POST" || typeof path !== "string") return null;
    for (const [pattern, route, site] of ROUTES) if (pattern.test(path)) return { route, site };
    return null;
};

const mayPropagate = (url) => {
    try {
        const base = globalThis.location?.href;
        const target = base ? new URL(url, base) : new URL(url);
        return target.origin === allowedOrigin && target.pathname.startsWith("/api/");
    } catch { return false; }
};

/**
 * A handle for one API request: `headers` to spread into the request (empty
 * unless the target is the exact allowed API origin), `end(status)` when a
 * response arrives, and `fail(code)` for a client-side failure the backend
 * cannot have seen: "transport_unreachable", "timeout" or "contract_mismatch".
 * Untraced routes, a disabled facade, or any adapter error give the inert handle.
 */
export function traceRequest(method, path, url) {
    if (!adapter) return INERT;
    try {
        const known = routeFor(method, path);
        if (!known) return INERT;
        const handle = adapter.request(known.route);
        if (!handle) return INERT;
        const header = typeof handle.traceHeader === "string" && mayPropagate(url) ? handle.traceHeader : null;
        let settled = false;
        return Object.freeze({
            headers: Object.freeze(header ? { "sentry-trace": header } : {}),
            end(httpStatus) {
                if (settled) return;
                settled = true;
                try { handle.end(httpStatus); } catch { /* telemetry must not affect the request */ }
            },
            fail(code) {
                if (settled) return;
                settled = true;
                try { handle.fail(known.site, code); } catch { /* telemetry must not affect the request */ }
            },
        });
    } catch { return INERT; }
}

/** Test-only: return the facade to its initial disabled state. */
export function resetTelemetryForTests() {
    adapter = null;
    status = "disabled";
    allowedOrigin = null;
    pending = null;
}
