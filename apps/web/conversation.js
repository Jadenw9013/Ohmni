// Reviewable proposals. Only server-owned confirmation can create a revision.
import { planSummaryHtml } from "./plan-summary.js";
import { escapeHtml as e } from "./view-model.js";
import { checkIdentity, projectRequest, parseProjectEnvelope, supportedBrief, sameBrief } from "./project-contract.js";

const labels = {
    project_name: "Project name", description: "Purpose", archetype: "Board family",
    input_power: "Power source", input_voltage_v: "Input voltage (V)", logic_voltage_v: "Logic voltage (V)",
    mcu_part_id: "Processor", sensors: "Sensors", status_led_count: "Status lights", button_count: "Buttons",
    spi_devices: "Memory", include_programming_header: "Programming header", max_board_layers: "Board layers",
    board_width_mm: "Width (mm)", board_height_mm: "Height (mm)", hand_solderable_preferred: "Prefer hand soldering",
    budget_usd: "Budget (USD)", safety_domains: "Special operating conditions",
    recorder_sample_rate_hz: "Recording sample rate (Hz)", recorder_max_seconds: "Maximum recording duration (seconds)",
};
const text = x => typeof x === "string" && x.length > 0;
const object = x => x !== null && typeof x === "object" && !Array.isArray(x);
export function parsePlan(payload, identity) {
    checkIdentity(payload, identity);
    const p = payload.plan;
    if (!object(p) || !/^[0-9a-f]{16}$/.test(p.plan_id) || !/^[0-9a-f]{64}$/.test(p.brief_fingerprint)
        || !object(p.brief) || typeof p.ready !== "boolean" || !Array.isArray(p.messages) || !p.messages.length || !p.messages.every(text)
        || !Array.isArray(p.questions) || !p.questions.every(text) || p.ready !== (p.questions.length === 0)
        || p.design_notes !== undefined && (!Array.isArray(p.design_notes) || !p.design_notes.every(text))
        || !Array.isArray(p.stated) || !p.stated.every(s => object(s) && Object.hasOwn(labels, s.field) && text(s.quote) && p.messages.some(m => m.includes(s.quote)))
        || !Array.isArray(p.assumed_fields) || !p.assumed_fields.every(f => Object.hasOwn(labels, f))) throw new Error("This plan cannot be read safely. Try again.");
    const fields = [...p.stated.map(s => s.field), ...p.assumed_fields];
    if (new Set(fields).size !== fields.length || Object.keys(labels).filter(f => !f.startsWith("recorder_") || p.brief.archetype === "a4_usb_voice_recorder" || Object.hasOwn(p.brief,f)).some(f => !fields.includes(f) || !Object.hasOwn(p.brief, f))
        || p.ready && (!supportedBrief(p.brief) || !object(p.preview))) throw new Error("This plan is incomplete. Try again.");
    return p;
}
function value(field, item) {
    if (item === null) return "Not specified";
    if (typeof item === "boolean") return item ? "Yes" : "No";
    if (field === "archetype") return ({a1_usb_i2c_sensor: "Sensor station", a2_usb_gpio_controller: "Buttons and lights", a3_usb_spi_peripheral: "Memory board", a4_usb_voice_recorder: "Voice recorder"})[item] || item;
    if (field === "input_power" && item === "usb_c_5v") return "USB-C power only";
    if (Array.isArray(item)) return item.length ? item.map(v => typeof v === "object" ? `${v.part_id}${v.address == null ? "" : ` (address ${v.address})`}` : v).join(", ") : "None";
    return String(item);
}
export function planHtml(plan, {includeSummary = true} = {}) {
    const rows = fields => fields.filter(f=>!f.startsWith("recorder_") || plan.brief.archetype === "a4_usb_voice_recorder").map(field => `<div><dt>${e(labels[field])}</dt><dd>${e(value(field, plan.brief[field]))}</dd></div>`).join("");
    return `${includeSummary ? planSummaryHtml(plan.brief, {requested:plan.stated.map(s=>s.field)}) : ""}
      <details class="plan-details"><summary>Parts, assumptions and technical settings</summary><p>Engineering checks have not run. These are proposed choices.</p><h3>From your words</h3><dl class="plan-choices">${rows(plan.stated.map(s=>s.field))}</dl>${plan.stated.map(s=>`<p>${e(labels[s.field])}: “${e(s.quote)}”</p>`).join("")}<h3>Suggested choices</h3><dl class="plan-choices">${rows(plan.assumed_fields)}</dl></details>
      <details><summary>Your conversation (${plan.messages.length})</summary>${plan.messages.map(m=>`<p class="conversation-message">${e(m)}</p>`).join("")}</details>`;

}
/** The confirmed project, only if its saved revision is exactly the reviewed plan. */
export function confirmedProject(project, reviewed) {
    const revision = project.revisions.at(-1);
    if (revision.brief_fingerprint !== reviewed.brief_fingerprint || !sameBrief(revision.brief, reviewed.brief)) throw new Error("The saved revision differs from the reviewed plan. Reopen it before generating.");
    return project;
}

export function mountConversation(root, { fetcher = globalThis.fetch, onOpen, onSaved, onGuided,
    now = () => Date.now(), setIntervalFn = globalThis.setInterval, clearIntervalFn = globalThis.clearInterval } = {}) {
    let plan = null, identity = null, busy = false, failed = false, version = 0, confirmed = null, initial = "";
    let activity = "", activityStarted = 0, activityTimer = null, editing = false, lastAttempt = "";
    root.innerHTML = `<div id="conversation-status" role="status" aria-live="polite"></div><div id="conversation-error" role="alert" hidden></div>
      <section id="conversation-recovery" class="conversation-recovery" aria-labelledby="conversation-recovery-title" tabindex="-1" hidden>
        <span class="recovery-mark" aria-hidden="true">!</span><div class="recovery-copy"><p class="eyebrow">Your idea is safe</p>
        <h2 id="conversation-recovery-title">We couldn’t create the plan</h2>
        <p id="conversation-recovery-message">We couldn’t prepare your plan. Your idea is still here.</p>
        <div class="preserved-request"><span>Your request</span><blockquote id="conversation-preserved"></blockquote></div>
        <details class="recovery-details"><summary>Technical details</summary><p id="conversation-error-detail"></p></details>
        <div class="recovery-actions"><button type="button" id="conversation-guided-recovery" class="primary">Continue with guided setup</button>
        <button type="button" id="conversation-retry" class="secondary">Retry AI planning</button></div></div>
      </section>
      <div id="conversation-questions"></div>
      <div class="conversation-activity" id="conversation-activity" hidden><span class="conversation-spinner" aria-hidden="true"></span><span id="conversation-activity-label"></span><span id="conversation-elapsed" aria-live="off"></span></div>
      <section id="conversation-edit" hidden><form id="conversation-reply-form" hidden><label id="conversation-reply-label" for="conversation-reply">Your reply</label>
      <p id="conversation-reply-help">Answer the question above, or tell us what you want to change.</p>
      <textarea id="conversation-reply" rows="2" maxlength="2000" aria-describedby="conversation-reply-help" placeholder="Tell us how you’d like to proceed…"></textarea>
      <button type="submit" class="primary">Send reply</button></form></section>
      <div id="conversation-summary" tabindex="-1"></div>
      <div class="conversation-actions" id="conversation-actions"><button type="button" id="conversation-confirm" class="primary" aria-describedby="conversation-confirm-hint" hidden>Generate my board</button>
      <button type="button" id="conversation-change" class="secondary" hidden>Change my plan</button>
      <button type="button" id="conversation-guided" class="ghost">Use guided setup</button></div>
      <p id="conversation-confirm-hint" class="conversation-confirm-hint" role="status" hidden></p>
      <div id="conversation-plan"></div>`;
    const $ = s => root.querySelector(s);
    function stopActivity() {
        if (activityTimer !== null) clearIntervalFn(activityTimer);
        activityTimer = null; activity = "";
        $("#conversation-activity").hidden = true;
    }
    function startActivity(kind) {
        stopActivity(); activity = kind; activityStarted = now();
        $("#conversation-activity").hidden = false;
        const tick = () => {
            const seconds = Math.max(0, Math.floor((now() - activityStarted) / 1000));
            $("#conversation-activity-label").textContent = activity === "planning"
                ? (seconds >= 20 ? "Still waiting for the AI response. No board has been generated." : "Preparing your plan…")
                : activity === "saving" ? "Saving the exact plan you reviewed…" : "Plan saved. Starting your board…";
            $("#conversation-elapsed").textContent = `${seconds}s elapsed`;
        };
        tick(); activityTimer = setIntervalFn(tick, 1000);
    }
    const error = (err, recoverable = false) => {
        const message = err.message || "This request could not be completed. Your text is still here.";
        $("#conversation-error").textContent = message;
        $("#conversation-error").hidden = recoverable;
        $("#conversation-error-detail").textContent = message;
        $("#conversation-recovery-message").textContent = message;
        failed = recoverable;
    };
    function sync() {
        root.setAttribute("aria-busy", String(busy));
        $("#conversation-recovery").hidden = !failed || busy;
        $("#conversation-actions").hidden = failed;
        $("#conversation-guided").textContent = busy && activity === "planning" ? "Cancel and use guided setup" : "Use guided setup";
        $("#conversation-reply-form").hidden = !plan || !!confirmed || (plan.ready && !editing);
        $("#conversation-edit").hidden = $("#conversation-reply-form").hidden;
        $("#conversation-reply-label").textContent = plan?.ready ? "What would you like to change?" : "Your reply — needed to continue";
        $("#conversation-change").hidden = !plan?.ready || !!confirmed || editing;
        $("#conversation-change").disabled = busy;
        $("#conversation-confirm").hidden = !plan?.ready;
        $("#conversation-confirm").disabled = busy || !plan?.ready;
        $("#conversation-confirm").textContent = busy && activity === "saving" ? "Saving your plan…"
            : busy && activity === "starting" ? "Starting your board…"
            : busy ? "Updating your plan…" : confirmed ? "Generate saved revision" : "Generate my board";
        const hint = $("#conversation-confirm-hint");
        hint.hidden = !plan || failed;
        hint.textContent = busy ? "Your request is in progress. Please wait; you don't need to click again."
            : !plan?.ready ? "Generation is paused: send your reply above. You’ll review the updated plan before building."
            : confirmed ? "Your plan is saved. You can retry starting this saved revision without saving it again."
            : "Plan ready. Generate my board will save these choices and start the engineering checks.";
        $("#conversation-reply-form button").textContent = busy && activity === "planning" ? "Updating your plan…" : plan?.ready ? "Update my plan" : "Send reply";
        $("#conversation-reply").disabled = busy;
        $("#conversation-reply-form button").disabled = busy;
        $("#conversation-retry").disabled = busy;
    }
    async function propose(message) {
        if (busy) return;
        if (message.trim().length < (plan ? 1 : 10) || message.length > 2000) { error(new Error("Describe your idea in 10 to 2000 characters, or enter a nonempty reply.")); return; }
        const current = ++version;
        lastAttempt = message;
        $("#conversation-preserved").textContent = plan ? `${initial}\n\nYour latest reply: ${message}` : message;
        busy = true; failed = false; $("#conversation-error").hidden = true;
        startActivity("planning");
        $("#conversation-status").textContent = "Preparing your plan… Your project will only be saved when you confirm."; sync();
        try {
            const response = await projectRequest("/api/project-plans", {fetcher, timeoutMs: 90000, method: "POST", data: {message, parent_id: plan?.plan_id || null}, parse: parsePlan});
            if (current !== version) return;
            const next = response.parsed;
            plan = next; identity = response.identity; confirmed = null; editing = false;
            $("#conversation-questions").innerHTML = plan.questions.length ? `<h2>Let’s resolve this together</h2>${plan.questions.map(q => `<p>${e(q)}</p>`).join("")}` : "";
            const summary = planSummaryHtml(plan.brief, {requested:plan.stated.map(s=>s.field), tentative:!plan.ready})
                + (plan.design_notes?.length ? `<aside class="plan-build-notes"><h3>Before you order or assemble</h3>${plan.design_notes.map(note => `<p>${e(note)}</p>`).join("")}</aside>` : "");
            $("#conversation-summary").innerHTML = plan.ready ? summary : `<details class="conversation-draft"><summary>View tentative hardware choices</summary>${summary}</details>`;
            $("#conversation-plan").innerHTML = planHtml(plan, {includeSummary:false});
            $("#conversation-reply").value = "";
            $("#conversation-status").textContent = plan.ready ? "Plan ready to review. Engineering checks have not run." : "One more step: reply below to continue planning. No board has been generated.";
        } catch (err) { if (current === version) { error(err, true); $("#conversation-status").textContent = "Planning paused. Your request has not been lost."; } }
        finally { if (current === version) { busy = false; stopActivity(); sync(); if (failed) $("#conversation-recovery").focus(); else if (plan) $(plan.ready ? "#conversation-summary" : "#conversation-reply").focus(); } }
    }
    async function confirm() {
        if (busy || !plan?.ready) return;
        const current = ++version;
        busy = true; $("#conversation-error").hidden = true;
        startActivity(confirmed ? "starting" : "saving");
        $("#conversation-status").textContent = "Saving the exact plan you reviewed…"; sync();
        try {
            if (!confirmed) {
                // The saved revision must match the reviewed plan before the
                // request counts as a success, so the check runs inside it.
                const reviewed = plan;
                const response = await projectRequest(`/api/project-plans/${reviewed.plan_id}/confirm`, {fetcher, identity, method: "POST",
                    parse: (payload, current) => confirmedProject(parseProjectEnvelope(payload, current), reviewed)});
                if (current !== version) return;
                confirmed = response.parsed;
            }
            $("#conversation-status").textContent = "Revision 1 saved. Starting its engineering checks…";
            startActivity("starting"); sync();
            await onSaved(confirmed, identity, fetcher);
        } catch (err) { if (current === version) error(err); }
        finally { if (current === version) { busy = false; stopActivity(); sync(); } }
    }
    $("#conversation-reply-form").addEventListener("submit", event => { event.preventDefault(); void propose($("#conversation-reply").value); });
    $("#conversation-confirm").addEventListener("click", () => void confirm());
    $("#conversation-retry").addEventListener("click", () => void propose(lastAttempt));
    $("#conversation-change").addEventListener("click", () => { editing = true; sync(); $("#conversation-reply").focus(); });
    const useGuided = () => { version++; busy = false; stopActivity(); onGuided(plan?.brief); };
    $("#conversation-guided").addEventListener("click", useGuided);
    $("#conversation-guided-recovery").addEventListener("click", useGuided);
    return { begin(message) { version++; busy = false; stopActivity(); plan = null; confirmed = null; identity = null; initial = message;
        failed = false; editing = false; $("#conversation-reply").value = ""; $("#conversation-preserved").textContent = message;
        $("#conversation-summary").innerHTML = ""; $("#conversation-plan").innerHTML = ""; $("#conversation-questions").innerHTML = ""; onOpen(); return propose(message); },
        cancel() { version++; busy = false; stopActivity(); sync(); }, propose, confirm };
}
