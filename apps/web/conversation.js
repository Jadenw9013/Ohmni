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
};
const text = x => typeof x === "string" && x.length > 0;
const object = x => x !== null && typeof x === "object" && !Array.isArray(x);
export function parsePlan(payload, identity) {
    checkIdentity(payload, identity);
    const p = payload.plan;
    if (!object(p) || !/^[0-9a-f]{16}$/.test(p.plan_id) || !/^[0-9a-f]{64}$/.test(p.brief_fingerprint)
        || !object(p.brief) || typeof p.ready !== "boolean" || !Array.isArray(p.messages) || !p.messages.length || !p.messages.every(text)
        || !Array.isArray(p.questions) || !p.questions.every(text) || p.ready !== (p.questions.length === 0)
        || !Array.isArray(p.stated) || !p.stated.every(s => object(s) && Object.hasOwn(labels, s.field) && text(s.quote) && p.messages.some(m => m.includes(s.quote)))
        || !Array.isArray(p.assumed_fields) || !p.assumed_fields.every(f => Object.hasOwn(labels, f))) throw new Error("This plan cannot be read safely. Try again.");
    const fields = [...p.stated.map(s => s.field), ...p.assumed_fields];
    if (new Set(fields).size !== fields.length || Object.keys(labels).some(f => !fields.includes(f) || !Object.hasOwn(p.brief, f))
        || p.ready && (!supportedBrief(p.brief) || !object(p.preview))) throw new Error("This plan is incomplete. Try again.");
    return p;
}
function value(field, item) {
    if (item === null) return "Not specified";
    if (typeof item === "boolean") return item ? "Yes" : "No";
    if (field === "archetype") return ({a1_usb_i2c_sensor: "Sensor station", a2_usb_gpio_controller: "Buttons and lights", a3_usb_spi_peripheral: "Memory board"})[item] || item;
    if (field === "input_power" && item === "usb_c_5v") return "USB-C power only";
    if (Array.isArray(item)) return item.length ? item.map(v => typeof v === "object" ? `${v.part_id}${v.address == null ? "" : ` (address ${v.address})`}` : v).join(", ") : "None";
    return String(item);
}
export function planHtml(plan, {includeSummary = true} = {}) {
    const rows = fields => fields.map(field => `<div><dt>${e(labels[field])}</dt><dd>${e(value(field, plan.brief[field]))}</dd></div>`).join("");
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

export function mountConversation(root, { fetcher = globalThis.fetch, onOpen, onSaved, onGuided } = {}) {
    let plan = null, identity = null, busy = false, failed = false, version = 0, confirmed = null, initial = "";
    root.innerHTML = `<div id="conversation-status" role="status" aria-live="polite"></div><div id="conversation-error" role="alert" hidden></div>
      <section id="conversation-recovery" class="conversation-recovery" aria-labelledby="conversation-recovery-title" tabindex="-1" hidden>
        <span class="recovery-mark" aria-hidden="true">!</span><div class="recovery-copy"><p class="eyebrow">Your idea is safe</p>
        <h2 id="conversation-recovery-title">We couldn’t create the plan</h2>
        <p>The AI planner is unavailable right now. Continue with the step-by-step setup, or retry without typing your idea again.</p>
        <div class="preserved-request"><span>Your request</span><blockquote id="conversation-preserved"></blockquote></div>
        <details class="recovery-details"><summary>Technical details</summary><p id="conversation-error-detail"></p></details>
        <div class="recovery-actions"><button type="button" id="conversation-guided-recovery" class="primary">Continue with guided setup</button>
        <button type="button" id="conversation-retry" class="secondary">Retry AI planning</button></div></div>
      </section>
      <div id="conversation-questions"></div><div id="conversation-summary"></div>
      <div class="conversation-actions" id="conversation-actions"><button type="button" id="conversation-confirm" class="primary" hidden>Generate my board</button>
      <button type="button" id="conversation-guided" class="ghost">Use guided setup</button></div>
      <details id="conversation-edit" hidden><summary>Change something</summary><form id="conversation-reply-form" hidden><label for="conversation-reply">Answer or change something</label>
      <textarea id="conversation-reply" rows="3" maxlength="2000" placeholder="For example: use two buttons and one light"></textarea>
      <button type="submit" class="secondary">Update my plan</button></form></details><div id="conversation-plan"></div>`;
    const $ = s => root.querySelector(s);
    const error = (err, recoverable = false) => {
        const message = err.message || "This request could not be completed. Your text is still here.";
        $("#conversation-error").textContent = message;
        $("#conversation-error").hidden = recoverable;
        $("#conversation-error-detail").textContent = message;
        failed = recoverable;
    };
    function sync() {
        root.setAttribute("aria-busy", String(busy));
        $("#conversation-recovery").hidden = !failed || busy;
        $("#conversation-actions").hidden = failed;
        $("#conversation-reply-form").hidden = !plan || !!confirmed;
        $("#conversation-edit").hidden = !plan || !!confirmed;
        if (plan && !plan.ready) $("#conversation-edit").open = true;
        $("#conversation-confirm").hidden = !plan;
        $("#conversation-confirm").disabled = busy || !plan?.ready;
        $("#conversation-confirm").textContent = confirmed ? "Generate saved revision" : "Generate my board";
        $("#conversation-reply").disabled = busy;
        $("#conversation-reply-form button").disabled = busy;
        $("#conversation-retry").disabled = busy;
    }
    async function propose(message) {
        if (busy) return;
        if (message.trim().length < (plan ? 1 : 10) || message.length > 2000) { error(new Error("Describe your idea in 10 to 2000 characters, or enter a nonempty reply.")); return; }
        const current = ++version;
        busy = true; failed = false; $("#conversation-error").hidden = true;
        $("#conversation-status").textContent = "Preparing your plan… Your project will only be saved when you confirm."; sync();
        try {
            const response = await projectRequest("/api/project-plans", {fetcher, timeoutMs: 90000, method: "POST", data: {message, parent_id: plan?.plan_id || null}, parse: parsePlan});
            if (current !== version) return;
            const next = response.parsed;
            plan = next; identity = response.identity; confirmed = null;
            $("#conversation-questions").innerHTML = plan.questions.length ? `<h2>Before we build</h2><ul>${plan.questions.map(q => `<li>${e(q)}</li>`).join("")}</ul>` : "";
            $("#conversation-summary").innerHTML = planSummaryHtml(plan.brief, {requested:plan.stated.map(s=>s.field)});
            $("#conversation-plan").innerHTML = planHtml(plan, {includeSummary:false});
            $("#conversation-reply").value = "";
            $("#conversation-status").textContent = plan.ready ? "Proposed plan. Engineering checks have not run." : "Your answer is needed. Nothing has been saved or generated.";
            if (!plan.ready) $("#conversation-reply").focus();
        } catch (err) { if (current === version) { error(err, true); $("#conversation-status").textContent = "Planning paused. Your request has not been lost."; } }
        finally { if (current === version) { busy = false; sync(); if (failed) $("#conversation-recovery").focus(); else if (plan && !plan.ready) $("#conversation-reply").focus(); } }
    }
    async function confirm() {
        if (busy || !plan?.ready) return;
        const current = ++version;
        busy = true; $("#conversation-error").hidden = true;
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
            await onSaved(confirmed, identity, fetcher);
        } catch (err) { if (current === version) error(err); }
        finally { if (current === version) { busy = false; sync(); } }
    }
    $("#conversation-reply-form").addEventListener("submit", event => { event.preventDefault(); void propose($("#conversation-reply").value); });
    $("#conversation-confirm").addEventListener("click", () => void confirm());
    $("#conversation-retry").addEventListener("click", () => void propose(initial));
    const useGuided = () => { version++; busy = false; onGuided(plan?.brief); };
    $("#conversation-guided").addEventListener("click", useGuided);
    $("#conversation-guided-recovery").addEventListener("click", useGuided);
    return { begin(message) { version++; busy = false; plan = null; confirmed = null; identity = null; initial = message;
        failed = false; $("#conversation-preserved").textContent = message;
        $("#conversation-summary").innerHTML = ""; $("#conversation-plan").innerHTML = ""; $("#conversation-questions").innerHTML = ""; onOpen(); return propose(message); },
        cancel() { version++; busy = false; }, propose, confirm };
}
