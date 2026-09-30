// Read-only learning UI. This module has no project, admission or export writes.
import { API_BASE, fetchHealth, pollHeaders, sameIdentity } from './client-contract.js';
import { ASSET_REGISTRY } from './visual-assets.js';
import { BoardView } from './board-view.js';
import { visualBoard } from './visual-explorer.js';

const START_HERE = ['GENERIC_RESISTOR', 'GENERIC_CAPACITOR', 'GENERIC_LED_GREEN',
    'GENERIC_MOMENTARY_BUTTON', 'HEADER_1X6_254', 'USB_C_RECEPTACLE_16P',
    'AP2112K-3.3TRG1', 'MCP1700T-3302E-TT', 'ESP32-WROOM-32E', 'BME280', 'TMP102AIDRLR', '25LC256-I/SN'];
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const text = (value, max = 500) => typeof value === 'string' && value.length > 0 && value.length <= max;
const invalid = () => { throw new Error('Component library unavailable'); };
const displayName = record => record.display_name.startsWith('GENERIC_')
    ? record.display_name.replace('GENERIC_', '').toLowerCase().replaceAll('_', ' ').replace(/^./, c => c.toUpperCase())
    : record.display_name;

export function storyQueue(items, query = '') {
    const rank = id => START_HERE.includes(id) ? START_HERE.indexOf(id) : START_HERE.length;
    const needle = query.trim().toLowerCase();
    return items.filter(item => [item.part_id, item.description, ...item.variants.map(v =>
        `${v.record.category} ${v.record.package_variant}`)].join(' ').toLowerCase().includes(needle))
        .slice().sort((a, b) => rank(a.part_id) - rank(b.part_id) || a.part_id.localeCompare(b.part_id, 'en'));
}

export function storySwipe(start, end) {
    if (!start || start.id !== end.pointerId || end.pointerType !== 'touch') return 0;
    const dx = end.clientX - start.x, dy = end.clientY - start.y;
    return Math.abs(dx) > 65 && Math.abs(dy) < 40 ? (dx < 0 ? 1 : -1) : 0;
}

export function parseLibraryPage(page, identity, offset, snapshot = null) {
    if (!page || !sameIdentity(page, identity) || !hash(page.snapshot_sha256)
        || (snapshot !== null && snapshot !== page.snapshot_sha256)
        || page.offset !== offset || page.limit !== 50 || !Number.isInteger(page.total)
        || page.total < 0 || page.total > 500 || !Array.isArray(page.items) || page.items.length > 50
        || page.total < offset + page.items.length
        || (page.next_offset !== null && (page.next_offset !== offset + page.items.length
            || !page.items.length || page.next_offset >= page.total))) invalid();
    if (page.next_offset === null && offset + page.items.length !== page.total) invalid();
    for (const item of page.items) {
        if (!text(item.part_id, 160) || typeof item.description !== 'string' || item.description.length > 4000
            || !Array.isArray(item.variants) || item.variants.length < 1 || item.variants.length > 40) invalid();
        for (const variant of item.variants) {
            const r = variant.record;
            if (!r || r.catalog_part?.id !== item.part_id || !hash(r.catalog_part.sha256)
                || !text(r.display_name) || !text(r.category, 160) || !text(r.package_variant)
                || !Array.isArray(r.evidence_summary) || r.evidence_summary.length > 40
                || !r.evidence_summary.length || !r.evidence_summary.every(value => text(value))
                || !['LEARN_ONLY', 'QUARANTINED', 'REVOKED', 'UNSUPPORTED'].includes(variant.eligibility?.eligibility)
                || !text(variant.eligibility.reason) || !text(variant.visual_note)
                || !['ILLUSTRATIVE', 'MISSING_MODEL'].includes(variant.visual_status)) invalid();
            if (r.visual && (!Array.isArray(r.visual.limitations) || r.visual.limitations.length > 20
                || !r.visual.limitations.every(value => text(value))
                || !['source', 'license', 'attribution'].every(key => text(r.visual.provenance?.[key])))) invalid();
        }
    }
    return structuredClone(page);
}

export async function readComponentLibrary(fetcher = globalThis.fetch, signal) {
    const boundedFetch = (url, options = {}) => fetcher(url, { ...options, signal });
    const identity = await fetchHealth(boundedFetch);
    const items = []; let offset = 0, snapshot = null, total = null;
    do {
        const query = new URLSearchParams({ limit: '50', offset: String(offset) });
        if (snapshot) query.set('snapshot', snapshot);
        const response = await boundedFetch(`${API_BASE}/api/components?${query}`, {
            headers: pollHeaders(identity), cache: 'no-store',
        });
        if (!response.ok) invalid();
        const page = parseLibraryPage(await response.json(), identity, offset, snapshot);
        if (total !== null && total !== page.total) invalid();
        total = page.total; snapshot = page.snapshot_sha256; items.push(...page.items);
        offset = page.next_offset;
    } while (offset !== null);
    if (new Set(items.map(item => item.part_id)).size !== items.length) invalid();
    return { items, snapshot, identity };
}

export function storyManifest(item, variant) {
    const visual = variant.record.visual;
    if (variant.visual_status !== 'ILLUSTRATIVE' || !visual
        || visual.representation_grade !== 'ILLUSTRATIVE_FAMILY'
        || visual.units !== 'mm' || visual.up_axis !== 'z' || visual.contact_plane_nm !== 0
        || visual.footprint !== null || !hash(visual.asset?.sha256)
        || !Object.hasOwn(ASSET_REGISTRY, visual.family)
        || visual.asset.id !== ASSET_REGISTRY[visual.family].modelAssetId) return null;
    const dims = visual.dimensions;
    if (!dims || dims.basis !== 'ARTISTIC_SAMPLE'
        || ![dims.width_nm, dims.depth_nm, dims.height_nm].every(n => Number.isInteger(n) && n > 0 && n <= 500e6)) return null;
    const width = dims.width_nm / 1e6, depth = dims.depth_nm / 1e6, height = dims.height_nm / 1e6;
    return { id: `story:${item.part_id}:${variant.record.package_variant}:${visual.asset.sha256}`,
        provenance: 'ILLUSTRATIVE_ONLY', width: Math.max(12, width * 2), depth: Math.max(12, depth * 2),
        thickness: 1.6, holes: [], pads: [], tracks: [], vias: [], silkscreen: [],
        instances: [{ id: 'specimen', name: variant.record.display_name, family: visual.family,
            x: 0, y: 0, rotation: 0, options: { width, depth, height, label: false } }] };
}

const element = (tag, value, parent) => {
    const node = document.createElement(tag); node.textContent = value; parent?.append(node); return node;
};

export function initializeComponentStories() {
    const dialog = document.querySelector('#component-stories');
    if (!dialog) return;
    let controller, view, library, queue = [], index = 0, packageIndex = 0, generation = 0;
    let opener;
    const $ = selector => dialog.querySelector(selector);
    const clearView = () => { view?.dispose(); view = null; };
    function close() { generation++; controller?.abort(); clearView(); dialog.close(); opener?.focus(); }
    function render() {
        const card = $('[data-story-details]'); card.replaceChildren();
        const stage = $('[data-story-stage]'); stage.querySelector('.story-model-note')?.remove();
        const progress = $('[data-story-progress]'); progress.replaceChildren();
        $('[data-story-prev]').disabled = index === 0 || !queue.length;
        $('[data-story-next]').disabled = index >= queue.length - 1;
        if (!queue.length) {
            clearView(); stage.replaceChildren();
            $('[data-story-status]').textContent = 'No components match. Try a part name, category or package.'; return;
        }
        const item = queue[index], variant = item.variants[packageIndex], r = variant.record;
        $('[data-story-status]').textContent = `${index + 1} of ${queue.length}: ${displayName(r)}`;
        queue.forEach((entry, i) => {
            const button = element('button', '', progress); button.type = 'button';
            button.setAttribute('aria-label', `View ${displayName(entry.variants[0].record)}, ${i + 1} of ${queue.length}`);
            if (i === index) button.setAttribute('aria-current', 'step');
            button.onclick = () => select(i);
        });
        element('h3', displayName(r), card);
        element('p', item.description, card).className = 'story-description';
        const label = element('label', 'Package ', card), choice = document.createElement('select'); label.append(choice);
        item.variants.forEach((v, i) => { const option = element('option', v.record.package_variant, choice); option.value = String(i); });
        choice.value = String(packageIndex); choice.onchange = () => { packageIndex = Number(choice.value); render(); $('[data-story-details] select').focus(); };
        element('h4', 'What we know', card);
        element('p', 'Catalog-reported information', card).className = 'story-badge';
        const evidence = element('ul', '', card);
        r.evidence_summary.forEach(value => element('li', value, evidence));
        element('h4', 'What remains unknown', card);
        element('p', variant.visual_note, card);
        element('p', 'Appearance does not verify dimensions, pad positions, connections or electrical behavior.', card);
        const action = element('button', 'Use in a project', card); action.type = 'button'; action.disabled = true;
        element('p', 'Adding parts to saved boards is not available yet. Explore the catalog here while that capability is being built.', card).className = 'story-muted';
        const source = element('details', '', card); element('summary', 'Source and model details', source);
        element('p', `Catalog revision: ${r.catalog_part.sha256}`, source);
        if (r.visual) {
            for (const value of [r.visual.provenance?.source, r.visual.provenance?.license,
                r.visual.provenance?.attribution, ...(r.visual.limitations ?? [])]) {
                if (typeof value === 'string') element('p', value, source);
            }
        }
        const manifest = storyManifest(item, variant);
        if (manifest) {
            if (!view) {
                stage.replaceChildren();
                const canvas = document.createElement('canvas'); canvas.tabIndex = 0; stage.append(canvas);
                view = new BoardView(canvas); view.options.showLabels = false; view.options.showCopper = false;
            }
            view.canvas.setAttribute('aria-label', `Illustration of ${displayName(r)}. Drag or use arrow keys to orbit; plus and minus zoom.`);
            view.setBoard(visualBoard(manifest)); view.setOptions({ isolate: 'specimen', hideBoard: true, showSilk: false }); view.focus('specimen');
            element('p', view.renderer ? 'Illustrative model. Drag to orbit; scroll to zoom.' :
                '3D rendering is unavailable. The text details remain available.', stage).className = 'story-model-note';
        } else {
            clearView(); stage.replaceChildren();
            element('p', 'No 3D model is available for this package. Explore its catalog details here.', stage).className = 'story-fallback';
        }
    }
    function select(next) {
        const progressFocused = document.activeElement?.closest('[data-story-progress]');
        index = Math.max(0, Math.min(queue.length - 1, next)); packageIndex = 0; render();
        if (progressFocused) $('[data-story-progress] [aria-current]')?.focus();
    }
    async function load() {
        const requestGeneration = ++generation;
        controller?.abort(); controller = new AbortController(); clearView();
        library = null; queue = [];
        $('[data-story-details]').replaceChildren(); $('[data-story-stage]').replaceChildren();
        $('[data-story-progress]').replaceChildren();
        $('[data-story-prev]').disabled = true; $('[data-story-next]').disabled = true;
        $('[data-story-status]').textContent = 'Loading component catalog…';
        $('[data-story-retry]').hidden = true;
        try {
            library = await readComponentLibrary(globalThis.fetch, controller.signal);
            if (requestGeneration !== generation || !dialog.open) return;
            queue = storyQueue(library.items, $('[data-story-search]').value); select(0);
        } catch {
            if (requestGeneration !== generation || !dialog.open) return;
            $('[data-story-details]').replaceChildren(); $('[data-story-stage]').replaceChildren();
            $('[data-story-progress]').replaceChildren(); queue = []; library = null;
            $('[data-story-status]').textContent = 'The component library is unavailable or changed. Retry to load a current snapshot.';
            $('[data-story-retry]').hidden = false;
            $('[data-story-prev]').disabled = true; $('[data-story-next]').disabled = true;
        }
    }
    document.querySelectorAll('[data-open-components]').forEach(button => button.addEventListener('click', () => {
        opener = button; dialog.showModal(); $('[data-story-search]').value = ''; void load();
    }));
    $('[data-story-close]').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    $('[data-story-retry]').onclick = load;
    $('[data-story-prev]').onclick = () => select(index - 1);
    $('[data-story-next]').onclick = () => select(index + 1);
    $('[data-story-search]').oninput = event => { if (library) { queue = storyQueue(library.items, event.target.value); select(0); } };
    dialog.addEventListener('keydown', event => {
        if (['INPUT', 'SELECT', 'CANVAS', 'TEXTAREA'].includes(event.target.tagName)) return;
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault(); select(index + (event.key === 'ArrowRight' ? 1 : -1));
        }
    });
    // Swipe the text panel to change stories; the canvas always owns orbit gestures.
    let swipe;
    const panel = $('[data-story-details]');
    panel.addEventListener('pointerdown', event => {
        if (event.pointerType !== 'touch' || event.target.closest('button,select,summary')) return;
        swipe = { id: event.pointerId, x: event.clientX, y: event.clientY };
    });
    panel.addEventListener('pointerup', event => {
        const direction = storySwipe(swipe, event); if (direction) select(index + direction);
        swipe = null;
    });
    panel.addEventListener('pointercancel', () => { swipe = null; });
}
