// Generation-bound HTTP contracts. This module validates transport shape and identity;
// it never creates engineering evidence or verdicts.

const API_VERSION = 2;
const DEMO_FIXTURE_ID = "esp32-bme280-environmental-logger";
const JOB_ID_PATTERN = /^[0-9a-f]{12}$/;
const INSTANCE_PATTERN = /^[0-9a-f]{16}$/;
const UI_VERSION_PATTERN = /^[0-9a-f]{64}$/;

const SERVER_ERROR_KINDS = Object.freeze({
    fixture_rejected: "fixture_rejected",
    api_version_mismatch: "api_ui_mismatch",
    server_instance_mismatch: "generation_mismatch",
    ui_version_mismatch: "generation_mismatch",
    job_start_unavailable: "job_initialization_failed",
    brief_unavailable: "brief_unavailable",
    job_not_found: "lost_job",
});
const FAILED_JOB_CODES = new Set([
    "worker_start_failed", "pipeline_failed", "progress_publication_failed", "job_state_invalid", "server_restarted", "routing_incomplete",
]);
class DemoClientError extends Error {
    constructor(kind) { super(kind); this.kind = kind; }
}
export const fail = (kind) => { throw new DemoClientError(kind); };
export const errorKind = (error, fallback) => (error instanceof DemoClientError ? error.kind : fallback);

function exactObject(value, fields) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        && Object.keys(value).length === fields.length
        && fields.every((field) => Object.hasOwn(value, field));
}

export async function serverErrorKind(response, fallback) {
    try {
        const payload = await response.json();
        if (exactObject(payload, ["error"]) && typeof payload.error === "string"
            && Object.hasOwn(SERVER_ERROR_KINDS, payload.error)) {
            return SERVER_ERROR_KINDS[payload.error];
        }
    } catch { /* a body we do not own tells us nothing */ }
    return fallback;
}

export const sameIdentity = (a, b) => a.api_version === b.api_version
    && a.server_instance_id === b.server_instance_id && a.ui_version === b.ui_version;

export function parseHealth(payload) {
    if (!exactObject(payload, ["status", "fixture_id", "api_version", "server_instance_id", "ui_version"])) fail("api_ui_mismatch");
    if (payload.api_version !== API_VERSION || payload.status !== "ready"
        || typeof payload.server_instance_id !== "string" || !INSTANCE_PATTERN.test(payload.server_instance_id)
        || typeof payload.ui_version !== "string" || !UI_VERSION_PATTERN.test(payload.ui_version)) fail("api_ui_mismatch");
    if (payload.fixture_id !== DEMO_FIXTURE_ID) fail("fixture_rejected");
    return {
        api_version: payload.api_version,
        server_instance_id: payload.server_instance_id,
        ui_version: payload.ui_version,
    };
}

export async function fetchHealth(fetcher) {
    let response;
    try { response = await fetcher("/api/health", { cache: "no-store" }); }
    catch { fail("backend_unavailable"); }
    if (!response.ok) fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
    let payload;
    try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
    return parseHealth(payload);
}

export const identityBody = (identity) => JSON.stringify({
    fixture_id: DEMO_FIXTURE_ID,
    api_version: API_VERSION,
    server_instance_id: identity.server_instance_id,
    ui_version: identity.ui_version,
});
export const pollHeaders = (identity) => ({
    "X-Ohmni-Server-Instance": identity.server_instance_id,
    "X-Ohmni-API-Version": String(API_VERSION),
    "X-Ohmni-UI-Version": identity.ui_version,
});

export function parseBrief(payload, identity) {
    if (!exactObject(payload, ["brief", "api_version", "server_instance_id", "ui_version"])) fail("api_ui_mismatch");
    if (payload.api_version !== API_VERSION) fail("api_ui_mismatch");
    if (payload.server_instance_id !== identity.server_instance_id
        || payload.ui_version !== identity.ui_version) fail("generation_mismatch");
    const brief = payload.brief;
    if (!brief || typeof brief !== "object"
        || !Array.isArray(brief.asked_for) || !Array.isArray(brief.assumed)
        || !Array.isArray(brief.needs_clarification)) fail("api_ui_mismatch");
    return brief;
}

export function parseStart(payload, identity) {
    if (!exactObject(payload, ["job_id", "status", "api_version", "server_instance_id", "ui_version"])) fail("api_ui_mismatch");
    if (payload.api_version !== API_VERSION) fail("api_ui_mismatch");
    if (payload.server_instance_id !== identity.server_instance_id
        || payload.ui_version !== identity.ui_version) fail("generation_mismatch");
    if (typeof payload.job_id !== "string" || !JOB_ID_PATTERN.test(payload.job_id)
        || payload.status !== "queued") fail("api_ui_mismatch");
    return payload.job_id;
}

const validProgressEvent = (event) =>
    exactObject(event, ["stage", "label", "status", "detail", "percent"])
    && [event.stage, event.label, event.status, event.detail].every((v) => typeof v === "string")
    && Number.isInteger(event.percent) && event.percent >= 0 && event.percent <= 100;

export function parseJob(payload, id, identity) {
    const fields = ["job_id", "status", "progress", "report", "error", "error_code",
                    "api_version", "server_instance_id", "ui_version"];
    if (!exactObject(payload, fields) || payload.api_version !== API_VERSION) fail("api_ui_mismatch");
    if (payload.server_instance_id !== identity.server_instance_id
        || payload.ui_version !== identity.ui_version) fail("generation_mismatch");
    if (payload.job_id !== id || !Array.isArray(payload.progress)
        || !payload.progress.every(validProgressEvent)) fail("api_ui_mismatch");
    if (payload.status === "queued" || payload.status === "running") {
        if (payload.report !== null || payload.error !== null || payload.error_code !== null) fail("api_ui_mismatch");
    } else if (payload.status === "complete") {
        if (payload.report === null || typeof payload.report !== "object" || Array.isArray(payload.report)
            || payload.error !== null || payload.error_code !== null) fail("api_ui_mismatch");
        if (!payload.report.experience || typeof payload.report.experience !== "object") fail("api_ui_mismatch");
    } else if (payload.status === "failed") {
        if (payload.report !== null || payload.error !== "Demo pipeline failed"
            || typeof payload.error_code !== "string" || !FAILED_JOB_CODES.has(payload.error_code)) fail("api_ui_mismatch");
    } else fail("api_ui_mismatch");
    return payload;
}

export function pollDisposition(status) {
    if (status === "queued" || status === "running") return "continue";
    if (status === "complete" || status === "failed") return status;
    return "invalid";
}
