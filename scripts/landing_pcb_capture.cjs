/* P1 visual evidence: actual local WebGL scene, not generated concept art.
 * OHMNI_PLAYWRIGHT_MODULE may select an existing local Playwright install.
 * node scripts/landing_pcb_capture.cjs http://127.0.0.1:8780 out/landing-pcb/p1
 */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:8780';
const output = path.resolve(process.argv[3] || 'out/landing-pcb/p1');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
fs.mkdirSync(output, { recursive: true });

(async () => {
    const sourceHash = hash('apps/web/reference-board.json');
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(`${base}/landing-pcb-prototype/`);
    await page.waitForFunction(() => ['ready', 'unavailable'].includes(document.body.dataset.state));
    const state = await page.locator('body').getAttribute('data-state');
    assert.equal(state, 'ready', JSON.stringify({ errors, failure: await page.locator('body').getAttribute('data-failure') }));
    const shot = async name => {
        await page.evaluate(() => document.fonts.ready);
        await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
    };
    await shot('01-overview-desktop');
    const evidence = { sourceSha256: sourceHash, capturedAt: new Date().toISOString(),
        prototypeOnly: true, baselineCommit: '42961353c1b6f111c8a11c82aed5620f6f31ebb0',
        overview: await page.evaluate(() => window.landingPrototype.stats()),
        browser: await browser.version() };
    evidence.gpu = await page.locator('#pcb-canvas').evaluate(canvas => {
        const gl = canvas.getContext('webgl2'), debug = gl.getExtension('WEBGL_debug_renderer_info');
        return debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : 'unavailable';
    });
    assert.equal(evidence.overview.refs.length, 29);
    await page.locator('#pcb-canvas').screenshot({ path: path.join(output, 'poster-desktop.png') });
    const video = await page.evaluate(async () => {
        const stream = document.querySelector('#pcb-canvas').captureStream(30);
        const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' });
        const chunks = [];
        recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
        const complete = new Promise(resolve => { recorder.onstop = async () => {
            const buffer = await new Blob(chunks, { type: 'video/webm' }).arrayBuffer();
            stream.getTracks().forEach(track => track.stop());
            resolve(Array.from(new Uint8Array(buffer)));
        }; });
        recorder.start(); window.landingPrototype.replay();
        setTimeout(() => recorder.stop(), 1600);
        return complete;
    });
    fs.writeFileSync(path.join(output, 'reveal.webm'), Buffer.from(video));
    for (const pose of ['top', 'side', 'underside']) {
        await page.evaluate(name => window.landingPrototype.pose(name), pose);
        await shot(`02-${pose}`);
    }
    for (const ref of ['U1', 'U3', 'J1']) {
        await page.evaluate(ref => window.landingPrototype.closeUp(ref), ref);
        await shot(`03-closeup-${ref}`);
    }
    await page.evaluate(() => window.landingPrototype.closeUp('J1', true));
    await shot('03-closeup-J1-frontal');
    evidence.bindings = await page.evaluate(() => window.landingPrototype.inventory);
    fs.writeFileSync(path.join(output, 'bindings.json'), JSON.stringify(evidence.bindings, null, 2));
    delete evidence.bindings;
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.landingPrototype.pose());
    await shot('04-mobile-390');
    await page.locator('#pcb-canvas').screenshot({ path: path.join(output, 'poster-mobile.png') });
    for (const width of [320, 768, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        await page.evaluate(() => window.landingPrototype.pose());
        await shot(`05-width-${width}`);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow at ${width}`);
    }
    await page.goto(`${base}/landing-pcb-prototype/?baseline=1`);
    await page.waitForFunction(() => document.body.dataset.state === 'ready');
    evidence.baseline = await page.evaluate(() => window.landingPrototype.stats());
    await shot('06-existing-renderer-baseline');
    await page.goto(`${base}/landing-pcb-prototype/?no-finish=1`);
    await page.waitForFunction(() => document.body.dataset.state === 'ready');
    await shot('07-overview-no-finish');
    await page.evaluate(() => window.landingPrototype.closeUp('U1'));
    await shot('07-closeup-U1-no-finish');
    assert.equal(hash('apps/web/reference-board.json'), sourceHash, 'Saved source changed during capture');
    evidence.errors = errors;
    fs.writeFileSync(path.join(output, 'capture.json'), JSON.stringify(evidence, null, 2));
    await browser.close();
    console.log(JSON.stringify({ output, overview: evidence.overview, gpu: evidence.gpu, errors }, null, 2));
    assert.deepEqual(errors, []);
})().catch(error => { console.error(error); process.exit(1); });
