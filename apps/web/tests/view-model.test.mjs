import test from"node:test";
import assert from"node:assert/strict";
import{artifactCurrent,badge,money,releaseReadiness,tone}from"../view-model.js";

const FIXTURE_ID="esp32-bme280-environmental-logger",INSTANCE="0123456789abcdef",OTHER_INSTANCE="fedcba9876543210",UI_VERSION="a".repeat(64),OTHER_UI_VERSION="b".repeat(64),JOB_ID="012345abcdef";
const response=(status,payload)=>({ok:status>=200&&status<300,status,json:async()=>payload});
const health=(values={})=>({status:"ready",fixture_id:FIXTURE_ID,api_version:2,server_instance_id:INSTANCE,ui_version:UI_VERSION,...values});
const identity={api_version:2,server_instance_id:INSTANCE,ui_version:UI_VERSION};
const startEnvelope=(values={})=>({job_id:JOB_ID,status:"queued",api_version:2,server_instance_id:INSTANCE,ui_version:UI_VERSION,...values});
const jobEnvelope=(values={})=>({job_id:JOB_ID,status:"running",progress:[],report:null,error:null,error_code:null,api_version:2,server_instance_id:INSTANCE,ui_version:UI_VERSION,...values});

function createDom(){
    const handlers={},windowHandlers={},documentHandlers={};
    const nodes={
        "#request-form":{addEventListener:(type,handler)=>{handlers[type]=handler}},
        "#request":{value:"SECRET contradictory mutable display text"},
        "#run-button":{disabled:false},
        "#progress-section":{hidden:true},
        "#workspace":{hidden:true,scrollIntoView:options=>nodes["#workspace"].scrollCalls.push(options),scrollCalls:[]},
        "#progress-list":{innerHTML:""},"#progress-percent":{textContent:"not reset"},"#progress-bar":{style:{width:"not reset"}},
    };
    for(const selector of["#overview","#repair","#evidence","#notebook","#artifacts","#bom","#release"])nodes[selector]={innerHTML:""};
    const document={hidden:false,querySelector:selector=>nodes[selector],addEventListener:(type,handler)=>{documentHandlers[type]=handler},removeEventListener:(type,handler)=>{if(documentHandlers[type]===handler)delete documentHandlers[type]}};
    const window={addEventListener:(type,handler)=>{windowHandlers[type]=handler},removeEventListener:(type,handler)=>{if(windowHandlers[type]===handler)delete windowHandlers[type]}};
    return{document,window,nodes,handlers,windowHandlers,documentHandlers};
}

let importSequence=0;
async function withApp(run){
    const originalDocument=globalThis.document,originalWindow=globalThis.window,originalFetch=globalThis.fetch;
    const dom=createDom();globalThis.document=dom.document;globalThis.window=dom.window;
    const app=await import(`../app.js?frontend-regression=${++importSequence}`);
    try{return await run(app,dom)}finally{app.stopCompletedMonitor();if(originalDocument===undefined)delete globalThis.document;else globalThis.document=originalDocument;if(originalWindow===undefined)delete globalThis.window;else globalThis.window=originalWindow;if(originalFetch===undefined)delete globalThis.fetch;else globalThis.fetch=originalFetch}
}

test("truthful status tones remain distinct",()=>{assert.equal(tone("PASS"),"pass");assert.equal(tone("VERIFIED"),"pass");assert.equal(tone("PASS_WITH_WARNINGS"),"warn");assert.equal(tone("PARTIALLY_VERIFIED"),"warn");assert.equal(tone("NOT_VERIFIED"),"fail");assert.equal(tone("FAIL"),"fail");assert.equal(tone("UNKNOWN"),"warn");assert.equal(tone("NOT_YET_VERIFIED"),"notyet")});
test("unknown money never renders as zero",()=>{assert.equal(money(null,"UNKNOWN"),"UNKNOWN");assert.equal(money("0","KNOWN"),"$0.00")});
test("artifact freshness is explicit",()=>{assert.equal(artifactCurrent({current:true}),"CURRENT");assert.equal(artifactCurrent({current:false}),"STALE")});
test("badges escape untrusted labels",()=>{assert.match(badge("<script>"),/&lt;script&gt;/)});

test("release readiness, completion motion, and polling states remain truthful",async()=>{
    assert.deepEqual(releaseReadiness({status:"READY_FOR_MANUFACTURING_REVIEW",current:true}),{status:"READY_FOR_MANUFACTURING_REVIEW",label:"Ready for manufacturing review"});
    assert.deepEqual(releaseReadiness({status:"READY_FOR_MANUFACTURING_REVIEW",current:false}),{status:"STALE",label:"Release is stale or not ready"});
    await withApp(async app=>{
        const calls=[],target={scrollIntoView:options=>calls.push(options)},queries=[];
        app.scrollWorkspaceIntoView(target,query=>{queries.push(query);return{matches:true}});
        app.scrollWorkspaceIntoView(target,query=>{queries.push(query);return{matches:false}});
        assert.deepEqual(queries,["(prefers-reduced-motion: reduce)","(prefers-reduced-motion: reduce)"]);
        assert.deepEqual(calls,[{behavior:"instant"},{behavior:"smooth"}]);
        assert.deepEqual(["queued","running","complete","failed","paused"].map(app.pollDisposition),["continue","continue","complete","failed","invalid"]);
    });
});

test("the registered submit handler performs health, POST, and owned job polling",async()=>withApp(async(_app,dom)=>{
    assert.equal(typeof dom.handlers.submit,"function");let prevented=false;const calls=[],scheduled=[];
    globalThis.fetch=async(url,options)=>{
        calls.push({url,options});
        if(url==="/api/health")return response(200,health());
        if(url==="/api/demo")return response(202,startEnvelope());
        if(url===`/api/jobs/${JOB_ID}`)return response(200,jobEnvelope({progress:[{stage:"requirements",label:"Interpreting request",status:"RUNNING",detail:"Owned progress",percent:5}]}));
        assert.fail(`unexpected URL ${url}`);
    };
    const originalSetTimeout=globalThis.setTimeout;globalThis.setTimeout=(callback,delay)=>{scheduled.push({callback,delay});return 1};
    try{await dom.handlers.submit({preventDefault:()=>{prevented=true}})}finally{globalThis.setTimeout=originalSetTimeout}
    assert.equal(prevented,true);assert.equal(calls.length,3);
    assert.deepEqual(calls[0],{url:"/api/health",options:{cache:"no-store"}});
    assert.equal(calls[1].url,"/api/demo");assert.equal(calls[1].options.method,"POST");assert.equal(calls[1].options.cache,"no-store");
    assert.deepEqual(JSON.parse(calls[1].options.body),{fixture_id:FIXTURE_ID,api_version:2,server_instance_id:INSTANCE,ui_version:UI_VERSION});
    assert.doesNotMatch(calls[1].options.body,/SECRET|contradictory|mutable/);
    assert.equal(calls[2].url,`/api/jobs/${JOB_ID}`);assert.equal(calls[2].options.cache,"no-store");
    assert.deepEqual(calls[2].options.headers,{"X-Ohmni-Server-Instance":INSTANCE,"X-Ohmni-API-Version":"2","X-Ohmni-UI-Version":UI_VERSION});
    assert.equal(dom.nodes["#progress-percent"].textContent,"5%");assert.equal(dom.nodes["#progress-bar"].style.width,"5%");assert.match(dom.nodes["#progress-list"].innerHTML,/Owned progress/);
    assert.equal(dom.nodes["#workspace"].hidden,true);assert.equal(dom.nodes["#run-button"].disabled,true);assert.equal(scheduled.length,1);assert.equal(scheduled[0].delay,900);
}));

test("start failures map only allowlisted backend conditions to actionable copy",async()=>withApp(async(app,dom)=>{
    const scenarios=[
        {fetcher:async()=>{throw new Error("SECRET network detail")},message:/backend is unavailable/},
        {fetcher:async()=>response(200,health({api_version:1})),message:/does not match the running Ohmni demo server/},
        {fetcher:async()=>response(200,health({fixture_id:"wrong-fixture"})),message:/rejected the deterministic demo fixture/},
        {responses:[response(200,health()),response(409,{error:"server_instance_mismatch"})],message:/server restarted or changed/},
        {responses:[response(200,health()),response(409,{error:"ui_version_mismatch"})],message:/server restarted or changed/},
        {responses:[response(200,health()),response(400,{error:"fixture_rejected"})],message:/rejected the deterministic demo fixture/},
        {responses:[response(200,health()),response(503,{error:"job_start_unavailable"})],message:/could not initialize the deterministic demo job/},
        {responses:[response(200,health()),response(202,startEnvelope({server_instance_id:OTHER_INSTANCE}))],message:/server restarted or changed/},
        {responses:[response(200,health()),response(202,{...startEnvelope(),extra:"SECRET backend detail"})],message:/does not match the running Ohmni demo server/},
        {responses:[response(500,{error:"SECRET backend detail"})],message:/backend is unavailable/},
    ];
    for(const scenario of scenarios){
        dom.nodes["#progress-list"].innerHTML="";dom.nodes["#progress-percent"].textContent="99%";dom.nodes["#progress-bar"].style.width="99%";dom.nodes["#workspace"].hidden=false;dom.nodes["#run-button"].disabled=true;
        let index=0,polled=false;const fetcher=scenario.fetcher||(async()=>scenario.responses[index++]);
        await app.startDemo({fetcher,poller:async()=>{polled=true}});
        assert.equal(polled,false);assert.equal(dom.nodes["#progress-percent"].textContent,"0%");assert.equal(dom.nodes["#progress-bar"].style.width,"0%");assert.equal(dom.nodes["#workspace"].hidden,true);assert.equal(dom.nodes["#run-button"].disabled,false);
        assert.match(dom.nodes["#progress-list"].innerHTML,scenario.message);assert.doesNotMatch(dom.nodes["#progress-list"].innerHTML,/SECRET|network detail|backend detail/);
    }
}));

test("polling distinguishes restart, lost job, worker start, and pipeline failures",async()=>withApp(async(app,dom)=>{
    const scenarios=[
        {result:response(404,{error:"job_not_found"}),message:/no longer available from the server that created it/},
        {result:response(409,{error:"server_instance_mismatch"}),message:/server restarted or changed/},
        {result:response(409,{error:"api_version_mismatch"}),message:/does not match the running Ohmni demo server/},
        {result:response(200,jobEnvelope({server_instance_id:OTHER_INSTANCE})),message:/server restarted or changed/},
        {result:response(200,jobEnvelope({status:"failed",error:"Demo pipeline failed",error_code:"worker_start_failed"})),message:/worker failed before progress began/},
        {result:response(200,jobEnvelope({status:"failed",error:"Demo pipeline failed",error_code:"pipeline_failed"})),message:/engineering pipeline failed/},
        {result:response(200,jobEnvelope({status:"failed",error:"Demo pipeline failed",error_code:"progress_publication_failed"})),message:/engineering pipeline failed/},
        {result:response(200,jobEnvelope({progress:[{stage:"x",label:"x",status:"RUNNING",detail:"SECRET backend detail",percent:"not-a-percent"}]})),message:/does not match the running Ohmni demo server/},
        {result:response(200,{...jobEnvelope(),extra:"SECRET backend detail"}),message:/does not match the running Ohmni demo server/},
        {error:new Error("SECRET fetch failure"),message:/backend is unavailable/},
    ];
    for(const scenario of scenarios){
        dom.nodes["#progress-list"].innerHTML="";dom.nodes["#run-button"].disabled=true;let scheduled=false;
        await app.poll(JOB_ID,identity,{fetcher:async()=>{if(scenario.error)throw scenario.error;return scenario.result},schedule:()=>{scheduled=true},monitorer:()=>assert.fail("failed jobs must not be monitored")});
        assert.equal(scheduled,false);assert.equal(dom.nodes["#run-button"].disabled,false);assert.match(dom.nodes["#progress-list"].innerHTML,scenario.message);assert.doesNotMatch(dom.nodes["#progress-list"].innerHTML,/SECRET|fetch failure|backend detail/);
    }
}));

test("completed-workspace monitoring invalidates unavailable or changed servers without runaway timers",async()=>withApp(async(app,dom)=>{
    const intervals=[],cleared=[],added=[],removed=[];let current=health();
    const setIntervalFn=(callback,delay)=>{const timer={callback,delay,unref:()=>{timer.unrefCalled=true}};intervals.push(timer);return timer};
    const clearIntervalFn=timer=>cleared.push(timer);
    const windowTarget={addEventListener:(type,handler)=>added.push({target:"window",type,handler}),removeEventListener:(type,handler)=>removed.push({target:"window",type,handler})};
    const documentTarget={hidden:false,addEventListener:(type,handler)=>added.push({target:"document",type,handler}),removeEventListener:(type,handler)=>removed.push({target:"document",type,handler})};
    dom.nodes["#workspace"].hidden=false;
    let check=app.beginCompletedMonitor(identity,{fetcher:async()=>response(200,current),setIntervalFn,clearIntervalFn,windowTarget,documentTarget});
    assert.equal(intervals.length,1);assert.equal(intervals[0].delay,3000);assert.equal(intervals[0].unrefCalled,true);assert.equal(added.length,2);assert.equal(await check(),true);assert.equal(dom.nodes["#workspace"].hidden,false);
    current=health({server_instance_id:OTHER_INSTANCE,ui_version:OTHER_UI_VERSION});assert.equal(await intervals[0].callback(),false);assert.equal(dom.nodes["#workspace"].hidden,true);assert.match(dom.nodes["#progress-list"].innerHTML,/server restarted or changed/);assert.equal(cleared.length,1);assert.equal(removed.length,2);
    dom.nodes["#workspace"].hidden=false;dom.nodes["#progress-list"].innerHTML="";
    check=app.beginCompletedMonitor(identity,{fetcher:async()=>{throw new Error("SECRET monitor failure")},setIntervalFn,clearIntervalFn,windowTarget,documentTarget});
    assert.equal(await check(),false);assert.equal(dom.nodes["#workspace"].hidden,true);assert.match(dom.nodes["#progress-list"].innerHTML,/backend is unavailable/);assert.doesNotMatch(dom.nodes["#progress-list"].innerHTML,/SECRET|monitor failure/);
}));
