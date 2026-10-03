const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('node:assert/strict');
const {chromium}=require(process.env.OHMNI_PLAYWRIGHT_MODULE||'playwright');
const base=process.argv[2]||'http://127.0.0.1:8778',out=path.resolve('out/component-library/completion/all-180');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1920,height:1200},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 await page.goto(base+'/component-library/preview/index.html?all=1');await page.locator('body[data-ready="true"]').waitFor({timeout:60000});
 await page.addStyleTag({content:'main{max-width:1880px}#tiles{grid-template-columns:repeat(6,1fr)}'});
 const stats=await page.evaluate(()=>({sheet:window.componentLibraryPreview.sheetStats,source_spec_sha256:window.componentLibraryPreview.source_spec_sha256,model_source_sha256:window.componentLibraryPreview.model_source_sha256}));assert.equal(stats.sheet.length,180);assert.equal(new Set(stats.sheet.map(r=>r.id)).size,180);
 await page.locator('#sheet').screenshot({path:path.join(out,'all-180-contact-sheet-LOD1.png')});
 for(let i=0;i<6;i++){await page.evaluate(i=>document.querySelectorAll('.tile').forEach((tile,n)=>tile.style.display=n>=i*30&&n<(i+1)*30?'':'none'),i);await page.locator('#sheet').screenshot({path:path.join(out,`review-${i*30+1}-${(i+1)*30}.png`)});}
 await page.evaluate(()=>document.querySelectorAll('.tile').forEach(tile=>tile.style.display=''));
 // Exercise selection, all LOD controls and picking in the unified browser path.
 const interactions=[];for(const id of ['OHM-001','OHM-053','OHM-091','OHM-130','OHM-165','OHM-180'])for(const lod of ['LOD0','LOD1','LOD2'])interactions.push(await page.evaluate(({id,lod})=>window.componentLibraryPreview.show(id,lod,'three-quarter'),{id,lod}));
 const pick=await page.evaluate(()=>window.componentLibraryPreview.pick(.5,.5));assert.ok(pick,'central model picking survives unified registry');assert.deepEqual(errors,[]);
 const artifacts=fs.readdirSync(out).filter(f=>f.endsWith('.png')).sort().map(file=>({file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex')}));
 fs.writeFileSync(path.join(out,'capture-report.json'),JSON.stringify({...stats,interactions,pick,browser_errors:errors,browser:await browser.version(),artifacts,visual_inspection:'PENDING'},null,2)+'\n');console.log('180 LOD1 models rendered; 18 selection/LOD interactions; picking passed; no browser errors');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
