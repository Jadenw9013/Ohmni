/* Read-only real-app serving/parity smoke check after the complete static scene audit. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.OHMNI_PLAYWRIGHT_MODULE||'playwright');
const base=process.argv[2]||'http://127.0.0.1:8781';
const output=path.resolve(process.argv[3]||'out/landing-pcb-controller/app-final');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const preview='landing-pcb-controller';
fs.mkdirSync(output,{recursive:true});

(async()=>{
    const browser=await chromium.launch({channel:'msedge',headless:true});
    try{
        const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
        await context.route('**/*',route=>{
            const request=route.request();
            if(!['GET','HEAD'].includes(request.method())||new URL(request.url()).origin!==new URL(base).origin)return route.abort();
            return route.continue();
        });
        const evidence={capturedAt:new Date().toISOString(),base,browser:await browser.version(),files:[]};
        const paths=[...['index.html','prototype.js','prototype.css','models.js','projection.js','presentation.js',
            'candidate-board.json','poster-desktop.webp','poster-mobile.webp'].map(p=>`${preview}/${p}`),
            'visual-board-scene.js','visual-renderer.js','visual-version.js','board-view.js',
            ...['chip2t','leaded','quad-grid','led-passive','completion-a'].map(p=>`component-library/data/${p}.json`)];
        for(const file of paths){
            const response=await context.request.get(`${base}/${file}`);
            assert.equal(response.status(),200,`Not served: ${file}`);
            const local=sha(fs.readFileSync(path.join('apps/web',file))),served=sha(await response.body());
            assert.equal(served,local,`Server bytes differ from audited source: ${file}`);
            evidence.files.push({file,sha256:served,mime:response.headers()['content-type']});
        }
        const health=await context.request.get(`${base}/api/health`);
        assert.equal(health.status(),200);evidence.health=await health.json();
        const page=await context.newPage(),errors=[],failed=[];
        page.on('pageerror',e=>errors.push(e.message));
        page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
        page.on('response',response=>{if(response.status()>=400)failed.push({url:response.url(),status:response.status()});});
        await page.goto(`${base}/#home`);
        const frame=page.frameLocator('#home-board-3d');
        await frame.locator('body[data-state="ready"]').waitFor({timeout:60000});
        await frame.locator('body').evaluate(()=>{window.landingPrototype.pose();window.__appCheckView=window.landingPrototype.view;});
        const source=await frame.locator('body').evaluate(()=>({refs:window.landingPrototype.stats().refs,
            fingerprint:window.landingPrototype.reference.board.artifact_fingerprint,checks:window.landingPrototype.reference.checks}));
        assert.equal(source.refs.length,69);evidence.source=source;
        await page.screenshot({path:path.join(output,'01-home-desktop.png'),fullPage:true});
        await frame.locator('#part-select').selectOption('U1');
        assert.match(await frame.locator('#part-title').innerText(),/^U1 /);
        await frame.locator('#motion').click();assert.equal(await frame.locator('#motion').innerText(),'Motion off');
        await page.evaluate(()=>{location.hash='#workspace';});
        await page.locator('#home-board-3d').waitFor({state:'hidden'});
        await page.evaluate(()=>{location.hash='#home';});
        await page.locator('#home-board-3d').waitFor({state:'visible'});
        assert.equal(await frame.locator('body').evaluate(()=>window.__appCheckView===window.landingPrototype.view),true);
        await frame.locator('body').evaluate(()=>window.landingPrototype.pose());
        await page.setViewportSize({width:320,height:900});
        await page.screenshot({path:path.join(output,'02-home-mobile.png'),fullPage:true});
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        assert.equal(await frame.locator('#pcb-canvas').count(),1);
        assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
        evidence.home={pageAndConsoleErrors:errors,failedResponses:failed,routeRoundTrip:true,singleCanvas:true,
            sourceSelection:true,motionControl:true,noMobileOverflow:true};
        fs.writeFileSync(path.join(output,'app-check.json'),JSON.stringify(evidence,null,2));
        console.log(JSON.stringify({output,filesCompared:evidence.files.length,components:source.refs.length,errors,failed},null,2));
    }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
