import { escapeHtml as e, requirementResultsHtml } from "./view-model.js";
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

function factValue(fact) {
    if (fact.id === "report.requirements" && Array.isArray(fact.value)) {
        const rows = fact.value.map(row=>({...row, value:row.display_value ?? "Saved choice", rule_ids:[]}));
        if (!requirementResultsHtml(rows)) return "These choice results could not be displayed safely.";
        const unmet=rows.filter(row=>row.status==="VIOLATED"), unknown=rows.filter(row=>row.status==="UNKNOWN"), met=rows.filter(row=>row.status==="MET");
        return `<p>${unmet.length} unmet · ${unknown.length} not yet verified · ${met.length} met within the recorded checks.</p>
            ${unmet.length ? requirementResultsHtml(unmet) : ""}
            ${unknown.length ? `<details><summary>Not yet verified (${unknown.length})</summary>${requirementResultsHtml(unknown)}</details>` : ""}
            ${met.length ? `<details><summary>Met within recorded checks (${met.length})</summary>${requirementResultsHtml(met)}</details>` : ""}`;
    }
    if (Array.isArray(fact.value) && fact.id !== "report.bom.parts") {
        return `<ul class="assistant-records">${fact.value.map(item=>`<li>${object(item) && fact.id === "report.verification_ladder"
            ? `<strong>${e(String(item.stage || item.label || "Recorded check"))}${item.status ? ` · ${e(String(item.status).replaceAll("_"," "))}` : ""}</strong>${item.detail ? `<p>${e(String(item.detail))}</p>` : `<p>${e(display(item))}</p>`}`
            : e(display(item))}</li>`).join("")}</ul>`;
    }
    if (fact.id === "report.bom.parts" && Array.isArray(fact.value)) {
        return `<ul class="assistant-parts">${fact.value.map(part => `<li><strong>${e(String(part.part ?? "Recorded part"))}</strong><span>${e(display(part.references ?? []))} · Quantity ${e(String(part.quantity ?? "not recorded"))}</span><span>${e(String(part.description ?? part.package ?? ""))}</span></li>`).join("")}</ul>`;
    }
    return e(display(fact.value));
}

export function turnHtml(t) {
    const facts = t.facts.length ? `<p>From revision ${t.revision_number}. AI selected these records; they may not fully answer your question.</p><dl class="assistant-facts">${t.facts.map(f=>`<div><dt>${e(label(f.label))}</dt><dd>${factValue(f)}<small>${e(f.source)} · ${e(f.basis.replaceAll("_"," "))}</small></dd></div>`).join("")}</dl>` : "";
    const changes = t.kind === "change" && t.changes.length ? `<h3>Review your changes</h3><dl class="assistant-diff">${t.changes.map(c=>`<div><dt>${e(label(c.field))}</dt><dd><span>Before: ${e(display(c.before))}</span><strong>After: ${e(display(c.after))}</strong></dd></div>`).join("")}</dl><p>${e(t.invalidation)}</p>` : "";
    const questions = t.questions.length ? `<h3>Let’s choose the next step</h3><p>These are proposed choices, not verified engineering results.</p><ul>${t.questions.map(q=>`<li>${e(q)}</li>`).join("")}</ul>` : "";
    const records = facts && t.questions.length ? `<details><summary>See the saved records behind these questions</summary>${facts}</details>` : facts;
    return `${t.kind === "change" && t.questions.length ? "<p>Let’s settle the next choice together. Nothing has changed yet.</p>" : t.kind === "answer" ? "<p>Here is what the saved records establish. Unverified items still need separate work.</p>" : ""}${questions}${changes}${records}${t.kind === "unavailable" ? "<p>The saved project records do not provide an answer to this question. No engineering claim has been inferred.</p>" : ""}<details><summary>This conversation (${t.messages.length})</summary>${t.messages.map(m=>`<p class="conversation-message">${e(m)}</p>`).join("")}</details>`;
}

/** The applied project, only if its new revision is exactly the reviewed proposal. */
export function appliedProject(project, selected, proposed) {
    const revision=project.revisions.at(-1);
    if(project.project_id!==selected.projectId || revision.number!==selected.revision.number+1 || !sameBrief(revision.brief,proposed.brief) || revision.job_id!==null)throw new Error("The saved revision does not match this proposal. Reopen the project before generating.");
    return project;
}

export function mountProjectAssistant(root, {fetcher=globalThis.fetch, onApplied=()=>{}, onApplying=()=>{}, idPrefix="", recovery=false}={}) {
    let context=null, key=null, turn=null, identity=null, busy=false, version=0, transcript=[];
    root.innerHTML=`<section class="project-assistant" aria-labelledby="assistant-title">
      <header class="assistant-header"><span class="assistant-avatar" aria-hidden="true">Ω</span><div><h2 id="assistant-title">Board chat</h2><p id="assistant-context"></p></div><button class="ghost" type="button" id="assistant-reset">New chat</button></header>
      <div class="assistant-thread"><div id="assistant-welcome" class="assistant-welcome"><span class="assistant-avatar" aria-hidden="true">Ω</span><h3>${recovery ? "Let’s work out the next step." : "Let's talk about your board."}</h3><p>${recovery ? "Your saved choices are safe. Ask what stopped this build, or explore a simpler supported design. Another run is not guaranteed to fix it." : "Ask what the results mean, what still needs work, or describe a change in everyday language."}</p><p class="assistant-example">You don’t need to know part numbers or electronics terms.</p></div><div id="assistant-response" role="log" aria-label="Board conversation" aria-live="polite"></div><p id="assistant-status" role="status" aria-live="polite"></p><p id="assistant-error" role="alert" hidden></p></div><div class="assistant-confirmation"><button class="secondary" type="button" id="assistant-apply" hidden>Save changes as a new revision</button></div>
      <div class="assistant-prompts" aria-label="Conversation starters"><button type="button" class="ghost" id="assistant-help">${recovery ? "Help me with this build" : "What still needs work?"}</button><button type="button" class="ghost" id="assistant-change">Help me change the design</button></div><form id="assistant-form" class="assistant-composer"><label for="assistant-message">Message Ohmni</label><textarea id="assistant-message" rows="3" maxlength="2000" placeholder="Ask about your board or describe a change…"></textarea><div class="assistant-actions"><span>Up to 2,000 characters</span><button class="primary" type="submit" id="assistant-send">Send <span aria-hidden="true">↑</span></button></div></form>
      <p class="assistant-footnote">Answers use saved project records. You review changes before saving; a new revision needs new checks.</p></section>`;
    if (idPrefix) root.innerHTML = root.innerHTML.replaceAll('id="assistant-', `id="${idPrefix}assistant-`).replaceAll('for="assistant-', `for="${idPrefix}assistant-`).replaceAll('aria-labelledby="assistant-', `aria-labelledby="${idPrefix}assistant-`);
    const $=s=>root.querySelector(s.replace("#assistant-", `#${idPrefix}assistant-`));
    const error=err=>{$("#assistant-error").textContent=err.message;$("#assistant-error").hidden=false;};
    function sync() {
        const available=!!context && !context.dirty;
        $("#assistant-context").textContent=!context ? "Save a revision to ask about it or propose changes." : context.dirty ? "Save or reopen your revision before asking, so your answer matches your choices." : `Working with saved revision ${context.revision.number}.`;
        $("#assistant-send").disabled=busy||!available;$("#assistant-message").disabled=busy||!available;
        $("#assistant-reset").disabled=busy;
        $("#assistant-help").disabled=busy||!available;$("#assistant-change").disabled=busy||!available;
        $("#assistant-send").textContent=busy ? "Working…" : "Send ↑";
        $("#assistant-apply").hidden=!turn?.ready;$("#assistant-apply").disabled=busy||!available;
        root.setAttribute("aria-busy",String(busy));
    }
    function reset() {version++;busy=false;transcript=[];$("#assistant-welcome").hidden=false;turn=null;identity=null;$("#assistant-response").innerHTML="";$("#assistant-status").textContent="";$("#assistant-error").hidden=true;sync();}
    let historyBefore = null;
    const historyRow = item => `<div class="assistant-user-message"><span>You${item.source === 'Fetch' ? ' · Fetch' : ''}</span><p>${e(item.message || '')}</p></div><div class="assistant-reply"><span class="assistant-speaker">Ohmni</span>${item.turn ? turnHtml({...item.turn,ready:false}) : `<p style="white-space:pre-wrap">${e(item.reply || '')}</p>`}</div>`;
    async function restoreHistory(older=false) {
        if (!globalThis.OHMNI_CONNECTED || !context || context.dirty) return;
        const current=version, selected=context;
        try {
            const response=await projectRequest(`/api/projects/${selected.projectId}/revisions/${selected.revision.revision_id}/history${older && historyBefore ? '?before='+historyBefore : ''}`,{fetcher});
            if(version!==current)return;
            const entries=response.payload.messages.map(historyRow);
            transcript=older ? [...entries,...transcript] : entries;
            historyBefore=response.payload.before;
            $("#assistant-response").innerHTML=transcript.join('');
            $("#assistant-welcome").hidden=transcript.length>0;
            root.querySelector('[data-older-chat]')?.remove();
            if(historyBefore){const button=document.createElement('button');button.type='button';button.className='ghost';button.dataset.olderChat='';button.textContent='Load earlier messages';button.onclick=()=>void restoreHistory(true);$("#assistant-response").prepend(button);}
        }catch(err){if(version===current)error(err);}
    }
    async function ask(message) {
        if (busy||!context||context.dirty) return;
        if (!message.trim()||message.length>2000) return error(new Error("Enter a question or change in up to 2000 characters."));
        const current=++version, selected=structuredClone(context);busy=true;$("#assistant-error").hidden=true;$("#assistant-status").textContent="Reading your saved revision…";sync();
        try {
            const response=await projectRequest(`/api/projects/${selected.projectId}/revisions/${selected.revision.revision_id}/assistant`,{fetcher,timeoutMs:90000,method:"POST",data:{message,parent_id:turn?.turn_id||null},parse:(payload,current)=>parseTurn(payload,current,selected)});
            if (version!==current)return;
            turn=response.parsed;identity=response.identity;
            transcript.push(`<div class="assistant-user-message"><span>You</span><p>${e(message.trim())}</p></div><div class="assistant-reply"><span class="assistant-speaker">Ohmni</span>${turnHtml(turn)}</div>`);
            $("#assistant-response").innerHTML=transcript.join("");$("#assistant-welcome").hidden=true;$("#assistant-message").value="";
            const thread=root.querySelector(".assistant-thread");
            thread.scrollTop=Math.max(0, (root.querySelector(".assistant-user-message:nth-last-child(2)")?.offsetTop ?? 0) - 20);
            $("#assistant-status").textContent=turn.questions.length ? "Your answer is needed. Reply below; your saved revision is unchanged." : turn.ready ? "Review every change before saving. Nothing has changed yet." : "Your saved revision is unchanged.";
        } catch(err){if(version===current){error(err);$("#assistant-status").textContent="Your saved revision is unchanged. Your request is still in the text field.";}}
        finally{if(version===current){busy=false;sync();}}
    }
    async function apply() {
        if(busy||!turn?.ready||!context||context.dirty)return;
        const current=++version, selected=structuredClone(context), proposed=turn;busy=true;$("#assistant-error").hidden=true;$("#assistant-status").textContent="Saving your reviewed changes as a new revision…";$("#assistant-apply").textContent="Saving revision…";sync();onApplying(true);
        try {
            // The applied revision must match the proposal before the request counts as a success.
            const response=await projectRequest(`/api/projects/${selected.projectId}/revisions/${selected.revision.revision_id}/assistant/${proposed.turn_id}/apply`,{fetcher,identity,method:"POST",parse:(payload,current)=>appliedProject(parseProjectEnvelope(payload,current),selected,proposed)});
            if(version!==current)return;
            const project=response.parsed, revision=project.revisions.at(-1);
            turn=null;onApplying(false);await onApplied(project,revision);
        }catch(err){if(version===current)error(err);}
        finally{onApplying(false);if(version===current){busy=false;$("#assistant-apply").textContent="Save changes as a new revision";sync();}}
    }
    const prepare = message => {if(busy || !context || context.dirty)return;$("#assistant-message").value=message;$("#assistant-message").focus();};
    $("#assistant-help").addEventListener("click",()=>prepare(recovery
        ? "Help me understand why this build stopped. Use its recorded results and ask me about supported alternatives before changing my goals."
        : "Which saved choices are unmet or unverified? Explain the obstacle simply and ask me about supported alternatives before changing my goals."));
    $("#assistant-change").addEventListener("click",()=>prepare("I would like help changing this design. Ask me what I want it to do and guide me through supported options."));
    $("#assistant-form").addEventListener("submit",event=>{event.preventDefault();void ask($("#assistant-message").value);});
    $("#assistant-apply").addEventListener("click",()=>void apply());
    $("#assistant-reset").addEventListener("click",()=>{reset();void restoreHistory();$("#assistant-message").focus();});
    if(globalThis.OHMNI_CONNECTED) $("#assistant-reset").textContent="New topic";
    sync();
    return {ask,apply,dispose:reset,setContext(next){const nextKey=JSON.stringify(next&&[next.projectId,next.revision.revision_id,next.revision.brief_fingerprint,next.revision.job_id,next.dirty]);context=next;if(key!==nextKey){key=nextKey;reset();void restoreHistory();}else sync();}};
}
