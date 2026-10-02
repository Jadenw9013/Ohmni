import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { parseLibraryPage, readComponentLibrary, storyManifest, storyQueue, storySwipe } from '../component-stories.js';

const identity = { api_version: 2, server_instance_id: 'a'.repeat(16), ui_version: 'b'.repeat(64) };
const ref = id => ({ id, sha256: 'c'.repeat(64) });
const item = (id = 'GENERIC_RESISTOR') => ({ part_id: id, description: `About ${id}`, variants: [{
    record: { catalog_part: ref(id), display_name: id, category: 'resistor', package_variant: '0805',
        evidence_summary: ['Catalog-reported; not reverified here.'], visual: null },
    eligibility: { eligibility: 'LEARN_ONLY', reason: 'Admission pending.' },
    visual_status: 'MISSING_MODEL', visual_note: 'No model available.',
}] });
const page = () => ({ ...identity, snapshot_sha256: 'd'.repeat(64), offset: 0, limit: 50,
    total: 1, next_offset: null, items: [item()] });

test('story ordering and search are stable and preserve backend facts', () => {
    const items = [item('BME280'), item(), item('GENERIC_CAPACITOR')];
    const before = structuredClone(items);
    assert.deepEqual(storyQueue(items).map(i => i.part_id), ['GENERIC_RESISTOR', 'GENERIC_CAPACITOR', 'BME280']);
    assert.deepEqual(storyQueue(items, ' bme ').map(i => i.part_id), ['BME280']);
    assert.equal(storyQueue(items, '0805').length, 3);
    assert.deepEqual(items, before);
});

test('stale identities, invented eligibility and broken pagination fail closed', () => {
    assert.equal(parseLibraryPage(page(), identity, 0).items.length, 1);
    for (const patch of [{ server_instance_id: 'e'.repeat(16) }, { snapshot_sha256: 'wrong' },
        { offset: 1 }, { total: 501 }, { next_offset: 0 }, { total: 2 }, { items: null }, { limit: 100 }]) {
        assert.throws(() => parseLibraryPage({ ...page(), ...patch }, identity, 0));
    }
    assert.throws(() => parseLibraryPage(page(), identity, 0, 'e'.repeat(64)));
    const forged = page(); forged.items[0].variants[0].eligibility.eligibility = 'DESIGN_ELIGIBLE';
    assert.throws(() => parseLibraryPage(forged, identity, 0));
    const wrongPart = page(); wrongPart.items[0].variants[0].record.catalog_part.id = 'OTHER';
    assert.throws(() => parseLibraryPage(wrongPart, identity, 0));
});

test('library fetch only reads the health and component endpoints with bound identity', async () => {
    const calls = [];
    const fetcher = async (url, options) => {
        calls.push({ url, options });
        return { ok: true, json: async () => url.endsWith('/api/health')
            ? { ...identity, status: 'ready', fixture_id: 'esp32-bme280-environmental-logger', free_text: false } : page() };
    };
    const result = await readComponentLibrary(fetcher);
    assert.equal(result.items[0].part_id, 'GENERIC_RESISTOR');
    assert.equal(calls.length, 2);
    assert.ok(calls.every(c => !c.options.method || c.options.method === 'GET'));
    assert.equal(calls[1].options.headers['X-Ohmni-UI-Version'], identity.ui_version);
    assert.ok(calls[1].url.startsWith('/api/components?'));
});

test('model mismatch falls back without creating footprints or pads', () => {
    const part = item(); const variant = part.variants[0];
    assert.equal(storyManifest(part, variant), null);
    variant.visual_status = 'ILLUSTRATIVE';
    variant.record.visual = { asset: ref('ohmni-procedural/chip_resistor@reference-packages-v1'), family: 'chip_resistor',
        representation_grade: 'ILLUSTRATIVE_FAMILY', units: 'mm', up_axis: 'z', contact_plane_nm: 0, footprint: null,
        dimensions: { width_nm: 2e6, depth_nm: 1e6, height_nm: 5e5, basis: 'ARTISTIC_SAMPLE' } };
    const manifest = storyManifest(part, variant);
    assert.equal(manifest.provenance, 'ILLUSTRATIVE_ONLY');
    assert.deepEqual(manifest.pads, []); assert.deepEqual(manifest.tracks, []);
    assert.equal(manifest.instances[0].options.actual, undefined);
    for (const patch of [{ family: 'invented' }, { asset: ref('other') }, { footprint: ref('real-looking') },
        { representation_grade: 'SOURCE_VERIFIED' }, { dimensions: { ...variant.record.visual.dimensions, width_nm: NaN } }]) {
        assert.equal(storyManifest(part, { ...variant, record: { ...variant.record, visual: { ...variant.record.visual, ...patch } } }), null);
    }
});

test('story markup exposes a modal, labelled controls, status, and persistent entry points', () => {
    const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
    assert.match(html, /<dialog id="component-stories"[^>]*aria-labelledby="component-stories-title"/);
    assert.ok((html.match(/data-open-components/g) ?? []).length >= 2);
    for (const query of ['BME280', 'ESP32', 'USB_C']) assert.ok(html.includes(`data-component-query="${query}"`));
    assert.match(html, /role="status" aria-live="polite" data-story-status/);
    assert.match(html, /aria-label="Component stories" data-story-progress/);
    assert.match(html, /<label class="story-search">Find a component<input/);
});

test('touch story gestures separate horizontal swipes from scroll, mouse orbit and cancellation', () => {
    const start = {id: 3, x: 100, y: 100};
    const end = {pointerId: 3, pointerType: 'touch', clientX: 0, clientY: 110};
    assert.equal(storySwipe(start, end), 1);
    assert.equal(storySwipe(start, {...end, clientX: 200}), -1);
    assert.equal(storySwipe(start, {...end, clientY: 200}), 0);
    assert.equal(storySwipe(start, {...end, clientX: 90}), 0);
    assert.equal(storySwipe(start, {...end, pointerType: 'mouse'}), 0);
    assert.equal(storySwipe(start, {...end, pointerId: 4}), 0);
    assert.equal(storySwipe(null, end), 0);
});
