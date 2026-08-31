import test from"node:test";import assert from"node:assert/strict";import{artifactCurrent,badge,money,releaseReadiness,tone}from"../view-model.js";
test("truthful status tones remain distinct",()=>{assert.equal(tone("PASS"),"pass");assert.equal(tone("PASS_WITH_WARNINGS"),"warn");assert.equal(tone("FAIL"),"fail");assert.equal(tone("UNKNOWN"),"warn");assert.equal(tone("NOT_YET_VERIFIED"),"notyet")});
test("unknown money never renders as zero",()=>{assert.equal(money(null,"UNKNOWN"),"UNKNOWN");assert.equal(money("0","KNOWN"),"$0.00")});
test("artifact freshness is explicit",()=>{assert.equal(artifactCurrent({current:true}),"CURRENT");assert.equal(artifactCurrent({current:false}),"STALE")});
test("badges escape untrusted labels",()=>{assert.match(badge("<script>"),/&lt;script&gt;/)});
test("release readiness fails closed on contradictory freshness",()=>{assert.deepEqual(releaseReadiness({status:"READY_FOR_MANUFACTURING_REVIEW",current:true}),{status:"READY_FOR_MANUFACTURING_REVIEW",label:"Ready for manufacturing review"});assert.deepEqual(releaseReadiness({status:"READY_FOR_MANUFACTURING_REVIEW",current:false}),{status:"STALE",label:"Release is stale or not ready"})});
