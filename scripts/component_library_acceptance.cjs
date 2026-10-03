/* Capture actual locally rendered geometry. No network research or concept art.
 * OHMNI_PLAYWRIGHT_MODULE may name an installed Playwright module.
 * node scripts/component_library_acceptance.cjs http://127.0.0.1:8773
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:8773';
const stage5 = process.argv.includes('--stage5');
const stage4 = process.argv.includes('--stage4');
const stage3 = process.argv.includes('--stage3');
const stage2 = process.argv.includes('--stage2');
const count = stage5 ? 32 : stage4 ? 25 : stage3 ? 19 : stage2 ? 21 : 20;
const reviewIds = stage5 ? ['OHM-074','OHM-078','OHM-084','OHM-083','OHM-029','OHM-030','OHM-034','OHM-011','OHM-037'] : stage4 ? ['OHM-057','OHM-059','OHM-061','OHM-065','OHM-093','OHM-098','OHM-100','OHM-096','OHM-071'] : stage3 ? ['OHM-123','OHM-130','OHM-133','OHM-135','OHM-137','OHM-140'] : stage2 ? ['OHM-104','OHM-110','OHM-116','OHM-119','OHM-094','OHM-120'] : ['OHM-004','OHM-023','OHM-041'];
const output = path.resolve(process.argv[3] || 'out/component-library/stage-1');
fs.mkdirSync(output, { recursive: true });
(async () => {
    const browser = await chromium.launch({ headless: true, channel: process.env.OHMNI_BROWSER_CHANNEL || 'msedge' });
    try {
        const page = await browser.newPage({ viewport: { width: 1320, height: 1100 }, deviceScaleFactor: 1 });
        const errors = []; page.on('pageerror', e => errors.push(e.message));
        await page.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
        const response = await page.goto(`${base}/component-library/preview/index.html${stage5 ? "?stage=5" : stage4 ? "?stage=4" : stage3 ? "?stage=3" : stage2 ? "?stage=2" : ""}`);
        await page.locator('body[data-ready="true"]').waitFor();
        const report = await page.evaluate(() => ({ source_spec_sha256: window.componentLibraryPreview.source_spec_sha256,
            model_source_sha256: window.componentLibraryPreview.model_source_sha256,
            contact_sheet: window.componentLibraryPreview.sheetStats, captures: [] }));
        report.ui_version = response.headers()['x-ohmni-ui-version'];
        assert.equal(report.contact_sheet.length, count);
        for (const id of reviewIds) {
            for (const view of ['top', 'underside', 'side', 'three-quarter']) {
                const stats = await page.evaluate(({ id, view }) => window.componentLibraryPreview.show(id, 'LOD1', view), { id, view });
                const name = `${id}-${view}-LOD1.png`;
                await page.locator('#review').screenshot({ path: path.join(output, name) });
                assert.ok(stats.triangles > 0); report.captures.push({ ...stats, file: name });
            }
        }
        if (stage3) {
            const stats = await page.evaluate(() => window.componentLibraryPreview.show('OHM-130', 'LOD1', 'underside', {terminal_pullback:0.05}));
            const name = 'OHM-130-underside-LOD1-pullback-demo.png';
            await page.locator('#review').screenshot({path:path.join(output,name)});
            report.captures.push({...stats,file:name});
            assert.ok(report.contact_sheet.every(s=>s.draw_calls<=8));
        }
        if (stage5) {
            for(const [id,lod,view,options,label] of [['OHM-074','LOD2','three-quarter',{lens:'clear',led_color:'#2868E8'},'clear'],['OHM-031','LOD1','side',{},'4mm-tail'],['OHM-086','LOD1','top',{},'hex'],['OHM-085','LOD1','underside',{},'pads']]) {
                const stats=await page.evaluate(({id,lod,view,options})=>window.componentLibraryPreview.show(id,lod,view,options),{id,lod,view,options});
                const name=`${id}-${view}-${lod}-${label}.png`;await page.locator('#review').screenshot({path:path.join(output,name)});report.captures.push({...stats,file:name});
            }
            await page.evaluate(()=>window.componentLibraryPreview.show('OHM-074','LOD1','three-quarter',{lens:'clear'}));
            assert.equal((await page.evaluate(()=>window.componentLibraryPreview.pick(.5,.5))).ref,'OHM-074');
            await page.selectOption('#lens','diffused');await page.locator('#led-color').fill('#2868e8');await page.locator('#led-color').dispatchEvent('change');
            assert.equal(await page.locator('#led-color').inputValue(),'#2868e8');
        }
        if (stage4) {
            for (const [id,view,options,label] of [['OHM-069','three-quarter',{bidirectional:true},'bidirectional'],['OHM-099','side',{outline:'AD'},'AD'],['OHM-099','side',{outline:'AC'},'AC'],['OHM-101','underside',{},'embedded-tab']]) {
                const stats=await page.evaluate(({id,view,options})=>window.componentLibraryPreview.show(id,'LOD1',view,options),{id,view,options});
                const name=`${id}-${view}-LOD1-${label}.png`;
                await page.locator('#review').screenshot({path:path.join(output,name)});report.captures.push({...stats,file:name});
            }
        }
        await page.locator('#comparison').screenshot({ path: path.join(output, stage5 ? 'stage5-same-scale-LOD1.png' : stage4 ? 'stage4-same-scale-LOD1.png' : stage3 ? 'stage3-same-scale-LOD1.png' : stage2 ? 'stage2-same-scale-LOD1.png' : '0603-same-scale-LOD1.png') });
        await page.locator('#sheet').screenshot({ path: path.join(output, `all-${count}-contact-sheet-LOD1.png`) });
        // Exercise explicit LOD, selection, material distinction and repeated scene disposal.
        await page.selectOption('#component', stage5 ? 'OHM-075' : stage4 ? 'OHM-071' : stage3 ? 'OHM-134' : stage2 ? 'OHM-119' : 'OHM-014');
        await page.selectOption('#lod', 'LOD2');
        assert.match(await page.locator('#status').innerText(), /PROVISIONAL/);
        await page.selectOption('#component', stage5 ? 'OHM-084' : stage4 ? 'OHM-093' : stage3 ? 'OHM-135' : stage2 ? 'OHM-108' : 'OHM-043');
        await page.locator('#review summary').click();
        assert.match(await page.locator('#notes').innerText(), stage5 ? /pin1.*not confirmed/ : /UNCERTAIN/);
        await page.locator('#review summary').click();
        await page.selectOption('#lod', 'LOD0');
        await page.selectOption('#lod', 'LOD1');
        for (let i = 0; i < 10; i++) await page.evaluate(id => window.componentLibraryPreview.show(id, 'LOD2', 'three-quarter'), reviewIds[0]);
        assert.deepEqual(errors, []);
        report.browser = await browser.version(); report.browser_errors = errors;
        report.visual_inspection = 'PENDING human/agent image inspection; capture success is not visual approval';
        report.artifacts = fs.readdirSync(output).filter(file => file.endsWith('.png')).sort().map(file => ({ file,
            sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(output, file))).digest('hex') }));
        fs.writeFileSync(path.join(output, 'capture-report.json'), JSON.stringify(report, null, 2) + '\n');
        console.log(`Captured ${report.artifacts.length} PNGs; ${count} entries; no browser errors.`);
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
