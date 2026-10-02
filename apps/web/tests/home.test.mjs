import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { HOME_PARTS, homeRoute, homeSpecimen, initializeHome } from '../home.js';
import { componentLesson } from '../component-stories.js';
import { ASSET_REGISTRY } from '../visual-assets.js';

const item = (eligibility = 'LEARN_ONLY') => ({ part_id: 'ESP32-WROOM-32E', variants: [{
    eligibility: { eligibility }, visual_status: 'ILLUSTRATIVE', record: { package_variant: 'Module-SMD-38',
        visual: { family: 'esp32_module', asset: { id: ASSET_REGISTRY.esp32_module.modelAssetId, sha256: 'a'.repeat(64) },
            representation_grade: 'ILLUSTRATIVE_FAMILY', units: 'mm', up_axis: 'z', contact_plane_nm: 0,
            footprint: null, dimensions: { basis: 'ARTISTIC_SAMPLE', width_nm: 19500000, depth_nm: 20500000, height_nm: 2800000 } } },
}] });

test('home is a navigation surface, and sample links retain an explicit workspace route', () => {
    assert.equal(homeRoute(''), 'home'); assert.equal(homeRoute('#home'), 'home');
    assert.equal(homeRoute('#workspace'), 'workspace'); assert.equal(homeRoute('#sample-board'), 'workspace');
    assert.equal(homeRoute('#visual-proof'), 'workspace');
});

test('specimens fail closed for missing, restricted and unbound catalog models', () => {
    const valid = homeSpecimen({items:[item()]}, 'ESP32-WROOM-32E');
    assert.equal(valid.manifest.provenance, 'ILLUSTRATIVE_ONLY');
    assert.deepEqual(valid.manifest.pads, []); assert.deepEqual(valid.manifest.tracks, []);
    assert.equal(homeSpecimen(null, 'ESP32-WROOM-32E'), null);
    assert.equal(homeSpecimen({items: []}, 'invented'), null);
    for (const state of ['QUARANTINED', 'REVOKED', 'UNSUPPORTED', 'DESIGN_ELIGIBLE'])
        assert.equal(homeSpecimen({items: [item(state)]}, 'ESP32-WROOM-32E'), null);
    const invalid = item(); invalid.variants[0].record.visual.footprint = {id: 'claimed-footprint'};
    assert.equal(homeSpecimen({items: [invalid]}, 'ESP32-WROOM-32E'), null);
});

test('human-readable lessons retain explicit catalog identities and do not invent unknown facts', () => {
    for (const part of HOME_PARTS) assert.ok(componentLesson(part.id));
    assert.match(componentLesson('GENERIC_RESISTOR')[1], /Limits current/);
    assert.equal(componentLesson('unidentified-image-body'), null);
});

function harness() {
    const nodes = new Map(), listeners = {}, motion = { matches: false, addEventListener(type, fn) { this.change = fn; } };
    function node(selector) {
        if (!nodes.has(selector)) nodes.set(selector, { hidden: false, textContent: '', style: {}, dataset: {}, attrs: {}, handlers: {},
            setAttribute(k,v) { this.attrs[k] = v; }, focus() { this.focused = true; },
            addEventListener(k,fn) { this.handlers[k] = fn; } });
        return nodes.get(selector);
    }
    const parts = HOME_PARTS.map((_,i) => node(`part${i}`)), start = node('start');
    const home = node('#home'); home.querySelector = node;
    home.querySelectorAll = selector => selector === '[data-home-part]' ? parts : [start];
    const originals = Object.fromEntries(['document','window','location','history','matchMedia'].map(k=>[k,globalThis[k]]));
    Object.assign(globalThis, {
        document: { querySelector: node, title: '' },
        window: { addEventListener: (k,fn) => {listeners[k]=fn;}, scrollTo() {} },
        location: { hash: '' }, history: { pushState: (_,__,hash) => {globalThis.location.hash=hash;} },
        matchMedia: () => motion,
    });
    return { node, parts, start, listeners, motion, restore() { for (const [k,v] of Object.entries(originals)) {
        if (v === undefined) delete globalThis[k]; else globalThis[k]=v;
    } } };
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('failed library has local retry; navigation alone never starts a new project', async () => {
    const h = harness(); let attempts=0, starts=0;
    try {
        initializeHome({ onStart: () => starts++, readLibrary: async () => { attempts++; throw new Error('offline'); } });
        await settle();
        assert.match(h.node('#home-model-status').textContent, /could not load/);
        assert.equal(h.node('#home-model-retry').hidden, false);
        h.node('#home-model-retry').handlers.click(); await settle(); assert.equal(attempts,2);
        location.hash='#workspace'; h.listeners.hashchange();
        assert.equal(h.node('#home').hidden,true); assert.equal(starts,0);
        location.hash='#home'; h.listeners.hashchange(); await settle(); assert.equal(starts,0);
        h.start.handlers.click({preventDefault(){}}); assert.equal(starts,1);
        assert.equal(location.hash,'#workspace');
    } finally { h.restore(); }
});

test('leaving home aborts pending load and ignores a late successful response', async () => {
    const h = harness(); let resolve, signal, renders=0;
    try {
        initializeHome({ readLibrary: (_, s) => { signal=s; return new Promise(r=>{resolve=r;}); }, createView:()=>{renders++;} });
        location.hash='#workspace'; h.listeners.hashchange(); assert.equal(signal.aborted,true);
        resolve({items:[item()]}); await settle();
        assert.equal(renders,0); assert.equal(h.node('#home').hidden,true);
    } finally { h.restore(); }
});

test('missing models leave the lesson usable without enabling graphics controls', async () => {
    const h = harness();
    try {
        initializeHome({readLibrary: async()=>({items:[]})}); await settle();
        assert.match(h.node('#home-model-status').textContent,/No model/);
        assert.equal(h.node('#home-spin').disabled,true);
        h.parts[1].handlers.click(); assert.equal(h.node('#home-part-title').textContent,'The sensor');
    } finally { h.restore(); }
});

test('rotation respects reduced motion, interaction is opt-in and leaving disposes the view', async () => {
    const h = harness(); let disposed = 0, renders = 0;
    const view = { canvas: h.node('#home-model-canvas'), options: {}, renderer: {scene:{background:{set(){}}}},
        setBoard() { renders++; }, setOptions(options) {Object.assign(this.options,options);}, focus(){}, dispose(){disposed++;} };
    try {
        initializeHome({readLibrary:async()=>({items:[item()]}), createView:()=>view}); await settle();
        assert.equal(renders,1); assert.equal(view.options.autoRotate,false);
        h.node('#home-spin').handlers.click(); assert.equal(view.options.autoRotate,true);
        h.motion.matches=true; h.motion.change(); assert.equal(view.options.autoRotate,false);
        assert.equal(h.node('#home-spin').disabled,true);
        h.node('#home-orbit').handlers.click();
        assert.equal(view.canvas.tabIndex,0); assert.equal(view.canvas.style.touchAction,'none');
        h.node('#home-orbit').handlers.click();
        assert.equal(view.canvas.tabIndex,-1); assert.equal(view.canvas.style.touchAction,'pan-y');
        location.hash='#workspace'; h.listeners.hashchange(); assert.equal(disposed,1);
    } finally {h.restore();}
});

test('renderer failure preserves text and shows a device fallback without enabling orbit', async () => {
    const h = harness();
    try {
        initializeHome({readLibrary:async()=>({items:[item()]}), createView:()=>{throw new Error('WebGL unavailable');}});
        await settle();
        assert.match(h.node('#home-model-status').textContent,/3D is unavailable/);
        assert.equal(h.node('#home-model-placeholder').hidden,false);
        assert.equal(h.node('#home-orbit').disabled,true);
        assert.equal(h.node('#home-part-title').textContent,'The processor');
    } finally {h.restore();}
});

test('markup keeps one dominant project action on home, named models and truthful limits', () => {
    const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
    const landing = html.slice(html.indexOf('<section id="home"'),html.indexOf('<div class="app-layout"'));
    assert.equal((landing.match(/data-home-start/g)||[]).length,1);
    assert.equal((landing.match(/data-home-part=/g)||[]).length,3);
    assert.match(landing,/have not been bench-tested/);
    assert.match(html,/<details class="workspace-examples" id="saved-example">/);
    assert.doesNotMatch(html,/id="home-atlas-canvas"/);
    assert.match(html,/Unsaved changes are lost/);
});
