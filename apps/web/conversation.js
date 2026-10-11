// Reviewable proposals. Only server-owned confirmation can create a revision.
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
export function planHtml(plan) {
    const rows = fields => fields.map(field => `<div><dt>${e(labels[field])}</dt><dd>${e(value(field, plan.brief[field]))}</dd></div>`).join("");
    const mainFields = new Set(["archetype", "input_power", "sensors", "button_count", "status_led_count", "spi_devices", "board_width_mm", "board_height_mm"]);
    const secondary = plan.assumed_fields.filter(f => !mainFields.has(f));
    return `<section><h2>${e(plan.brief.project_name)}</h2><p>Proposed choices for your review. Engineering checks have not run.</p>
      <details><summary>Your conversation (${plan.messages.length} message${plan.messages.length === 1 ? "" : "s"})</summary>${plan.messages.map(m => `<p class="conversation-message">${e(m)}</p>`).join("")}</details></section>
      <section><h3>From your words</h3><p>AI interpretations. Check that these match your intent.</p><dl class="plan-choices">${rows(plan.stated.map(s => s.field))}</dl>${plan.stated.map(s => `<p class="fineprint">${e(labels[s.field])}: “${e(s.quote)}”</p>`).join("")}${plan.stated.length ? "" : "<p>No specific choices were attributed to your wording.</p>"}</section>
      <section><h3>Suggested choices</h3><p>Defaults or inferences you can change before confirming.</p><dl class="plan-choices">${rows(plan.assumed_fields.filter(f => mainFields.has(f)))}</dl>${secondary.length ? `<details><summary>Other suggested choices (${secondary.length})</summary><dl class="plan-choices">${rows(secondary)}</dl></details>` : ""}</section>
      <p class="fineprint">USB-C provides power, not USB programming. Firmware and physical testing are still needed. Support checks on this plan do not verify electrical or manufacturing performance.</p>`;
}
export function mountConversation(root, { fetcher = globalThis.fetch, onOpen, onSaved, onGuided } = {}) {
    let plan = null, identity = null, busy = false, version = 0, confirmed = null, initial = "";
    root.innerHTML = `<div id="conversation-status" role="status" aria-live="polite"></div><div id="conversation-error" role="alert" hidden></div>
      <div id="conversation-questions"></div><form id="conversation-reply-form" hidden><label for="conversation-reply">Answer or change something</label>
      <textarea id="conversation-reply" rows="3" maxlength="2000" placeholder="For example: use two buttons and one light"></textarea>
      <button type="submit" class="secondary">Update my plan</button></form><div id="conversation-plan"></div>
      <div class="conversation-actions"><button type="button" id="conversation-confirm" class="primary" hidden>Confirm &amp; generate my board</button>
      <button type="button" id="conversation-retry" class="secondary" hidden>Retry planning</button><button type="button" id="conversation-guided" class="ghost">Use guided setup</button></div>`;
    const $ = s => root.querySelector(s);
    const error = err => { $("#conversation-error").textContent = err.message || "This request could not be completed. Your text is still here."; $("#conversation-error").hidden = false; };
    function sync() {
        root.setAttribute("aria-busy", String(busy));
        $("#conversation-reply-form").hidden = !plan || !!confirmed;
        $("#conversation-confirm").hidden = !plan;
        $("#conversation-confirm").disabled = busy || !plan?.ready;
        $("#conversation-confirm").textContent = confirmed ? "Generate saved revision" : "Confirm & generate my board";
        $("#conversation-reply").disabled = busy;
        $("#conversation-reply-form button").disabled = busy;
        $("#conversation-retry").hidden = !!plan || busy;
    }
    async function propose(message) {
        if (busy) return;
        if (message.trim().length < (plan ? 1 : 10) || message.length > 2000) { error(new Error("Describe your idea in 10 to 2000 characters, or enter a nonempty reply.")); return; }
        const current = ++version;
        busy = true; $("#conversation-error").hidden = true;
        $("#conversation-status").textContent = "Preparing your plan… Your project will only be saved when you confirm."; sync();
        try {
            const response = await projectRequest("/api/project-plans", {fetcher, timeoutMs: 90000, method: "POST", data: {message, parent_id: plan?.plan_id || null}});
            if (current !== version) return;
            const next = parsePlan(response.payload, response.identity);
            plan = next; identity = response.identity; confirmed = null;
            $("#conversation-questions").innerHTML = plan.questions.length ? `<h2>Before we build</h2><ul>${plan.questions.map(q => `<li>${e(q)}</li>`).join("")}</ul>` : "";
            $("#conversation-plan").innerHTML = planHtml(plan);
            $("#conversation-reply").value = "";
            $("#conversation-status").textContent = plan.ready ? "Review the choices, then confirm to save and generate." : "Your answer is needed. Nothing has been saved or generated.";
            if (!plan.ready) $("#conversation-reply").focus();
        } catch (err) { if (current === version) { error(err); $("#conversation-status").textContent = "Your request is preserved. Try again or use guided setup."; } }
        finally { if (current === version) { busy = false; sync(); if (plan && !plan.ready) $("#conversation-reply").focus(); } }
    }
    async function confirm() {
        if (busy || !plan?.ready) return;
        const current = ++version;
        busy = true; $("#conversation-error").hidden = true;
        $("#conversation-status").textContent = "Saving the exact plan you reviewed…"; sync();
        try {
            if (!confirmed) {
                const response = await projectRequest(`/api/project-plans/${plan.plan_id}/confirm`, {fetcher, identity, method: "POST"});
                if (current !== version) return;
                const project = parseProjectEnvelope(response.payload, response.identity);
                const revision = project.revisions.at(-1);
                if (revision.brief_fingerprint !== plan.brief_fingerprint || !sameBrief(revision.brief, plan.brief)) throw new Error("The saved revision differs from the reviewed plan. Reopen it before generating.");
                confirmed = project;
            }
            $("#conversation-status").textContent = "Revision 1 saved. Starting its engineering checks…";
            await onSaved(confirmed, identity, fetcher);
        } catch (err) { if (current === version) error(err); }
        finally { if (current === version) { busy = false; sync(); } }
    }
    $("#conversation-reply-form").addEventListener("submit", event => { event.preventDefault(); void propose($("#conversation-reply").value); });
    $("#conversation-confirm").addEventListener("click", () => void confirm());
    $("#conversation-retry").addEventListener("click", () => void propose(initial));
    $("#conversation-guided").addEventListener("click", () => { version++; busy = false; onGuided(); });
    return { begin(message) { version++; busy = false; plan = null; confirmed = null; identity = null; initial = message;
        $("#conversation-plan").innerHTML = ""; $("#conversation-questions").innerHTML = ""; onOpen(); return propose(message); },
        cancel() { version++; busy = false; }, propose, confirm };
}
