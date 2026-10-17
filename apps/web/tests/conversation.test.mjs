import assert from "node:assert/strict";
import test from "node:test";
import { mountConversation, parsePlan, planHtml } from "../conversation.js";
import { defaultProjectBrief } from "../project-contract.js";

const identity = {api_version:2, server_instance_id:"a".repeat(16), ui_version:"b".repeat(64)};
const brief = () => ({...defaultProjectBrief(),button_count:0,spi_devices:[],board_width_mm:100,board_height_mm:70});
const plan = (overrides={}) => ({plan_id:"c".repeat(16),brief_fingerprint:"d".repeat(64),messages:["A USB temperature board"],brief:brief(),stated:[],assumed_fields:Object.keys(brief()).filter(k=>k!=="schema_version"),questions:[],ready:true,preview:{},...overrides});
const response = (body,status=200) => ({ok:status<400,status,json:async()=>({...identity,...body})});
const project = p => ({project_id:"e".repeat(16),created_at:"now",updated_at:"now",revisions:[{revision_id:"f".repeat(16),number:1,created_at:"now",brief:p.brief,brief_fingerprint:p.brief_fingerprint,preview:{asked_for:[],assumed:[],needs_clarification:[]},job_id:null}]});
function dom() {
    const nodes = new Map();
    const root = {innerHTML:"",setAttribute(){},querySelector(s){
        if (!nodes.has(s)) nodes.set(s,{innerHTML:"",textContent:"",value:"",hidden:false,disabled:false,
            focus(){this.focused=true;},addEventListener(type,handler){this.listeners ||= {};this.listeners[type]=handler;},click(){this.listeners?.click?.({preventDefault(){}});}});
        return nodes.get(s);
    }};
    return {root,node:s=>root.querySelector(s)};
}
function transport(p, calls, confirmProject=project(p)) {
    return async (url, options={}) => {
        calls.push({url,body: options.body ? JSON.parse(options.body) : null});
        if (url==="/api/health") return response({status:"ready",fixture_id:"esp32-bme280-environmental-logger",free_text:true});
        if (url.endsWith("/confirm")) return response({project:confirmProject},201);
        return response({plan:p});
    };
}
test("confirmation sends only plan identity and runs the exact saved revision",async()=>{
    const p=plan(), calls=[], ui=dom(), saved=[];
    const controller=mountConversation(ui.root,{fetcher:transport(p,calls),onOpen(){},onSaved:async(...args)=>saved.push(args)});
    await controller.begin(p.messages[0]);
    await controller.confirm();
    const confirmation=calls.find(c=>c.url.endsWith("/confirm"));
    assert.deepEqual(confirmation.body,identity);
    assert.equal(saved[0][0].revisions[0].brief_fingerprint,p.brief_fingerprint);
    assert.equal(ui.node("#conversation-confirm").textContent,"Generate saved revision");
    await controller.confirm();
    assert.equal(calls.filter(c=>c.url.endsWith("/confirm")).length,1);
});
test("unresolved questions disable confirmation and short answers reference their plan",async()=>{
    const p=plan({ready:false,questions:["USB power only. Is that acceptable?"]}),calls=[],ui=dom();
    const controller=mountConversation(ui.root,{fetcher:transport(p,calls),onOpen(){},onSaved(){assert.fail("must not run");}});
    await controller.begin(p.messages[0]);
    await controller.confirm();
    assert.equal(ui.node("#conversation-confirm").disabled,true);
    assert.match(ui.node("#conversation-confirm-hint").textContent,/Generation is paused: send your reply/);
    assert.equal(ui.node("#conversation-confirm").hidden,true);
    assert.equal(ui.node("#conversation-edit").hidden,false);
    assert.equal(ui.node("#conversation-reply-form").hidden,false);
    assert.ok(ui.root.innerHTML.indexOf('id="conversation-reply-form"') < ui.root.innerHTML.indexOf('id="conversation-summary"'));
    assert.match(ui.node("#conversation-summary").innerHTML,/<details class="conversation-draft"><summary>View tentative hardware choices/);
    assert.doesNotMatch(ui.node("#conversation-summary").innerHTML, /<h2>.*temperature.*<\/h2>/);
    assert.equal(ui.node("#conversation-reply").focused,true);
    await controller.propose("Yes");
    assert.equal(calls.at(-1).body.parent_id,p.plan_id);
    assert.equal(calls.at(-1).body.message,"Yes");
    assert.equal(calls.some(c=>c.url.endsWith("/confirm")),false);
});
test("accepting an alternative reveals the reviewed plan and enables its exact confirmation",async()=>{
    const blocked=plan({ready:false,questions:["Audio recording is unsupported. Build a button-and-light controller instead?"]});
    blocked.brief.project_name="Voice diary recorder";
    const ready=plan({plan_id:"1".repeat(16),messages:[...blocked.messages,"Yes, build the controller instead."]});
    ready.brief.project_name="Button and light controller";
    const ui=dom(),calls=[],saved=[];let proposals=0;
    const base=transport(ready,calls);
    const controller=mountConversation(ui.root,{onOpen(){},onSaved:p=>saved.push(p),fetcher:async(url,options)=>{
        if(url==="/api/project-plans") {calls.push({url,body:JSON.parse(options.body)});return response({plan:proposals++?ready:blocked});}
        return base(url,options);
    }});
    await controller.begin(blocked.messages[0]);
    assert.doesNotMatch(ui.node("#conversation-summary").innerHTML,/Voice diary recorder/);
    await controller.propose(ready.messages[1]);
    assert.equal(calls.filter(c=>c.url==="/api/project-plans")[1].body.parent_id,blocked.plan_id);
    assert.equal(ui.node("#conversation-confirm").hidden,false);
    assert.equal(ui.node("#conversation-confirm").disabled,false);
    assert.equal(ui.node("#conversation-edit").hidden,true);
    assert.equal(ui.node("#conversation-summary").focused,true);
    assert.match(ui.node("#conversation-summary").innerHTML,/Button and light controller/);
    await controller.confirm();
    assert.equal(saved[0].revisions[0].brief.project_name,ready.brief.project_name);
});
test("retrying a failed clarification resends the reply with its parent, not the initial idea",async()=>{
    const p=plan({ready:false,questions:["Use a controller instead?"]}),ui=dom(),calls=[];let proposals=0;
    const base=transport(p,calls);
    const controller=mountConversation(ui.root,{onOpen(){},fetcher:async(url,options)=>{
        if(url==="/api/project-plans" && proposals++===1) {calls.push({url,body:JSON.parse(options.body)});return response({error:"plan_unavailable"},503);}
        return base(url,options);
    }});
    await controller.begin(p.messages[0]);
    await controller.propose("Yes, use the controller instead.");
    assert.match(ui.node("#conversation-preserved").textContent,/Your latest reply: Yes, use the controller instead\./);
    ui.node("#conversation-retry").click();await new Promise(setImmediate);
    assert.equal(calls.at(-1).body.message,"Yes, use the controller instead.");
    assert.equal(calls.at(-1).body.parent_id,p.plan_id);
});
test("ready plans can be edited without searching below the technical details",async()=>{
    const ui=dom();const controller=mountConversation(ui.root,{fetcher:transport(plan(),[]),onOpen(){}});
    await controller.begin("A temperature board");
    assert.equal(ui.node("#conversation-edit").hidden,true);
    ui.node("#conversation-change").click();
    assert.equal(ui.node("#conversation-edit").hidden,false);
    assert.equal(ui.node("#conversation-reply").focused,true);
    assert.equal(ui.node("#conversation-reply-form button").textContent,"Update my plan");
});
test("a mismatched saved brief never reaches generation",async()=>{
    const p=plan(),calls=[],ui=dom(), changed=project(p);
    changed.revisions[0].brief={...p.brief,status_led_count:0};
    const controller=mountConversation(ui.root,{fetcher:transport(p,calls,changed),onOpen(){},onSaved(){assert.fail("must not run");}});
    await controller.begin(p.messages[0]);await controller.confirm();
    assert.match(ui.node("#conversation-error").textContent,/differs/);
});
test("cancelled planning cannot replace the visible conversation",async()=>{
    const p=plan(),ui=dom();let resolve;
    const controller=mountConversation(ui.root,{onOpen(){},fetcher:async url=>url==="/api/health"?response({status:"ready",fixture_id:"esp32-bme280-environmental-logger"}):new Promise(r=>{resolve=r;})});
    const pending=controller.begin(p.messages[0]);
    await new Promise(setImmediate);controller.cancel();resolve(response({plan:p}));await pending;
    assert.equal(ui.node("#conversation-plan").innerHTML,"");
});
test("failed planning preserves the request and offers an accessible guided escape",async()=>{
    const idea="A USB-powered plant monitor with two lights";const ui=dom(),guided=[];
    const fetcher=async url=>url==="/api/health"
        ? response({status:"ready",fixture_id:"esp32-bme280-environmental-logger",free_text:true})
        : response({error:"plan_unavailable"},503);
    const controller=mountConversation(ui.root,{fetcher,onOpen(){},onSaved(){assert.fail("must not run");},onGuided:brief=>guided.push(brief)});
    await controller.begin(idea);
    assert.equal(ui.node("#conversation-preserved").textContent,idea);
    assert.equal(ui.node("#conversation-recovery").hidden,false);
    assert.equal(ui.node("#conversation-error").hidden,true);
    assert.match(ui.node("#conversation-error-detail").textContent,/AI planner is unavailable/);
    assert.equal(ui.node("#conversation-recovery").focused,true);
    ui.node("#conversation-guided-recovery").click();
    assert.deepEqual(guided,[undefined]);
});
test("model text is escaped and suggested choices do not become verified facts",()=>{
    const p=plan({messages:["<img src=x onerror=alert(1)>"]});p.brief.project_name="<script>bad</script>";
    const html=planHtml(p);
    assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
    assert.match(html,/Engineering checks have not run/);assert.match(html,/Suggested choices/);
});
test("invalid plan recovery does not claim the planner is unavailable",async()=>{
    const ui=dom();
    const detail="The AI returned a response that did not match the supported board plan.";
    const fetcher=async url=>url==="/api/health"
        ? response({status:"ready",fixture_id:"esp32-bme280-environmental-logger",free_text:true})
        : response({error:"invalid_plan",refusal:{message:detail}},502);
    const controller=mountConversation(ui.root,{fetcher,onOpen(){},onSaved(){assert.fail("must not save");}});
    await controller.begin("A USB-powered sensor board");
    assert.equal(ui.node("#conversation-recovery-message").textContent,detail);
    assert.doesNotMatch(ui.node("#conversation-recovery-message").textContent,/unavailable/);
    assert.equal(ui.node("#conversation-preserved").textContent,"A USB-powered sensor board");
});
test("plan shape, attribution and readiness inconsistencies fail closed",()=>{
    for (const p of [plan({ready:true,questions:["unresolved"]}),plan({stated:[{field:"verified",quote:"USB"}]}),plan({assumed_fields:[]}),plan({stated:[{field:"status_led_count",quote:"invented"}]})]) {
        assert.throws(()=>parsePlan({...identity,plan:p},identity));
    }
});

test("planning displays elapsed feedback and cancellation clears its timer",async()=>{
    const ui=dom();let resolve,tick,clock=1000,cleared=0;
    const controller=mountConversation(ui.root,{onOpen(){},now:()=>clock,
        setIntervalFn:fn=>{tick=fn;return 123;},clearIntervalFn:id=>{assert.equal(id,123);cleared++;},
        fetcher:async url=>url==="/api/health"?response({status:"ready",fixture_id:"esp32-bme280-environmental-logger"}):new Promise(r=>{resolve=r;})});
    const pending=controller.begin("USB temperature board");await new Promise(setImmediate);
    assert.equal(ui.node("#conversation-activity").hidden,false);
    clock=22000;tick();
    assert.match(ui.node("#conversation-activity-label").textContent,/Still waiting/);
    assert.match(ui.node("#conversation-elapsed").textContent,/21s elapsed/);
    controller.cancel();assert.equal(cleared,1);assert.equal(ui.node("#conversation-activity").hidden,true);
    resolve(response({plan:plan()}));await pending;
    assert.equal(ui.node("#conversation-plan").innerHTML,"");
});

test("saving and starting display separate states without duplicate confirmation",async()=>{
    const p=plan(),ui=dom(),calls=[];let save,start;
    const base=transport(p,calls);
    const controller=mountConversation(ui.root,{onOpen(){},
        fetcher:async(url,options)=>url.endsWith("/confirm")?new Promise(resolve=>{calls.push({url});save=()=>resolve(response({project:project(p)},201));}):base(url,options),
        onSaved:()=>new Promise(resolve=>{start=resolve;})});
    await controller.begin(p.messages[0]);const pending=controller.confirm();
    await new Promise(setImmediate);
    assert.equal(ui.node("#conversation-confirm").textContent,"Saving your plan…");
    await controller.confirm();assert.equal(calls.filter(c=>c.url.endsWith("/confirm")).length,1);
    save();await new Promise(setImmediate);
    assert.equal(ui.node("#conversation-confirm").textContent,"Starting your board…");
    start();await pending;assert.equal(ui.node("#conversation-activity").hidden,true);
});

test("assembly guidance is shown before confirmation and server text is escaped",async()=>{
    const p=plan({design_notes:["Assembly service needed <script>unsafe</script>"]}),ui=dom();
    const controller=mountConversation(ui.root,{fetcher:transport(p,[]),onOpen(){},onSaved(){}});
    await controller.begin(p.messages[0]);
    assert.match(ui.node("#conversation-summary").innerHTML,/Before you order or assemble/);
    assert.match(ui.node("#conversation-summary").innerHTML,/&lt;script&gt;/);
    assert.doesNotMatch(ui.node("#conversation-summary").innerHTML,/<script>/);
    assert.equal(ui.node("#conversation-confirm").disabled,false);
    assert.throws(()=>parsePlan({...identity,plan:plan({design_notes:[42]})},identity));
});
