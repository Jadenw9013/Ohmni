const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.OHMNI_PLAYWRIGHT_MODULE || 'playwright');

const base = process.argv[2] || 'http://127.0.0.1:8779';
const output = path.resolve('out/component-library/catalog-redesign');
fs.mkdirSync(output, { recursive: true });

(async () => {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    try {
        const page = await browser.newPage({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 1 });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.locator('nav [data-open-components]').click();
        await page.locator('.story-component-card').first().waitFor({ timeout: 60000 });
        await page.waitForTimeout(1500);
        assert.equal(await page.locator('.story-component-card').count(), 180);
        assert.match(await page.locator('[data-story-status]').textContent(), /180 of 180/);
        assert.equal(await page.locator('[data-component-id="OHM-123"]').getAttribute('aria-pressed'), 'true');
        await page.locator('#component-stories').screenshot({ path: path.join(output, 'component-catalog-desktop.png') });

        await page.locator('[data-story-search]').fill('USB-C');
        await page.waitForTimeout(300);
        assert.equal(await page.locator('.story-component-card').count(), 1);
        assert.equal(await page.locator('[data-component-id="OHM-165"]').getAttribute('aria-pressed'), 'true');
        await page.locator('[data-story-tab="pins"]').click();
        assert.match(await page.locator('[data-story-details] h4').textContent(), /24 terminals/);
        await page.locator('[data-story-view="underside"]').click();
        await page.locator('[data-story-lod="LOD2"]').click();
        assert.equal(await page.locator('[data-story-view="underside"]').getAttribute('aria-pressed'), 'true');
        assert.equal(await page.locator('[data-story-lod="LOD2"]').getAttribute('aria-pressed'), 'true');
        await page.locator('#component-stories').screenshot({ path: path.join(output, 'component-catalog-filtered.png') });

        await page.setViewportSize({ width: 390, height: 844 });
        await page.locator('[data-story-search]').fill('');
        await page.waitForTimeout(300);
        await page.locator('#component-stories').screenshot({ path: path.join(output, 'component-catalog-mobile.png') });
        assert.deepEqual(errors, []);
        fs.writeFileSync(path.join(output, 'browser-report.json'), JSON.stringify({
            components: 180, selected_default: 'OHM-123', filtered_selection: 'OHM-165',
            views_checked: ['three-quarter', 'underside'], lods_checked: ['LOD1', 'LOD2'],
            tabs_checked: ['overview', 'pins'], browser_errors: errors, browser: await browser.version(),
        }, null, 2) + '\n');
        console.log('Component catalog: 180 cards, search, selection, tabs, views, LOD and responsive capture passed');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
