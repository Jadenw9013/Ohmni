// Source for apps/web/vendor/sentry-telemetry.js (built by build.mjs).
//
// The only browser module that touches @sentry/browser. It is loaded lazily by
// apps/web/telemetry.js, and only when the public telemetry config enables it.
// Everything here is manual and allowlisted: no default integrations (no global
// error handlers, console, DOM, fetch or history capture), no breadcrumbs, no
// raw thrown values, and every outgoing event or transaction is rebuilt from a
// fixed set of bounded fields before the SDK may send it.
import {
    SDK_VERSION, captureEvent, init, spanToTraceHeader, startInactiveSpan, withActiveSpan,
} from "@sentry/browser";

export const VERSION = SDK_VERSION;
export const FAILURE_TYPE = "OhmniClientFailure";
export const SITES = Object.freeze(["browser.brief", "browser.demo_start", "browser.project_request"]);
export const CODES = Object.freeze(["transport_unreachable", "timeout", "contract_mismatch"]);
export const ROUTES = Object.freeze([
    "POST /api/brief",
    "POST /api/demo",
    "POST /api/project-plans",
    "POST /api/project-plans/{plan}/confirm",
    "POST /api/projects/{project}/revisions/{revision}/assistant",
    "POST /api/projects/{project}/revisions/{revision}/assistant/{turn}/apply",
    "POST /api/projects/{project}/revisions/{revision}/run",
]);
const SITE_SET = new Set(SITES);
const CODE_SET = new Set(CODES);
const ROUTE_SET = new Set(ROUTES);
const HEX = /^[0-9a-f]+$/;
const SPAN_STATUSES = new Set(["ok", "internal_error", "cancelled", "deadline_exceeded", "unknown_error"]);

const ownedValue = (value) => {
    if (typeof value !== "string") return null;
    const dot = value.indexOf(".", "browser.".length);
    const site = value.slice(0, dot);
    const code = value.slice(dot + 1);
    return dot > 0 && SITE_SET.has(site) && CODE_SET.has(code) ? { site, code } : null;
};

const traceContext = (trace) => {
    if (!trace || typeof trace !== "object") return null;
    const { trace_id: traceId, span_id: spanId } = trace;
    if (typeof traceId !== "string" || traceId.length !== 32 || !HEX.test(traceId)) return null;
    if (typeof spanId !== "string" || spanId.length !== 16 || !HEX.test(spanId)) return null;
    return { trace_id: traceId, span_id: spanId };
};

const envelopeBase = (event) => ({
    event_id: event.event_id,
    timestamp: event.timestamp,
    platform: "javascript",
    environment: event.environment,
    release: event.release,
    sdk: { name: "sentry.javascript.browser", version: SDK_VERSION },
});

/** Rebuild an owned client failure from bounded fields; drop anything else. */
export function filterEvent(event) {
    try {
        if (!event || event.type !== undefined) return null;
        const values = event.exception?.values;
        if (!Array.isArray(values) || values.length !== 1 || values[0]?.type !== FAILURE_TYPE) return null;
        const owned = ownedValue(values[0].value);
        if (!owned) return null;
        const trace = traceContext(event.contexts?.trace);
        return {
            ...envelopeBase(event),
            level: "error",
            exception: { values: [{ type: FAILURE_TYPE, value: `${owned.site}.${owned.code}` }] },
            fingerprint: [FAILURE_TYPE, owned.site, owned.code],
            tags: { "ohmni.site": owned.site, "ohmni.code": owned.code },
            ...(trace ? { contexts: { trace } } : {}),
        };
    } catch { return null; }
}

/** Rebuild one manual request transaction from bounded fields; drop anything else. */
export function filterTransaction(event) {
    try {
        if (!event || event.type !== "transaction" || !ROUTE_SET.has(event.transaction)) return null;
        const source = event.contexts?.trace;
        const trace = traceContext(source);
        if (!trace || source.op !== "http.client") return null;
        const status = SPAN_STATUSES.has(source.status) ? source.status : "unknown_error";
        const code = source.data?.["http.response.status_code"];
        const data = { "sentry.op": "http.client", "sentry.origin": "manual", "sentry.source": "custom" };
        if (Number.isInteger(code) && code >= 100 && code <= 599) data["http.response.status_code"] = code;
        return {
            ...envelopeBase(event),
            type: "transaction",
            transaction: event.transaction,
            transaction_info: { source: "custom" },
            start_timestamp: event.start_timestamp,
            contexts: { trace: { ...trace, op: "http.client", origin: "manual", status, data } },
            spans: [],
        };
    } catch { return null; }
}

export function start(config) {
    init({
        dsn: config.dsn,
        environment: config.environment,
        release: config.release,
        tracesSampleRate: config.traceSampleRate,
        traceLifecycle: "static",
        defaultIntegrations: false,
        integrations: [],
        tracePropagationTargets: [],
        sendClientReports: false,
        maxBreadcrumbs: 0,
        attachStacktrace: false,
        enhanceFetchErrorMessages: false,
        dataCollection: {
            userInfo: false, cookies: false, httpHeaders: false, httpBodies: [], urlQueryParams: false,
            graphQL: { document: false, variables: false }, genAI: { inputs: false, outputs: false },
            databaseQueryData: false, queues: false, stackFrameVariables: false, frameContextLines: 0,
        },
        beforeBreadcrumb: () => null,
        beforeSend: filterEvent,
        beforeSendTransaction: filterTransaction,
    });
}

const statusFor = (httpStatus) => (httpStatus >= 200 && httpStatus < 400 ? "ok" : "internal_error");

/** One manual request transaction. Its trace header is offered, not applied. */
export function request(route) {
    if (!ROUTE_SET.has(route)) return null;
    const span = startInactiveSpan({ name: route, op: "http.client", forceTransaction: true });
    let open = true;
    const close = (status) => {
        if (!open) return;
        open = false;
        span.setStatus({ code: status === "ok" ? 1 : 2, message: status });
        span.end();
    };
    return {
        traceHeader: spanToTraceHeader(span),
        end(httpStatus) {
            if (!open) return;
            if (Number.isInteger(httpStatus)) span.setAttribute("http.response.status_code", httpStatus);
            close(statusFor(httpStatus));
        },
        fail(site, code) {
            if (!SITE_SET.has(site) || !CODE_SET.has(code)) return;
            withActiveSpan(span, () => captureEvent({
                level: "error",
                exception: { values: [{ type: FAILURE_TYPE, value: `${site}.${code}` }] },
                fingerprint: [FAILURE_TYPE, site, code],
            }));
            close(code === "timeout" ? "deadline_exceeded" : "internal_error");
        },
    };
}
