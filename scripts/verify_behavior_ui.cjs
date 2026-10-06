// Run with the bundled Playwright package on NODE_PATH. Only localhost is accepted.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const assert=require('node:assert/strict');
const base=process.argv[2] || 'http://127.0.0.1:8781';
const out=process.argv[3] || 'build/stage6-browser';
assert(['127.0.0.1','localhost'].includes(new URL(base).hostname));
fs.mkdirSync(out,{recursive:true});
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const receipt={started_at:new Date().toISOString(),base,script_sha256:hash(fs.readFileSync(__filename)),checks:[],runs:[],page_errors:[],passed:false};
let browser,page;
const check=name=>{receipt.checks.push({name,passed:true});console.log(name)};
async function select(id){await page.locator('[data-story-search]').fill(id);await page.locator(`[data-story-canvas][data-model-entry="${id}"]`).waitFor({timeout:30000});}
async function run(id){
 await select(id);await page.locator('[data-story-tab="behavior"]').click();
 await page.locator('[data-behavior-run]:enabled').waitFor({timeout:30000});
 const reply=page.waitForResponse(r=>r.url().endsWith(`/api/behavior/${id}/run`) && r.request().method()==='POST');
 await page.locator('[data-behavior-run]').click();
 const response=await reply;assert.equal(response.status(),200);const body=await response.json();
 assert.equal(body.result.entry_id,id);assert.equal(body.result.status,'ran');assert.match(body.result.version_output,/ngspice-42/);
 receipt.runs.push({entry_id:id,status:body.result.status,rating_status:body.result.rating_status,version_output:body.result.version_output,
                    run_id:body.result.run_id,netlist_sha256:body.result.netlist_sha256,circuit_hash:body.result.circuit_hash});
 return body;
}
async function main(){
 browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>receipt.page_errors.push(e.message));
 await page.goto(base,{waitUntil:'networkidle'});
 receipt.server_identity=await (await page.request.get(base+'/api/health')).json();
 await page.locator('[data-open-components]').first().click();
 await page.locator('[data-story-status]').filter({hasText:'180'}).waitFor();
 for(let n=1;n<=180;n++){await select(`OHM-${String(n).padStart(3,'0')}`);}
 check('All 180 selected models expose the matching rendered component identity');
 const resistor=await run('OHM-004');
 assert.equal(resistor.result.rating_status,'unknown');
 await page.locator('[data-behavior-run-status]').filter({hasText:'Simulation ran.'}).waitFor();
 assert.match(await page.locator('[data-story-details]').innerText(),/0.00025 A/);
 await page.screenshot({path:path.join(out,'desktop.png')});
 check('Actual ngspice42 resistor run displays measured current and unknown thermal context');
 const tvs=await run('OHM-069');assert.equal(tvs.result.rating_status,'violation');
 await page.locator('[data-behavior-run-status]').filter({hasText:'Rating violation.'}).waitFor();
 check('Actual DC TVS reference stress remains a rating violation');
 await select('OHM-083');await page.locator('.behavior-blocked').waitFor();
 assert.equal(await page.locator('[data-behavior-run]').isEnabled(),false);
 assert.equal(await page.locator('[data-behavior-results]').innerText(),'');
 check('Blocked RGB entry explains why and clears the previous result');
 await select('OHM-004');await page.locator('[data-behavior-run]:enabled').waitFor();
 const identity=receipt.server_identity;
 await page.route('**/api/behavior/OHM-004/run',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    api_version:identity.api_version,server_instance_id:identity.server_instance_id,ui_version:identity.ui_version,
    result:{...resistor.result,status:'failed',rating_status:'within_model_limits'}})}));
 await page.locator('[data-behavior-run]').click();
 await page.locator('[data-behavior-run-status]').filter({hasText:'Simulation not run.'}).waitFor();
 assert.doesNotMatch(await page.locator('[data-behavior-results]').innerText(),/0.00025 A|Within the checked limits/);
 check('Synthetic errored transport response cannot display stale successful measurements');
 await page.unroute('**/api/behavior/OHM-004/run');
 let release,startedResolve;const started=new Promise(resolve=>{startedResolve=resolve});
 const held=new Promise(resolve=>{release=resolve});
 await page.route('**/api/behavior/OHM-004/run',async route=>{startedResolve();await held;try{await route.fulfill({status:503,body:'{}'})}catch{}});
 await page.locator('[data-behavior-run]').click();await started;
 await page.locator('[data-story-search]').fill('NO_SUCH_COMPONENT');release();
 assert.equal(await page.locator('[data-story-name]').innerText(),'No component selected');
 assert.equal(await page.locator('[data-story-details]').innerText(),'');
 await page.unroute('**/api/behavior/OHM-004/run');
 check('Changing to an empty selection aborts a pending run without stale output');
 await select('OHM-083');await page.locator('.behavior-blocked').waitFor();
 await page.setViewportSize({width:390,height:844});
 await page.locator('[data-behavior-run]').scrollIntoViewIfNeeded();
 const bounds=await page.locator('[data-behavior-run]').boundingBox();assert(bounds.y>=0 && bounds.y+bounds.height<=844);
 await page.screenshot({path:path.join(out,'mobile.png')});
 await page.locator('[data-story-tab="behavior"]').focus();await page.keyboard.press('ArrowLeft');
 assert.equal(await page.locator('[data-story-tab="source"]').getAttribute('aria-selected'),'true');
 await page.keyboard.press('Escape');assert.equal(await page.locator('#component-stories').evaluate(d=>d.open),false);
 check('Mobile behavior control is reachable; keyboard tabs and Escape preserve modal access');
 assert.deepEqual(receipt.page_errors,[]);check('No browser runtime errors');
 receipt.screenshots=Object.fromEntries(['desktop.png','mobile.png'].map(name=>[name,hash(fs.readFileSync(path.join(out,name)))]));
 receipt.passed=true;
}
main().catch(e=>{receipt.error=e.message;process.exitCode=1;console.error(e)}).finally(async()=>{
 receipt.finished_at=new Date().toISOString();fs.writeFileSync(path.join(out,'BROWSER_RESULTS.json'),JSON.stringify(receipt,null,2)+'\n');
 if(browser)await browser.close();
});
