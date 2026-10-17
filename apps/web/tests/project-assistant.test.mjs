import assert from "node:assert/strict";
import test from "node:test";
import { mountProjectAssistant, parseTurn, turnHtml } from "../project-assistant.js";
import { defaultProjectBrief } from "../project-contract.js";

const identity={api_version:2,server_instance_id:"a".repeat(16),ui_version:"b".repeat(64)};
const brief={...defaultProjectBrief(),button_count:0,spi_devices:[],board_width_mm:100,board_height_mm:70};
const revision={revision_id:"c".repeat(16),number:1,brief,brief_fingerprint:"d".repeat(64),created_at:"now",preview:{asked_for:[],assumed:[],needs_clarification:[]},job_id:null};
const context={projectId:"e".repeat(16),revision,dirty:false};
const change=()=>({turn_id:"f".repeat(16),project_id:context.projectId,revision_id:revision.revision_id,revision_number:1,base_brief_fingerprint:revision.brief_fingerprint,context_fingerprint:"1".repeat(64),messages:["Make it 80 mm wide"],kind:"change",facts:[],brief:{...brief,board_width_mm:80},changes:[{field:"board_width_mm",before:100,after:80}],questions:[],ready:true,invalidation:"New checks are needed; existing results stay with revision 1."});
const project=t=>({project_id:context.projectId,created_at:"now",updated_at:"now",revisions:[revision,{...revision,revision_id:"2".repeat(16),number:2,brief:t.brief,brief_fingerprint:"3".repeat(64)}]});
const response=body=>({ok:true,status:200,json:async()=>({...identity,...body})});
function dom(){const nodes=new Map();const root={innerHTML:"",setAttribute(){},querySelector(s){if(!nodes.has(s))nodes.set(s,{innerHTML:"",textContent:"",value:"",hidden:false,disabled:false,focus(){},addEventListener(){}});return nodes.get(s);}};return {root,node:s=>root.querySelector(s)};}
const health=()=>response({status:"ready",fixture_id:"esp32-bme280-environmental-logger"});

test("review shows exact diff then applies by identity only",async()=>{
    const ui=dom(),t=change(),calls=[];let saved;
    const c=mountProjectAssistant(ui.root,{fetcher:async(url,options={})=>{calls.push({url,data:options.body&&JSON.parse(options.body)});return url==="/api/health"?health():url.endsWith("/apply")?response({project:project(t)}):response({turn:t});},onApplied:p=>{saved=p;}});
    c.setContext(context);await c.ask("Make it 80 mm wide");
    assert.match(ui.node("#assistant-response").innerHTML,/Before: 100/);
    assert.equal(saved,undefined);assert.equal(ui.node("#assistant-apply").hidden,false);
    await c.apply();assert.equal(saved.revisions[1].brief.board_width_mm,80);
    assert.deepEqual(calls.find(c=>c.url.endsWith("/apply")).data,identity);
});
test("dirty draft and late response cannot overwrite a changed selection",async()=>{
    const ui=dom();let deliver,calls=0;
    const c=mountProjectAssistant(ui.root,{fetcher:async url=>{if(url==="/api/health")return health();calls++;return new Promise(r=>{deliver=r;});}});
    c.setContext({...context,dirty:true});await c.ask("change");assert.equal(calls,0);
    c.setContext(context);const pending=c.ask("change");await new Promise(setImmediate);
    c.setContext({...context,revision:{...revision,revision_id:"9".repeat(16)}});deliver(response({turn:change()}));await pending;
    assert.equal(ui.node("#assistant-response").innerHTML,"");assert.equal(ui.node("#assistant-apply").hidden,true);
});
test("answers cannot silently apply changes; missing and extra diff fields fail closed",()=>{
    const t=change();for(const overrides of [{revision_id:"9".repeat(16)},{changes:[]},{changes:[...t.changes,...t.changes]},{kind:"answer"},{base_brief_fingerprint:"0".repeat(64)}])assert.throws(()=>parseTurn({...identity,turn:{...t,...overrides}},identity,context));
    const valid={...t,kind:"answer",brief:null,changes:[],ready:false,facts:[{id:"run.status",label:"Run status",source:"Revision 1 run record",basis:"run_state",value:"not_run"}]};
    assert.equal(parseTurn({...identity,turn:valid},identity,context),valid);
});
test("clarification replies retain server turn identity and never auto apply",async()=>{
    const ui=dom(),calls=[],t={...change(),questions:["Use 80 mm?"],ready:false};
    const c=mountProjectAssistant(ui.root,{fetcher:async(url,opts={})=>{if(url==="/api/health")return health();calls.push(JSON.parse(opts.body));return response({turn:t});}});
    c.setContext(context);await c.ask("Make it smaller");await c.apply();await c.ask("Yes");
    assert.equal(calls.length,2);assert.equal(calls[1].parent_id,t.turn_id);assert.equal(calls[1].message,"Yes");
});
test("mismatched saved revision is never activated",async()=>{
    const ui=dom(),t=change(),wrong=project(t);let activated=false;wrong.revisions[1].brief={...brief};
    const c=mountProjectAssistant(ui.root,{fetcher:async url=>url==="/api/health"?health():url.endsWith("/apply")?response({project:wrong}):response({turn:t}),onApplied:()=>{activated=true;}});
    c.setContext(context);await c.ask("change");await c.apply();assert.equal(activated,false);assert.match(ui.node("#assistant-error").textContent,/does not match/);
});
test("facts, questions and changed values are escaped and remain qualified",()=>{
    const t={...change(),facts:[{label:"<script>",value:"<img onerror=bad>",source:"<source>",basis:"saved_requirement"}],questions:["<svg>"],messages:["<b>"]};
    const html=turnHtml(t);assert.doesNotMatch(html,/<script>|<img|<svg>|<source>/);assert.match(html,/AI selected/);assert.match(html,/not verified engineering/);
});
test("JSON object property order cannot invent a sensor change",()=>{
    const selected={...context,revision:{...revision,brief:{...brief,sensors:[{address:null,part_id:"BME280"}]}}};
    const t=change();t.brief.sensors=[{part_id:"BME280",address:null}];
    assert.equal(parseTurn({...identity,turn:t},identity,selected),t);
});

test("chat retains escaped user turns and resets when revision changes",async()=>{
    const ui=dom(), t=change();
    const c=mountProjectAssistant(ui.root,{fetcher:async url=>url==="/api/health"?health():response({turn:t})});
    c.setContext(context);
    await c.ask("<img src=x> Make it smaller");
    await c.ask("Make it 80 mm wide");
    const html=ui.node("#assistant-response").innerHTML;
    assert.equal((html.match(/class="assistant-user-message"/g)||[]).length,2);
    assert.match(html,/&lt;img src=x&gt;/);assert.doesNotMatch(html,/<img/);
    assert.equal(ui.node("#assistant-welcome").hidden,true);
    c.setContext({...context,revision:{...revision,revision_id:"9".repeat(16)}});
    assert.equal(ui.node("#assistant-response").innerHTML,"");
    assert.equal(ui.node("#assistant-welcome").hidden,false);
});

test("generated parts render as escaped readable records",()=>{
    const html=turnHtml({...change(),kind:"answer",facts:[{id:"report.bom.parts",label:"Parts used",source:"Saved BOM",basis:"recorded_result",value:[{part:"<script>",references:["U1"],quantity:1,description:"<img>"}]}]});
    assert.match(html,/assistant-parts/);assert.match(html,/U1 · Quantity 1/);
    assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>|<img>/);
});

test("requirement facts stay readable and distinguish unmet from unverified",()=>{
    const html=turnHtml({...change(),kind:"answer",facts:[{id:"report.requirements",label:"Saved choices",source:"Recorded checks",basis:"recorded_result",value:[
        {field:"hand_solderable_preferred",label:"Assembly",status:"VIOLATED",detail:"Needs reflow <tool>.",display_value:"Yes"},
        {field:"budget_usd",label:"Budget",status:"UNKNOWN",detail:"Total cost unknown.",display_value:"$20"},
    ]}]});
    assert.match(html,/Violated/);assert.match(html,/Unknown/);assert.match(html,/Needs reflow &lt;tool&gt;/);
    assert.doesNotMatch(html,/<tool>/);
});

test("a clarification leads with the decision and keeps supporting records collapsed",()=>{
    const html=turnHtml({...change(),changes:[],ready:false,questions:["Would you accept reflow assembly?"],facts:[
        {id:"run.status",label:"Run",source:"Run record",basis:"run_state",value:"complete"},
    ]});
    assert.ok(html.indexOf("Would you accept reflow assembly?") < html.indexOf("See the saved records"));
    assert.doesNotMatch(html,/Review your changes|No changes were proposed/);
    assert.match(html,/<details><summary>See the saved records/);
});
