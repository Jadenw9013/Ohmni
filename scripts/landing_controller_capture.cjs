/* Capture and exercise the actual source-derived controller scene. No generated media. */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const sharp = require(process.env.OHMNI_SHARP_MODULE || 'sharp');
const base = process.argv[2] || 'http://127.0.0.1:8780';
const output = path.resolve(process.argv[3] || 'out/landing-pcb-controller/visual');
const directory = path.resolve('apps/web/landing-pcb-controller');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
fs.mkdirSync(output, { recursive: true });

(async () => {
    const sourcePath=path.join(directory,'candidate-board.json'), source=JSON.parse(fs.readFileSync(sourcePath));
    const before=hash(sourcePath), browser=await chromium.launch({channel:'msedge',headless:true});
    try {
        const context=await browser.newContext({viewport:{width:1440,height:1050},deviceScaleFactor:1});
        await context.route('**/*',route=>{
            const url=new URL(route.request().url());
            if(!['GET','HEAD'].includes(route.request().method()))return route.abort();
            if(url.origin!==new URL(base).origin)return route.abort();
            if(/\/landing-pcb-controller\/poster-(desktop|mobile)\.webp$/.test(url.pathname)
                && !fs.existsSync(path.join(directory,path.basename(url.pathname))))return route.fulfill({status:204,body:''});
            return route.continue();
        });
        const page=await context.newPage(), errors=[];
        page.on('pageerror',e=>errors.push(e.message));
        page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
        const ready=async()=>{
            await page.waitForFunction(()=>['ready','unavailable'].includes(document.body.dataset.state),null,{timeout:60000});
            assert.equal(await page.locator('body').getAttribute('data-state'),'ready',await page.locator('body').getAttribute('data-failure'));
        };
        await page.goto(`${base}/landing-pcb-controller/`);await ready();
        const shot=async name=>{await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(output,`${name}.png`),fullPage:true});};
        const evidence={sourceSha256:before,capturedAt:new Date().toISOString(),browser:await browser.version(),
            overview:await page.evaluate(()=>window.landingPrototype.stats()),
            coordinateProjection:await page.evaluate(()=>window.landingPrototype.displayReference.display_projection)};
        assert.equal(evidence.overview.refs.length,source.board.components.length);
        const point=await page.evaluate(()=>{
            const view=window.landingPrototype.view,region=view.hitRegions.find(r=>r.ref==='U1');
            const rect=document.getElementById('pcb-canvas').getBoundingClientRect();
            return {x:rect.left+region.centre.x,y:rect.top+region.centre.y};
        });
        await page.mouse.click(point.x,point.y);
        assert.match(await page.locator('#part-title').innerText(),/^U1 /);
        evidence.mousePicking='U1 actual pointer click';
        const initialYaw=await page.evaluate(()=>window.landingPrototype.view.camera.yaw);
        await page.mouse.move(point.x,point.y);await page.mouse.down();
        await page.mouse.move(point.x+60,point.y+15,{steps:6});await page.mouse.up();
        assert.notEqual(await page.evaluate(()=>window.landingPrototype.view.camera.yaw),initialYaw);
        evidence.pointerOrbit=true;
        await page.mouse.move(5,5);
        await page.evaluate(()=>window.landingPrototype.pose());
        await shot('01-overview');
        await page.locator('#pcb-canvas').screenshot({path:path.join(output,'poster-desktop.png')});
        for(const pose of ['top','side','underside']){
            await page.evaluate(pose=>window.landingPrototype.pose(pose),pose);await shot(`02-${pose}`);
        }
        for(const ref of ['U1','U2','U3','U4','J1','J2','D1'])if(source.board.components.some(p=>p.ref===ref)){
            await page.evaluate(ref=>window.landingPrototype.closeUp(ref),ref);await shot(`03-${ref}`);
        }
        await page.evaluate(()=>window.landingPrototype.closeUp('J1',true));await shot('03-J1-opening');
        for(const part of source.board.components){
            await page.locator('#part-select').selectOption(part.ref);
            assert.match(await page.locator('#part-title').innerText(),new RegExp(`^${part.ref} `));
        }
        evidence.selectorSelectableParts=source.board.components.length;
        await page.locator('#part-select').focus();await page.keyboard.press('Home');
        for(const part of source.board.components){
            await page.keyboard.press('ArrowDown');
            assert.equal(await page.locator('#part-select').inputValue(),part.ref,
                `Native keyboard selection could not reach ${part.ref}`);
            assert.match(await page.locator('#part-title').innerText(),new RegExp(`^${part.ref} `));
        }
        evidence.keyboardSelectableParts=source.board.components.length;
        evidence.bindings=await page.evaluate(()=>[...window.landingPrototype.view.renderer.owners].map(([ref,object])=>({
            ref,modelAsset:object.userData.model_asset_id,binding:object.userData.package_binding,
            contacts:object.userData.contacts,geometryClaim:object.userData.geometryClaim,
            sourcePadContacts:object.userData.source_pad_contacts,
            uncertainty:object.userData.model_metadata?.library_metadata,
        })));
        const displayParts=await page.evaluate(()=>window.landingPrototype.displayReference.board.components);
        for(const binding of evidence.bindings){
            const part=displayParts.find(p=>p.ref===binding.ref);
            binding.contactProjection=(binding.contacts?.length?binding.contacts:binding.sourcePadContacts).map(contact=>{
                const number=contact.terminal??contact.number;
                const pads=part.pads.filter(p=>String(p.number)===String(number));
                const distances=pads.map(p=>({pad:p,dx:Math.abs(p.x_mm-contact.center_mm[0]),dy:Math.abs(p.y_mm-contact.center_mm[1])}));
                distances.sort((a,b)=>(a.dx*a.dx+a.dy*a.dy)-(b.dx*b.dx+b.dy*b.dy));
                const nearest=distances[0];
                assert.ok(nearest,`${binding.ref} contact ${number} has no named source pad`);
                // A nominal package contact center need not equal a land center.
                // It must still overlap that same-numbered copper land. THT pins
                // and source-derived contacts must align at their hole centers.
                const exact=contact.type==='tht'||contact.basis==='SOURCE_PAD_DERIVED_VISUAL_CONTACT';
                const maxX=exact?1e-6:(nearest.pad.width_mm+(contact.size_mm?.[0]??0))/2;
                const maxY=exact?1e-6:(nearest.pad.height_mm+(contact.size_mm?.[1]??0))/2;
                assert.ok(nearest.dx<=maxX&&nearest.dy<=maxY,
                    `${binding.ref} contact ${number} misses its source pad: ${nearest.dx},${nearest.dy}`);
                return {number,delta_mm:[nearest.dx,nearest.dy],check:exact?'CENTER_MATCH':'SAME_NUMBERED_LAND_OVERLAP'};
            });
            assert.ok(binding.contactProjection.length,`${binding.ref} has no inspectable contact metadata`);
        }
        fs.writeFileSync(path.join(output,'bindings.json'),JSON.stringify(evidence.bindings,null,2));delete evidence.bindings;
        evidence.reflow=[];
        for(const width of [390,320,768]){
            await page.setViewportSize({width,height:950});await page.evaluate(()=>window.landingPrototype.pose());
            await shot(`04-width-${width}`);
            assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
            evidence.reflow.push(width);
            if(width===390)await page.locator('#pcb-canvas').screenshot({path:path.join(output,'poster-mobile.png')});
        }
        evidence.posters=[];
        for(const kind of ['desktop','mobile']){
            const target=path.join(directory,`poster-${kind}.webp`);
            await sharp(path.join(output,`poster-${kind}.png`)).webp({quality:90,effort:6}).toFile(target);
            evidence.posters.push({kind,sha256:hash(target),bytes:fs.statSync(target).size});
        }
        await page.setViewportSize({width:850,height:640});
        await page.goto(`${base}/landing-pcb-controller/?embed=1`);await ready();await page.evaluate(()=>window.landingPrototype.pose());await shot('05-embedded');
        assert.ok(await page.locator('.embed-open').isVisible());
        assert.equal(await page.locator('.header').isVisible(),false);
        await page.locator('#embed-view').click();
        assert.equal(await page.locator('#embed-view').innerText(),'Angle view');
        await page.setViewportSize({width:320,height:450});await shot('05-embedded-320');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        await page.emulateMedia({reducedMotion:'reduce'});await page.reload();await ready();
        assert.equal(await page.locator('#motion').innerText(),'Motion off');
        const camera=await page.evaluate(()=>({...window.landingPrototype.view.camera}));
        await page.evaluate(()=>window.landingPrototype.replay());
        assert.deepEqual(await page.evaluate(()=>({...window.landingPrototype.view.camera})),camera);
        evidence.reducedMotion=true;
        assert.equal(hash(sourcePath),before,'Rendering changed source geometry');
        assert.deepEqual(errors,[]);
        const home=await context.newPage(),homeErrors=[],homeConsole=[];
        home.on('pageerror',e=>homeErrors.push(e.message));
        home.on('console',m=>{if(m.type()==='error')homeConsole.push(m.text());});
        await home.setViewportSize({width:1440,height:1000});
        await home.goto(`${base}/#home`);
        const embed=home.frameLocator('#home-board-3d');
        await embed.locator('body[data-state="ready"]').waitFor({timeout:60000});
        await embed.locator('body').evaluate(()=>window.landingPrototype.pose());
        await embed.locator('body').evaluate(()=>{window.__controllerLifecycleView=window.landingPrototype.view;});
        await home.screenshot({path:path.join(output,'06-home-desktop.png'),fullPage:true});
        await home.evaluate(()=>{location.hash='#workspace';});
        await home.locator('#home-board-3d').waitFor({state:'hidden',timeout:10000});
        await home.evaluate(()=>{location.hash='#home';});
        await home.locator('#home-board-3d').waitFor({state:'visible',timeout:10000});
        assert.equal(await embed.locator('#pcb-canvas').count(),1);
        assert.equal(await embed.locator('body').evaluate(()=>window.__controllerLifecycleView===window.landingPrototype.view),true);
        await home.setViewportSize({width:320,height:900});
        await home.screenshot({path:path.join(output,'06-home-320.png'),fullPage:true});
        assert.ok(await home.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Home overflow at 320');
        assert.deepEqual(homeErrors,[]);
        evidence.home={routeRoundTrip:true,singleCanvas:true,pageErrors:homeErrors,consoleErrors:homeConsole};
        const fallback=await context.newPage();
        await fallback.addInitScript(()=>{
            const getContext=HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext=function(kind,...args){
                return kind==='webgl2'?null:getContext.call(this,kind,...args);
            };
        });
        await fallback.goto(`${base}/landing-pcb-controller/`);
        await fallback.locator('body[data-state="unavailable"]').waitFor();
        assert.equal(await fallback.locator('#poster').isVisible(),true);
        await fallback.locator('#part-select').selectOption('U1');
        assert.match(await fallback.locator('#part-title').innerText(),/^U1 /);
        assert.equal(await fallback.locator('#binding-download').isVisible(),true);
        await fallback.screenshot({path:path.join(output,'07-no-webgl.png'),fullPage:true});
        evidence.noWebGL={poster:true,sourceDownload:true,componentDescriptions:true};
        evidence.errors=errors;fs.writeFileSync(path.join(output,'capture.json'),JSON.stringify(evidence,null,2));
        console.log(JSON.stringify({output,parts:evidence.keyboardSelectableParts,posters:evidence.posters,errors},null,2));
    }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
