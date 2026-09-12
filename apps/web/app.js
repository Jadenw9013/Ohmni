// Ohmni product experience.
//
// This file owns journey state, rendering and disclosure. It owns no
// engineering. Every status, number, net, coordinate and verdict shown here is
// copied from the `experience` projection the backend built out of verified
// typed reports. There is no place in this file where a PASS or FAIL is
// decided, a voltage computed, or a net membership inferred.

import { artifactCurrent, badge, escapeHtml, money, releaseReadiness, requirementResultsHtml } from "./view-model.js";
import { BoardView, createCamera } from "./board-view.js";
import { schematicSvg, transitionFrame, transitionTracks } from "./schematic-view.js";
import { initializeReferencePreview } from "./reference-preview.js";
import { mountBoardControls } from "./board-controls.js";
import { mountCircuitLessons } from "./circuit-lessons.js";
import { mountProjectWorkbench } from "./project-workbench.js";
import { projectRequest, parseProjectStart } from "./project-contract.js";

import { errorKind, fetchHealth, identityBody, requestBody, freeTextProblem, pollHeaders, sameIdentity, fail, serverErrorKind, parseBrief, parseStart, parseJob, pollDisposition, API_BASE } from "./client-contract.js";
export { parseHealth, parseBrief, parseStart, parseJob, pollDisposition, requestBody, freeTextProblem } from "./client-contract.js";

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

const MESSAGES = Object.freeze({
    backend_unavailable: "The demo backend is unavailable. Your page is still here. Check that the local Ohmni server is running, then try again.",
    api_ui_mismatch: "This page does not match the running Ohmni demo server. Reload the page to use the current version.",
    generation_mismatch: "The Ohmni server restarted or changed. This run belongs to the earlier server. Start a new example to continue.",
    fixture_rejected: "The server rejected the deterministic demo fixture. This page needs the matching Ohmni server; reload after restarting it.",
    brief_unavailable: "The server could not prepare the example brief. Nothing has been built. Try again when the server is ready.",
    job_initialization_failed: "The server could not start this example. Nothing has been built. Try again.",
    worker_start_failed: "The demo worker failed before progress began. Check the local server setup, then start a fresh run.",
    lost_job: "This run is no longer available from the server that created it. Start a new example to continue.",
    pipeline_failed: "The engineering pipeline failed before a completed result was available. Start a fresh run after checking the local server setup.",
    routing_incomplete: "Ohmni could not finish all copper connections. No build package was released. Routing has a three-minute time limit and bounded search. Retry with fewer builds running, or simplify your project and try again.",
    eda_tool_failed: "KiCad could not complete the hardware checks. No build package was released. Check that KiCad can run on this computer, then retry this revision. Your saved choices are safe.",
});
const STAGES = ["describe", "agree", "design", "review", "build"];

const state = {
    stage: "describe",
    panel: "board",
    brief: null,
    // The free-text request this session is running, or null for the scripted
    // fixture. It decides which payload shape every later call sends.
    request: null,
    runStatus: "idle",
    connection: "unchecked",
    retryAction: null,
    reconnect: null,
    pollVersion: 0,
    identity: null,
    jobId: null,
    experience: null,
    report: null,
    boardView: null,
    boardControls: null,
    boardLessons: null,
    flowId: null,
    systemId: null,
    selected: null,
    transitionTracks: [],
    transitionTimer: null,
    repairTimer: null,
    completionMonitor: null,
    customProject: false,
    workbench: null,
    revisionContext: null,
    projectName: null,
};

// ── journey ─────────────────────────────────────────────────────────────

const STAGE_TITLES = Object.freeze({
    describe: "Your next little invention",
    agree: "Meet your project",
    design: "Inside the workshop",
    review: "Explore your board",
    build: "From design to device",
});

const setText = (selector, value) => { const node = $(selector); if (node) node.textContent = value; };
const setHidden = (selector, hidden) => { const node = $(selector); if (node) node.hidden = hidden; };

export function canNavigate(stage) {
    if (stage === "describe") return true;
    if (stage === "agree") return Boolean(state.brief) || state.customProject;
    if (stage === "design") return state.runStatus !== "idle";
    if (stage === "review" || stage === "build") return Boolean(state.report);
    return false;
}

function updateShell() {
    const status = state.runStatus === "running" || state.runStatus === "starting" ? "Building your board"
        : state.runStatus === "paused" ? "Connection interrupted"
        : state.runStatus === "failed" ? "Run needs attention"
        : state.report ? "Completed design · hardware not yet tested"
        : state.customProject ? "Your saved project workspace"
        : state.brief ? "Example brief · ready to explore" : "A guided electronics workspace";
    setText("#workspace-title", STAGE_TITLES[state.stage]);
    setText("#workspace-status", status);
    setText("#project-label", state.brief?.project_name || state.experience?.headline || (state.customProject && state.projectName) || "Room sensor example");
    $$('[data-navigate]').forEach((button) => {
        const active = button.dataset.navigate === state.stage;
        button.disabled = !canNavigate(button.dataset.navigate);
        button.classList.toggle("active", active);
        if (active) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
    });
}

function show(stage, { focus = true } = {}) {
    if (stage !== "review") stopLearningAnimations();
    state.stage = stage;
    for (const name of STAGES) setHidden(`#${name}`, name !== stage);
    const index = STAGES.indexOf(stage);
    $$("#journey li").forEach((item, i) => {
        item.classList.toggle("here", i === index);
        item.classList.toggle("done", i < index);
    });
    updateShell();
    if (focus) {
        $(`#${stage}`)?.scrollIntoView({ behavior: "instant", block: "start" });
        const heading = $(`#${stage}-title`);
        heading?.setAttribute("tabindex", "-1");
        heading?.focus?.({ preventScroll: true });
    }
    if (stage === "review" && state.panel === "board") state.boardView?.frame();
}

export function navigate(stage) {
    if (!canNavigate(stage)) return false;
    show(stage);
    return true;
}

export function selectResultPanel(panel) {
    if (!["board", "learn", "checks"].includes(panel)) return false;
    if (panel !== "learn") stopLearningAnimations();
    state.panel = panel;
    $$('[data-panel]').forEach((button) => {
        const active = button.dataset.panel === panel;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
        button.setAttribute("tabindex", active ? "0" : "-1");
    });
    $$('[data-result-panel]').forEach((section) => { section.hidden = section.dataset.resultPanel !== panel; });
    if (panel === "board" && $("#board-canvas")?.clientWidth > 0) state.boardView?.frame();
    if (panel === "learn" && state.transitionTracks.length) drawTransform(Number($("#transform-scrub").value) / 100);
    return true;
}
const prefersReducedMotion = () =>
    typeof globalThis.matchMedia === "function"
    && globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches === true;

function clearError() {
    setHidden("#run-error", true);
    setHidden("#error-retry", true);
    setHidden("#error-back", true);
    state.retryAction = null;
}

function showError(kind, retryAction = null, retryLabel = "Try again") {
    const box = $("#run-error");
    box.hidden = false;
    box.textContent = MESSAGES[kind] || MESSAGES.backend_unavailable;
    state.retryAction = retryAction;
    setHidden("#error-retry", !retryAction);
    setText("#error-retry", retryLabel);
    setHidden("#error-back", false);
    if (!state.report) show("design");
    updateShell();
}

export async function retryLastAction() { return state.retryAction?.(); }

function setConnection(status) {
    state.connection = status;
    setText("#connection-status", { connected: "Connected", disconnected: "Connection lost", changed: "Server changed", unchecked: "Local workspace" }[status]);
    setHidden("#connection-banner", status === "connected" || status === "unchecked");
    setText("#connection-message", status === "changed"
        ? "This result is from an earlier server. You can keep exploring it. Downloads are paused; start a new example to create current files."
        : "Connection lost. Your completed result remains available to explore. Downloads will return when the same server reconnects.");
    $$('[data-reconnect]').forEach((button) => { button.hidden = status !== "disconnected"; });
    $$('[data-restart]').forEach((button) => { button.hidden = status !== "changed"; });
    $$('[data-artifact-download]').forEach((link) => {
        const enabled = status === "connected" && link.dataset.current === "true";
        link.setAttribute("aria-disabled", String(!enabled));
        if (enabled) {
            link.setAttribute("href", link.dataset.downloadUrl);
            link.removeAttribute("tabindex");
        } else {
            link.removeAttribute("href");
            link.setAttribute("tabindex", "-1");
        }
    });
}

export async function restartExample({ fetcher = globalThis.fetch } = {}) {
    state.pollVersion += 1;
    stopCompletionMonitor();
    stopTransformTimer();
    if (state.repairTimer) clearInterval(state.repairTimer);
    state.repairTimer = null;
    state.identity = null;
    state.jobId = null;
    state.brief = null;
    state.report = null;
    state.experience = null;
    state.runStatus = "idle";
    clearError();
    setConnection("unchecked");
    show("describe");
    return openBrief({ fetcher, request: state.request });
}

// ── describe → agree ────────────────────────────────────────────────────

// Offer the request box only where the server says it can answer one. A server
// with no model provider rejects free text, so an input there would be a
// placeholder that lies about what the page can do.
export async function revealFreeText({ fetcher = globalThis.fetch } = {}) {
    try {
        const identity = await fetchHealth(fetcher);
        state.identity = identity;
        setHidden("#free-text-starter", !identity.free_text);
        return identity.free_text;
    } catch {
        // A health check that fails tells us nothing about the capability, and
        // the describe stage still works: leave the input hidden and stay quiet.
        setHidden("#free-text-starter", true);
        return false;
    }
}

export function showFreeTextProblem(message) {
    const slot = $("#free-text-problem");
    if (!slot) return;
    slot.textContent = message || "";
    setHidden("#free-text-problem", !message);
}

export async function openBrief({ fetcher = globalThis.fetch, request = null } = {}) {
    if (["running", "starting", "paused"].includes(state.runStatus)) { show("design"); return; }
    const problem = request === null ? null : freeTextProblem(request);
    if (problem) { showFreeTextProblem(problem); return; }
    showFreeTextProblem(null);
    state.request = request === null ? null : String(request).trim();
    state.customProject = false;
    state.revisionContext = null;
    setHidden("#project-workbench", true);
    setHidden("#reference-brief", false);
    setText("#agree-title", state.request ? "Here is what Ohmni understood." : "Meet the reference project.");
    setText("#agree-description", state.request
        ? "A model read your description and proposed these requirements. Nothing has been checked yet."
        : "Explore the fixed room-sensor example before its engineering run starts.");
    setBriefBoundary(Boolean(state.request));
    const button = $(state.request ? "#start-free-text" : "#start-supported");
    if (button) button.disabled = true;
    clearError();
    try {
        state.identity = await fetchHealth(fetcher);
        let response;
        try {
            response = await fetcher(API_BASE + "/api/brief", {
                method: "POST", cache: "no-store",
                headers: { "content-type": "application/json" },
                body: state.request ? requestBody(state.identity, state.request) : identityBody(state.identity),
            });
        } catch { fail("backend_unavailable"); }
        if (!response.ok) fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        state.brief = parseBrief(payload, state.identity);
        renderBrief(state.brief);
        setConnection("connected");
        show("agree");
    } catch (error) {
        showError(errorKind(error, "backend_unavailable"), () => openBrief({ fetcher, request }));
    } finally {
        if (button) button.disabled = false;
    }
}

// Static copy only: the two modes say different true things about where the
// brief came from, and neither ever interpolates what the user typed.
function setBriefBoundary(proposed) {
    const slot = $("#brief-boundary");
    if (!slot) return;
    slot.innerHTML = proposed
        ? `<strong>A model proposed this from your description.</strong>
           <p>Requirements a model wrote are a proposal, not a verdict. Every check
              that follows is the same deterministic verification the reference
              example runs, and it can still refuse this design.</p>`
        : `<strong>This is the fixed reference example.</strong>
           <p>Its design and repair are pre-authored. To choose your own configuration,
              return home and select “Choose my board.”</p>`;
}

function briefGroup(kind, title, note, lines, emptyText) {
    const exampleLabels = { "What you described": "Example request", "Part you named": "Requested part", "You want to solder it yourself": "Prefer hand soldering" };
    const body = lines.length
        ? lines.map((line) => `<div class="brief-line">
             <div class="brief-label">${escapeHtml(exampleLabels[line.label] || line.label)}</div>
             <div class="brief-value">${escapeHtml(line.value)}</div>
           </div>`).join("")
        : `<p class="brief-empty">${escapeHtml(emptyText)}</p>`;
    return `<section class="brief-group ${kind}">
        <h3>${escapeHtml(title)} <small>${lines.length}</small></h3>
        <p class="fineprint">${escapeHtml(note)}</p>${body}</section>`;
}

export function renderBrief(brief, proposed = Boolean(state.request)) {
    $("#brief").innerHTML = [
        // Ordered by how much attention each deserves: the things Ohmni decided
        // come first, because those are what a user is here to catch.
        briefGroup("unclear", "Design choices",
                   proposed ? "Values nobody stated. Ohmni filled these in."
                            : "Values filled in when the example brief was prepared.",
                   brief.needs_clarification,
                   "No additional choices were recorded."),
        briefGroup("assumed", "Assumptions to know",
                   proposed ? "Assumptions Ohmni supplied, not facts you gave it."
                            : "These assumptions are part of this example, not facts you supplied.",
                   brief.assumed, "No additional assumptions were recorded."),
        briefGroup("asked", proposed ? "From your description" : "From the example brief",
                   proposed ? "What the model read out of the words you wrote."
                            : "The starting requirements for the room sensor you selected.",
                   brief.asked_for, "No explicit requirements were recorded."),
    ].join("");
    const decided = brief.needs_clarification.length + brief.assumed.length;
    $("#agree-note").textContent =
        (proposed
            ? `Ohmni decided ${decided} thing${decided === 1 ? "" : "s"} your description did not settle. Read them before spending the run. `
            : `This example includes ${decided} design choice${decided === 1 ? "" : "s"} and assumption${decided === 1 ? "" : "s"}. `)
        + `Continue to run the actual checks and generate its board files. `
        + `Allow a few minutes. Copper routing has a three-minute limit; the other checks add time.`
        + (proposed ? " A proposal that fails a check is reported, not quietly fixed." : " Editing this example is not available yet.");
}

// ── agree → design ──────────────────────────────────────────────────────

export async function startRun({ fetcher = globalThis.fetch, poller = poll, pollDependencies = {} } = {}) {
    if (state.runStatus === "running" || state.runStatus === "starting") { show("design"); return; }
    state.pollVersion += 1;
    stopCompletionMonitor();
    stopTransformTimer();
    if (state.repairTimer) clearInterval(state.repairTimer);
    state.repairTimer = null;
    state.report = null;
    state.experience = null;
    state.runStatus = "starting";
    clearError();
    $("#confirm-brief").disabled = true;
    renderPendingStages();
    setText("#activity-explanation", "A connection can look right and still be wrong. This fixed reference example checks a pre-authored circuit, applies its bounded repair, and runs the checks again.");
    show("design");
    let jobId;
    try {
        const identity = state.identity || await fetchHealth(fetcher);
        state.identity = identity;
        let response;
        try {
            response = await fetcher(API_BASE + "/api/demo", {
                method: "POST", cache: "no-store",
                headers: { "content-type": "application/json" },
                body: state.request ? requestBody(identity, state.request) : identityBody(identity),
            });
        } catch { fail("backend_unavailable"); }
        if (!response.ok || response.status !== 202) {
            fail(await serverErrorKind(response, response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        }
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        jobId = parseStart(payload, identity);
        state.jobId = jobId;
        state.runStatus = "running";
        setConnection("connected");
        updateShell();
    } catch (error) {
        state.runStatus = "failed";
        $("#confirm-brief").disabled = false;
        return showError(errorKind(error, "backend_unavailable"), () => restartExample({ fetcher }), "Start a new example");
    }
    return poller(jobId, state.identity, { fetcher, ...pollDependencies });
}

/** Editing or selecting another saved revision invalidates the current result view. */
export function invalidateProjectResult() {
    state.pollVersion += 1;
    stopCompletionMonitor();
    stopLearningAnimations();
    state.report = null;
    state.experience = null;
    state.brief = null;
    state.jobId = null;
    state.revisionContext = null;
    state.runStatus = "idle";
    setConnection("unchecked");
    $$('[data-artifact-download]').forEach((link) => {
        link.dataset.current = "false";
        link.removeAttribute("href");
        link.setAttribute("aria-disabled", "true");
        link.setAttribute("tabindex", "-1");
    });
    updateShell();
}

function openProjectWorkspace(name) {
    state.customProject = true;
    state.projectName = name;
    setHidden("#project-workbench", false);
    setHidden("#reference-brief", true);
    setText("#agree-title", "Make room for your ideas.");
    setText("#agree-description", "Choose a purpose and the parts to match. Save a revision, then turn that exact design into a board.");
    show("agree", { focus: false });
    setText("#project-label", name);
}

export async function startProjectRun({ projectId, revisionId, identity, preview, fetcher = globalThis.fetch,
    poller = poll, pollDependencies = {} } = {}) {
    invalidateProjectResult();
    state.customProject = true;
    state.revisionContext = { projectId, revisionId, preview };
    state.identity = identity;
    state.brief = preview;
    state.runStatus = "starting";
    clearError();
    renderPendingStages(true);
    setText("#activity-explanation", "Ohmni builds the parts and connections from your saved choices, then checks the circuit and generated board. This flow does not apply a scripted repair.");
    show("design");
    const version = state.pollVersion;
    try {
        const { payload } = await projectRequest(`/api/projects/${encodeURIComponent(projectId)}/revisions/${encodeURIComponent(revisionId)}/run`, {
            fetcher, identity, method: "POST",
        });
        if (version !== state.pollVersion) return;
        const jobId = parseProjectStart(payload, identity);
        state.jobId = jobId;
        state.runStatus = "running";
        setConnection("connected");
        updateShell();
        return poller(jobId, identity, { fetcher, ...pollDependencies });
    } catch (error) {
        if (version !== state.pollVersion) return;
        state.runStatus = "failed";
        showError(errorKind(error, "job_initialization_failed"), () => retryProjectRun({ fetcher }), "Retry this revision");
    }
}

async function retryProjectRun({ fetcher = globalThis.fetch } = {}) {
    const context = state.revisionContext;
    if (!context) return openProjectWorkspace("Your project");
    try {
        const identity = await fetchHealth(fetcher);
        return startProjectRun({ ...context, identity, fetcher });
    } catch (error) {
        showError(errorKind(error, "backend_unavailable"), () => retryProjectRun({ fetcher }), "Retry this revision");
    }
}

const freshRun = (fetcher) => state.customProject ? retryProjectRun({ fetcher }) : restartExample({ fetcher });

const PENDING_STAGES = [
    "Loading the example brief", "Preparing its parts and connections",
    "Checking the electrical design", "Fixing what it found",
    "Drawing the schematic", "Arranging parts on the board",
    "Drawing the copper", "Checking it can be made",
];

function renderPendingStages(custom = false) {
    const detail = $("#progress-detail");
    if (detail) detail.textContent = "";
    const labels = custom ? ["Loading your saved revision", "Building its parts and connections", "Checking the electrical design", "Recording the check results", "Drawing the schematic", "Arranging parts on the board", "Drawing the copper", "Checking it can be made"] : PENDING_STAGES;
    $("#stage-list").innerHTML = labels.map((label, i) =>
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
    // The explanation of what the slow stage is doing. Copied verbatim from the
    // job's own progress event; the long routing wait is the reason it exists.
    const detail = $("#progress-detail");
    if (detail) detail.textContent = last ? last.detail : "";
    const items = $$("#stage-list li");
    const current = { requirements: 0, check: 2, repair: 3, schematic: 4, placement: 5, routing: 6, drc: 7, manufacturing: 7, release: 7 }[last?.stage] ?? 0;
    items.forEach((item, i) => {
        item.classList.toggle("pending", i > current);
        item.classList.toggle("running", i === current);
    });
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
    const version = state.pollVersion;
    state.jobId = id;
    state.identity = identity;
    try {
        let response;
        try { response = await fetcher(API_BASE + `/api/jobs/${id}`, { cache: "no-store", headers: pollHeaders(identity) }); }
        catch { fail("backend_unavailable"); }
        if (!response.ok) {
            fail(await serverErrorKind(response, response.status === 404 ? "lost_job"
                : response.status >= 500 ? "backend_unavailable" : "api_ui_mismatch"));
        }
        let payload;
        try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
        if (version !== state.pollVersion) return;
        const job = parseJob(payload, id, identity);
        const disposition = pollDisposition(job.status);
        if (disposition === "complete") {
            clearError();
            state.runStatus = "complete";
            $("#confirm-brief").disabled = false;
            renderResult(job.report, id);
            monitorer(identity, { fetcher });
            return;
        }
        if (disposition === "failed") {
            state.runStatus = "failed";
            $("#confirm-brief").disabled = false;
            const kind = ["worker_start_failed", "routing_incomplete", "eda_tool_failed"].includes(job.error_code)
                ? job.error_code : "pipeline_failed";
            return showError(kind,
                () => freshRun(fetcher), state.customProject ? "Retry this revision" : "Start a new example");
        }
        clearError();
        state.runStatus = "running";
        updateShell();
        renderProgress(job.progress);
        const dependencies = { fetcher, schedule, monitorer };
        schedule(() => { if (version === state.pollVersion) void poll(id, identity, dependencies); }, 900);
    } catch (error) {
        if (version !== state.pollVersion) return;
        const kind = errorKind(error, "backend_unavailable");
        state.runStatus = kind === "backend_unavailable" ? "paused" : "failed";
        $("#confirm-brief").disabled = false;
        return showError(kind, kind === "backend_unavailable"
            ? () => poll(id, identity, { fetcher, schedule, monitorer })
            : () => freshRun(fetcher), kind === "backend_unavailable" ? "Reconnect to this run" : state.customProject ? "Retry this revision" : "Start a new example");
    }
}

export function stopCompletionMonitor() {
    const cleanup = state.completionMonitor;
    state.completionMonitor = null;
    state.reconnect = null;
    if (cleanup) cleanup();
}

export function beginCompletionMonitor(identity, { fetcher = globalThis.fetch, setIntervalFn = globalThis.setInterval, clearIntervalFn = globalThis.clearInterval, windowTarget = globalThis.window, documentTarget = globalThis.document } = {}) {
    stopCompletionMonitor();
    let stopped = false;
    let busy = false;
    const check = async () => {
        if (stopped || busy) return true;
        busy = true;
        try {
            const current = await fetchHealth(fetcher);
            if (stopped) return false;
            if (!sameIdentity(identity, current)) { setConnection("changed"); return false; }
            setConnection("connected");
            return true;
        } catch (error) {
            if (!stopped) setConnection(errorKind(error, "backend_unavailable") === "backend_unavailable" ? "disconnected" : "changed");
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
    state.reconnect = check;
    return check;
}

// ── result ──────────────────────────────────────────────────────────────

function renderResult(report, jobId) {
    state.report = report;
    state.experience = report.experience;
    const exp = state.experience;
    state.brief = exp.brief;
    state.runStatus = "complete";

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
    const requirements = requirementResultsHtml(report.requirements);
    const choices = $("#choices-checked");
    if (choices) {
        choices.hidden = report.mode !== "bounded_synthesis";
        choices.innerHTML = `<h2>Your choices checked</h2><p>See which requested choices are present in this design and what still needs proof. These checks do not establish working firmware or tested hardware.</p>${requirements || `<p>No usable per-choice results were supplied by this run.</p>`}`;
    }
    renderConfidence(exp.confidence);
    renderParts(exp.components);
    renderFiles(report, jobId);
    renderBringUp(exp);
    setupTransform(exp);
    $("#schematic-holder").innerHTML = schematicSvg(exp.schematic, {});

    selectResultPanel("board");
    show("review");
    setupBoard(exp.board);
    setConnection("connected");
}

function setupBoard(board) {
    const note = $("#board-thickness-note");
    if (note) note.textContent = `${board.thickness_note} Component bodies, heights, and materials are illustrative. Light pulses highlight connections; they do not simulate electricity.`;
    const canvas = $("#board-canvas");
    if (!canvas || typeof canvas.getContext !== "function") {
        $("#board-empty").hidden = false;
        return;
    }
    if (!state.boardView) {
        state.boardView = new BoardView(canvas, {
            onSelect: (ref) => renderSelection(ref),
            onHover: (ref) => {
                const part = state.experience?.components.find((item) => item.ref === ref);
                setText("#board-hover-label", part ? `${part.name?.human || ref} · ${ref}` : "");
                setHidden("#board-hover-label", !part);
            },
        });
        globalThis.addEventListener?.("resize", () => {
            if (canvas.clientWidth > 0) state.boardView?.frame();
            if (state.stage === "review" && state.panel === "learn") drawTransform(Number($("#transform-scrub").value) / 100);
        });
    }
    if (state.boardView.available === false) { $("#board-empty").hidden = false; return; }
    $("#board-empty").hidden = true;
    state.flowId = null;
    state.systemId = null;
    state.boardView.setBoard(board);
    resetBoardView();
    state.boardControls?.dispose();
    state.boardLessons?.dispose();
    state.boardControls = mountBoardControls($("#board-visual-controls"), state.boardView, { stage: canvas.closest?.(".board-stage"), fullscreen: true, explodeControl: $("#explode") });
    state.boardLessons = mountCircuitLessons($("#board-lessons"), state.experience, state.boardView, { onViewChange: () => state.boardControls?.sync() });
}

function resetBoardView() {
    if (!state.boardView) return;
    state.boardView.camera = createCamera();
    state.boardView.setOptions({ explode: 0, showCopper: true, showComponents: true, showBack: false });
    state.boardView.setOptions({ autoRotate: false, animateFlow: false, xray: false, showLabels: true });
    state.boardView.select(null);
    selectFlow(null);
    state.boardView.frame();
    $("#explode").value = "0";
    $$("[data-view]").forEach((button) => {
        const active = button.dataset.view === "front";
        button.classList.toggle("on", active);
        if (button.dataset.view !== "reset") button.setAttribute("aria-pressed", String(active));
    });
    $$("[data-toggle]").forEach((button) => { button.classList.add("on"); button.setAttribute("aria-pressed", "true"); });
    state.boardControls?.sync();
}

export function renderSelection(ref) {
    const box = $("#selection");
    const exp = state.experience;
    state.selected = ref;
    state.boardLessons?.select(ref);
    $$("#schematic-holder .sym").forEach((symbol) => {
        const selected = symbol.dataset.ref === ref;
        symbol.classList.toggle("sel", selected);
        symbol.setAttribute("aria-pressed", String(selected));
    });
    if (!ref) {
        box.innerHTML = `<p class="eyebrow">A board, explained</p><h4>Every part has a purpose.</h4>
            <p>Select a part on the board or in the list to learn what it does.</p>`;
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
        <button type="button" class="system-head" data-system-select="${escapeHtml(system.system)}" aria-expanded="false" aria-controls="system-parts-${escapeHtml(system.system)}">
          <span class="system-name"><span class="dot ${escapeHtml(system.system)}"></span>${escapeHtml(system.label)}</span>
          <p>${escapeHtml(system.summary)}</p>
        </button>
        <ul class="system-parts" id="system-parts-${escapeHtml(system.system)}" hidden>${system.component_refs.map((ref) => {
            const card = byRef.get(ref);
            return `<li><button type="button" class="part-pick" data-ref="${escapeHtml(ref)}">
              <span>${human(card?.name, ref)}</span>
              <span class="ident">${escapeHtml(ref)}</span></button></li>`;
        }).join("")}</ul>
      </section>`).join("");
}

function renderFlows(flows) {
    $("#flow-tabs").innerHTML = flows.map((flow) =>
        `<button type="button" class="chip" data-flow="${escapeHtml(flow.flow_id)}"
          aria-pressed="false">${escapeHtml(flow.label)}</button>`).join("")
        + `<button type="button" class="chip" data-flow="" aria-pressed="false">Show everything</button>`;
    $("#flow-detail").innerHTML = `<p class="flow-summary">Pick one above.</p>`;
}

function selectFlow(flowId) {
    const exp = state.experience;
    state.boardLessons?.pause();
    state.flowId = flowId || null;
    state.systemId = null;
    $$("#flow-tabs .chip").forEach((chip) => {
        const on = chip.dataset.flow === (flowId || "");
        chip.classList.toggle("on", on);
        chip.setAttribute("aria-pressed", String(on));
    });
    $$(".system").forEach((item) => item.classList.remove("on"));
    $$(".system-head").forEach((button) => button.setAttribute("aria-expanded", "false"));
    $$(".system-parts").forEach((list) => { list.hidden = true; });
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
    state.boardLessons?.pause();
    const system = exp.systems.find((s) => s.system === systemId);
    if (!system) return;
    if (state.systemId === systemId) { selectFlow(null); return; }
    state.systemId = systemId;
    state.flowId = null;
    $$(".system").forEach((item) => item.classList.toggle("on", item.dataset.system === systemId));
    $$(".system-head").forEach((button) => button.setAttribute("aria-expanded", String(button.dataset.systemSelect === systemId)));
    $$(".system-parts").forEach((list) => { list.hidden = list.id !== `system-parts-${systemId}`; });
    $$("#systems .part-pick").forEach((button) => button.classList.remove("on"));
    $$("#flow-tabs .chip").forEach((chip) => { chip.classList.remove("on"); chip.setAttribute("aria-pressed", "false"); });
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
    $$("#repair-panel .repair-steps li").forEach((item) => item.classList.add("shown"));
}

function stopLearningAnimations() {
    stopTransformTimer();
    if (state.repairTimer) clearInterval(state.repairTimer);
    state.repairTimer = null;
    $$("#repair-panel .repair-steps li").forEach((item) => item.classList.add("shown"));
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
    $("#transform-scrub").oninput = (event) => {
        stopTransformTimer();
        drawTransform(Number(event.target.value) / 100);
    };
    $("#transform-play").onclick = () => playTransform();
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
        element.style.left = `${36 + frame.x * (width - 72)}px`;
        element.style.top = `${36 + frame.y * (height - 72)}px`;
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
              ["reflow_recommended", "unsupported_for_hand_assembly", "unknown"]
                  .includes(card.assembly_difficulty) ? "hard" : ""
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
    const download = (name, label, section) => {
        const url = `/api/artifacts/${escapeHtml(jobId)}/${name}`;
        const current = section?.current ?? report.release.current;
        return `<a href="${url}" data-artifact-download data-download-url="${url}" data-current="${current === true}">${label}<span aria-hidden="true"> ↗</span></a>`;
    };
    $("#files-panel").innerHTML = `<p class="eyebrow">Take your design with you</p><h3>Your board files</h3>
      <p class="panel-note">Take the schematic, board, manufacturing outputs, parts list, and bring-up guide together.
        The package includes the check results and their limitations. No physical board has been tested.</p>
      <div class="download-row">
        ${download("build-package.zip", "Download complete build package", report.release)}
        ${download("golden.kicad_sch", "Download schematic", report.schematic)}
        ${download("golden.kicad_pcb", "Download board", report.pcb)}
      </div>
      <details class="disclose"><summary>Generated manufacturing inventory · ${report.release.files.length} files</summary>
      <p class="fineprint">These files are included in the build package. Review the check results and assembly requirements before ordering a board.</p>
      <ul class="file-list">${report.release.files.map((file) => `<li>
          <span>${escapeHtml(file.relative_path)} <span class="fineprint">${escapeHtml(file.kind)}</span></span>
          <span class="hash">${escapeHtml(String(file.sha256).slice(0, 16))}…</span></li>`).join("")}</ul></details>
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
    initializeReferencePreview();
    if ($("#project-workbench")?.dataset.projectWorkbench === "true") {
        state.workbench = mountProjectWorkbench($("#project-workbench"), {
            shelf: $("#saved-projects"), onOpen: openProjectWorkspace,
            onInvalidate: invalidateProjectResult, onRun: startProjectRun,
        });
        $("#create-project")?.addEventListener("click", () => state.workbench?.openNew());
    }
    $$('[data-navigate]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.navigate)));
    $$('[data-panel]').forEach((button) => {
        button.addEventListener("click", () => selectResultPanel(button.dataset.panel));
        button.addEventListener("keydown", (event) => {
            const tabs = $$('[data-panel]');
            const index = tabs.indexOf(button);
            const target = event.key === "ArrowRight" ? (index + 1) % tabs.length
                : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length
                : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
            if (target < 0) return;
            event.preventDefault();
            selectResultPanel(tabs[target].dataset.panel);
            tabs[target].focus();
        });
    });
    $("#error-retry")?.addEventListener("click", () => void retryLastAction());
    $("#error-back")?.addEventListener("click", () => { clearError(); navigate("describe"); });
    $$('[data-reconnect]').forEach((button) => button.addEventListener("click", () => void state.reconnect?.()));
    $$('[data-restart]').forEach((button) => button.addEventListener("click", () => void freshRun(globalThis.fetch)));
    $("#files-panel")?.addEventListener("click", (event) => {
        const link = event.target.closest?.('[data-artifact-download]');
        if (link?.getAttribute("aria-disabled") === "true") event.preventDefault();
    });
    const activateSchematic = (event) => {
        if (event.type === "keydown" && !["Enter", " "].includes(event.key)) return;
        const symbol = event.target.closest?.('.sym[data-ref]');
        if (!symbol || !state.experience?.components.some((card) => card.ref === symbol.dataset.ref)) return;
        event.preventDefault();
        selectResultPanel("board");
        navigate("review");
        state.boardView?.select(symbol.dataset.ref);
        state.boardView?.setHighlight({ refs: [symbol.dataset.ref] });
        renderSelection(symbol.dataset.ref);
        $("#selection")?.setAttribute("tabindex", "-1");
        $("#selection")?.focus?.({ preventScroll: true });
    };
    $("#schematic-holder")?.addEventListener("click", activateSchematic);
    $("#schematic-holder")?.addEventListener("keydown", activateSchematic);
    $("#start-supported")?.addEventListener("click", () => void openBrief());
    $("#start-free-text")?.addEventListener("click", () =>
        void openBrief({ request: $("#free-text-request")?.value ?? "" }));
    $("#free-text-request")?.addEventListener("input", () => showFreeTextProblem(null));
    void revealFreeText();
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
        if (view === "reset") { resetBoardView(); return; }
        $$("[data-view]").forEach((other) => {
            other.classList.toggle("on", other === button);
            if (other.dataset.view !== "reset") other.setAttribute("aria-pressed", String(other === button));
        });
        state.boardView?.setCameraPreset(view);
    }));
    $$("[data-toggle]").forEach((button) => button.addEventListener("click", () => {
        const key = button.dataset.toggle;
        const on = !state.boardView?.options[key];
        button.classList.toggle("on", on);
        button.setAttribute("aria-pressed", String(on));
        state.boardView?.setOptions({ [key]: on });
    }));
    $("#explode")?.addEventListener("input", (event) => {
        state.boardView?.setOptions({ explode: Number(event.target.value) / 100 });
    });
    setConnection("unchecked");
    clearError();
    selectResultPanel("board");
    show("describe", { focus: false });
}

if (typeof document !== "undefined" && document.getElementById("start-supported")) attach();
