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
    assert.equal(ui.node("#conversation-reply").focused,true);
    await controller.propose("Yes");
    assert.equal(calls.at(-1).body.parent_id,p.plan_id);
    assert.equal(calls.at(-1).body.message,"Yes");
    assert.equal(calls.some(c=>c.url.endsWith("/confirm")),false);
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
