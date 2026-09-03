// Ohmni product experience.
//
// This file owns journey state, rendering and disclosure. It owns no
// engineering. Every status, number, net, coordinate and verdict shown here is
// copied from the `experience` projection the backend built out of verified
// typed reports. There is no place in this file where a PASS or FAIL is
// decided, a voltage computed, or a net membership inferred.

import { artifactCurrent, badge, escapeHtml, money, releaseReadiness } from "./view-model.js";
import { BoardView } from "./board-view.js";
import { schematicSvg, transitionFrame, transitionTracks } from "./schematic-view.js";

const $ = (selector) => document.querySelector(selector);

/** A projected Term: lead with the readable name, keep the identifier beside it. */
const human = (term, fallback = "") =>
    escapeHtml(term && typeof term === "object" ? term.human : (term ?? fallback));
/** A term as it reads mid-sentence: lowercase an ordinary leading word only. */
const phrase = (term, fallback = "") => {
    const text = term && typeof term === "object" ? term.human : (term ?? fallback);
    const value = String(text);
    return escapeHtml(value.length > 1 && value[0] !== value[0].toLowerCase()
        && value[1] === value[1].toLowerCase() ? value[0].toLowerCase() + value.slice(1) : value);
};
const technical = (term) =>
    term && typeof term === "object" && term.technical
        ? `<span class="ident">${escapeHtml(term.technical)}</span>` : "";
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const API_VERSION = 2;
const DEMO_FIXTURE_ID = "esp32-bme280-environmental-logger";
const JOB_ID_PATTERN = /^[0-9a-f]{12}$/;
const INSTANCE_PATTERN = /^[0-9a-f]{16}$/;
const UI_VERSION_PATTERN = /^[0-9a-f]{64}$/;

const MESSAGES = Object.freeze({
    backend_unavailable: "The Ohmni demo backend is unavailable. From the repository root, run .\\.venv\\Scripts\\python.exe .\\scripts\\demo_server.py, keep that terminal open, then reload this page.",
    api_ui_mismatch: "This page does not match the running Ohmni demo server. Stop any older demo server, restart it with .\\.venv\\Scripts\\python.exe .\\scripts\\demo_server.py, then reload this page.",
    generation_mismatch: "The Ohmni demo server restarted or changed. Reload this page before starting again.",
    fixture_rejected: "The running Ohmni server rejected the deterministic demo fixture. Restart the demo server from this repository, then reload this page.",
    brief_unavailable: "The backend could not interpret the request. Check the server terminal, then retry.",
    job_initialization_failed: "The backend could not initialize the deterministic demo job. Check the server terminal, then retry.",
    worker_start_failed: "The demo worker failed before progress began. Check the server terminal, then retry.",
    lost_job: "This run is no longer available from the server that created it. Reload this page and start again.",
    pipeline_failed: "The deterministic engineering pipeline failed. Check the server terminal for the fixed diagnostic code, then retry.",
});
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
    "worker_start_failed", "pipeline_failed", "progress_publication_failed", "job_state_invalid",
]);
const STAGES = ["describe", "agree", "design", "review", "build"];

const state = {
    identity: null,
    jobId: null,
    experience: null,
    report: null,
    boardView: null,
    flowId: null,
    systemId: null,
    selected: null,
    transitionTracks: [],
    transitionTimer: null,
    repairTimer: null,
    completionMonitor: null,
};

class DemoClientError extends Error {
    constructor(kind) { super(kind); this.kind = kind; }
}
const fail = (kind) => { throw new DemoClientError(kind); };
const errorKind = (error, fallback) => (error instanceof DemoClientError ? error.kind : fallback);

function exactObject(value, fields) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        && Object.keys(value).length === fields.length
        && fields.every((field) => Object.hasOwn(value, field));
}

async function serverErrorKind(response, fallback) {
    try {
        const payload = await response.json();
        if (exactObject(payload, ["error"]) && typeof payload.error === "string"
            && Object.hasOwn(SERVER_ERROR_KINDS, payload.error)) {
            return SERVER_ERROR_KINDS[payload.error];
        }
    } catch { /* a body we do not own tells us nothing */ }
    return fallback;
}

const sameIdentity = (a, b) => a.api_version === b.api_version
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

async function fetchHealth(fetcher) {
    let response;
    try { response = await fetcher("/api/health", { cache: "no-store" }); }
    catch { fail("backend_unavailable"); }
    if (!response.ok) fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
    let payload;
    try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
    return parseHealth(payload);
}

const identityBody = (identity) => JSON.stringify({
    fixture_id: DEMO_FIXTURE_ID,
    api_version: API_VERSION,
    server_instance_id: identity.server_instance_id,
    ui_version: identity.ui_version,
});
const pollHeaders = (identity) => ({
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

// ── journey ─────────────────────────────────────────────────────────────

// Once a run finishes, the record of what happened, the result, and the files
// are read together. Hiding the Design stage at that point would delete the
// account of what Ohmni actually did, which is most of the point.
const VISIBLE = Object.freeze({
    describe: ["describe"],
    agree: ["agree"],
    design: ["design"],
    review: ["design", "review", "build"],
    build: ["design", "review", "build"],
});

function show(stage) {
    const visible = VISIBLE[stage] || [stage];
    for (const name of STAGES) $(`#${name}`).hidden = !visible.includes(name);
    const index = STAGES.indexOf(stage);
    $$("#journey li").forEach((item, i) => {
        item.classList.toggle("here", i === index);
        item.classList.toggle("done", i < index);
    });
    $(`#${stage}`).scrollIntoView({ behavior: prefersReducedMotion() ? "instant" : "smooth", block: "start" });
}
const prefersReducedMotion = () =>
    typeof globalThis.matchMedia === "function"
    && globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches === true;

function showError(kind) {
    const box = $("#run-error");
    box.hidden = false;
    box.textContent = MESSAGES[kind] || MESSAGES.backend_unavailable;
    $("#design").hidden = false;
}

// ── describe → agree ────────────────────────────────────────────────────

export async function openBrief({ fetcher = globalThis.fetch } = {}) {
    const button = $("#start-supported");
    button.disabled = true;
    try {
        state.identity = await fetchHealth(fetcher);
        let response;
        try {
            response = await fetcher("/api/brief", {
                method: "POST", cache: "no-store",
                headers: { "content-type": "application/json" },
                body: identityBody(state.identity),
            });
        } catch { fail("backend_unavailable"); }
        if (!response.ok) fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        renderBrief(parseBrief(payload, state.identity));
        show("agree");
    } catch (error) {
        showError(errorKind(error, "backend_unavailable"));
    } finally {
        button.disabled = false;
    }
}

function briefGroup(kind, title, note, lines, emptyText) {
    const body = lines.length
        ? lines.map((line) => `<div class="brief-line">
             <div class="brief-label">${escapeHtml(line.label)}</div>
             <div class="brief-value">${escapeHtml(line.value)}</div>
           </div>`).join("")
        : `<p class="brief-empty">${escapeHtml(emptyText)}</p>`;
    return `<section class="brief-group ${kind}">
        <h3>${escapeHtml(title)} <small>${lines.length}</small></h3>
        <p class="fineprint">${escapeHtml(note)}</p>${body}</section>`;
}

export function renderBrief(brief) {
    $("#brief").innerHTML = [
        // Ordered by how much attention each deserves: the things Ohmni decided
        // come first, because those are what a user is here to catch.
        briefGroup("unclear", "Check these — Ohmni worked them out",
                   "You did not say these. Ohmni read them out of your description or filled "
                   + "them in. If any are wrong, go back and say so.",
                   brief.needs_clarification,
                   "Nothing. Everything below came straight from your own words."),
        briefGroup("assumed", "Ohmni assumed",
                   "Assumptions Ohmni made on your behalf, stated so you can disagree.",
                   brief.assumed, "Ohmni assumed nothing."),
        briefGroup("asked", "Straight from what you wrote",
                   "These appear in your own words.",
                   brief.asked_for, "You did not state anything specific."),
    ].join("");
    const decided = brief.needs_clarification.length + brief.assumed.length;
    $("#agree-note").textContent =
        `Ohmni worked out ${decided} thing${decided === 1 ? "" : "s"} you did not say. `
        + `If they look right, it will spend about 90 seconds designing `
        + `"${brief.project_name}" — choosing parts, wiring them, checking the design, `
        + `laying out the board and packaging the files.`;
}

// ── agree → design ──────────────────────────────────────────────────────

export async function startRun({ fetcher = globalThis.fetch, poller = poll, pollDependencies = {} } = {}) {
    stopCompletionMonitor();
    $("#run-error").hidden = true;
    $("#confirm-brief").disabled = true;
    renderPendingStages();
    show("design");
    let jobId;
    try {
        const identity = state.identity || await fetchHealth(fetcher);
        state.identity = identity;
        let response;
        try {
            response = await fetcher("/api/demo", {
                method: "POST", cache: "no-store",
                headers: { "content-type": "application/json" },
                body: identityBody(identity),
            });
        } catch { fail("backend_unavailable"); }
        if (!response.ok || response.status !== 202) {
            fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        }
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        jobId = parseStart(payload, identity);
        state.jobId = jobId;
    } catch (error) {
        $("#confirm-brief").disabled = false;
        return showError(errorKind(error, "backend_unavailable"));
    }
    return poller(jobId, state.identity, { fetcher, ...pollDependencies });
}

const PENDING_STAGES = [
    "Understanding what you asked for", "Choosing parts and wiring them up",
    "Checking the electrical design", "Fixing what it found",
    "Drawing the schematic", "Arranging parts on the board",
    "Drawing the copper", "Checking it can be made",
];

function renderPendingStages() {
    $("#stage-list").innerHTML = PENDING_STAGES.map((label, i) =>
        `<li class="pending"><span class="num">${i + 1}</span>
         <span><span class="what">${escapeHtml(label)}</span></span><span></span></li>`).join("");
    $("#progress-bar").style.width = "0%";
    $("#progress-percent").textContent = "0%";
    $("#progress-now").textContent = "";
}

/** Live progress. Only ever rendered while a job is genuinely in flight. */
function renderProgress(events) {
    const last = events.at(-1);
    const percent = last ? last.percent : 0;
    $("#progress-bar").style.width = `${percent}%`;
    $("#progress-percent").textContent = `${percent}%`;
    $("#progress-now").textContent = last ? last.label : "";
    const items = $$("#stage-list li");
    const reached = Math.min(items.length, events.length);
    items.forEach((item, i) => item.classList.toggle("pending", i >= reached));
}

/**
 * Terminal stage cards for a finished run.
 *
 * The projection emits no RUNNING status for a completed project, so there is
 * nothing here that can imply a finished board is still executing.
 */
function renderSettledStages(stages) {
    $("#progress-bar").style.width = "100%";
    $("#progress-percent").textContent = "100%";
    $("#progress-now").textContent = "Finished";
    $("#stage-list").innerHTML = stages.map((stage, i) => `<li class="settled">
        <span class="num">${i + 1}</span>
        <span><span class="what">${escapeHtml(stage.label)}</span>
              <span class="detail">${escapeHtml(stage.outcome)}</span></span>
        ${badge(stage.status)}</li>`).join("");
}

export async function poll(id, identity, { fetcher = globalThis.fetch, schedule = globalThis.setTimeout, monitorer = beginCompletionMonitor } = {}) {
    try {
        let response;
        try { response = await fetcher(`/api/jobs/${id}`, { cache: "no-store", headers: pollHeaders(identity) }); }
        catch { fail("backend_unavailable"); }
        if (!response.ok) {
            fail(await serverErrorKind(response, response.status === 404 ? "lost_job"
                : response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        }
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        const job = parseJob(payload, id, identity);
        const disposition = pollDisposition(job.status);
        if (disposition === "complete") {
            $("#confirm-brief").disabled = false;
            renderResult(job.report, id);
            monitorer(identity, { fetcher });
            return;
        }
        if (disposition === "failed") {
            $("#confirm-brief").disabled = false;
            return showError(job.error_code === "worker_start_failed" ? "worker_start_failed" : "pipeline_failed");
        }
        renderProgress(job.progress);
        const dependencies = { fetcher, schedule, monitorer };
        schedule(() => void poll(id, identity, dependencies), 900);
    } catch (error) {
        $("#confirm-brief").disabled = false;
        return showError(errorKind(error, "backend_unavailable"));
    }
}

export function stopCompletionMonitor() {
    const cleanup = state.completionMonitor;
    state.completionMonitor = null;
    if (cleanup) cleanup();
}

export function beginCompletionMonitor(identity, { fetcher = globalThis.fetch, setIntervalFn = globalThis.setInterval, clearIntervalFn = globalThis.clearInterval, windowTarget = globalThis.window, documentTarget = globalThis.document } = {}) {
    stopCompletionMonitor();
    let stopped = false;
    let busy = false;
    const invalidate = (kind) => {
        if (stopped) return;
        $("#review").hidden = true;
        $("#build").hidden = true;
        showError(kind);
    };
    const check = async () => {
        if (stopped || busy) return true;
        busy = true;
        try {
            const current = await fetchHealth(fetcher);
            if (!sameIdentity(identity, current)) { invalidate("generation_mismatch"); return false; }
            return true;
        } catch (error) {
            invalidate(errorKind(error, "backend_unavailable"));
            return false;
        } finally { busy = false; }
    };
    const timer = typeof setIntervalFn === "function" ? setIntervalFn(check, 3000) : null;
    if (timer && typeof timer.unref === "function") timer.unref();
    const focus = () => { void check(); };
    const visible = () => { if (documentTarget?.hidden === false) void check(); };
    windowTarget?.addEventListener?.("focus", focus);
    documentTarget?.addEventListener?.("visibilitychange", visible);
    state.completionMonitor = () => {
        stopped = true;
        if (timer !== null && typeof clearIntervalFn === "function") clearIntervalFn(timer);
        windowTarget?.removeEventListener?.("focus", focus);
        documentTarget?.removeEventListener?.("visibilitychange", visible);
    };
    return check;
}

// ── result ──────────────────────────────────────────────────────────────

function renderResult(report, jobId) {
    state.report = report;
    state.experience = report.experience;
    const exp = state.experience;

    renderSettledStages(exp.stages);
    $("#review-title").textContent = exp.headline;
    $("#review-subhead").textContent = exp.subhead;

    const release = releaseReadiness(report.release);
    $("#release-badge").innerHTML = `${badge(release.status)}
        <p>${escapeHtml(release.label)}. ${escapeHtml(artifactCurrent(report.release))} against the board Ohmni just built.</p>`;

    renderSystems(exp.systems);
    renderFlows(exp.flows);
    renderRepair(exp.repair);
    renderTour(exp.tour);
    renderChecks(exp.check_sections);
    renderConfidence(exp.confidence);
    renderParts(exp.components);
    renderFiles(report, jobId);
    renderBringUp(exp);
    setupTransform(exp);
    $("#schematic-holder").innerHTML = schematicSvg(exp.schematic, {});

    show("review");
    setupBoard(exp.board);
}

function setupBoard(board) {
    const note = $("#board-thickness-note");
    if (note) note.textContent = board.thickness_note;
    const canvas = $("#board-canvas");
    if (!canvas || typeof canvas.getContext !== "function" || !canvas.getContext("2d")) {
        $("#board-empty").hidden = false;
        return;
    }
    state.boardView = new BoardView(canvas, {
        onSelect: (ref) => { state.selected = ref; renderSelection(ref); },
    });
    state.boardView.setBoard(board);
    globalThis.addEventListener?.("resize", () => state.boardView?.render());
    renderSelection(null);
}

export function renderSelection(ref) {
    const box = $("#selection");
    const exp = state.experience;
    if (!ref) {
        box.innerHTML = `<h4>Nothing selected</h4>
            <p>Pick any part — on the board, or from a system on the right — to see what it
               is and why Ohmni put it there.</p>`;
        return;
    }
    const card = exp.components.find((c) => c.ref === ref);
    const placed = exp.board.components.find((c) => c.ref === ref);
    const grouping = exp.grouping.find((g) => g.component_ref === ref);
    const system = exp.systems.find((s) => s.system === card?.system);
    if (!card || !placed) return;
    const nets = placed.net_names.map((name) => {
        const match = exp.flows.flatMap((f) => f.stages).find((s) => s.net_names.includes(name));
        return match ? name : name;
    });
    box.innerHTML = `<h4>${human(card.name, card.ref)}</h4>
        <div class="part-id">${escapeHtml(card.ref)} · ${escapeHtml(card.part_id)}</div>
        <p>${escapeHtml(card.purpose)}</p>
        <dl>
          <dt>Part of</dt><dd>${escapeHtml(system ? system.label : card.system)}</dd>
          ${card.value ? `<dt>Value</dt><dd>${escapeHtml(card.value)}</dd>` : ""}
          <dt>Difficulty</dt><dd>${escapeHtml(
              card.assembly_reason || card.assembly_difficulty || "not assessed")}</dd>
        </dl>
        <details class="disclose"><summary>Technical details</summary>
          <p class="fineprint">Reference <code>${escapeHtml(card.ref)}</code>,
             part <code>${escapeHtml(card.part_id)}</code>,
             package <code>${escapeHtml(card.package)}</code>.</p>
          <p class="fineprint">Connects to: <span class="nets">${
              escapeHtml(nets.join(" · ") || "nothing")}</span></p>
          ${card.name?.detail ? `<p class="fineprint">${escapeHtml(card.name.detail)}</p>` : ""}
          <p class="fineprint">Grouped because: ${escapeHtml(grouping ? grouping.basis : "unknown")}.</p>
          <p class="fineprint">Placed because: ${escapeHtml(placed.placement_reason)}.</p>
          <p class="fineprint">${escapeHtml(card.assembly_basis)}</p>
          <p class="fineprint">Price knowledge ${escapeHtml(card.price_knowledge)}
             · ${escapeHtml(card.unit_price ? `unit ${money(card.unit_price)}` : "unit price UNKNOWN")}</p>
        </details>`;
}

function renderSystems(systems) {
    const byRef = new Map(state.experience.components.map((c) => [c.ref, c]));
    $("#systems").innerHTML = systems.map((system) => `<section class="system"
        data-system="${escapeHtml(system.system)}">
        <button type="button" class="system-head" data-system-select="${escapeHtml(system.system)}">
          <span class="system-name"><span class="dot ${escapeHtml(system.system)}"></span>${escapeHtml(system.label)}</span>
          <p>${escapeHtml(system.summary)}</p>
        </button>
        <ul class="system-parts">${system.component_refs.map((ref) => {
            const card = byRef.get(ref);
            return `<li><button type="button" class="part-pick" data-ref="${escapeHtml(ref)}">
              <span>${human(card?.name, ref)}</span>
              <span class="ident">${escapeHtml(ref)}</span></button></li>`;
        }).join("")}</ul>
      </section>`).join("");
}

function renderFlows(flows) {
    $("#flow-tabs").innerHTML = flows.map((flow) =>
        `<button type="button" class="chip" role="tab" data-flow="${escapeHtml(flow.flow_id)}"
          aria-selected="false">${escapeHtml(flow.label)}</button>`).join("")
        + `<button type="button" class="chip" data-flow="" aria-selected="false">Show everything</button>`;
    $("#flow-detail").innerHTML = `<p class="flow-summary">Pick one above.</p>`;
}

function selectFlow(flowId) {
    const exp = state.experience;
    state.flowId = flowId || null;
    state.systemId = null;
    $$("#flow-tabs .chip").forEach((chip) => {
        const on = chip.dataset.flow === (flowId || "");
        chip.classList.toggle("on", on);
        chip.setAttribute("aria-selected", String(on));
    });
    $$(".system").forEach((item) => item.classList.remove("on"));
    $$("#systems .part-pick").forEach((button) => button.classList.remove("on"));
    if (!flowId) {
        $("#flow-detail").innerHTML = `<p class="flow-summary">Showing the whole board.</p>`;
        state.boardView?.setHighlight({});
        return;
    }
    const flow = exp.flows.find((f) => f.flow_id === flowId);
    if (!flow) return;
    $("#flow-detail").innerHTML = `
        <p class="flow-summary"><strong>${escapeHtml(flow.question)}</strong> ${escapeHtml(flow.summary)}</p>
        <ol class="flow-stages">${flow.stages.map((stage, i) => `<li>
            <button type="button" class="stage-focus" data-stage="${i}">
              <span class="step">${i + 1}</span>
              <div><strong>${escapeHtml(stage.title)}</strong>
                <p>${escapeHtml(stage.detail)}</p>
                ${stage.net_names.length ? `<p class="nets">${escapeHtml(stage.net_names.join(" · "))}</p>` : ""}
              </div></button></li>`).join("")}</ol>
        <p class="fineprint">Click a step to light up only that part of the path.</p>
        <details class="disclose"><summary>Where did this come from?</summary>
          <p class="fineprint">Derived from ${escapeHtml(flow.basis)}. Ohmni does not
          invent a path: every connection named above exists in the circuit.</p></details>`;
    // Start on the first step. The union of a whole flow is often most of the
    // board, which lights everything and therefore explains nothing.
    focusFlowStage(0);
}

export function focusFlowStage(index) {
    const flow = state.experience?.flows.find((f) => f.flow_id === state.flowId);
    const stage = flow?.stages[index];
    if (!stage) return;
    $$("#flow-detail .stage-focus").forEach((button) =>
        button.classList.toggle("on", Number(button.dataset.stage) === index));
    state.boardView?.setHighlight({ refs: stage.component_refs, nets: stage.net_names });
}

function selectSystem(systemId) {
    const exp = state.experience;
    const system = exp.systems.find((s) => s.system === systemId);
    if (!system) return;
    state.systemId = systemId;
    state.flowId = null;
    $$(".system").forEach((item) => item.classList.toggle("on", item.dataset.system === systemId));
    $$("#systems .part-pick").forEach((button) => button.classList.remove("on"));
    $$("#flow-tabs .chip").forEach((chip) => { chip.classList.remove("on"); chip.setAttribute("aria-selected", "false"); });
    $("#flow-detail").innerHTML = `<p class="flow-summary"><strong>${escapeHtml(system.label)}.</strong>
        ${escapeHtml(system.summary)}</p>
        <p class="nets">${escapeHtml(system.component_refs.join(" · "))}</p>`;
    state.boardView?.setHighlight({ systems: [systemId] });
}

// ── repair replay ───────────────────────────────────────────────────────

function renderRepair(repair) {
    const panel = $("#repair-panel");
    if (!repair.happened) {
        panel.innerHTML = `<h3>Nothing needed fixing</h3><p class="panel-note">${escapeHtml(repair.headline)}</p>`;
        return;
    }
    // Every number on this scale comes from the projection. A value the
    // backend did not supply is left off rather than drawn at zero.
    const { applied_v: applied, limit_v: limit, absolute_max_v: absMax,
            repaired_v: repaired, operating_min_v: minimum } = repair;
    const span = Math.max(applied || 0, limit || 0, absMax || 0) * 1.15 || 1;
    const pct = (value) => `${Math.min(100, Math.max(0, (value / span) * 100)).toFixed(1)}%`;
    const mark = (value, kind, label) => (typeof value === "number"
        ? `<div class="scale-mark ${kind}" style="left:${pct(value)}" title="${escapeHtml(label)}"></div>`
        : "");
    panel.innerHTML = `
      <h3>${escapeHtml(repair.plain_summary || "Ohmni caught a problem")}</h3>
      <p class="panel-note">Ohmni found this before anything was drawn. It is the part that
        makes the rest worth trusting.</p>
      <div class="voltage-scale">
        <div class="scale-bar">
          ${typeof minimum === "number" && typeof limit === "number"
            ? `<div class="scale-ok" style="left:${pct(minimum)};width:${
                (Math.min(100, Math.max(0, ((limit - minimum) / span) * 100)).toFixed(1))}%"></div>` : ""}
          ${mark(absMax, "absmax", "can be damaged above this")}
          ${mark(applied, "applied", "what it was connected to")}
          ${mark(repaired, "fixed", "what Ohmni moved it to")}
        </div>
        <div class="scale-legend"><span>0 V</span><span>${span.toFixed(1)} V</span></div>
        <ul class="scale-keys">
          <li class="key ok">The ${phrase(repair.part, "part")} works between
            ${escapeHtml(minimum ?? "?")} V and ${escapeHtml(limit ?? "?")} V</li>
          ${typeof absMax === "number"
            ? `<li class="key absmax">Above ${escapeHtml(absMax)} V it can be permanently damaged</li>` : ""}
          <li class="key applied">${typeof applied === "number"
            ? `It was going to get ${phrase(repair.from_net, `${applied} V`)}`
            : "The applied voltage is UNKNOWN"}</li>
          ${typeof repaired === "number"
            ? `<li class="key fixed">Ohmni moved it to ${phrase(repair.to_net, "another supply")}</li>` : ""}
        </ul>
      </div>
      <ol class="repair-steps">${repair.steps.map((step) => `<li class="key-${escapeHtml(step.key)}">
          <strong>${escapeHtml(step.headline)}</strong><p>${escapeHtml(step.body)}</p></li>`).join("")}</ol>
      <div class="repair-controls">
        <button type="button" id="repair-play" class="secondary">Replay what happened</button>
      </div>
      <details class="disclose"><summary>Show the manufacturer evidence</summary>
        ${repair.evidence.map((item) => `<p class="fineprint">
          ${badge(item.status)} <strong>${escapeHtml(item.label)}</strong> —
          ${escapeHtml(item.value || "UNKNOWN")}
          ${item.source ? ` · ${escapeHtml(item.source)}${item.page ? ` p.${escapeHtml(item.page)}` : ""}` : ""}
          <br>${escapeHtml(item.detail || "")}</p>`).join("")}</details>
      <details class="disclose"><summary>Technical details</summary>
        <p class="fineprint">Part <code>${escapeHtml(repair.component_ref || "")}</code>
          (<code>${escapeHtml(repair.part_id || "")}</code>) moved from
          <code>${escapeHtml(repair.from_net?.technical || "")}</code> to
          <code>${escapeHtml(repair.to_net?.technical || "")}</code>
          — ${escapeHtml(repair.moved_pins.length)} pin(s).</p>
        <p class="fineprint">Rule <code>${escapeHtml(repair.rule_id || "")}</code>,
          severity ${escapeHtml(repair.severity || "")}.
          Specified range ${escapeHtml(repair.supported_range || "unknown")}.</p>
        <p class="fineprint">${escapeHtml(repair.technical_description || "")}</p></details>`;
    $("#repair-play")?.addEventListener("click", () => playRepair(repair));
    playRepair(repair);
}

function playRepair(repair) {
    if (state.repairTimer) { clearInterval(state.repairTimer); state.repairTimer = null; }
    const items = $$("#repair-panel .repair-steps li");
    items.forEach((item) => item.classList.remove("shown"));
    if (prefersReducedMotion()) {
        items.forEach((item) => item.classList.add("shown"));
        state.boardView?.setHighlight({ refs: [repair.component_ref], nets: [repair.to_net] });
        return;
    }
    let index = 0;
    const advance = () => {
        if (index >= items.length) { clearInterval(state.repairTimer); state.repairTimer = null; return; }
        items[index].classList.add("shown");
        const step = repair.steps[index];
        if (step && state.boardView) {
            state.boardView.setHighlight({ refs: step.component_refs, nets: step.net_names });
        }
        index += 1;
    };
    advance();
    state.repairTimer = setInterval(advance, 1400);
}

// ── schematic → board ───────────────────────────────────────────────────

function setupTransform(exp) {
    state.transitionTracks = transitionTracks(exp.schematic, exp.board);
    const stage = $("#transform-stage");
    stage.innerHTML = state.transitionTracks.map((track) =>
        `<div class="tpart" data-ref="${escapeHtml(track.ref)}">
           <span class="sym">${escapeHtml(track.ref)}</span>
           <span class="fp">${escapeHtml(track.ref)}</span></div>`).join("");
    drawTransform(0);
    $("#transform-scrub").addEventListener("input", (event) => {
        stopTransformTimer();
        drawTransform(Number(event.target.value) / 100);
    });
    $("#transform-play").addEventListener("click", () => playTransform());
}

function stopTransformTimer() {
    if (state.transitionTimer) { clearInterval(state.transitionTimer); state.transitionTimer = null; }
}

function drawTransform(t) {
    const frames = transitionFrame(state.transitionTracks, t);
    const stage = $("#transform-stage");
    const width = stage.clientWidth || 520;
    const height = stage.clientHeight || 260;
    for (const frame of frames) {
        const element = stage.querySelector(`[data-ref="${CSS.escape(frame.ref)}"]`);
        if (!element) continue;
        element.style.left = `${8 + frame.x * (width - 16)}px`;
        element.style.top = `${14 + frame.y * (height - 28)}px`;
        const scale = Math.max(14, Math.min(64, frame.w * 2.6));
        element.style.width = `${scale}px`;
        element.style.height = `${Math.max(12, Math.min(64, frame.h * 2.6))}px`;
        element.querySelector(".sym").style.opacity = String(frame.symbolOpacity);
        element.querySelector(".fp").style.opacity = String(frame.footprintOpacity);
    }
    $("#transform-scrub").value = String(Math.round(t * 100));
    $("#transform-label").textContent =
        t < 0.05 ? "Schematic — what connects to what"
        : t > 0.95 ? "Board — where everything physically is"
        : "Moving parts into their places";
}

function playTransform() {
    stopTransformTimer();
    if (prefersReducedMotion()) { drawTransform(1); return; }
    let t = 0;
    drawTransform(0);
    state.transitionTimer = setInterval(() => {
        t += 0.02;
        if (t >= 1) { drawTransform(1); stopTransformTimer(); return; }
        drawTransform(t);
    }, 28);
}

// ── tour ────────────────────────────────────────────────────────────────

function renderTour(tour) {
    const panel = $("#tour-panel");
    panel.innerHTML = `<h3>Walk me through my board</h3>
      <p class="panel-note">A guided read of what you built. Each step is written from this
        project's own recorded data — it is a deterministic walkthrough, not a language model.</p>
      <div class="tour-body">
        <ol class="tour-steps">${tour.steps.map((step, i) =>
            `<li><button type="button" data-tour="${i}">${escapeHtml(step.title)}</button></li>`).join("")}</ol>
        <div class="tour-narration" id="tour-narration"></div>
      </div>
      <details class="disclose"><summary>How this would work with a real model</summary>
        <p class="fineprint">Narration source: <code>${escapeHtml(tour.narration_source)}</code>.
          Each step already carries the exact authoritative facts a model would be given. A model
          may one day rephrase the narration; it will still not choose the facts, the components,
          or any verification result.</p></details>`;
    showTourStep(0);
}

function showTourStep(index) {
    const tour = state.experience.tour;
    const step = tour.steps[index];
    if (!step) return;
    $$("#tour-panel [data-tour]").forEach((button) =>
        button.classList.toggle("on", Number(button.dataset.tour) === index));
    $("#tour-narration").innerHTML = `<h4>${escapeHtml(step.title)}</h4>
        <p>${escapeHtml(step.narration)}</p>
        <ul class="tour-facts">${step.facts.map((fact) => `<li>${escapeHtml(fact)}</li>`).join("")}</ul>`;
    if (state.boardView) {
        state.boardView.setHighlight(
            step.component_refs.length || step.net_names.length
                ? { refs: step.component_refs, nets: step.net_names }
                : {},
        );
    }
}

// ── checks and confidence ───────────────────────────────────────────────

function renderChecks(sections) {
    $("#checks").innerHTML = sections.map((section) => `<section class="check-family">
        <h4>${escapeHtml(section.label)}</h4>
        <p class="fineprint">${escapeHtml(section.summary)}</p>
        ${section.groups.map((group) => `<details class="check">
          <summary><span>${badge(group.status)}</span>
            <span><span class="check-label">${escapeHtml(group.label)}</span><br>
                  <span class="check-q">${escapeHtml(group.question)}</span></span></summary>
          <div class="check-rules">${group.rules.length ? group.rules.map((rule) => `
              <div class="rule"><code>${escapeHtml(rule.rule_id)}</code>
                <span>${escapeHtml(rule.title)}</span>${badge(rule.outcome)}
                ${rule.limitations.length ? `<span class="limits">A pass here does not establish:
                   ${escapeHtml(rule.limitations.join("; "))}</span>` : ""}
                ${rule.missing_data.length ? `<span class="limits">Missing data:
                   ${escapeHtml(rule.missing_data.join("; "))}</span>` : ""}
              </div>`).join("")
          : `<p class="fineprint">Ohmni has no rules here, so it reports
               ${escapeHtml(group.status)} rather than a pass.</p>`}</div></details>`).join("")}
      </section>`).join("");
}

function renderConfidence(confidence) {
    const line = (item) => `<li>
        <div class="conf-head"><strong>${escapeHtml(item.label)}</strong>${badge(item.status)}</div>
        <p>${escapeHtml(item.detail)}</p></li>`;
    $("#confidence-panel").innerHTML = `<h3>How much should you trust this?</h3>
      <div class="conf-cols">
        <div><h4>Checked</h4>
          <p>Each of these ran and reported a result.</p>
          <ul class="conf-list">${confidence.checked.map(line).join("")}</ul></div>
        <div><h4>Not verified</h4>
          <p>Ohmni is telling you what it did not establish. This half matters more.</p>
          <ul class="conf-list">${confidence.not_verified.map(line).join("")}</ul></div>
      </div>`;
}

// ── build ───────────────────────────────────────────────────────────────

function renderParts(components) {
    $("#parts").innerHTML = components.map((card) => `<article class="part-card">
        <header><span class="ref">${human(card.name, card.ref)}</span>
          <span class="ident">${escapeHtml(card.ref)}</span></header>
        <p class="purpose">${escapeHtml(card.purpose)}</p>
        <div class="meta">
          ${card.assembly_reason ? `<span class="tag ${
              /reflow|not realistic|does not recognise/.test(card.assembly_reason) ? "hard" : ""
          }">${escapeHtml(card.assembly_reason)}</span>` : ""}
          <span class="tag">${escapeHtml(card.price_knowledge === "UNKNOWN" ? "price UNKNOWN"
              : money(card.unit_price, card.price_knowledge))}</span>
        </div>
        <details class="disclose"><summary>Technical details</summary>
          <p class="fineprint">${escapeHtml(card.part_id)} · package
            ${escapeHtml(card.package)}${card.value ? ` · ${escapeHtml(card.value)}` : ""}
            · ${escapeHtml(card.line_quantity)} of this part on the board</p>
          ${card.name?.detail ? `<p class="fineprint">${escapeHtml(card.name.detail)}</p>` : ""}
          <p class="fineprint">${escapeHtml(card.assembly_basis)}</p>
        </details>
      </article>`).join("");
}

function renderFiles(report, jobId) {
    const economics = report.economics;
    $("#files-panel").innerHTML = `<h3>Files</h3>
      <p class="panel-note">These open in KiCad 10 and are what a fabricator needs. Ohmni checked
        them; nobody has built them.</p>
      <div class="download-row">
        <a href="/api/artifacts/${escapeHtml(jobId)}/golden.kicad_sch">Schematic (.kicad_sch)</a>
        <a href="/api/artifacts/${escapeHtml(jobId)}/golden.kicad_pcb">Board (.kicad_pcb)</a>
      </div>
      <ul class="file-list">${report.release.files.map((file) => `<li>
          <span>${escapeHtml(file.relative_path)} <span class="fineprint">${escapeHtml(file.kind)}</span></span>
          <span class="hash">${escapeHtml(String(file.sha256).slice(0, 16))}…</span></li>`).join("")}</ul>
      <p class="fineprint">Prototype economics: ${escapeHtml(money(economics.known_consumption_cost))}
        of known parts on one board, ${escapeHtml(money(economics.known_purchase_requirement))} to actually
        buy them. Fabrication ${escapeHtml(economics.fabrication)}, shipping ${escapeHtml(economics.shipping)}.
        ${escapeHtml(economics.pricing_source)}.</p>`;
}

/** Bench steps, each carrying only what Ohmni actually derived. */
function renderBringUp(exp) {
    const bench = exp.confidence.not_verified.find((item) => item.status === "NOT_YET_VERIFIED");
    $("#bringup-panel").innerHTML = `<h3>When the board arrives</h3>
      <p class="panel-note">${escapeHtml(bench ? bench.detail : "")} Where Ohmni worked a value
        out, it is shown so you can compare it against what the hardware actually does.</p>
      <ol class="bringup-list">${exp.bring_up.map((step) => `<li>
          <span>${escapeHtml(step.action)}
            ${step.basis ? `<span class="fineprint">${escapeHtml(step.basis)}</span>` : ""}</span>
          <span class="predicted ${step.prediction ? "" : "none"}">${
            step.prediction ? escapeHtml(step.prediction) : "Ohmni has no prediction"}</span></li>`).join("")}</ol>
      <p class="fineprint">If a measurement disagrees with a value Ohmni worked out, the hardware
        is right. Where Ohmni has no prediction it says so rather than guessing.</p>`;
}

// ── wiring ──────────────────────────────────────────────────────────────

function attach() {
    $("#start-supported")?.addEventListener("click", () => void openBrief());
    $("#confirm-brief")?.addEventListener("click", () => void startRun());
    $("#back-to-describe")?.addEventListener("click", () => show("describe"));

    $("#flow-tabs")?.addEventListener("click", (event) => {
        const chip = event.target.closest("[data-flow]");
        if (chip) selectFlow(chip.dataset.flow);
    });
    $("#flow-detail")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-stage]");
        if (button) focusFlowStage(Number(button.dataset.stage));
    });
    $("#systems")?.addEventListener("click", (event) => {
        const part = event.target.closest("[data-ref]");
        if (part) {
            // A non-spatial route to any component: the board follows the list.
            state.boardView?.select(part.dataset.ref);
            state.boardView?.setHighlight({ refs: [part.dataset.ref] });
            renderSelection(part.dataset.ref);
            $$("#systems .part-pick").forEach((button) =>
                button.classList.toggle("on", button.dataset.ref === part.dataset.ref));
            return;
        }
        const head = event.target.closest("[data-system-select]");
        if (head) selectSystem(head.dataset.systemSelect);
    });
    $("#tour-panel")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-tour]");
        if (button) showTourStep(Number(button.dataset.tour));
    });
    $$("[data-view]").forEach((button) => button.addEventListener("click", () => {
        const view = button.dataset.view;
        $$("[data-view]").forEach((other) => other.classList.toggle("on", other === button && view !== "reset"));
        if (view === "reset") { state.boardView?.setOptions({}); state.boardView?.frame(); return; }
        state.boardView?.setOptions({ showBack: view === "back" });
    }));
    $$("[data-toggle]").forEach((button) => button.addEventListener("click", () => {
        const key = button.dataset.toggle;
        const on = !button.classList.contains("on");
        button.classList.toggle("on", on);
        state.boardView?.setOptions({ [key]: on });
    }));
    $("#explode")?.addEventListener("input", (event) => {
        state.boardView?.setOptions({ explode: Number(event.target.value) / 100 });
    });
}

if (typeof document !== "undefined" && document.getElementById("start-supported")) attach();
