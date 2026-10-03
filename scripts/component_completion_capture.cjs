const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),crypto=require('crypto');
const {chromium}=require(process.env.OHMNI_PLAYWRIGHT_MODULE||'playwright');
const base=process.argv[2]||'http://127.0.0.1:8778',group=process.argv[3]||'a';
const output=path.resolve(`out/component-library/completion/group-${group}`);
const review={a:['OHM-151','OHM-161'],b:[],c:['OHM-165','OHM-169','OHM-179'],d:['OHM-053'],e:['OHM-091']};
const counts={a:12,b:9,c:19,d:11,e:12};
fs.mkdirSync(output,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1320,height:1100},deviceScaleFactor:1}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 await page.goto(`${base}/component-library/preview/index.html?group=${group}`);await page.locator('body[data-ready="true"]').waitFor();
 const report=await page.evaluate(()=>({source_spec_sha256:window.componentLibraryPreview.source_spec_sha256,model_source_sha256:window.componentLibraryPreview.model_source_sha256,contact_sheet:window.componentLibraryPreview.sheetStats,captures:[]}));
 assert.equal(report.contact_sheet.length,counts[group]);
 for(const id of review[group])for(const view of ['top','underside','side','three-quarter']){
  const stats=await page.evaluate(({id,view})=>window.componentLibraryPreview.show(id,'LOD1',view),{id,view});
  const file=`${id}-${view}-LOD1.png`;await page.locator('#review').screenshot({path:path.join(output,file)});report.captures.push({...stats,file});
 }
 if(group==='a'){
  const stats=await page.evaluate(()=>window.componentLibraryPreview.show('OHM-161','LOD1','three-quarter',{assembled:false}));
  const file='OHM-161-separated-LOD1.png';await page.locator('#review').screenshot({path:path.join(output,file)});report.captures.push({...stats,file});
 }
 await page.locator('#sheet').screenshot({path:path.join(output,`all-${counts[group]}-contact-sheet-LOD1.png`)});
 assert.deepEqual(errors,[]);report.browser_errors=errors;report.browser=await browser.version();report.visual_inspection='PENDING';
 report.artifacts=fs.readdirSync(output).filter(f=>f.endsWith('.png')).sort().map(file=>({file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(output,file))).digest('hex')}));
 fs.writeFileSync(path.join(output,'capture-report.json'),JSON.stringify(report,null,2)+'\n');console.log(`${report.artifacts.length} Group ${group} renders, no browser errors`);
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
