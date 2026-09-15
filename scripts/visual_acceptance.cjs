/* Real-browser visual/interaction acceptance. No generated concept images.
 * Set OHMNI_PLAYWRIGHT_MODULE to an installed Playwright module if not local.
 * node scripts/visual_acceptance.cjs http://127.0.0.1:8767 out/visual-reference
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:8767';
const output = path.resolve(process.argv[3] || 'out/visual-reference');
const screenshots = path.join(output, 'screenshots'); fs.mkdirSync(screenshots, { recursive: true });
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const sourceFile = path.resolve('apps/web/reference-board.json');

(async () => {
    const sourceBefore = digest(sourceFile), errors = [], evidence = {};
    const browser = await chromium.launch({ headless: true, channel: process.env.OHMNI_BROWSER_CHANNEL || 'msedge' });
    const context = await browser.newContext({ viewport: { width: 1500, height: 853 }, deviceScaleFactor: 1 });
    // Runtime must be local/offline-capable: refuse every external network request.
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    const shot = async name => { await page.waitForTimeout(200); await page.screenshot({ path: path.join(screenshots, `${name}.png`) }); };
    const stats = selector => page.locator(selector).evaluate(canvas => {
        const gl = canvas.getContext('webgl2'), debug = gl?.getExtension('WEBGL_debug_renderer_info');
        return { ...canvas.dataset, width: canvas.width, height: canvas.height,
            gpu: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : 'unavailable' };
    });
    await page.goto(base);
    await page.locator('#open-reference-lab').click();
    await page.locator('#lab-canvas[data-renderer="three"]').waitFor();
    await page.waitForTimeout(700); await shot('10-actual-after'); evidence.actual = await stats('#lab-canvas');
    // Render the exact artifact in a private canvas to compare static GPU pixels.
    // This has no animation or component label overlay that could mask a lost net.
    evidence.staticNetHighlight = await page.evaluate(async () => {
        const { VisualRenderer } = await import('/visual-renderer.js');
        const { actualSceneManifest } = await import('/visual-board-scene.js');
        const { board } = await (await fetch('/reference-board.json')).json();
        const renderer = new VisualRenderer(document.createElement('canvas'));
        renderer.setScene(actualSceneManifest(board));
        const camera = {yaw:.35,pitch:1.1,distance:150,focal:700,zoom:1,panX:0,panY:0};
        const capture = nets => { renderer.render(camera,{width:700,height:450},{highlight:{nets},showComponents:false}); return renderer.canvas.toDataURL(); };
        const before = capture([]), selected = capture(['SDA']), cleared = capture([]);
        renderer.dispose();
        return { changed:before !== selected, exactReset:before === cleared, source: 'SDA from actual artifact', animated:false };
    });
    assert.equal(evidence.staticNetHighlight.changed, true); assert.equal(evidence.staticNetHighlight.exactReset, true);
    for (const id of ['J1','U1','SW1','J2']) {
        await page.locator('#lab-lessons .lab-component-index summary').click();
        await page.locator(`#lab-lessons .lab-component-index [data-ref="${id}"]`).click();
        await page.locator('#lab-lessons [data-lesson-action="inspect"]').click();
        await page.waitForTimeout(700); await shot(`actual-${id}-macro`);
        if (id === 'U1') {
            await page.locator('#lab-lessons [data-net="SDA"]').click();
            await shot('13-actual-sda-highlight');
        }
    }
    await page.getByRole('button', { name: 'Underside', exact: true }).click();
    await page.waitForTimeout(700); await shot('11-actual-underside');
    await page.getByRole('button', { name: 'Solder mask', exact: true }).click();
    await shot('12-actual-copper-layer');
    await page.locator('#close-circuit-lab').click();
    await page.locator('#open-sample-board').click();
    await page.locator('#visual-explorer canvas[data-renderer="three"]').waitFor();
    await shot('20-dense-sample'); evidence.sample = await stats('#visual-explorer canvas[data-renderer]');
    assert.equal(await page.locator('.visual-list button').count(), 124);
    assert.match(await page.locator('.visual-status').innerText(), /not an electrically verified design/);
    assert.equal(await page.locator('.app-layout').evaluate(node => node.inert), true);
    assert.equal(await page.locator('#visual-explorer a[href*="artifacts"],#visual-explorer a[download]').count(), 0);

    const select = async (id, name) => {
        await page.locator('.visual-inspector input').fill(id);
        await page.locator('.visual-list button').first().click();
        await page.waitForTimeout(700); await shot(name);
        assert.match(await page.locator('.visual-detail').innerText(), /electrical function/);
    };
    for (const [id, name] of [['IC01', '30-ic-leads'], ['H05', '31-header-contacts'], ['C15', '32-silver-can'],
        ['E03', '33-navy-capacitor'], ['P54', '34-banded-passive'], ['P13', '35-tan-passive'],
        ['L01', '36-winding'], ['J03', '37-metal-shell'], ['S08', '38-small-part-list']]) await select(id, name);
    // Clicking real rendered submeshes returns their owner; no synthetic BOM identities.
    evidence.meshOwnership = await page.evaluate(() => {
        const view = document.querySelector('#visual-explorer')._visualView;
        const object = view.renderer.owners.get('IC01'); const original = view.selected;
        view.select('IC01'); view.focus('IC01');
        return { owner: object.userData.owner, original, instanceCount: view.renderer.owners.size };
    });
    assert.equal(evidence.meshOwnership.instanceCount, 124);
    await page.getByRole('button', { name: 'Reset camera', exact: true }).click(); await page.waitForTimeout(700);
    const positions = () => page.evaluate(() => [...document.querySelector('#visual-explorer')._visualView.renderer.owners].map(([id, object]) => [id, ...object.position.toArray()]));
    const beforeExplode = await positions();
    await page.getByRole('button', { name: 'Explode', exact: true }).click(); assert.notDeepEqual(await positions(), beforeExplode);
    await shot('39-exploded');
    await page.getByRole('button', { name: 'Explode', exact: true }).click(); assert.deepEqual(await positions(), beforeExplode);
    await page.getByRole('button', { name: 'Edge view', exact: true }).click(); await shot('40-board-edge-holes');
    await page.getByRole('button', { name: 'Underside', exact: true }).click(); await page.waitForTimeout(700); await shot('41-sample-underside');
    await page.getByRole('button', { name: 'Asset library', exact: true }).click();
    assert.equal(await page.locator('.visual-family-tile').count(), 18); await shot('42-asset-library');
    await page.locator('.visual-library').screenshot({ path: path.join(screenshots, '43-complete-library.png') });
    await page.getByRole('button', { name: 'Return to board', exact: true }).click();
    // Every family gets an actual browser macro, including uncertain patches.
    const specimens = await page.evaluate(() => {
        const m = document.querySelector('#visual-explorer')._visualView.renderer.manifest;
        return [...new Map(m.instances.map(entry => [entry.family, entry.id])).entries()];
    });
    for (const [family, id] of specimens) await select(id, `family-${family}`);
    await page.getByRole('button', { name: 'Asset library', exact: true }).click();
    await page.getByRole('button', { name: 'Unresolved small-detail region', exact: true }).click();
    await page.waitForTimeout(700); await shot('family-unresolved_patch');
    assert.match(await page.locator('.visual-detail').innerText(), /not a component/);
    assert.match(await page.locator('.visual-detail').getAttribute('data-detail-id'), /^X/);
    assert.equal(await page.evaluate(() => document.querySelector('#visual-explorer')._visualView.selected), null);
    assert.equal(await page.evaluate(() => document.querySelector('#visual-explorer')._visualView.renderer.owners.size), 124);
    evidence.familyCloseups = specimens.length + 1;
    assert.equal(evidence.familyCloseups, 18);

    await page.getByRole('button', { name: 'Reset camera', exact: true }).click(); await page.waitForTimeout(700);
    evidence.performance = await page.evaluate(async () => {
        const view = document.querySelector('#visual-explorer')._visualView;
        const intervals = [], cpu = []; let previous;
        for (let i = 0; i < 90; i++) {
            const now = await new Promise(requestAnimationFrame); if (previous) intervals.push(now - previous); previous = now;
            view.camera.yaw += .008; const start = performance.now(); view.render(); cpu.push(performance.now() - start);
        }
        const sorted = values => values.slice().sort((a,b) => a-b), quantile = (values, p) => sorted(values)[Math.floor((values.length-1)*p)];
        return { frames: 90, rafMedianMs: quantile(intervals,.5), rafP95Ms: quantile(intervals,.95),
            cpuMedianMs: quantile(cpu,.5), cpuP95Ms: quantile(cpu,.95), gpuTimeMeasured: false };
    });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('button', { name: 'Reset camera', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#visual-explorer').evaluate(node => { node.scrollTop = 0; });
    await shot('50-compact-reduced-motion');
    assert.equal(await page.evaluate(() => document.querySelector('#visual-explorer')._visualView.reducedMotion), true);
    assert.equal(await page.evaluate(() => document.querySelector('#visual-explorer').scrollWidth > innerWidth), false);
    await page.setViewportSize({ width: 1500, height: 853 });
    // Real context-loss fallback, not a mocked renderer status.
    await page.evaluate(() => document.querySelector('#visual-explorer canvas[data-renderer]').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
    await page.locator('#visual-explorer canvas[data-renderer="canvas"]').waitFor();
    await shot('51-context-loss-fallback');
    await page.locator('.visual-inspector input').fill('P54'); await page.locator('.visual-list button').first().click();
    assert.match(await page.locator('.visual-detail').innerText(), /P54/);
    await page.getByRole('button', { name: 'Close explorer', exact: true }).click();
    assert.equal(await page.locator('.app-layout').evaluate(node => node.inert), false);
    await page.locator('#open-reference-lab').click();
    assert.equal(await page.locator('#lab-part-count').innerText(), '29 components');
    assert.equal(digest(sourceFile), sourceBefore);
    evidence.sourcePreviewSha256 = sourceBefore; evidence.browser = await browser.version(); evidence.errors = errors;
    const runtime = ['visual-assets.js','visual-inventory.js','visual-renderer.js','visual-layers.js','visual-board-scene.js','visual-explorer.js','visual-version.js'];
    evidence.transfer = Object.fromEntries([...runtime,'vendor/three.module.js','vendor/three.core.min.js'].map(file => {
        const data = fs.readFileSync(path.join('apps/web',file)); return [file,{ bytes:data.length,gzipBytes:zlib.gzipSync(data).length }];
    }));
    fs.writeFileSync(path.join(output, 'browser-evidence.json'), JSON.stringify(evidence,null,2));
    await browser.close(); assert.deepEqual(errors, []); console.log(JSON.stringify(evidence, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
