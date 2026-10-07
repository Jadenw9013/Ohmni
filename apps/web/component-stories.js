// Read-only learning UI. This module has no project, admission or export writes.
import { API_BASE, fetchHealth, pollHeaders, sameIdentity } from './client-contract.js';
import { ASSET_REGISTRY } from './visual-assets.js';
import { BoardView } from './board-view.js';
import { visualBoard } from './visual-explorer.js';
import { openComponentSandbox } from './component-sandbox.js';
import { loadFullLibrary, createFullComponent } from './component-library/full-registry.js';
import { mountBehaviorPanel } from './component-behavior.js';
import { ModelPreview } from './component-library/preview/model-preview.js';

const START_HERE = ['GENERIC_RESISTOR', 'GENERIC_CAPACITOR', 'GENERIC_LED_GREEN',
    'GENERIC_MOMENTARY_BUTTON', 'HEADER_1X6_254', 'USB_C_RECEPTACLE_16P',
    'AP2112K-3.3TRG1', 'MCP1700T-3302E-TT', 'ESP32-WROOM-32E', 'BME280', 'TMP102AIDRLR', '25LC256-I/SN'];
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const text = (value, max = 500) => typeof value === 'string' && value.length > 0 && value.length <= max;
const invalid = () => { throw new Error('Component library unavailable'); };
const LESSONS = Object.freeze({
    GENERIC_RESISTOR: ['Resistor', 'Limits current or sets a voltage together with other parts. Its resistance must be chosen for the circuit.'],
    GENERIC_CAPACITOR: ['Capacitor', 'Stores a small amount of charge. Near a chip, it can help smooth changes in its power supply.'],
    GENERIC_LED_GREEN: ['Green indicator light', 'Turns electrical current into light. It needs a suitable current-limiting circuit.'],
    GENERIC_MOMENTARY_BUTTON: ['Push button', 'Connects contacts while pressed, giving your program a physical input.'],
    HEADER_1X6_254: ['Pin header', 'Provides a row of connections for wires or another board. The circuit determines what each pin does.'],
    USB_C_RECEPTACLE_16P: ['USB-C connector', 'Connects a USB cable. Supporting circuitry determines how the board uses power and signals.'],
    'AP2112K-3.3TRG1': ['Voltage regulator', 'Provides a regulated supply within its operating limits. Check those limits before choosing an input or load.'],
    'MCP1700T-3302E-TT': ['Voltage regulator', 'Provides a regulated supply within its operating limits. The package illustration is not an electrical specification.'],
    'ESP32-WROOM-32E': ['ESP32 processor module', 'Runs your firmware and connects to sensors, buttons and other parts. Ohmni does not write or test that firmware.'],
    BME280: ['Environment sensor', 'Measures temperature, humidity and air pressure for your program to read.'],
    TMP102AIDRLR: ['Temperature sensor', 'Measures temperature and reports a reading to your program.'],
    '25LC256-I/SN': ['Memory chip', 'Keeps stored data when power is removed. Your firmware controls what gets written and read.'],
});
export const componentLesson = id => LESSONS[id] ?? null;
const displayName = record => componentLesson(record.catalog_part.id)?.[0] ?? (record.display_name.startsWith('GENERIC_')
    ? record.display_name.replace('GENERIC_', '').toLowerCase().replaceAll('_', ' ').replace(/^./, c => c.toUpperCase())
    : record.display_name);

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

function initializeLegacyComponentStories() {
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
        element('p', componentLesson(item.part_id)?.[1] ?? item.description, card).className = 'story-description';
        element('p', item.part_id, card).className = 'story-muted';
        const label = element('label', 'Package ', card), choice = document.createElement('select'); label.append(choice);
        item.variants.forEach((v, i) => { const option = element('option', v.record.package_variant, choice); option.value = String(i); });
        choice.value = String(packageIndex); choice.onchange = () => { packageIndex = Number(choice.value); render(); $('[data-story-details] select').focus(); };
        element('h4', 'About this model', card);
        element('p', variant.visual_note, card);
        element('p', 'Appearance does not verify dimensions, pad positions, connections or electrical behavior.', card);
        element('p', 'Try a layout to practice arranging parts. Practice layouts are temporary and cannot change a saved project.', card).className = 'story-muted';
        const source = element('details', '', card); element('summary', 'Source and model details', source);
        element('p', item.description, source);
        element('p', 'Catalog-reported information; not reverified by this library.', source);
        const evidence = element('ul', '', source);
        r.evidence_summary.forEach(value => element('li', value, evidence));
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
        $('[data-story-sandbox]').disabled = true;
        $('[data-story-details]').replaceChildren(); $('[data-story-stage]').replaceChildren();
        $('[data-story-progress]').replaceChildren();
        $('[data-story-prev]').disabled = true; $('[data-story-next]').disabled = true;
        $('[data-story-status]').textContent = 'Loading component catalog…';
        $('[data-story-retry]').hidden = true;
        try {
            library = await readComponentLibrary(globalThis.fetch, controller.signal);
            if (requestGeneration !== generation || !dialog.open) return;
            queue = storyQueue(library.items, $('[data-story-search]').value); select(0);
            $('[data-story-sandbox]').disabled = false;
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
        opener = button; dialog.showModal(); $('[data-story-search]').value = button.dataset.componentQuery ?? ''; void load();
    }));
    $('[data-story-close]').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    $('[data-story-retry]').onclick = load;
    $('[data-story-sandbox]').onclick = event => {
        if (!library) return;
        const definitions = library.items.flatMap(item => item.variants.flatMap(variant => {
            if (variant.eligibility.eligibility !== 'LEARN_ONLY') return [];
            const specimen = storyManifest(item, variant)?.instances[0];
            return specimen ? [{ id: `${item.part_id}/${variant.record.package_variant}`,
                name: `${displayName(variant.record)} (${variant.record.package_variant})`,
                family: specimen.family, options: specimen.options }] : [];
        }));
        openComponentSandbox(definitions, event.currentTarget);
    };
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

const words = value => String(value ?? '').replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase())
    .replace(/\b(Smd|Tht|Ic|Usb|Led|Lcd|Oled|Bga|Qfn|Qfp|Dfn|Wlcsp|Pcb|Rj)\b/g, token => token.toUpperCase());
const dimensionValue = value => typeof value === 'number' ? value : value?.default;
const mm = value => Number.isFinite(value) ? `${Number(value.toFixed(4))} mm` : 'Not recorded';
const recordPins = record => Number.isInteger(record.terminals?.count) ? record.terminals.count : null;
const searchAliases = Object.freeze({ usb_c: 'usb c', usb: 'usb', resistor: 'resistor', capacitor: 'capacitor' });
const FEATURED = Object.freeze(['OHM-123','OHM-130','OHM-110','OHM-094','OHM-004','OHM-023','OHM-041','OHM-065','OHM-078','OHM-165','OHM-155','OHM-172','OHM-174','OHM-169','OHM-030','OHM-143','OHM-098','OHM-138','OHM-034','OHM-179']);
const directionName = value => {
    if (!Array.isArray(value) || value.length !== 3) return String(value ?? 'Not recorded');
    const axes = ['X','Y','Z'], terms = value.map((amount, index) => amount ? `${amount > 0 ? '+' : '−'}${axes[index]}` : '').filter(Boolean);
    return terms.join(' / ') || 'Not recorded';
};

export function componentSearchText(record) {
    return [record.id, record.slug, record.canonical_name, record.category, record.subcategory,
        record.package_family, record.package_member, record.generator, record.mounting,
        ...(record.names?.aliases ?? [])].filter(Boolean).join(' ').replaceAll('_', ' ').toLowerCase();
}

export function filterComponentRecords(records, filters = {}) {
    const rawQuery = String(filters.query ?? '').trim().toLowerCase();
    const query = searchAliases[rawQuery] ?? rawQuery.replaceAll('_', ' ');
    const result = records.filter(record => (!query || componentSearchText(record).includes(query))
        && (!filters.category || record.category === filters.category)
        && (!filters.packageFamily || record.package_family === filters.packageFamily)
        && (!filters.mounting || record.mounting === filters.mounting)
        && (!filters.source || record.status === filters.source));
    const sort = filters.sort ?? 'featured';
    return result.slice().sort((a, b) => {
        if (sort === 'featured') {
            const ai = FEATURED.indexOf(a.id), bi = FEATURED.indexOf(b.id);
            if (ai >= 0 || bi >= 0) return (ai < 0 ? FEATURED.length : ai) - (bi < 0 ? FEATURED.length : bi);
        }
        if (sort === 'name') return a.canonical_name.localeCompare(b.canonical_name, 'en') || a.id.localeCompare(b.id, 'en');
        if (sort === 'family') return a.package_family.localeCompare(b.package_family, 'en') || a.id.localeCompare(b.id, 'en');
        return a.id.localeCompare(b.id, 'en');
    });
}

const addDefinition = (list, term, description) => {
    const row = document.createElement('div');
    element('dt', term, row); element('dd', description, row); list.append(row);
};

export function initializeComponentStories() {
    const dialog = document.querySelector('#component-stories');
    if (!dialog) return;
    const $ = selector => dialog.querySelector(selector);
    let library = null, records = [], visible = [], selectedId = null;
    let disposeBehavior = null;
    let preview = null, thumbnailPreview = null, thumbnailObserver = null, opener = null;
    let model = null, view = 'three-quarter', lod = 'LOD1', tab = 'overview', loadGeneration = 0;

    const setStatus = value => { $('[data-story-status]').textContent = value; };
    const ownerSide = id => library?.owners?.[id] === 'completion-c' ? 1 : -1;
    const modelSize = current => (current?.userData.expected_dimensions_mm ?? []).map(value => Number(value.toFixed(4)));
    const renderSize = () => {
        const stage = $('[data-story-stage]');
        return { width: Math.max(420, Math.round(stage.clientWidth || 760)), height: Math.max(300, Math.round(stage.clientHeight || 520)) };
    };
    const disposeRenderers = () => {
        thumbnailObserver?.disconnect(); thumbnailObserver = null;
        preview?.dispose(); preview = null; thumbnailPreview?.dispose(); thumbnailPreview = null; model = null;
    };
    const populate = (selector, values) => {
        const select = $(selector), current = select.value;
        select.querySelectorAll('option:not(:first-child)').forEach(option => option.remove());
        for (const value of [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'en'))) {
            const option = element('option', words(value), select); option.value = value;
        }
        if ([...select.options].some(option => option.value === current)) select.value = current;
    };
    const filters = () => ({ query: $('[data-story-search]').value, category: $('[data-story-category]').value,
        packageFamily: $('[data-story-package]').value, mounting: $('[data-story-mounting]').value,
        source: $('[data-story-source]').value, sort: $('[data-story-sort]').value });

    function ensurePreview() {
        if (preview) return true;
        try {
            preview = new ModelPreview($('[data-story-canvas]'));
            $('[data-story-fallback]').hidden = true; return true;
        } catch {
            $('[data-story-canvas]').hidden = true; $('[data-story-fallback]').hidden = false; return false;
        }
    }

    function drawSelected() {
        if (!library || !selectedId || !ensurePreview()) return;
        model = createFullComponent(library, selectedId, { lod });
        preview.setModel(model);
        $('[data-story-canvas]').hidden = false; $('[data-story-fallback]').hidden = true;
        $('[data-story-canvas]').dataset.modelEntry = model.userData.component_id;
        const size = renderSize();
        const stats = preview.renderView(view, { ...size, sideSign: ownerSide(selectedId) });
        $('[data-story-render-note]').textContent = `${stats.triangles.toLocaleString()} triangles · ${stats.draw_calls} draws`;
        $('[data-story-canvas]').setAttribute('aria-label', `${library.records[selectedId].canonical_name}, ${view} view, model detail ${lod.slice(-1)}`);
    }

    function overview(record) {
        const details = $('[data-story-details]');
        const badge = element('p', `${words(record.status)} source record${record.library_metadata.provisional ? ' · provisional model details' : ''}`, details);
        badge.className = `story-source-badge ${record.status === 'partial' ? 'partial' : ''}`;
        element('h4', 'Key information', details);
        const list = element('dl', '', details), size = modelSize(model);
        addDefinition(list, 'Package', `${record.package_family}.${record.package_member}`);
        addDefinition(list, 'Terminals', String(model?.userData.terminal_count ?? recordPins(record) ?? 'Not recorded'));
        addDefinition(list, 'Mounting', words(record.mounting));
        addDefinition(list, 'Model bounds', size.length === 3 ? `${size.join(' × ')} mm` : 'Not recorded');
        addDefinition(list, 'Category', `${words(record.category)} · ${words(record.subcategory)}`);
        addDefinition(list, 'Generator', record.generator);
        addDefinition(list, 'Model detail', `${lod} of LOD0 / LOD1 / LOD2`);
        element('h4', 'About this model', details);
        element('p', `${record.canonical_name} is a reusable package model generated from the recorded ${record.package_family} data.`, details);
        const caveat = element('p', 'The model helps with visual recognition. It does not verify a footprint, electrical behavior, manufacturing fit, or source completeness. Any OHM ID shown on the body is a preview label, not a manufacturer marking.', details);
        caveat.className = 'story-caveat';
    }

    function dimensions(record) {
        const details = $('[data-story-details]'); element('h4', 'Recorded dimensions', details);
        const list = element('dl', '', details); list.className = 'story-dimension-list';
        for (const [name, specification] of Object.entries(record.dimensions_mm ?? {})) {
            const value = dimensionValue(specification), confidence = specification?.confidence ? ` · confidence ${specification.confidence}` : '';
            addDefinition(list, words(name), `${mm(value)}${confidence}`);
        }
        if (!list.children.length) addDefinition(list, 'Dimensions', 'No named source dimensions were recorded.');
        element('h4', 'Rendered bounds', details);
        const bounds = model?.userData.expected_bounds_mm;
        const rendered = element('dl', '', details);
        addDefinition(rendered, 'Overall X × Y × Z', modelSize(model).length === 3 ? `${modelSize(model).join(' × ')} mm` : 'Not recorded');
        if (bounds?.min && bounds?.max) {
            addDefinition(rendered, 'Minimum corner', bounds.min.map(value => Number(value.toFixed(4))).join(', '));
            addDefinition(rendered, 'Maximum corner', bounds.max.map(value => Number(value.toFixed(4))).join(', '));
        }
    }

    function pins() {
        const details = $('[data-story-details]'), contacts = model?.userData.contacts ?? [];
        element('h4', `${contacts.length} terminal${contacts.length === 1 ? '' : 's'}`, details);
        if (model?.userData.mating_direction) element('p', `Mating direction: ${directionName(model.userData.mating_direction)}`, details);
        const table = element('table', '', details), head = element('thead', '', table), row = element('tr', '', head);
        for (const heading of ['Terminal', 'Position (X, Y, Z mm)', 'Type / side']) element('th', heading, row);
        const body = element('tbody', '', table);
        for (const contact of contacts) {
            const line = element('tr', '', body), center = contact.center_mm ?? contact.position ?? [];
            element('td', contact.terminal ?? '—', line);
            element('td', center.length ? center.map(value => Number(value.toFixed(4))).join(', ') : 'Not recorded', line);
            element('td', [contact.type, contact.side].filter(Boolean).join(' · ') || '—', line);
        }
    }

    function source(record) {
        const details = $('[data-story-details]'); element('h4', 'Source and model status', details);
        const list = element('dl', '', details);
        addDefinition(list, 'Source status', words(record.status));
        addDefinition(list, 'Document', record.source?.document ?? 'Repository component specification');
        addDefinition(list, 'Spec location', record.source?.line ? `Line ${record.source.line}` : 'Not recorded');
        addDefinition(list, 'Appearance confidence', record.confidence?.materials_appearance ?? 'Not recorded');
        addDefinition(list, 'Implementation', record.library_metadata.implementation_status);
        addDefinition(list, 'Footprint binding', record.library_metadata.footprint_binding ?? 'None');
        const uncertain = record.library_metadata.uncertain_values ?? [];
        if (uncertain.length) {
            const disclosure = element('details', '', details); element('summary', `Provisional and uncertain values (${uncertain.length})`, disclosure);
            const values = element('ul', '', disclosure); uncertain.forEach(value => element('li', value, values));
        }
        const conflicts = record.library_metadata.conflicts ?? [];
        if (conflicts.length) {
            const disclosure = element('details', '', details); element('summary', `Recorded geometry conflicts (${conflicts.length})`, disclosure);
            const values = element('ul', '', disclosure); conflicts.forEach(value => element('li', JSON.stringify(value), values));
        }
        element('p', `Spec revision ${library.source_spec_sha256}`, details).className = 'story-muted';
    }

    function renderDetails() {
        disposeBehavior?.(); disposeBehavior = null;
        const record = library?.records[selectedId], details = $('[data-story-details]'); details.replaceChildren();
        if (!record) return;
        details.id = `story-panel-${tab}`; details.setAttribute('role', 'tabpanel'); details.setAttribute('aria-labelledby', `story-tab-${tab}`);
        if (tab === 'behavior') { disposeBehavior = mountBehaviorPanel(details, record.id); return; }
        ({ overview, dimensions, pins, source })[tab](record);
    }

    function select(id, { focus = false } = {}) {
        if (!library?.records[id]) return;
        selectedId = id; const record = library.records[id];
        dialog.querySelectorAll('[data-component-id]').forEach(card => card.setAttribute('aria-pressed', String(card.dataset.componentId === id)));
        $('[data-story-name]').textContent = record.canonical_name;
        $('[data-story-identity]').textContent = `${record.id} · ${record.package_family} · ${words(record.mounting)}`;
        $('[data-story-copy]').disabled = false;
        drawSelected(); renderDetails();
        if (focus) dialog.querySelector(`[data-component-id="${id}"]`)?.focus();
    }

    function thumb(image, id) {
        if (!dialog.open || !image.isConnected || image.dataset.ready || !library) return;
        try {
            thumbnailPreview ??= new ModelPreview(document.createElement('canvas'));
            thumbnailPreview.setModel(createFullComponent(library, id, { lod: 'LOD0' }));
            thumbnailPreview.renderView('three-quarter', { width: 260, height: 195, sideSign: ownerSide(id) });
            image.src = thumbnailPreview.canvas.toDataURL('image/webp', .82); image.dataset.ready = 'true';
        } catch { image.closest('.story-thumb')?.classList.add('unavailable'); }
    }

    function renderGrid() {
        const grid = $('[data-story-grid]'); grid.replaceChildren(); thumbnailObserver?.disconnect();
        const browser = $('[data-story-browser]');
        if ('IntersectionObserver' in globalThis) thumbnailObserver = new IntersectionObserver(entries => {
            for (const entry of entries) if (entry.isIntersecting) {
                thumbnailObserver.unobserve(entry.target); requestAnimationFrame(() => thumb(entry.target, entry.target.dataset.thumbId));
            }
        }, { root: browser, rootMargin: '180px' });
        for (const record of visible) {
            const card = document.createElement('button'); card.type = 'button'; card.className = 'story-component-card';
            card.dataset.componentId = record.id; card.setAttribute('aria-pressed', String(record.id === selectedId));
            card.setAttribute('aria-label', `${record.canonical_name}, ${record.id}, ${words(record.status)} source record`);
            const visual = element('span', '', card); visual.className = 'story-thumb';
            const image = new Image(); image.alt = ''; image.dataset.thumbId = record.id; visual.append(image);
            const status = element('span', '', visual); status.className = `story-card-status ${record.status === 'partial' ? 'partial' : ''}`; status.title = `${words(record.status)} source record`;
            const copy = element('span', '', card); copy.className = 'story-card-copy';
            element('strong', record.canonical_name, copy); element('small', `${record.id} · ${record.package_member}`, copy);
            card.onclick = () => select(record.id); grid.append(card);
            if (thumbnailObserver) thumbnailObserver.observe(image); else if (grid.children.length <= 24) requestAnimationFrame(() => thumb(image, record.id));
        }
        $('[data-story-empty]').hidden = visible.length > 0;
    }

    function applyFilters({ preserveSelection = true } = {}) {
        if (!library) return;
        visible = filterComponentRecords(records, filters()); renderGrid();
        const currentVisible = visible.some(record => record.id === selectedId);
        setStatus(`${visible.length.toLocaleString()} of ${records.length.toLocaleString()} components${filters().query ? ` matching “${filters().query}”` : ''}`);
        if (!preserveSelection || !currentVisible) selectedId = visible[0]?.id ?? null;
        if (selectedId) select(selectedId); else {
            disposeBehavior?.(); disposeBehavior = null;
            $('[data-story-canvas]').hidden = true; delete $('[data-story-canvas]').dataset.modelEntry;
            $('[data-story-name]').textContent = 'No component selected'; $('[data-story-identity]').textContent = '';
            $('[data-story-details]').replaceChildren(); $('[data-story-copy]').disabled = true;
        }
    }

    async function load() {
        const generation = ++loadGeneration; disposeRenderers(); library = null; records = []; visible = []; selectedId = null;
        $('[data-story-grid]').replaceChildren(); $('[data-story-empty]').hidden = true; $('[data-story-retry]').hidden = true;
        setStatus('Loading all 180 component models…');
        try {
            const loaded = await loadFullLibrary(); if (generation !== loadGeneration || !dialog.open) return;
            library = loaded; records = library.components;
            populate('[data-story-category]', records.map(record => record.category));
            populate('[data-story-package]', records.map(record => record.package_family));
            populate('[data-story-mounting]', records.map(record => record.mounting));
            applyFilters({ preserveSelection: false });
            if (!visible.length && $('[data-story-search]').value) {
                const requested = $('[data-story-search]').value;
                $('[data-story-search]').value = ''; applyFilters({ preserveSelection: false });
                setStatus(`No exact package model is assigned to “${requested}”; showing all ${records.length} library models.`);
            }
        } catch {
            if (generation !== loadGeneration || !dialog.open) return;
            setStatus('The component models could not be loaded. Retry the local library snapshot.'); $('[data-story-retry]').hidden = false;
        }
    }

    function clearFilters() {
        $('[data-story-search]').value = '';
        for (const selector of ['[data-story-category]','[data-story-package]','[data-story-mounting]','[data-story-source]']) $(selector).value = '';
        $('[data-story-sort]').value = 'featured'; applyFilters({ preserveSelection: false }); $('[data-story-search]').focus();
    }
    function close() { disposeBehavior?.(); disposeBehavior = null; loadGeneration++; disposeRenderers(); dialog.close(); opener?.focus(); }

    document.querySelectorAll('[data-open-components]').forEach(button => button.addEventListener('click', () => {
        opener = button; dialog.showModal(); $('[data-story-search]').value = button.dataset.componentQuery ?? ''; void load();
    }));
    $('[data-story-close]').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    $('[data-story-retry]').onclick = load; $('[data-story-clear]').onclick = clearFilters;
    $('[data-story-search]').oninput = () => applyFilters({ preserveSelection: false });
    for (const selector of ['[data-story-category]','[data-story-package]','[data-story-mounting]','[data-story-source]','[data-story-sort]']) $(selector).onchange = () => applyFilters();
    dialog.querySelectorAll('[data-story-view]').forEach(button => button.onclick = () => {
        view = button.dataset.storyView; dialog.querySelectorAll('[data-story-view]').forEach(item => item.setAttribute('aria-pressed', String(item === button))); drawSelected();
    });
    dialog.querySelectorAll('[data-story-lod]').forEach(button => button.onclick = () => {
        lod = button.dataset.storyLod; dialog.querySelectorAll('[data-story-lod]').forEach(item => item.setAttribute('aria-pressed', String(item === button))); drawSelected(); renderDetails();
    });
    dialog.querySelectorAll('[data-story-tab]').forEach(button => button.onclick = () => {
        tab = button.dataset.storyTab; dialog.querySelectorAll('[data-story-tab]').forEach(item => { const active = item === button; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; }); renderDetails();
    });
    $('[data-story-copy]').onclick = async () => {
        if (!selectedId) return;
        try { await navigator.clipboard.writeText(selectedId); $('[data-story-copy]').textContent = 'Copied'; setTimeout(() => { $('[data-story-copy]').textContent = 'Copy ID'; }, 1200); }
        catch { setStatus(`${selectedId} is selected. Clipboard access is unavailable.`); }
    };
    dialog.addEventListener('keydown', event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); $('[data-story-search]').focus(); }
        if (event.target.closest('[role="tablist"]') && ['ArrowLeft','ArrowRight'].includes(event.key)) {
            event.preventDefault(); const tabs = [...dialog.querySelectorAll('[data-story-tab]')], index = tabs.indexOf(event.target);
            tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length].click();
            dialog.querySelector('[data-story-tab][aria-selected="true"]')?.focus();
        }
    });
    let resizeTimer;
    globalThis.addEventListener?.('resize', () => { if (!dialog.open || !selectedId) return; clearTimeout(resizeTimer); resizeTimer = setTimeout(drawSelected, 120); });
}
