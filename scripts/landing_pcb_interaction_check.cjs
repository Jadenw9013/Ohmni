/* Bounded P1 browser evidence. This is not P2 acceptance or physical-mobile testing.
 * OHMNI_PLAYWRIGHT_MODULE may select an existing installed Playwright package.
 * node scripts/landing_pcb_interaction_check.cjs http://127.0.0.1:8780 out/landing-pcb/p1-ux
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:8780';
const output = path.resolve(process.argv[3] || 'out/landing-pcb/p1-ux');
const url = `${base}/landing-pcb-prototype/`;
const watched = ['apps/web/landing-pcb-prototype/index.html','apps/web/landing-pcb-prototype/prototype.js',
    'apps/web/landing-pcb-prototype/prototype.css','apps/web/board-view.js','apps/web/reference-board.json'];
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const hashes = () => Object.fromEntries(watched.map(file => [file,digest(fs.readFileSync(file))]));
const expectedRefs = ['C1','C2','C3','C4','C5','C6','C7','D1','D2','D3','D4','J1','J2',
    'R1','R2','R3','R4','R5','R10','R11','R12','R13','R20','R21','SW1','SW2','U1','U2','U3'];
fs.mkdirSync(output,{recursive:true});

(async () => {
    const report = { scope:'P1_ISOLATED_PROTOTYPE_BROWSER_CHECK', url, startedAt:new Date().toISOString(),
        inputHashesBefore:hashes(), browser:null, physicalMobileTested:false,
        limitations:['Headless Microsoft Edge; touch uses browser/CDP emulation, not a physical phone.',
            'This script does not certify assistive-technology support or all WCAG requirements.',
            'P1 tests require honest unavailable states; the full P2 semantic fallback is outside this check.'],
        cases:[], observations:[], mutationRequests:[], pageErrors:[] };
    const browser = await chromium.launch({channel:'msedge',headless:true});
    report.browser = await browser.version();
    const contexts = [];
    async function makePage(options={}) {
        const context = await browser.newContext({viewport:{width:1440,height:800},deviceScaleFactor:1,...options});
        contexts.push(context);
        await context.route('**/*',route => {
            const request=route.request();
            if (!['GET','HEAD'].includes(request.method())) {report.mutationRequests.push({method:request.method(),url:request.url()});return route.abort();}
            return new URL(request.url()).origin===new URL(base).origin ? route.continue() : route.abort();
        });
        const page=await context.newPage();page.setDefaultTimeout(10000);
        page.on('pageerror',error=>report.pageErrors.push({url:page.url(),message:error.message}));
        return {context,page};
    }
    async function ready(page) {
        await page.goto(url,{waitUntil:'domcontentloaded'});
        await page.waitForFunction(()=>['ready','unavailable'].includes(document.body.dataset.state));
        assert.equal(await page.locator('body').getAttribute('data-state'),'ready',await page.locator('body').getAttribute('data-failure'));
    }
    async function shot(page,name) {await page.screenshot({path:path.join(output,`${name}.png`),fullPage:true});}
    async function check(name,fn) {
        const started=Date.now();
        try {const detail=await fn();report.cases.push({name,status:'PASS',durationMs:Date.now()-started,detail});}
        catch(error) {report.cases.push({name,status:'FAIL',durationMs:Date.now()-started,error:error.message});}
    }
    async function keyboardSelect(page,ref) {
        const values=await page.locator('#part-select option').evaluateAll(options=>options.map(option=>option.value));
        const index=values.indexOf(ref);assert.ok(index>=0,`Missing ${ref}`);
        await page.locator('#part-select').focus();
        await page.keyboard.press('Home');
        for(let i=0;i<index;i++)await page.keyboard.press('ArrowDown');
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#part-select').inputValue(),ref);
        const title=await page.locator('#part-title').innerText();
        assert.ok(title.startsWith(`${ref} ·`),`Native selector chose ${ref}, but inspector still reads ${JSON.stringify(title)}`);
        return {value:ref,title:await page.locator('#part-title').innerText(),description:await page.locator('#part-description').innerText()};
    }
    try {
        const desktop=await makePage();await ready(desktop.page);
        report.gpu=await desktop.page.locator('#pcb-canvas').evaluate(canvas=>{
            const gl=canvas.getContext('webgl2'),debug=gl?.getExtension('WEBGL_debug_renderer_info');
            return debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):'unavailable';
        });
        await check('29 native part options and keyboard R1/J2 inspection',async()=>{
            const options=await desktop.page.locator('#part-select option').evaluateAll(options=>options.filter(option=>option.value).map(option=>({value:option.value,label:option.textContent})));
            assert.deepEqual(options.map(option=>option.value).sort(),[...expectedRefs].sort());
            const r1=await keyboardSelect(desktop.page,'R1'),j2=await keyboardSelect(desktop.page,'J2');
            await desktop.page.keyboard.press('Tab');
            assert.equal(await desktop.page.evaluate(()=>document.activeElement.id),'focus-part');
            await shot(desktop.page,'01-keyboard-j2');return {options,r1,j2,tabExitsSelector:true};
        });
        await check('native wheel scroll over board leaves camera unchanged',async()=>{
            await desktop.page.evaluate(()=>{window.landingPrototype.pose();scrollTo(0,0);});
            const bounds=await desktop.page.locator('#pcb-canvas').boundingBox();
            const before=await desktop.page.evaluate(()=>({scrollY,camera:{...window.landingPrototype.view.camera}}));
            await desktop.page.mouse.move(bounds.x+bounds.width/2,Math.min(600,bounds.y+bounds.height/2));
            await desktop.page.mouse.wheel(0,380);
            await desktop.page.waitForFunction(old=>scrollY>old,before.scrollY,{timeout:2000});
            const after=await desktop.page.evaluate(()=>({scrollY,camera:{...window.landingPrototype.view.camera}}));
            for(const key of ['zoom','yaw','pitch'])assert.equal(after.camera[key],before.camera[key],`${key} changed during page scroll`);
            return {before,after};
        });
        await check('session Motion Off survives OS reduced motion then return',async()=>{
            await desktop.page.locator('#motion').click();
            assert.equal(await desktop.page.locator('#motion').innerText(),'Motion off');
            await desktop.page.emulateMedia({reducedMotion:'reduce'});
            await desktop.page.waitForFunction(()=>window.landingPrototype.view.reducedMotion);
            await desktop.page.emulateMedia({reducedMotion:'no-preference'});
            await desktop.page.waitForTimeout(100);
            assert.equal(await desktop.page.locator('#motion').innerText(),'Motion off');
            assert.equal(await desktop.page.locator('#replay').isDisabled(),true);
            assert.equal(await desktop.page.evaluate(()=>window.landingPrototype.view.reducedMotion),true);
            await shot(desktop.page,'02-motion-off');return {motionOff:true,replayDisabled:true};
        });
        await check('initial OS reduced motion disables replay and keeps stable pose',async()=>{
            const reduced=await makePage({reducedMotion:'reduce'});await ready(reduced.page);
            assert.equal(await reduced.page.locator('#replay').isDisabled(),true);
            assert.equal(await reduced.page.locator('#motion').innerText(),'Motion off');
            const before=await reduced.page.evaluate(()=>({...window.landingPrototype.view.camera}));
            await reduced.page.evaluate(()=>window.landingPrototype.replay());await reduced.page.waitForTimeout(120);
            assert.deepEqual(await reduced.page.evaluate(()=>({...window.landingPrototype.view.camera})),before);
            return {replayDisabled:true,stablePose:true};
        });
        const mobile=await makePage({viewport:{width:320,height:844},isMobile:true,hasTouch:true});await ready(mobile.page);
        await check('320 CSS px reflow and all-parts inspection',async()=>{
            const sizes=await mobile.page.evaluate(()=>({innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth}));
            assert.ok(sizes.scrollWidth<=sizes.innerWidth,JSON.stringify(sizes));
            await mobile.page.locator('#part-select').selectOption('R1');
            assert.match(await mobile.page.locator('#part-title').innerText(),/^R1 ·/);
            await mobile.page.locator('#part-select').selectOption('J2');
            assert.match(await mobile.page.locator('#part-title').innerText(),/^J2 ·/);
            await shot(mobile.page,'03-mobile-320');return {...sizes,selectionMethod:'native select API; gesture scroll tested separately'};
        });
        await check('emulated native touch scroll over canvas does not orbit',async()=>{
            await mobile.page.locator('#pcb-canvas').scrollIntoViewIfNeeded();
            const box=await mobile.page.locator('#pcb-canvas').boundingBox();
            const before=await mobile.page.evaluate(()=>({scrollY,camera:{...window.landingPrototype.view.camera},touchAction:getComputedStyle(document.getElementById('pcb-canvas')).touchAction}));
            assert.match(before.touchAction,/pan-y/);assert.match(before.touchAction,/pinch-zoom/);
            const cdp=await mobile.context.newCDPSession(mobile.page),x=box.x+box.width/2,y=Math.min(box.y+box.height*.75,760);
            await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
            for(let i=1;i<=6;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-i*28}]});await mobile.page.waitForTimeout(20);}
            await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
            await mobile.page.waitForFunction(old=>scrollY>old,before.scrollY,{timeout:2000});
            const after=await mobile.page.evaluate(()=>({scrollY,camera:{...window.landingPrototype.view.camera}}));
            for(const key of ['yaw','pitch','zoom'])assert.equal(after.camera[key],before.camera[key],`${key} changed during touch scroll`);
            await cdp.detach();return {before,after,physicalDevice:false};
        });
        await check('missing reference JSON gives an honest P1 unavailable state',async()=>{
            const missing=await makePage();await missing.page.route('**/reference-board.json',route=>route.fulfill({status:503,body:'Unavailable'}));
            await missing.page.goto(url);await missing.page.waitForFunction(()=>document.body.dataset.state==='unavailable');
            assert.equal(await missing.page.locator('#part-controls').isVisible(),false);
            assert.equal(await missing.page.locator('#view-controls').isVisible(),false);
            assert.match(await missing.page.locator('#loading').innerText(),/3D view is unavailable/);
            assert.equal(await missing.page.getByRole('link',{name:'Open existing app',exact:true}).isVisible(),true);
            await shot(missing.page,'04-missing-reference');return {state:'unavailable',scope:'P1 summary-only fallback'};
        });
        await check('initialization cancellation cannot mount a late renderer',async()=>{
            const cancelled=await makePage();let release,requested;
            const requestedPromise=new Promise(resolve=>requested=resolve),releasePromise=new Promise(resolve=>release=resolve);
            await cancelled.page.route('**/reference-board.json',async route=>{
                requested();await releasePromise;
                try {await route.fulfill({status:200,contentType:'application/json',body:fs.readFileSync('apps/web/reference-board.json','utf8')});}catch{/* Abort is expected. */}
            });
            await cancelled.page.goto(url,{waitUntil:'domcontentloaded'});await requestedPromise;
            await cancelled.page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:false})));
            release();await cancelled.page.waitForTimeout(250);
            const state=await cancelled.page.evaluate(()=>({mounted:Boolean(window.landingPrototype),state:document.body.dataset.state??null,controlsVisible:!document.getElementById('view-controls').hidden}));
            assert.equal(state.mounted,false);assert.equal(state.controlsVisible,false);
            return {...state,method:'Synthetic pagehide exercises actual disposal hook while reference response is pending.'};
        });
        await check('context loss leaves no active dead part-inspection control',async()=>{
            const lost=await makePage();await ready(lost.page);await keyboardSelect(lost.page,'J2');
            const supported=await lost.page.locator('#pcb-canvas').evaluate(canvas=>{
                const extension=canvas.getContext('webgl2').getExtension('WEBGL_lose_context');
                if(!extension)return false;extension.loseContext();return true;
            });
            assert.equal(supported,true,'WEBGL_lose_context unavailable');
            await lost.page.waitForFunction(()=>document.body.dataset.state==='unavailable');
            await shot(lost.page,'05-context-loss');
            const visible=await lost.page.locator('#part-select').isVisible(),disabled=await lost.page.locator('#part-select').isDisabled();
            if(visible&&!disabled)await keyboardSelect(lost.page,'R1');
            return {state:'unavailable',partSelectorVisible:visible,partSelectorDisabled:disabled,
                behavior:visible&&!disabled?'Text inspection remains functional':'Unavailable part control hidden/disabled'};
        });
        await check('no-JS retains readable P1 description and working plain app link',async()=>{
            const nojs=await makePage({javaScriptEnabled:false});await nojs.page.goto(url);
            assert.equal(await nojs.page.locator('#part-controls').isVisible(),false);
            assert.equal(await nojs.page.locator('#view-controls').isVisible(),false);
            assert.match(await nojs.page.locator('noscript').innerText(),/JavaScript is required/);
            assert.match(await nojs.page.locator('#part-description').innerText(),/saved design/);
            assert.equal(await nojs.page.getByRole('link',{name:'Open existing app',exact:true}).getAttribute('href'),'../');
            const loadingVisible=await nojs.page.locator('#loading').isVisible();
            if(loadingVisible)report.observations.push({severity:'LOW',topic:'no-JS',detail:'The readable no-JS notice exists, but the scene also retains Preparing the saved board indefinitely.'});
            await shot(nojs.page,'06-no-js');return {enhancementControlsHidden:true,loadingVisible};
        });
        assert.deepEqual(report.mutationRequests,[],'Prototype attempted a mutating request');
    } finally {
        report.inputHashesAfter=hashes();report.inputsChangedDuringCheck=JSON.stringify(report.inputHashesAfter)!==JSON.stringify(report.inputHashesBefore);
        report.finishedAt=new Date().toISOString();
        report.summary={passed:report.cases.filter(item=>item.status==='PASS').length,failed:report.cases.filter(item=>item.status==='FAIL').length};
        fs.writeFileSync(path.join(output,'interaction-report.json'),JSON.stringify(report,null,2));
        await Promise.all(contexts.map(context=>context.close()));await browser.close();
        console.log(JSON.stringify({output,summary:report.summary,cases:report.cases,observations:report.observations,inputsChangedDuringCheck:report.inputsChangedDuringCheck},null,2));
        if(report.summary.failed)process.exitCode=1;
    }
})().catch(error=>{console.error(error);process.exitCode=1;});
