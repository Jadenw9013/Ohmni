import { escapeHtml } from "./view-model.js";
import { errorKind, fetchHealth } from "./client-contract.js";
import { defaultProjectBrief, parseProjectEnvelope, parseProjectList, projectRequest, sameBrief, supportedBrief, checkIdentity, briefAddress, briefChanges, ProjectRequestError } from "./project-contract.js";

const e = escapeHtml;
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const hasText = (value) => typeof value === "string" && value.length > 0;

export function parseExercise(payload, identity) {
    checkIdentity(payload, identity);
    const exercise = payload.exercise;
    if (!object(exercise) || !hasText(exercise.id) || !hasText(exercise.title) || !hasText(exercise.prompt)
        || !hasText(exercise.limitation) || !Array.isArray(exercise.choices) || !exercise.choices.length
        || !exercise.choices.every((choice) => object(choice) && /^[a-z][a-z0-9_]*$/.test(choice.id) && hasText(choice.label))
        || new Set(exercise.choices.map((choice) => choice.id)).size !== exercise.choices.length) throw new Error("Invalid exercise response");
    return exercise;
}

export function parseExerciseResult(payload, identity, choice) {
    checkIdentity(payload, identity);
    const result = payload.result;
    const report = (value) => object(value) && /^[a-f0-9]{64}$/.test(value.circuit_hash)
        && hasText(value.rule_id) && hasText(value.outcome)
        && ["pass", "fail", "insufficient_data", "not_applicable", "error"].includes(value.outcome.toLowerCase()) && Array.isArray(value.findings)
        && value.findings.every((finding) => object(finding) && hasText(finding.title) && hasText(finding.description));
    if (!object(result) || result.choice !== choice || typeof result.correct !== "boolean"
        || !hasText(result.explanation) || !hasText(result.limitation) || !report(result.before) || !report(result.after)
        || !Array.isArray(result.evidence) || !result.evidence.every((item) => object(item) && (item.source === null || hasText(item.source))
            && hasText(item.status))) throw new Error("Invalid exercise result");
    return result;
}

function message(error) {
    const kind = errorKind(error, null);
    if (kind === "generation_mismatch") return "The server changed. Your edits are still here. Retry to connect to the current server.";
    if (kind === "api_ui_mismatch") return "This page and the server do not match. Reload the page before continuing.";
    if (error?.name === "ProjectRequestError") return error.message;
    return "The server could not provide a usable response. No result has been assumed. Try again.";
}

/** A bounded editor. Saved revisions and lesson results always come from the server. */
export function mountProjectWorkbench(root, {
    shelf = null, fetcher = globalThis.fetch, onOpen = () => {}, onInvalidate = () => {}, onRun = async () => {},
} = {}) {
    if (!root) return null;
    let project = null;
    let revision = null;
    let draft = defaultProjectBrief();
    let busy = false;
    let exercise = null;
    let exerciseIdentity = null;
    let exerciseVersion = 0;
    let shelfVersion = 0;
    let disposed = false;
    const $ = (selector) => root.querySelector(selector);

    function render() {
        const address = briefAddress(draft);
        root.innerHTML = `<div class="project-edit-layout">
          <div class="project-editor">
            <div class="project-editor-heading"><div><h2>Your room sensor, your choices.</h2><p>Keep the essentials. Decide what belongs on your board.</p></div><span class="project-save-state" id="project-save-state" role="status"></span></div>
            <form id="project-form">
              <label class="project-name-label" for="project-name">Give your project a name</label>
              <input id="project-name" name="project_name" type="text" required maxlength="120" value="${e(draft.project_name)}" autocomplete="off">
              <div class="project-circuit-strip" aria-label="Supported circuit: USB-C power, 3.3 volt regulator, ESP32 processor, BME280 sensor"><span>USB-C<small>5 V power</small></span><i aria-hidden="true"></i><span>3.3 V<small>Regulated supply</small></span><i aria-hidden="true"></i><span>ESP32<small>Your processor</small></span><i aria-hidden="true"></i><span>BME280<small>Your sensor</small></span></div>
              <p class="project-envelope">This first project supports one BME280 temperature, humidity, and pressure sensor on a two-layer ESP32 board.</p>
              <fieldset class="project-choice"><legend>A little signal you can see</legend><p>An LED gives firmware a way to show status. It does not light up automatically without a program.</p><div class="project-choice-options">
                <label><input type="radio" name="led" value="1" ${draft.status_led_count === 1 ? "checked" : ""}><span><strong>Include a status light</strong><small>LED and its current-limiting resistor</small></span></label>
                <label><input type="radio" name="led" value="0" ${draft.status_led_count === 0 ? "checked" : ""}><span><strong>Keep it minimal</strong><small>Leave the light and its resistor out</small></span></label>
              </div></fieldset>
              <fieldset class="project-choice"><legend>How you will program it</legend><p>USB-C supplies power. Programming uses a separate USB-to-serial adapter and the board's programming connections.</p><div class="project-choice-options">
                <label><input type="radio" name="header" value="yes" ${draft.include_programming_header ? "checked" : ""}><span><strong>Include the programming header</strong><small>Recommended for your first board</small></span></label>
                <label><input type="radio" name="header" value="no" ${!draft.include_programming_header ? "checked" : ""}><span><strong>Leave the header out</strong><small>Requires your own programming access</small></span></label>
              </div></fieldset>
              <details class="project-address"><summary>Sensor address <span id="project-address-summary">${address === 118 ? "0x76" : "0x77"}</span></summary><label for="project-address">The address tells firmware which device to talk to.</label><select id="project-address" name="address"><option value="118" ${address === 118 ? "selected" : ""}>0x76 — address pin tied to ground</option><option value="119" ${address === 119 ? "selected" : ""}>0x77 — address pin tied to 3.3 V</option></select><p>Saving changes the sensor's address connection in the actual design.</p></details>
              <div id="project-error" class="run-error" role="alert" hidden></div>
              <div class="project-editor-actions"><button type="submit" id="project-save" class="secondary">Save first revision</button><button type="button" id="project-run" class="primary" disabled>Generate my board</button></div>
              <p id="project-action-note" class="project-action-note" aria-live="polite"></p>
            </form>
            <section class="project-history" aria-labelledby="project-history-title"><div><h3 id="project-history-title">Your saved revisions</h3><p>Every save keeps a separate version on this server. Reopen one to compare or build it.</p></div><div id="project-history-options"></div><div id="project-preview"></div></section>
          </div>
          <aside class="project-learning">
            <div class="project-learning-intro"><span aria-hidden="true">↳</span><div><h2>Before you build,<br>follow the power.</h2><p>A short challenge to understand the most important connection on your board.</p></div></div>
            <div id="sensor-exercise" aria-live="polite"><button type="button" class="secondary" data-load-exercise>Try the sensor challenge</button><p class="fineprint">A separate teaching circuit. Your saved design stays as you chose it.</p></div>
            <div class="project-build-boundary"><strong>What you get</strong><p>A generated schematic and PCB, actual engineering check results, and a downloadable build package.</p><strong>What still needs your work</strong><p>Physical assembly, a program, and bench testing. Component models and animations do not simulate a working device.</p></div>
          </aside>
        </div>`;
        renderHistory();
        sync();
    }

    function sync() {
        if (!$("#project-form")) return;
        const dirty = !revision || !sameBrief(draft, revision.brief);
        $("#project-save-state").textContent = busy ? "Working…" : dirty ? "Unsaved changes" : `Revision ${revision.number} saved`;
        $("#project-save").textContent = busy ? "Working…" : project ? "Save new revision" : "Save first revision";
        $("#project-save").disabled = busy || !dirty;
        $("#project-run").disabled = busy || dirty || !revision;
        $("#project-run").textContent = revision?.job_id ? "Open this revision's run" : "Generate my board";
        $("#project-action-note").textContent = dirty ? "Save your choices first. Existing revisions keep their original design and files."
            : `Revision ${revision.number} is saved. ${revision.job_id ? "Reopen its engineering run." : "Generate its board and run the real checks. Allow a few minutes."}`;
        root.querySelectorAll("#project-form input, #project-form select, #project-revision").forEach((input) => { input.disabled = busy; });
    }

    function renderHistory() {
        $("#project-history-options").innerHTML = project ? `<label for="project-revision">Open a saved version</label><select id="project-revision">${project.revisions.toReversed().map((item) => `<option value="${e(item.revision_id)}" ${item.revision_id === revision?.revision_id ? "selected" : ""}>Revision ${item.number} — ${e(item.brief.project_name)}</option>`).join("")}</select>` : `<p class="project-empty">Your first saved revision will appear here.</p>`;
        const preview = revision?.preview;
        const previous = project?.revisions.find((item) => item.number === revision?.number - 1);
        $("#project-preview").innerHTML = preview ? `<div class="revision-changes"><p>${previous ? `Changes from revision ${previous.number}` : "Your starting point"}</p><ul>${briefChanges(previous?.brief, revision.brief).map((change) => `<li>${e(change)}</li>`).join("")}</ul></div><details class="disclose"><summary>What the server recorded for revision ${revision.number}</summary>${[...preview.asked_for || [], ...preview.assumed || [], ...preview.needs_clarification || []].map((line) => `<p><strong>${e(line.label)}</strong><br>${e(line.value)}</p>`).join("")}<p class="fineprint">This is the saved brief. Engineering results appear only after its run completes.</p></details>` : "";
    }

    function showError(error) {
        $("#project-error").textContent = message(error);
        $("#project-error").hidden = false;
    }

    function openNew() {
        if (busy) return;
        exerciseVersion += 1;
        project = null; revision = null; draft = defaultProjectBrief();
        onInvalidate(); render(); onOpen(draft.project_name);
        $("#project-name")?.focus();
    }

    async function refreshShelf() {
        if (!shelf) return;
        const version = ++shelfVersion;
        shelf.innerHTML = `<p class="project-empty">Loading your saved projects…</p>`;
        try {
            const { payload, identity } = await projectRequest("/api/projects", { fetcher });
            const projects = parseProjectList(payload, identity);
            if (disposed || version !== shelfVersion) return;
            shelf.innerHTML = projects.length ? projects.map((item) => `<button type="button" class="saved-project" data-project-open="${e(item.project_id)}"><span><strong>${e(item.name)}</strong><small>${item.revision_count} saved revision${item.revision_count === 1 ? "" : "s"}</small></span><span aria-hidden="true">↗</span></button>`).join("") : `<p class="project-empty">A space for the things you make. Save your first project to pick it up here later.</p>`;
        } catch (error) {
            if (disposed || version !== shelfVersion) return;
            shelf.innerHTML = `<p class="project-empty">${e(message(error))}</p><button type="button" class="ghost" data-refresh-projects>Reload saved projects</button>`;
        }
    }

    async function openProject(projectId) {
        if (busy) return;
        busy = true;
        exerciseVersion += 1;
        project = null; revision = null; draft = defaultProjectBrief();
        onInvalidate(); onOpen("Your saved project"); render(); sync();
        try {
            const { payload, identity } = await projectRequest(`/api/projects/${encodeURIComponent(projectId)}`, { fetcher });
            const next = parseProjectEnvelope(payload, identity);
            if (next.project_id !== projectId) throw new Error("Project identity mismatch");
            project = next; revision = next.revisions.at(-1); draft = structuredClone(revision.brief);
            render(); onOpen(draft.project_name);
        } catch (error) { showError(error); }
        finally { busy = false; sync(); }
    }

    async function save() {
        if (busy) return;
        if (!supportedBrief(draft)) return showError(new ProjectRequestError("Give your project a name before saving. Use between 1 and 120 characters."));
        busy = true; sync(); $("#project-error").hidden = true;
        try {
            const path = project ? `/api/projects/${project.project_id}/revisions` : "/api/projects";
            const { payload, identity } = await projectRequest(path, { fetcher, method: "POST", data: { brief: draft } });
            const next = parseProjectEnvelope(payload, identity);
            if (project && next.project_id !== project.project_id) throw new Error("Project identity mismatch");
            const saved = next.revisions.at(-1);
            if (!sameBrief(draft, saved.brief)) throw new Error("Saved brief differs from request");
            project = next; revision = saved; draft = structuredClone(saved.brief);
            renderHistory(); onOpen(draft.project_name); void refreshShelf();
        } catch (error) { showError(error); }
        finally { busy = false; sync(); }
    }

    async function run() {
        if (busy || !revision || !sameBrief(draft, revision.brief)) return;
        const projectId = project.project_id;
        const revisionId = revision.revision_id;
        busy = true; sync(); $("#project-error").hidden = true;
        try {
            const identity = await fetchHealth(fetcher);
            await onRun({ projectId, revisionId, identity, preview: revision.preview, fetcher });
            const refreshed = await projectRequest(`/api/projects/${projectId}`, { fetcher });
            const next = parseProjectEnvelope(refreshed.payload, refreshed.identity);
            if (disposed || project?.project_id !== projectId) return;
            if (next.project_id !== projectId) throw new Error("Project identity mismatch");
            const selected = next.revisions.find((item) => item.revision_id === revision?.revision_id);
            if (!selected || selected.brief_fingerprint !== revision.brief_fingerprint) throw new Error("Saved revision identity mismatch");
            // Refresh server-owned run metadata while preserving the current draft and selection.
            project = next;
            revision = selected;
            renderHistory();
        } catch (error) { showError(error); }
        finally { busy = false; sync(); }
    }

    function renderExercise() {
        $("#sensor-exercise").innerHTML = `<h3>${e(exercise.title)}</h3><p>${e(exercise.prompt)}</p><label class="exercise-reflection" for="sensor-prediction">${e(exercise.prediction_prompt || "What do you expect to happen? Explain it in your own words.")}<textarea id="sensor-prediction" rows="3" placeholder="My prediction…"></textarea><span>This reflection stays in this page and is not graded.</span></label><form id="sensor-choice-form"><fieldset><legend>Choose the repair you would make</legend>${exercise.choices.map((choice) => `<label class="exercise-option"><input type="radio" name="repair" value="${e(choice.id)}" required><span>${e(choice.label)}</span></label>`).join("")}</fieldset><button type="submit" class="secondary">Check my repair</button></form><div id="sensor-result" role="status"></div><p class="exercise-limit">${e(exercise.limitation)}</p>`;
    }

    async function loadExercise() {
        const version = ++exerciseVersion;
        $("#sensor-exercise").innerHTML = `<p>Loading the teaching circuit…</p>`;
        try {
            const { payload, identity } = await projectRequest("/api/exercises/sensor-rail", { fetcher });
            const next = parseExercise(payload, identity);
            if (version !== exerciseVersion || disposed) return;
            exercise = next; exerciseIdentity = identity; renderExercise();
        } catch (error) {
            if (version !== exerciseVersion || disposed) return;
            $("#sensor-exercise").innerHTML = `<p role="alert">${e(message(error))}</p><button type="button" class="secondary" data-load-exercise>Retry challenge</button>`;
        }
    }

    async function checkRepair(choice) {
        if (!exercise?.choices.some((item) => item.id === choice)) return;
        const version = ++exerciseVersion;
        const form = $("#sensor-choice-form");
        form.querySelectorAll("input, button").forEach((input) => { input.disabled = true; });
        $("#sensor-result").innerHTML = `<p>Running the circuit check…</p>`;
        try {
            const { payload, identity } = await projectRequest("/api/exercises/sensor-rail", { fetcher, identity: exerciseIdentity, method: "POST", data: { choice } });
            const result = parseExerciseResult(payload, identity, choice);
            if (version !== exerciseVersion || disposed) return;
            $("#sensor-result").innerHTML = `<div class="exercise-feedback ${result.correct ? "exercise-resolved" : "exercise-retry"}"><h4>${e(result.title || (result.correct ? "Your repair resolves this check." : "Keep following the supply connections."))}</h4><p>${e(result.explanation)}</p><dl class="exercise-checks"><div><dt>Original circuit</dt><dd>${e(result.before.outcome)}</dd></div><div><dt>Your repair</dt><dd>${e(result.after.outcome)}</dd></div></dl><details><summary>See the rule and its evidence</summary><p>Rule ${e(result.after.rule_id)}</p>${result.after.findings.map((finding) => `<p><strong>${e(finding.title)}</strong> ${e(finding.description)}</p>`).join("")}${result.evidence.map((item) => `<p>${e(item.source || "Source not supplied")}${item.page == null ? "" : `, page ${e(item.page)}`}<br>${e(item.status)}${item.value == null ? "" : `: ${e(typeof item.value === "object" ? JSON.stringify(item.value) : item.value)}`}</p>`).join("")}</details><p class="exercise-limit">${e(result.limitation)}</p><button type="button" class="ghost" data-load-exercise>Reset the challenge</button></div>`;
        } catch (error) {
            if (version !== exerciseVersion || disposed) return;
            $("#sensor-result").innerHTML = `<p role="alert">${e(message(error))}</p><button type="button" class="ghost" data-load-exercise>Reload challenge</button>`;
        } finally {
            if (version === exerciseVersion) form.querySelectorAll("input, button").forEach((input) => { input.disabled = false; });
        }
    }

    function input(event) {
        if (event.target.closest?.("#sensor-choice-form")) {
            exerciseVersion += 1;
            $("#sensor-result").innerHTML = "";
        }
        if (!event.target.closest?.("#project-form")) return;
        const next = structuredClone(draft);
        next.project_name = $("#project-name").value;
        next.status_led_count = Number($("input[name=led]:checked").value);
        next.include_programming_header = $("input[name=header]:checked").value === "yes";
        next.sensors[0].address = Number($("#project-address").value);
        if (!sameBrief(next, draft)) { draft = next; onInvalidate(); }
        $("#project-address-summary").textContent = draft.sensors[0].address === 118 ? "0x76" : "0x77";
        sync();
    }
    function change(event) {
        if (event.target.id === "project-revision") {
            const next = project?.revisions.find((item) => item.revision_id === event.target.value);
            if (next) { exerciseVersion += 1; revision = next; draft = structuredClone(next.brief); onInvalidate(); render(); onOpen(draft.project_name); }
        }
    }
    function submit(event) {
        if (event.target.id === "project-form") { event.preventDefault(); void save(); }
        if (event.target.id === "sensor-choice-form") { event.preventDefault(); void checkRepair($("input[name=repair]:checked")?.value); }
    }
    function click(event) {
        if (event.target.closest?.("#project-run")) void run();
        if (event.target.closest?.("[data-load-exercise]")) void loadExercise();
    }
    function shelfClick(event) {
        const button = event.target.closest?.("[data-project-open]");
        if (button) void openProject(button.dataset.projectOpen);
        if (event.target.closest?.("[data-refresh-projects]")) void refreshShelf();
    }
    root.addEventListener("input", input); root.addEventListener("change", change);
    root.addEventListener("submit", submit); root.addEventListener("click", click);
    shelf?.addEventListener("click", shelfClick);
    render(); void refreshShelf();
    return { openNew, openProject, refreshShelf, dispose() {
        disposed = true; exerciseVersion += 1; shelfVersion += 1;
        root.removeEventListener("input", input); root.removeEventListener("change", change);
        root.removeEventListener("submit", submit); root.removeEventListener("click", click);
        shelf?.removeEventListener("click", shelfClick);
    } };
}
