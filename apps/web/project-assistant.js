import { escapeHtml as e } from "./view-model.js";
import { checkIdentity, projectRequest, parseProjectEnvelope, sameBrief, supportedBrief } from "./project-contract.js";

const id = x => typeof x === "string" && /^[a-f0-9]{16}$/.test(x);
const hash = x => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
const object = x => x !== null && typeof x === "object" && !Array.isArray(x);
const text = x => typeof x === "string" && x.length > 0;
const canonical = x => Array.isArray(x) ? x.map(canonical) : object(x) ? Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])) : x;
const equal = (a,b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const label = field => ({board_width_mm:"Board width (mm)",board_height_mm:"Board height (mm)",input_voltage_v:"Input voltage (V)",logic_voltage_v:"Logic voltage (V)",status_led_count:"Status lights",button_count:"Buttons",spi_devices:"Memory",include_programming_header:"Programming header",mcu_part_id:"Processor",input_power:"Power source",max_board_layers:"Board layers",budget_usd:"Budget (USD)"})[field.replaceAll(" ","_")] || field.replaceAll("_", " ").replace(/^./, x=>x.toUpperCase());
const display = x => x === null ? "Not specified" : typeof x === "boolean" ? x ? "Yes" : "No"
    : Array.isArray(x) ? x.length ? x.map(display).join(", ") : "None"
    : object(x) ? Object.entries(x).map(([k,v])=>`${label(k)}: ${display(v)}`).join("; ")
    : ({not_run:"Not run yet",usb_c_5v:"USB-C power only",a1_usb_i2c_sensor:"Sensor station",a2_usb_gpio_controller:"Buttons and lights",a3_usb_spi_peripheral:"Memory board"})[x] || String(x);

export function parseTurn(payload, identity, context) {
    checkIdentity(payload, identity);
    const t = payload.turn;
    if (!object(t) || !id(t.turn_id) || t.project_id !== context.projectId || t.revision_id !== context.revision.revision_id
        || t.revision_number !== context.revision.number || t.base_brief_fingerprint !== context.revision.brief_fingerprint
        || !hash(t.context_fingerprint) || !["answer","change","unavailable"].includes(t.kind)
        || !Array.isArray(t.messages) || !t.messages.length || !t.messages.every(text)
        || !Array.isArray(t.facts) || !t.facts.every(f => object(f) && text(f.id) && text(f.label) && text(f.source) && text(f.basis) && Object.hasOwn(f,"value"))
        || !Array.isArray(t.questions) || !t.questions.every(text) || !Array.isArray(t.changes)
        || !text(t.invalidation) || typeof t.ready !== "boolean") throw new Error("This response does not match the selected revision. Reopen it and ask again.");
    if (t.kind === "change") {
        if (!object(t.brief) || Object.keys(t.brief).length !== Object.keys(context.revision.brief).length) throw new Error("Incomplete change proposal.");
        const expected = Object.keys(context.revision.brief).filter(k => !equal(t.brief[k],context.revision.brief[k]));
        if (t.changes.length !== expected.length || new Set(t.changes.map(c=>c.field)).size !== expected.length
            || t.changes.some(c => !expected.includes(c.field) || !equal(c.before,context.revision.brief[c.field]) || !equal(c.after,t.brief[c.field]))
            || t.ready !== (expected.length > 0 && !t.questions.length) || t.ready && !supportedBrief(t.brief)) throw new Error("The change review is incomplete. Ask again.");
    } else if (t.brief !== null || t.changes.length || t.ready || t.questions.length || t.kind === "answer" && !t.facts.length) throw new Error("Unexpected change in an answer.");
    return t;
}

export function turnHtml(t) {
    const facts = t.facts.length ? `<p>From revision ${t.revision_number}. AI selected these records; they may not fully answer your question.</p><dl class="assistant-facts">${t.facts.map(f=>`<div><dt>${e(label(f.label))}</dt><dd>${e(display(f.value))}<small>${e(f.source)} · ${e(f.basis.replaceAll("_"," "))}</small></dd></div>`).join("")}</dl>` : "";
    const changes = t.kind === "change" ? `<h3>Review your changes</h3>${t.changes.length ? `<dl class="assistant-diff">${t.changes.map(c=>`<div><dt>${e(label(c.field))}</dt><dd><span>Before: ${e(display(c.before))}</span><strong>After: ${e(display(c.after))}</strong></dd></div>`).join("")}</dl>` : "<p>No changes were proposed.</p>"}<p>${e(t.invalidation)}</p>` : "";
    return `${facts}${t.kind === "unavailable" ? "<p>The saved project records do not provide an answer to this question. No engineering claim has been inferred.</p>" : ""}${changes}${t.questions.length ? `<h3>Clarify the request</h3><p>These are AI questions or support-policy limits, not verified engineering results.</p><ul>${t.questions.map(q=>`<li>${e(q)}</li>`).join("")}</ul>` : ""}<details><summary>This conversation (${t.messages.length})</summary>${t.messages.map(m=>`<p class="conversation-message">${e(m)}</p>`).join("")}</details>`;
}

export function mountProjectAssistant(root, {fetcher=globalThis.fetch, onApplied=()=>{}, onApplying=()=>{}, idPrefix=""}={}) {
    let context=null, key=null, turn=null, identity=null, busy=false, version=0;
    root.innerHTML=`<section class="project-assistant" aria-labelledby="assistant-title"><h2 id="assistant-title">Ask about your board. Shape what comes next.</h2><p id="assistant-context"></p><form id="assistant-form"><label for="assistant-message">Ask a question or describe a change</label><textarea id="assistant-message" rows="2" maxlength="2000" placeholder="Can I make the board 80 mm wide?"></textarea><div class="assistant-actions"><button class="primary" type="submit" id="assistant-send">Ask Ohmni</button><button class="ghost" type="button" id="assistant-reset">New question</button></div></form><p id="assistant-status" role="status" aria-live="polite"></p><p id="assistant-error" role="alert" hidden></p><div id="assistant-response"></div><button class="secondary" type="button" id="assistant-apply" hidden>Save changes as a new revision</button><p class="fineprint">Answers use saved project records. Proposed edits need your confirmation and new engineering checks. Use Your plan for detailed controls.</p></section>`;
    if (idPrefix) root.innerHTML = root.innerHTML.replaceAll('id="assistant-', `id="${idPrefix}assistant-`).replaceAll('for="assistant-', `for="${idPrefix}assistant-`).replaceAll('aria-labelledby="assistant-', `aria-labelledby="${idPrefix}assistant-`);
    const $=s=>root.querySelector(s.replace("#assistant-", `#${idPrefix}assistant-`));
    const error=err=>{$("#assistant-error").textContent=err.message;$("#assistant-error").hidden=false;};
    function sync() {
        const available=!!context && !context.dirty;
        $("#assistant-context").textContent=!context ? "Save a revision to ask about it or propose changes." : context.dirty ? "Save or reopen your revision before asking, so your answer matches your choices." : `Working with saved revision ${context.revision.number}.`;
        $("#assistant-send").disabled=busy||!available;$("#assistant-message").disabled=busy||!available;
        $("#assistant-reset").disabled=busy;
        $("#assistant-apply").hidden=!turn?.ready;$("#assistant-apply").disabled=busy||!available;
        root.setAttribute("aria-busy",String(busy));
    }
    function reset() {version++;busy=false;turn=null;identity=null;$("#assistant-response").innerHTML="";$("#assistant-status").textContent="";$("#assistant-error").hidden=true;sync();}
    async function ask(message) {
        if (busy||!context||context.dirty) return;
        if (!message.trim()||message.length>2000) return error(new Error("Enter a question or change in up to 2000 characters."));
        const current=++version, selected=structuredClone(context);busy=true;$("#assistant-error").hidden=true;$("#assistant-status").textContent="Reading your saved revision…";sync();
        try {
            const response=await projectRequest(`/api/projects/${selected.projectId}/revisions/${selected.revision.revision_id}/assistant`,{fetcher,timeoutMs:90000,method:"POST",data:{message,parent_id:turn?.turn_id||null}});
            if (version!==current)return;
            turn=parseTurn(response.payload,response.identity,selected);identity=response.identity;
            $("#assistant-response").innerHTML=turnHtml(turn);$("#assistant-message").value="";
            $("#assistant-status").textContent=turn.ready ? "Review every change before saving. Nothing has changed yet." : "Your saved revision is unchanged.";
        } catch(err){if(version===current){error(err);$("#assistant-status").textContent="Your saved revision is unchanged. Your request is still in the text field.";}}
        finally{if(version===current){busy=false;sync();}}
    }
    async function apply() {
        if(busy||!turn?.ready||!context||context.dirty)return;
        const current=++version, selected=structuredClone(context), proposed=turn;busy=true;$("#assistant-error").hidden=true;sync();onApplying(true);
        try {
            const response=await projectRequest(`/api/projects/${selected.projectId}/revisions/${selected.revision.revision_id}/assistant/${proposed.turn_id}/apply`,{fetcher,identity,method:"POST"});
            if(version!==current)return;
            const project=parseProjectEnvelope(response.payload,response.identity), revision=project.revisions.at(-1);
            if(project.project_id!==selected.projectId || revision.number!==selected.revision.number+1 || !sameBrief(revision.brief,proposed.brief) || revision.job_id!==null)throw new Error("The saved revision does not match this proposal. Reopen the project before generating.");
            turn=null;onApplying(false);await onApplied(project,revision);
        }catch(err){if(version===current)error(err);}
        finally{onApplying(false);if(version===current){busy=false;sync();}}
    }
    $("#assistant-form").addEventListener("submit",event=>{event.preventDefault();void ask($("#assistant-message").value);});
    $("#assistant-apply").addEventListener("click",()=>void apply());
    $("#assistant-reset").addEventListener("click",()=>{reset();$("#assistant-message").focus();});
    sync();
    return {ask,apply,dispose:reset,setContext(next){const nextKey=JSON.stringify(next&&[next.projectId,next.revision.revision_id,next.revision.brief_fingerprint,next.revision.job_id,next.dirty]);context=next;if(key!==nextKey){key=nextKey;reset();}else sync();}};
}
