/* Homepage discovery and repeated keyboard entry in a real browser.
 * node scripts/homepage_acceptance.cjs http://127.0.0.1:8767 out/visual-reference
 * Set OHMNI_PLAYWRIGHT_MODULE if Playwright is installed outside this project.
 */
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const base = process.argv[2] || 'http://127.0.0.1:8767';
const output = path.resolve(process.argv[3] || 'out/visual-reference');
const screenshots = path.join(output, 'screenshots');
fs.mkdirSync(screenshots, { recursive: true });

(async () => {
    const browser = await chromium.launch({ headless: true, channel: process.env.OHMNI_BROWSER_CHANNEL || 'msedge' });
    try {
        const context = await browser.newContext({ viewport: { width: 1500, height: 950 } });
        await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin
            ? route.continue() : route.abort());
        const page = await context.newPage(), errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(base);
        await page.locator('#home-atlas-canvas[data-renderer="three"]').waitFor();
        assert.match(await page.locator('#home-atlas-count').innerText(), /124.*18/);
        await page.screenshot({ path: path.join(screenshots, '60-homepage-dense-entry.png') });
        await page.locator('#open-sample-board').click();
        assert.equal(await page.locator('.visual-list button').count(), 124);
        assert.match(await page.locator('.visual-status').innerText(), /not an electrically verified design/);
        await page.getByRole('button', { name: 'Close explorer', exact: true }).click();

        await page.locator('#home-atlas-canvas').focus();
        for (let attempt = 0; attempt < 3; attempt++) {
            await page.keyboard.press('Enter');
            await page.locator('#visual-explorer').waitFor({ state: 'visible' });
            assert.match(await page.locator('.visual-detail').innerText(), /IC01/);
            await page.keyboard.press('Escape');
            assert.equal(await page.locator('#home-atlas-canvas').evaluate(node => document.activeElement === node), true);
        }
        await page.locator('.sidebar-dense-board').click();
        assert.equal(await page.locator('#visual-explorer').isVisible(), true);
        await page.getByRole('button', { name: 'Close explorer', exact: true }).click();
        await page.locator('#open-reference-lab').click();
        assert.equal(await page.locator('#lab-part-count').innerText(), '29 components');
        await page.locator('#close-circuit-lab').click();
        for (const width of [849, 390]) {
            await page.setViewportSize({ width, height: 950 });
            await page.evaluate(() => scrollTo(0, 0));
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
            await page.screenshot({ path: path.join(screenshots, `61-homepage-${width}.png`), fullPage: true });
            await page.locator('#open-sample-board').click();
            assert.equal(await page.locator('.visual-list button').count(), 124);
            await page.getByRole('button', { name: 'Close explorer', exact: true }).click();
        }
        assert.deepEqual(errors, []);
        fs.writeFileSync(path.join(output, 'homepage-browser-check.json'), JSON.stringify({
            result: 'PASS', errors, viewports: [1500, 849, 390],
            checks: ['Homepage live 124-body preview with 18 families', 'Prominent CTA',
                'Repeated preview keyboard entry opens matching inspector', 'Persistent sidebar entry',
                'Escape closes and restores preview focus', 'Actual 29-part lab remains accessible',
                'No horizontal overflow', 'Local-only network'],
        }, null, 2));
        console.log('Homepage browser checks PASS');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
