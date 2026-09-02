import{artifactCurrent,badge,escapeHtml,money,releaseReadiness}from"./view-model.js";
const $=selector=>document.querySelector(selector);const form=$("#request-form"),button=$("#run-button"),progressSection=$("#progress-section"),workspace=$("#workspace");
const API_VERSION=2,DEMO_FIXTURE_ID="esp32-bme280-environmental-logger",JOB_ID_PATTERN=/^[0-9a-f]{12}$/,INSTANCE_PATTERN=/^[0-9a-f]{16}$/,UI_VERSION_PATTERN=/^[0-9a-f]{64}$/;
const MESSAGES=Object.freeze({
backend_unavailable:"The Ohmni demo backend is unavailable. From the repository root, run .\\.venv\\Scripts\\python.exe .\\scripts\\demo_server.py, keep that terminal open, then reload this page.",
api_ui_mismatch:"This page does not match the running Ohmni demo server. Stop any older demo server, restart it with .\\.venv\\Scripts\\python.exe .\\scripts\\demo_server.py, then reload this page.",
generation_mismatch:"The Ohmni demo server restarted or changed. Reload this page before starting the engineering workflow again.",
fixture_rejected:"The running Ohmni server rejected the deterministic demo fixture. Restart the demo server from this repository, then reload this page.",
job_initialization_failed:"The backend could not initialize the deterministic demo job. Check the server terminal, then retry.",
worker_start_failed:"The demo worker failed before progress began. Check the server terminal, then retry.",
lost_job:"This demo job is no longer available from the server that created it. Reload this page and start a fresh run.",
pipeline_failed:"The deterministic engineering pipeline failed. Check the server terminal for the fixed diagnostic code, then retry.",
});
const SERVER_ERROR_KINDS=Object.freeze({fixture_rejected:"fixture_rejected",api_version_mismatch:"api_ui_mismatch",server_instance_mismatch:"generation_mismatch",ui_version_mismatch:"generation_mismatch",job_start_unavailable:"job_initialization_failed",job_not_found:"lost_job"});
const FAILED_JOB_CODES=new Set(["worker_start_failed","pipeline_failed","progress_publication_failed","job_state_invalid"]);
let completionMonitorCleanup=null;

class DemoClientError extends Error{constructor(kind){super(kind);this.kind=kind}}
function fail(kind){throw new DemoClientError(kind)}
function errorKind(error,fallback){return error instanceof DemoClientError?error.kind:fallback}
function exactObject(value,fields){return value!==null&&typeof value==="object"&&!Array.isArray(value)&&Object.keys(value).length===fields.length&&fields.every(field=>Object.hasOwn(value,field))}
async function serverErrorKind(response,fallback){try{const payload=await response.json();if(exactObject(payload,["error"])&&typeof payload.error==="string"&&Object.hasOwn(SERVER_ERROR_KINDS,payload.error))return SERVER_ERROR_KINDS[payload.error]}catch{}return fallback}
function sameIdentity(left,right){return left.api_version===right.api_version&&left.server_instance_id===right.server_instance_id&&left.ui_version===right.ui_version}
function parseHealth(payload){
    if(!exactObject(payload,["status","fixture_id","api_version","server_instance_id","ui_version"]))fail("api_ui_mismatch");
    if(payload.api_version!==API_VERSION||payload.status!=="ready"||typeof payload.server_instance_id!=="string"||!INSTANCE_PATTERN.test(payload.server_instance_id)||typeof payload.ui_version!=="string"||!UI_VERSION_PATTERN.test(payload.ui_version))fail("api_ui_mismatch");
    if(payload.fixture_id!==DEMO_FIXTURE_ID)fail("fixture_rejected");
    return{api_version:payload.api_version,server_instance_id:payload.server_instance_id,ui_version:payload.ui_version};
}
async function fetchHealth(fetcher){
    let response;try{response=await fetcher("/api/health",{cache:"no-store"})}catch{fail("backend_unavailable")}
    if(!response.ok)fail(await serverErrorKind(response,response.status>=500?"backend_unavailable":"api_ui_mismatch"));
    let payload;try{payload=await response.json()}catch{fail("api_ui_mismatch")}
    return parseHealth(payload);
}
function startHeaders(){return{"content-type":"application/json"}}
function pollHeaders(identity){return{"X-Ohmni-Server-Instance":identity.server_instance_id,"X-Ohmni-API-Version":String(API_VERSION),"X-Ohmni-UI-Version":identity.ui_version}}
function parseStart(payload,identity){
    if(!exactObject(payload,["job_id","status","api_version","server_instance_id","ui_version"]))fail("api_ui_mismatch");
    if(payload.api_version!==API_VERSION)fail("api_ui_mismatch");
    if(payload.server_instance_id!==identity.server_instance_id||payload.ui_version!==identity.ui_version)fail("generation_mismatch");
    if(typeof payload.job_id!=="string"||!JOB_ID_PATTERN.test(payload.job_id)||payload.status!=="queued")fail("api_ui_mismatch");
    return payload.job_id;
}
function validProgressEvent(event){return exactObject(event,["stage","label","status","detail","percent"])&&[event.stage,event.label,event.status,event.detail].every(value=>typeof value==="string")&&Number.isInteger(event.percent)&&event.percent>=0&&event.percent<=100}
function parseJob(payload,id,identity){
    const fields=["job_id","status","progress","report","error","error_code","api_version","server_instance_id","ui_version"];
    if(!exactObject(payload,fields)||payload.api_version!==API_VERSION)fail("api_ui_mismatch");
    if(payload.server_instance_id!==identity.server_instance_id||payload.ui_version!==identity.ui_version)fail("generation_mismatch");
    if(payload.job_id!==id||!Array.isArray(payload.progress)||!payload.progress.every(validProgressEvent))fail("api_ui_mismatch");
    if(payload.status==="queued"||payload.status==="running"){
        if(payload.report!==null||payload.error!==null||payload.error_code!==null)fail("api_ui_mismatch");
    }else if(payload.status==="complete"){
        if(payload.report===null||typeof payload.report!=="object"||Array.isArray(payload.report)||payload.error!==null||payload.error_code!==null)fail("api_ui_mismatch");
    }else if(payload.status==="failed"){
        if(payload.report!==null||payload.error!=="Demo pipeline failed"||typeof payload.error_code!=="string"||!FAILED_JOB_CODES.has(payload.error_code))fail("api_ui_mismatch");
    }else fail("api_ui_mismatch");
    return payload;
}
function resetRun(){stopCompletedMonitor();button.disabled=true;progressSection.hidden=false;workspace.hidden=true;renderProgress([])}
export function scrollWorkspaceIntoView(target,mediaQuery=globalThis.matchMedia){const prefersReducedMotion=typeof mediaQuery==="function"&&mediaQuery("(prefers-reduced-motion: reduce)").matches===true;target.scrollIntoView({behavior:prefersReducedMotion?"instant":"smooth"})}
export async function startDemo({fetcher=globalThis.fetch,poller=poll,pollDependencies={}}={}){
    resetRun();let identity,jobId;
    try{
        identity=await fetchHealth(fetcher);
        let response;try{response=await fetcher("/api/demo",{method:"POST",headers:startHeaders(),cache:"no-store",body:JSON.stringify({fixture_id:DEMO_FIXTURE_ID,api_version:API_VERSION,server_instance_id:identity.server_instance_id,ui_version:identity.ui_version})})}catch{fail("backend_unavailable")}
        if(!response.ok||response.status!==202)fail(await serverErrorKind(response,response.status>=500?"backend_unavailable":"api_ui_mismatch"));
        let payload;try{payload=await response.json()}catch{fail("api_ui_mismatch")}
        jobId=parseStart(payload,identity);
    }catch(error){return stopPolling(MESSAGES[errorKind(error,"backend_unavailable")])}
    return poller(jobId,identity,{fetcher,...pollDependencies});
}
form.addEventListener("submit",event=>{event.preventDefault();return startDemo()});
export function pollDisposition(status){if(status==="queued"||status==="running")return"continue";if(status==="complete"||status==="failed")return status;return"invalid"}
export async function poll(id,identity,{fetcher=globalThis.fetch,schedule=globalThis.setTimeout,monitorer=beginCompletedMonitor}={}){
    try{
        let response;try{response=await fetcher(`/api/jobs/${id}`,{cache:"no-store",headers:pollHeaders(identity)})}catch{fail("backend_unavailable")}
        if(!response.ok)fail(await serverErrorKind(response,response.status===404?"lost_job":response.status>=500?"backend_unavailable":"api_ui_mismatch"));
        let payload;try{payload=await response.json()}catch{fail("api_ui_mismatch")}
        const job=parseJob(payload,id,identity);renderProgress(job.progress);
        if(job.status==="complete"){
            render(job.report,id);button.disabled=false;workspace.hidden=false;scrollWorkspaceIntoView(workspace);monitorer(identity,{fetcher});return;
        }
        if(job.status==="failed")return stopPolling(MESSAGES[job.error_code==="worker_start_failed"?"worker_start_failed":"pipeline_failed"]);
        const dependencies={fetcher,schedule,monitorer};schedule(()=>void poll(id,identity,dependencies),900);
    }catch(error){return stopPolling(MESSAGES[errorKind(error,"backend_unavailable")])}
}
export function stopCompletedMonitor(){const cleanup=completionMonitorCleanup;completionMonitorCleanup=null;if(cleanup)cleanup()}
export function beginCompletedMonitor(identity,{fetcher=globalThis.fetch,setIntervalFn=globalThis.setInterval,clearIntervalFn=globalThis.clearInterval,windowTarget=globalThis.window,documentTarget=globalThis.document}={}){
    stopCompletedMonitor();let stopped=false,busy=false;
    const invalidate=kind=>{if(stopped)return;workspace.hidden=true;stopPolling(MESSAGES[kind])};
    const check=async()=>{if(stopped||busy)return true;busy=true;try{const current=await fetchHealth(fetcher);if(!sameIdentity(identity,current)){invalidate("generation_mismatch");return false}return true}catch(error){invalidate(errorKind(error,"backend_unavailable"));return false}finally{busy=false}};
    const timer=typeof setIntervalFn==="function"?setIntervalFn(check,3000):null;if(timer&&typeof timer.unref==="function")timer.unref();
    const focus=()=>{void check()},visible=()=>{if(documentTarget?.hidden===false)void check()};
    windowTarget?.addEventListener?.("focus",focus);documentTarget?.addEventListener?.("visibilitychange",visible);
    completionMonitorCleanup=()=>{stopped=true;if(timer!==null&&typeof clearIntervalFn==="function")clearIntervalFn(timer);windowTarget?.removeEventListener?.("focus",focus);documentTarget?.removeEventListener?.("visibilitychange",visible)};
    return check;
}
function stopPolling(message){stopCompletedMonitor();showError(message);button.disabled=false}
function renderProgress(events){const last=events.at(-1)||{percent:0};$("#progress-percent").textContent=`${last.percent}%`;$("#progress-bar").style.width=`${last.percent}%`;$("#progress-list").innerHTML=events.map(item=>`<li class="${escapeHtml(item.status)}"><strong>${escapeHtml(item.label)}</strong>${badge(item.status)} ${escapeHtml(item.detail)}</li>`).join("")}
function render(report,job){$("#overview").innerHTML=`${heading("System view","Independent checks stay independent")}<div class="grid"><div class="card wide"><h3>${escapeHtml(report.project.name)}</h3><p>${escapeHtml(report.project.request)}</p><div class="ladder">${report.verification_ladder.map((row,index)=>`<div class="ladder-row"><span class="ladder-dot">${index+1}</span><div><strong>${escapeHtml(row.stage)}</strong><p>${escapeHtml(row.detail)}</p></div>${badge(row.status)}</div>`).join("")}</div></div><div class="card"><h3>Requirements provenance</h3>${report.requirements.map(item=>`<p>${badge(item.origin)} <strong>${escapeHtml(item.field)}</strong><br>${escapeHtml(item.value)}</p>`).join("")}</div></div>`;
const fix=report.failure_and_repair;$("#repair").innerHTML=`${heading("Failure & repair","The model was wrong. The verifier was not impressed.")}<div class="repair-card"><div>${badge("FAIL")} <strong>${escapeHtml(fix.rule)}</strong></div><div class="repair-flow"><div class="repair-state"><strong>ORIGINAL CONNECTION</strong>${escapeHtml(fix.original)}<p>Allowed operating range: ${escapeHtml(fix.operating_range)}</p></div><div class="repair-arrow">→</div><div class="repair-state"><strong>BOUNDED REPAIR</strong>${fix.operations.map(op=>`${escapeHtml(op.component_ref)}.${escapeHtml(op.pin)}: ${escapeHtml(op.from_net)} → ${escapeHtml(op.to_net)}`).join("<br>")}<p>${badge("PASS")} ${escapeHtml(fix.result)}</p></div></div>${report.lessons.map(lesson=>`<p><strong>${escapeHtml(lesson.topic)}</strong><br>${escapeHtml(lesson.body)}</p>`).join("")}</div>`;
$("#evidence").innerHTML=`${heading("Evidence","Important values keep their source and strength")}<div class="card full"><table class="evidence-table"><thead><tr><th>Component</th><th>Claim</th><th>Value</th><th>Status</th><th>Location</th></tr></thead><tbody>${report.evidence.map(item=>`<tr><td>${escapeHtml(item.component)}</td><td>${escapeHtml(item.claim)}</td><td>${escapeHtml(item.value)}</td><td>${badge(item.status)}</td><td>${escapeHtml(item.source||"UNKNOWN")}${item.page?` · p.${item.page}`:""}</td></tr>`).join("")}</tbody></table></div>`;
$("#notebook").innerHTML=`${heading("Engineering Notebook","A factual timeline—not hidden chain-of-thought")}<div class="timeline">${report.notebook.map(event=>`<div class="event"><span class="event-kind">${escapeHtml(event.sequence)} · ${escapeHtml(event.phase)}<br>${escapeHtml(event.kind)}</span><span class="event-node"></span><span class="event-summary">${escapeHtml(event.summary)} ${event.finding_ids?.length?`<small>${escapeHtml(event.finding_ids.join(", "))}</small>`:""}</span></div>`).join("")}</div>`;
const pcb=report.pcb,sch=report.schematic;$("#artifacts").innerHTML=`${heading("Engineering artifacts","Views derived from exact compiled topology and route geometry")}<div class="artifact-tabs"><article class="artifact"><h3>Compiled schematic sheet ${badge(sch.erc_status)}</h3><p>KiCad global-label geometry; matching labels are electrically connected.</p>${sch.svg}<p class="fingerprint">${escapeHtml(sch.fingerprint)} · ${artifactCurrent(sch)}</p><a href="/api/artifacts/${job}/golden.kicad_sch">Download .kicad_sch</a></article><article class="artifact"><h3>Routed PCB ${badge(pcb.drc_status)}</h3>${pcb.svg}<p class="fingerprint">${escapeHtml(pcb.fingerprint)} · ${artifactCurrent(pcb)}</p><p>${pcb.statistics.track_segment_count} emitted track segments · ${pcb.statistics.via_count} emitted via entities · ${Number(pcb.statistics.total_track_length_mm).toFixed(1)} mm</p><a href="/api/artifacts/${job}/golden.kicad_pcb">Download .kicad_pcb</a></article></div>`;
const econ=report.economics;$("#bom").innerHTML=`${heading("BOM & prototype economics","Consumption is not the same as cash required")}<div class="grid"><div class="card"><span class="eyebrow">Consumed on one board</span><div class="metric">${money(econ.known_consumption_cost)}</div><p>Known component consumption only</p></div><div class="card"><span class="eyebrow">Purchase requirement</span><div class="metric">${money(econ.known_purchase_requirement)}</div><p>MOQ and purchase increments included</p></div><div class="card"><span class="eyebrow">Pricing coverage</span><div class="metric">${(econ.pricing_coverage*100).toFixed(1)}%</div><p>${escapeHtml(econ.pricing_source)}</p></div><div class="card full"><table class="bom-table"><thead><tr><th>Refs</th><th>Part</th><th>Package</th><th>Qty</th><th>Price knowledge</th><th>Purchase</th></tr></thead><tbody>${report.bom.lines.map(line=>`<tr><td>${escapeHtml(line.references.join(", "))}</td><td>${escapeHtml(line.part)}</td><td>${escapeHtml(line.package)}</td><td>${line.quantity}</td><td>${badge(line.knowledge)}</td><td>${money(line.purchase_cost,line.knowledge)}</td></tr>`).join("")}</tbody></table></div></div>`;
const release=releaseReadiness(report.release);$("#release").innerHTML=`${heading("Release readiness","The strongest status the evidence supports")}<div class="grid"><div class="card wide"><h3>${badge(release.status)} ${escapeHtml(release.label)}</h3><p>Package fingerprint</p><p class="fingerprint">${escapeHtml(report.release.package_fingerprint)} · ${artifactCurrent(report.release)}</p><p>${report.release.files.length} fabrication outputs + integrity manifest · ${report.manufacturing.findings.length} manufacturing checks</p></div><div class="card"><h3>Assembly</h3>${badge(report.assembly.hand_solder_requirement_satisfied?"PASS":"PASS_WITH_WARNINGS")}<p>${report.assembly.risks.filter(r=>r.difficulty.includes("recommended")||r.difficulty.includes("unsupported")||r.difficulty==="unknown").map(r=>`${escapeHtml(r.references.join(", "))}: ${escapeHtml(r.difficulty)}`).join("<br>")}</p></div><div class="card full limitations"><h3>Known limitations</h3><ul>${report.limitations.map(item=>`<li>${escapeHtml(item)}</li>`).join("")}</ul><p>Fabrication: ${badge(econ.fabrication)} Shipping: ${badge(econ.shipping)} Bench: ${badge("NOT_YET_VERIFIED")}</p></div></div>`}
function heading(eyebrow,title){return `<div class="section-heading"><div><p class="eyebrow">${escapeHtml(eyebrow)}</p><h2>${escapeHtml(title)}</h2></div></div>`}function showError(message){progressSection.hidden=false;$("#progress-list").innerHTML+=`<li class="FAIL"><strong>Pipeline stopped</strong>${badge("FAIL")} ${escapeHtml(message)}</li>`}
