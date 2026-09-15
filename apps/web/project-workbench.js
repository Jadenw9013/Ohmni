import { escapeHtml } from "./view-model.js";
import { errorKind, fetchHealth } from "./client-contract.js";
import { defaultProjectBrief, parseProjectEnvelope, parseProjectList, parseProjectOptions, projectRequest, sameBrief, supportedBrief, briefFitsOptions, checkIdentity, briefChanges, ProjectRequestError } from "./project-contract.js";

const e = escapeHtml;
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const hasText = (value) => typeof value === "string" && value.length > 0;
const familyCopy = {
    a1_usb_i2c_sensor: { title: "Measure your space", outcome: "Build a sensor station", icon: "M11 5a3 3 0 0 1 6 0v10a5 5 0 1 1-6 0ZM14 8v11M21 6h3m-3 5h3" },
    a2_usb_gpio_controller: { title: "Buttons & lights", outcome: "Build a controller", icon: "M3 14h10v9H3zM5 11h6v3M18 8a4 4 0 1 1 8 0v5h-8ZM20 13v7m4-7v7M17 3l-2-2m12 2 2-2" },
    a3_usb_spi_peripheral: { title: "Store data", outcome: "Build a memory board", icon: "M7 6h16v18H7zM11 10h8v10h-8zM3 9h4m-4 6h4m-4 6h4m16-12h4m-4 6h4m-4 6h4" },
};
const addressLabel = (value) => value == null ? "Automatic" : `0x${value.toString(16).toUpperCase()}`;
const exerciseStartHtml = () => `<button type="button" class="secondary" data-load-exercise>Try the sensor challenge</button><p class="fineprint">A separate teaching circuit. Your project stays as you chose it.</p>`;

export function switchFamilyDraft(current, familyId, options, previousDrafts = new Map()) {
    previousDrafts.set(current.archetype, structuredClone(current));
    const previousDefault = options.families.find((family) => family.id === current.archetype)?.defaults;
    const targetDefault = defaultProjectBrief(options, familyId);
    const target = structuredClone(previousDrafts.get(familyId) || targetDefault);
    const specific = new Set(["archetype", "sensors", "spi_devices", "button_count", "status_led_count", "include_programming_header"]);
    for (const [key, value] of Object.entries(current)) if (!specific.has(key)) target[key] = structuredClone(value);
    if (current.project_name === previousDefault?.project_name) target.project_name = targetDefault.project_name;
    if (current.description === previousDefault?.description) target.description = targetDefault.description;
    return target;
}

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
    let pendingProjectId = null;
    let pendingNewSeed = null;
    let editorVersion = 0;
    let draft = defaultProjectBrief();
    let busy = false;
    let options = null;
    let optionsPromise = null;
    const familyDrafts = new Map();
    const sensorDrafts = new Map();
    const memoryDrafts = new Map();
    let exercise = null;
    let exerciseIdentity = null;
    let exerciseVersion = 0;
    let shelfVersion = 0;
    let disposed = false;
    const $ = (selector) => root.querySelector(selector);

    function countSelect(field, label, count, range) {
        return `<label class="feature-count" for="project-${field}"><span>${e(label)}</span><select id="project-${field}" name="${field}">${Array.from({ length: range.max - range.min + 1 }, (_, i) => range.min + i).map((value) => `<option value="${value}" ${value === count ? "selected" : ""}>${value === 0 ? "None" : value}</option>`).join("")}</select></label>`;
    }

    function sensorControls(family) {
        if (!family.sensor_count.max) return "";
        return `<fieldset class="project-choice"><legend>Sensors that read your surroundings</legend><p>Choose what your board can measure. A program will read the sensors and decide what to do with the values.</p>${countSelect("sensor-count", "Number of sensors", draft.sensors.length, family.sensor_count)}<div class="sensor-slots">${draft.sensors.map((sensor, i) => {
            const part = options.sensors.find((item) => item.part_id === sensor.part_id);
            return `<div class="sensor-slot"><label for="project-sensor-${i}">Sensor ${i + 1}</label><select id="project-sensor-${i}" data-sensor-part="${i}">${options.sensors.map((item) => `<option value="${e(item.part_id)}" ${item.part_id === sensor.part_id ? "selected" : ""}>${e(item.label)}</option>`).join("")}</select><p>${e(part?.description || "This saved part is not offered by the current server.")}</p><label class="sensor-address" for="project-address-${i}"><span>Address on the shared connection</span><select id="project-address-${i}" data-sensor-address="${i}"><option value="auto" ${sensor.address == null ? "selected" : ""}>Automatic</option>${(part?.addresses || []).map((address) => `<option value="${address}" ${sensor.address === address ? "selected" : ""}>${addressLabel(address)}</option>`).join("")}</select></label></div>`;
        }).join("")}</div><p class="feature-help">Each sensor needs its own address. Automatic lets the server choose when you save; any conflict comes back with an explanation.</p></fieldset>`;
    }

    function memoryControls(family) {
        if (!family.spi_count.max) return "";
        return `<fieldset class="project-choice"><legend>A place to keep data</legend><p>EEPROM can retain stored values without power. Your firmware will control what gets written and read.</p>${countSelect("memory-count", "Memory devices", draft.spi_devices?.length || 0, family.spi_count)}${(draft.spi_devices || []).map((device, i) => `<div class="memory-slot"><label for="project-memory-${i}">Memory ${i + 1}</label><select id="project-memory-${i}" data-memory-part="${i}">${options.spi_devices.map((part) => `<option value="${e(part.part_id)}" ${part.part_id === device.part_id ? "selected" : ""}>${e(part.label)}</option>`).join("")}</select><p>${e(options.spi_devices.find((part) => part.part_id === device.part_id)?.description || "")}</p></div>`).join("")}</fieldset>`;
    }

    function render() {
        // Keep the actual form: an in-flight check must re-enable the same
        // controls after the surrounding feature editor is redrawn.
        const retainedExercise = $("#sensor-exercise");
        const family = options?.families.find((item) => item.id === draft.archetype);
        root.innerHTML = `<form id="project-form" class="family-workbench">
          <div class="project-editor-heading"><div><h2>What would you like to make?</h2><p>Start with a purpose. Make the details yours.</p></div><span class="project-save-state" id="project-save-state" role="status"></span></div>
          <fieldset class="family-picker"><legend class="sr-only">Choose the kind of board</legend>${Object.entries(familyCopy).map(([id, copy]) => `<label class="family-option"><input type="radio" name="family" value="${id}" ${id === draft.archetype ? "checked" : ""}><svg viewBox="0 0 32 28" aria-hidden="true"><path d="${copy.icon}"/></svg><span><strong>${copy.title}</strong><small>${copy.outcome}</small></span></label>`).join("")}</fieldset>
          <div id="project-error" class="run-error" role="alert" hidden></div>
          <div id="project-load-retry" hidden><button type="button" class="secondary" data-load-project>Retry opening saved project</button></div>
          ${!options ? `<div class="project-options-loading"><p>Loading the available parts and board choices from your server…</p><button type="button" class="secondary" data-load-options>Retry loading choices</button></div>` : ""}
          <div class="project-edit-layout">
            <section class="project-editor" aria-label="Your board features">
              <label class="project-name-label" for="project-name">Give your project a name</label><input id="project-name" name="project_name" type="text" required maxlength="120" value="${e(draft.project_name)}" autocomplete="off">
              <div class="project-circuit-strip" aria-label="USB-C power, regulated supply, ESP32 processor and your chosen features"><span>USB-C<small>5 V power</small></span><i aria-hidden="true"></i><span>3.3 V<small>Regulated supply</small></span><i aria-hidden="true"></i><span>ESP32<small>Your processor</small></span></div>
              <p class="project-envelope">${e(family?.description || "Your server provides the supported combinations.")}</p>
              ${family ? memoryControls(family) + sensorControls(family) : ""}
              ${options?.board_dimensions ? `<fieldset class="project-choice"><legend>Make space for your circuit</legend><p>A smaller board brings the parts closer. The placement and routing checks determine whether your choices fit.</p><div class="board-dimensions">${[["board_width_mm", "Width"], ["board_height_mm", "Height"]].map(([field, label]) => {
                  const size = options.board_dimensions[field];
                  return `<label for="project-${field}">${label} (mm)<input id="project-${field}" type="number" min="${size.min}" max="${size.max}" step="any" required value="${draft[field] ?? size.default}"></label>`;
              }).join("")}</div></fieldset>` : ""}
              ${family?.button_count.max ? `<fieldset class="project-choice"><legend>Give your program an input</legend><p>Physical buttons give you a simple way to interact with your device. Firmware decides how it responds.</p>${countSelect("button-count", "Push buttons", draft.button_count || 0, family.button_count)}</fieldset>` : ""}
              ${family ? `<fieldset class="project-choice"><legend>A signal you can see</legend><p>A light can show what your program is doing. Each selected LED comes with its current-limiting resistor.</p>${countSelect("led", "Status lights", draft.status_led_count, family.status_led_count)}</fieldset>` : ""}
              <fieldset class="project-choice"><legend>How you will program it</legend><p>USB-C supplies power. Programming needs a separate 3.3 V USB-to-serial adapter.</p><div class="project-choice-options">
                <label><input type="radio" name="header" value="yes" ${draft.include_programming_header ? "checked" : ""}><span><strong>Include the programming header</strong><small>A connection for your external adapter</small></span></label>
                <label><input type="radio" name="header" value="no" ${!draft.include_programming_header ? "checked" : ""}><span><strong>Leave the header out</strong><small>You will need to provide programming access</small></span></label>
              </div></fieldset>
              <details class="saved-details"><summary>Additional saved requirements</summary><p>These stay with your revision when you edit the features above.</p><label for="project-description">What this project is for<textarea id="project-description" rows="3" maxlength="1000">${e(draft.description)}</textarea></label><dl><div><dt>Input supply</dt><dd>${e(draft.input_voltage_v)} V</dd></div><div><dt>Logic supply</dt><dd>${e(draft.logic_voltage_v)} V</dd></div><div><dt>Board layers</dt><dd>${e(draft.max_board_layers)}</dd></div><div><dt>Budget preference</dt><dd>${draft.budget_usd == null ? "Not specified" : `$${e(draft.budget_usd)} (total cost is unknown)`}</dd></div><div><dt>Hand soldering preferred</dt><dd>${draft.hand_solderable_preferred ? "Yes" : "No"}</dd></div></dl></details>
            </section>
            <aside class="project-confirmation" aria-labelledby="confirmed-brief-title"><div class="confirmation-heading"><span aria-hidden="true">↳</span><div><h2 id="confirmed-brief-title">Your confirmed brief</h2><p id="project-preview-note">Save your choices to see what the server will build.</p></div></div><div class="project-editor-actions"><button type="submit" id="project-save" class="secondary">Save first revision</button><button type="button" id="project-run" class="primary" disabled>Generate my board</button></div><p id="project-action-note" class="project-action-note" aria-live="polite"></p><div id="project-preview"></div><div class="project-build-boundary"><strong>A board is the beginning.</strong><p>You get a schematic, PCB, recorded engineering checks, and build files. Assembly, firmware, and testing turn it into a working device.</p><details><summary>Know the limits before building</summary>${(options?.limitations || []).map((limit) => `<p>${e(limit)}</p>`).join("")}</details></div></aside>
          </div>
        </form>
        <div class="project-secondary"><section class="project-history" aria-labelledby="project-history-title"><h2 id="project-history-title">Your saved revisions</h2><p>Every save keeps a separate version on this server. Reopen one to compare or build it.</p><div id="project-history-options"></div><div id="project-revision-changes"></div></section><aside class="project-learning"><div class="project-learning-intro"><span aria-hidden="true">↳</span><div><h2>Follow the power.</h2><p>Try a short sensor challenge while your own design takes shape.</p></div></div><div id="sensor-exercise" aria-live="polite">${exerciseStartHtml()}</div></aside></div>`;
        if (retainedExercise) $("#sensor-exercise").replaceWith(retainedExercise);
        renderHistory(); sync();
    }

    function applyNewDraft() {
        const seed = pendingNewSeed;
        const valid = seed && briefFitsOptions(seed, options);
        draft = valid ? structuredClone(seed) : defaultProjectBrief(options);
        pendingNewSeed = null;
        render();
        if (seed) {
            onOpen(draft.project_name);
            if (!valid) showError(new ProjectRequestError("This saved board uses choices the current server does not offer. Choose an available configuration below."));
        }
    }

    async function ensureOptions() {
        if (options) return options;
        if (optionsPromise) return optionsPromise;
        optionsPromise = (async () => {
            try {
                const result = await projectRequest("/api/project-options", { fetcher });
                const next = parseProjectOptions(result.payload, result.identity);
                if (disposed) return null;
                options = next;
                if (!project && !revision && !pendingProjectId) applyNewDraft();
                else render();
                return options;
            } catch (error) { if (!disposed) showError(error); return null; }
            finally { optionsPromise = null; sync(); }
        })();
        return optionsPromise;
    }

    function sync() {
        if (!$("#project-form")) return;
        const dirty = !revision || !sameBrief(draft, revision.brief);
        $("#project-save-state").textContent = busy ? "Working…" : pendingProjectId ? "Saved project unavailable" : !options ? "Choices unavailable" : dirty ? "Unsaved changes" : `Revision ${revision.number} saved`;
        $("#project-save").textContent = busy ? "Working…" : project ? "Save new revision" : "Save first revision";
        $("#project-save").disabled = busy || !options || !!pendingProjectId || !dirty;
        $("#project-run").disabled = busy || !options || !!pendingProjectId || dirty || !revision;
        $("#project-run").textContent = revision?.job_id ? "Open this revision's run" : "Generate my board";
        $("#project-action-note").textContent = pendingProjectId ? "Retry opening this saved project to recover its choices and revisions."
            : dirty ? "Save your choices first. Existing revisions keep their original design and files."
            : `Revision ${revision.number} is saved. ${revision.job_id ? "Reopen its engineering run." : "Generate its board and run the real checks. This usually takes a short wait; a difficult route can take up to three minutes."}`;
        $("#project-preview-note").textContent = !revision ? "Save your choices to see what the server will build."
            : dirty ? `These are revision ${revision.number}'s saved choices. Save your changes to confirm a new brief.`
                : `Revision ${revision.number} is confirmed. Its engineering checks begin when you generate the board.`;
        $("#project-load-retry").hidden = !pendingProjectId || !options || busy;
        root.querySelectorAll("[data-load-options], [data-load-project]").forEach((button) => { button.disabled = busy; });
        root.querySelectorAll("#project-form input, #project-form select, #project-form textarea, #project-revision").forEach((input) => { input.disabled = busy || !options || !!pendingProjectId; });
    }

    function renderHistory() {
        $("#project-history-options").innerHTML = project ? `<label for="project-revision">Open a saved version</label><select id="project-revision">${project.revisions.toReversed().map((item) => `<option value="${e(item.revision_id)}" ${item.revision_id === revision?.revision_id ? "selected" : ""}>Revision ${item.number} — ${e(item.brief.project_name)}</option>`).join("")}</select>` : `<p class="project-empty">Your first saved revision will appear here.</p>`;
        const preview = revision?.preview;
        const previous = project?.revisions.find((item) => item.number === revision?.number - 1);
        $("#project-revision-changes").innerHTML = preview ? `<div class="revision-changes"><p>${previous ? `Changes from revision ${previous.number}` : "Your starting point"}</p><ul>${briefChanges(previous?.brief, revision.brief).map((change) => `<li>${e(change)}</li>`).join("")}</ul></div>` : "";
        $("#project-preview").innerHTML = preview ? `<dl class="confirmed-choices">${(preview.asked_for || []).map((line) => `<div><dt>${e(line.label)}</dt><dd>${e(line.value)}</dd></div>`).join("")}</dl><details class="disclose"><summary>Assumptions and things to check</summary>${[...preview.assumed || [], ...preview.needs_clarification || []].map((line) => `<p><strong>${e(line.label)}</strong><br>${e(line.value)}</p>`).join("")}<p class="fineprint">This is the saved brief. Engineering results appear after its run completes.</p></details>` : `<div class="unconfirmed-brief"><p>Choose your parts on the left, then save a revision.</p><p>The server will record the exact configuration and explain any choices it cannot support.</p></div>`;
    }

    function showError(error) {
        $("#project-error").textContent = message(error);
        $("#project-error").hidden = false;
    }

    async function openNew(seed = null) {
        if (busy) return;
        const version = ++editorVersion;
        pendingNewSeed = seed ? structuredClone(seed) : null;
        resetExercise();
        project = null; revision = null; pendingProjectId = null; draft = defaultProjectBrief(options);
        familyDrafts.clear(); sensorDrafts.clear(); memoryDrafts.clear();
        onInvalidate(); render(); onOpen(draft.project_name);
        if (options) applyNewDraft();
        await ensureOptions();
        if (version === editorVersion && !disposed) $("#project-name")?.focus();
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
        editorVersion += 1;
        pendingNewSeed = null;
        busy = true;
        pendingProjectId = projectId;
        resetExercise();
        project = null; revision = null; draft = defaultProjectBrief();
        onInvalidate(); onOpen("Your saved project"); render(); sync();
        try {
            if (!await ensureOptions()) return;
            const { payload, identity } = await projectRequest(`/api/projects/${encodeURIComponent(projectId)}`, { fetcher });
            const next = parseProjectEnvelope(payload, identity);
            if (next.project_id !== projectId) throw new Error("Project identity mismatch");
            if (!next.revisions.every((item) => briefFitsOptions(item.brief, options))) throw new ProjectRequestError("This project contains choices that the current editor cannot display. Reload after updating the app and server together.");
            project = next; revision = next.revisions.at(-1); draft = structuredClone(revision.brief);
            pendingProjectId = null;
            familyDrafts.clear(); sensorDrafts.clear(); memoryDrafts.clear();
            render(); onOpen(draft.project_name);
        } catch (error) { showError(error); }
        finally { busy = false; sync(); }
    }

    async function save() {
        if (busy || !options || pendingProjectId) return;
        if (!draft.project_name.trim() || draft.project_name.length > 120) return showError(new ProjectRequestError("Give your project a name before saving. Use between 1 and 120 characters."));
        if (!draft.description.length || draft.description.length > 1000) {
            const description = $("#project-description");
            const details = description?.closest?.("details");
            if (details) details.open = true;
            description?.focus();
            return showError(new ProjectRequestError("Add a short project purpose under Additional saved requirements. Use between 1 and 1,000 characters."));
        }
        if (!supportedBrief(draft)) return showError(new ProjectRequestError("Some saved requirements cannot be read by this editor. Reload after updating the app and server together."));
        if (!briefFitsOptions(draft, options)) return showError(new ProjectRequestError("Some saved choices are not offered by this server. Review the parts and counts before saving."));
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
        if (busy || !options || !revision || !sameBrief(draft, revision.brief)) return;
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

    function resetExercise() {
        exerciseVersion += 1;
        exercise = null;
        exerciseIdentity = null;
        const container = $("#sensor-exercise");
        if (container) container.innerHTML = `<p>The teaching challenge has been reset for this project.</p>${exerciseStartHtml()}`;
    }

    async function loadExercise() {
        const version = ++exerciseVersion;
        exercise = null;
        exerciseIdentity = null;
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

    function rememberSlots() {
        const sensors = sensorDrafts.get(draft.archetype) || [];
        draft.sensors.forEach((sensor, i) => { sensors[i] = structuredClone(sensor); });
        sensorDrafts.set(draft.archetype, sensors);
        const memories = memoryDrafts.get(draft.archetype) || [];
        (draft.spi_devices || []).forEach((device, i) => { memories[i] = structuredClone(device); });
        memoryDrafts.set(draft.archetype, memories);
    }

    function input(event) {
        if (event.target.closest?.("#sensor-choice-form")) {
            exerciseVersion += 1;
            $("#sensor-result").innerHTML = "";
        }
        if (!event.target.closest?.("#project-form") || busy || !options || pendingProjectId) return;
        const target = event.target;
        let next = structuredClone(draft);
        let redraw = false;
        const family = options.families.find((item) => item.id === draft.archetype);
        if (target.name === "family" && target.value !== draft.archetype) {
            rememberSlots();
            next = switchFamilyDraft(draft, target.value, options, familyDrafts);
            redraw = true;
        } else if (target.id === "project-name") next.project_name = target.value;
        else if (target.id === "project-description") next.description = target.value;
        else if (target.id === "project-led") next.status_led_count = Number(target.value);
        else if (target.id === "project-button-count") next.button_count = Number(target.value);
        else if (target.id === "project-board_width_mm") next.board_width_mm = Number(target.value);
        else if (target.id === "project-board_height_mm") next.board_height_mm = Number(target.value);
        else if (target.name === "header") next.include_programming_header = target.value === "yes";
        else if (target.id === "project-sensor-count") {
            rememberSlots();
            next.sensors = Array.from({ length: Number(target.value) }, (_, i) => structuredClone(
                sensorDrafts.get(draft.archetype)?.[i] || family.sensor_slot_defaults[i]));
            redraw = true;
        } else if (target.id === "project-memory-count") {
            rememberSlots();
            next.spi_devices = Array.from({ length: Number(target.value) }, (_, i) => structuredClone(
                memoryDrafts.get(draft.archetype)?.[i] || family.defaults.spi_devices?.[0] || { part_id: options.spi_devices[0].part_id }));
            redraw = true;
        } else if (target.dataset?.sensorPart !== undefined) {
            next.sensors[Number(target.dataset.sensorPart)] = { part_id: target.value, address: null };
            redraw = true;
        } else if (target.dataset?.sensorAddress !== undefined) {
            next.sensors[Number(target.dataset.sensorAddress)].address = target.value === "auto" ? null : Number(target.value);
        } else if (target.dataset?.memoryPart !== undefined) {
            next.spi_devices[Number(target.dataset.memoryPart)].part_id = target.value;
        }
        if (!sameBrief(next, draft)) {
            draft = next; onInvalidate();
            $("#project-error").hidden = true;
            if (redraw) {
                render();
                const selector = target.name === "family" ? `input[name="family"][value="${draft.archetype}"]` : `#${target.id}`;
                $(selector)?.focus();
            }
        }
        sync();
    }
    function change(event) {
        if (event.target.id === "project-revision") {
            const next = project?.revisions.find((item) => item.revision_id === event.target.value);
            if (next && !busy) { resetExercise(); revision = next; draft = structuredClone(next.brief); familyDrafts.clear(); sensorDrafts.clear(); memoryDrafts.clear(); onInvalidate(); render(); onOpen(draft.project_name); }
        }
    }
    function submit(event) {
        if (event.target.id === "project-form") { event.preventDefault(); void save(); }
        if (event.target.id === "sensor-choice-form") { event.preventDefault(); void checkRepair($("input[name=repair]:checked")?.value); }
    }
    function click(event) {
        if (event.target.closest?.("#project-run")) void run();
        if (event.target.closest?.("[data-load-options]")) void (pendingProjectId ? openProject(pendingProjectId) : ensureOptions());
        if (event.target.closest?.("[data-load-project]") && pendingProjectId) void openProject(pendingProjectId);
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
    render(); void ensureOptions(); void refreshShelf();
    return { openNew, openProject, refreshShelf, dispose() {
        disposed = true; exerciseVersion += 1; shelfVersion += 1;
        root.removeEventListener("input", input); root.removeEventListener("change", change);
        root.removeEventListener("submit", submit); root.removeEventListener("click", click);
        shelf?.removeEventListener("click", shelfClick);
    } };
}
