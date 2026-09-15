import { BoardView } from './board-view.js';
import { VisualRenderer } from './visual-renderer.js';
import { createIllustrativeSceneManifest, getVisualFamilyCatalog, FAMILY_LESSONS } from './visual-inventory.js';

export const SAMPLE_LABEL = 'Reference-inspired educational model · not an electrically verified design';
export const PROOF = Object.freeze({
    id: 'five-object-proof', provenance: 'ILLUSTRATIVE_ONLY', width: 66, depth: 46, thickness: 1.6,
    holes: [{ x: -28, y: -18, radius: 1.6, annulus: 3 }, { x: 28, y: -18, radius: 1.6, annulus: 3 },
        { x: -28, y: 18, radius: 1.6, annulus: 3 }, { x: 28, y: 18, radius: 1.6, annulus: 3 }],
    instances: [
        { id: 'IC', family: 'qfp', x: -11, y: 1, options: { width: 14, depth: 14, height: 1.5 }, name: 'Leaded integrated circuit' },
        { id: 'HEADER', family: 'header', x: 0, y: 15, options: { width: 28, depth: 5, height: 6, contactCount: 12 }, name: 'Recessed connector and contacts' },
        { id: 'CAN', family: 'aluminum_can', x: 16, y: 2, options: { diameter: 7, height: 9 }, name: 'Aluminum can, rim and base' },
        { id: 'RESISTOR', family: 'axial_resistor', x: 11, y: -12, options: { width: 6, diameter: 2.4 }, name: 'Banded axial body and bent leads' },
    ],
});

// Presentation adapter only: never sent to project, verification or export APIs.
export function visualBoard(manifest) {
    if (manifest.provenance !== 'ILLUSTRATIVE_ONLY') throw new Error('Sample scene must remain illustrative');
    return { kind: 'illustrative_sample', visual_manifest: manifest,
        width_mm: manifest.width, height_mm: manifest.depth, display_thickness_mm: manifest.thickness,
        tracks: [], vias: [], components: manifest.instances.map((entry) => ({
            ref: entry.id, part_id: entry.name, package: entry.family, footprint_id: null, system: entry.region ?? 'visual',
            x_mm: entry.x + manifest.width / 2, y_mm: entry.y + manifest.depth / 2,
            width_mm: entry.options.width ?? entry.options.diameter ?? 6,
            height_mm: entry.options.depth ?? entry.options.diameter ?? 5,
            rotation_deg: entry.rotation ?? 0, side: 'F.Cu', net_names: [], pads: [],
        })) };
}

export function mountVisualExplorer(container, manifest = createIllustrativeSceneManifest()) {
    container._visualView?.dispose();
    const opener = document.activeElement;
    container.innerHTML = `<div class="visual-heading"><div><p class="eyebrow">OHMNI / COMPONENT ATLAS</p><h2>A closer look at electronics.</h2></div><div class="visual-heading-actions"><button data-library>Asset library</button><button data-close>Close explorer</button></div></div>
        <p class="visual-status">${SAMPLE_LABEL}</p>
        <div class="visual-layout"><div class="visual-stage"><canvas aria-label="Interactive educational component model" tabindex="0"></canvas>
        <div class="visual-toolbar"><button data-action="reset">Reset camera</button><button data-action="top">Top</button><button data-action="back">Underside</button><button data-action="grazing">Edge view</button><button data-action="explode">Explode</button><button data-action="showMask">Mask</button><button data-action="showCopper">Illustrative paths</button><button data-action="showSilk">Printed labels</button><button data-action="showComponents">Components</button><button data-action="quality">Low GPU load</button></div>
        <p class="visual-help">Drag to orbit · scroll to zoom · arrow keys rotate · Tab finds controls</p></div>
        <aside class="visual-inspector"><label>Find a component<input type="search" placeholder="Name, family, region or visual ID"></label><p class="visual-count"></p><div class="visual-list"></div><div class="visual-detail" aria-live="polite"><h3>Select a component</h3><p>Inspect its body, contacts and construction. Guide paths are artistic, with no electrical connectivity assigned.</p></div></aside></div><div class="visual-library" hidden></div>`;
    const canvas = container.querySelector('canvas'), detail = container.querySelector('.visual-detail');
    const view = new BoardView(canvas, { rendererFactory: node => new VisualRenderer(node), onSelect: id => {
        const entry = manifest.instances.find(item => item.id === id); if (!entry) return;
        detail.replaceChildren(); delete detail.dataset.detailId;
        for (const [tag, value] of [['h3', entry.name], ['p', entry.description ?? 'General educational explanation; this image does not establish the part’s electrical function.'],
            ['p', entry.lesson?.inspect ?? 'Illustrative geometry · chosen dimensions and generic markings. No verified electrical identity.'], ['small', `Visual ID ${entry.id} · ${entry.family}`]]) {
            const element = document.createElement(tag); element.textContent = value; detail.append(element);
        }
        const notice = document.createElement('p'); notice.textContent = entry.educationNotice ?? 'General educational explanation; this image does not establish the part’s electrical function.'; detail.append(notice);
        const details = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = 'Source and model details'; details.append(summary);
        for (const value of [entry.knownSourceFacts?.observation, entry.unknownFacts, `Appearance: ${entry.modelAssetId ?? entry.family}. Original procedural project source; license unspecified.`,
            `Artist-selected dimensions: ${entry.options.width ?? 6} × ${entry.options.depth ?? 5} × ${entry.options.height ?? 3} mm. Lead/contact counts and markings are illustrative.`].filter(Boolean)) {
            const p = document.createElement('p'); p.textContent = value; details.append(p);
        }
        detail.append(details);
        const closeup = document.createElement('button'); closeup.textContent = 'View close-up'; closeup.onclick = () => view.focus(id); detail.append(closeup);
        const isolate = document.createElement('button'); isolate.textContent = 'Isolate / show all'; isolate.onclick = () => view.setOptions({ isolate: view.options.isolate ? null : id }); detail.append(isolate);
    } });
    container._visualView = view;
    view.setBoard(visualBoard(manifest)); view.options.showLabels = false; view.options.showSilk = true;
    // The atlas has no overlaid labels: use the available stage height for detail.
    view.options.frameHeightFraction = .92;
    view.camera.yaw = 25 * Math.PI / 180; view.camera.pitch = 43 * Math.PI / 180; view.frame();
    function inspectPatch(entry) {
        // X regions have no component owner or electrical identity. Focus their
        // surface bounds directly without inserting a fake body into the board.
        view.select(null); view.setOptions({ isolate: null, explode: 0, showBack: false });
        detail.replaceChildren(); detail.dataset.detailId = entry.id;
        const lesson = FAMILY_LESSONS.unresolved_patch;
        for (const [tag, value] of [['h3', `${entry.label} · ${entry.id}`],
            ['p', 'Surface detail specimen · not a component'], ['p', lesson.general],
            ['p', lesson.inspect], ['p', lesson.unknown], ['p', entry.knownSourceFacts?.observation],
            ['small', `Illustrative footprint ${entry.options.width} × ${entry.options.depth} mm; artist-selected dimensions. No electrical connections assigned.`]]) {
            if (!value) continue;
            const element = document.createElement(tag); element.textContent = value; detail.append(element);
        }
        const focus = () => view.focusPoints([-1, 1].flatMap(sx => [-1, 1].map(sy => ({
            x: entry.x + sx * entry.options.width / 2, y: entry.y + sy * entry.options.depth / 2,
            z: manifest.thickness / 2 + entry.options.height,
        }))));
        const button = document.createElement('button'); button.textContent = 'View detail close-up'; button.onclick = focus; detail.append(button);
        focus();
    }
    const patches = document.createElement('details'); patches.className = 'visual-patches';
    const patchTitle = document.createElement('summary'); patchTitle.textContent = 'Unresolved surface details'; patches.append(patchTitle);
    const patchList = document.createElement('div'); patches.append(patchList);
    if (manifest.microdetailPatches?.length) container.querySelector('.visual-inspector').insertBefore(patches, detail);
    const list = container.querySelector('.visual-list');
    function filter(query = '') {
        list.replaceChildren();
        const entries = manifest.instances.filter(item => `${item.id} ${item.name} ${item.family} ${item.region} ${item.subdetailIds ?? []}`.toLowerCase().includes(query.toLowerCase()));
        container.querySelector('.visual-count').textContent = `${entries.length} of ${manifest.instances.length} illustrative bodies · no BOM`;
        for (const entry of entries) {
            const button = document.createElement('button'); button.textContent = `${entry.name} · ${entry.id}`;
            button.onclick = () => { view.select(entry.id); view.focus(entry.id); }; list.append(button);
        }
        patchList.replaceChildren();
        for (const entry of (manifest.microdetailPatches ?? []).filter(item => `${item.id} ${item.family} ${item.region}`.toLowerCase().includes(query.toLowerCase()))) {
            const button = document.createElement('button'); button.textContent = `${entry.label} · ${entry.id}`;
            button.onclick = () => inspectPatch(entry); patchList.append(button);
        }
    }
    filter(); container.querySelector('input').oninput = event => filter(event.target.value);
    const close = () => { view.dispose(); container._visualView = null; container.hidden = true; document.body.classList.remove('visual-open'); document.querySelector('.app-layout').inert = false; opener?.focus?.(); };
    container.querySelector('[data-close]').onclick = close;
    for (const button of container.querySelectorAll('[data-action]')) button.onclick = () => {
        const action = button.dataset.action;
        if (action === 'reset') { view.select(null); view.setOptions({ explode: 0, isolate: null, showComponents: true, xray: false, showBack: false }); view.setCameraPreset('iso'); }
        else if (action === 'top' || action === 'back') view.setCameraPreset(action);
        else if (action === 'grazing') { view.camera.pitch = 9 * Math.PI / 180; view.frame(); }
        else if (action === 'explode') view.setOptions({ explode: view.options.explode ? 0 : 1 });
        else if (action.startsWith('show')) { view.setOptions({ [action]: !view.options[action] }); button.setAttribute('aria-pressed', String(view.options[action])); }
        else if (action === 'quality') { view.setOptions({ quality: view.options.quality === 'low' ? 'high' : 'low' }); button.setAttribute('aria-pressed', String(view.options.quality === 'low')); }
    };
    container.querySelector('[data-library]').onclick = () => {
        const library = container.querySelector('.visual-library');
        library.hidden = !library.hidden; container.querySelector('.visual-layout').hidden = !library.hidden;
        container.querySelector('[data-library]').textContent = library.hidden ? 'Asset library' : 'Return to board';
        if (!library.hidden && !library.children.length) mountFamilyCatalog(library, family => {
            library.hidden = true; container.querySelector('.visual-layout').hidden = false;
            container.querySelector('[data-library]').textContent = 'Asset library';
            const entry = manifest.instances.find(item => item.family === family);
            if (entry) { view.select(entry.id); view.focus(entry.id); }
            else {
                const patch = manifest.microdetailPatches?.find(item => item.family === family);
                if (patch) inspectPatch(patch);
            }
        });
        view.render();
    };
    container.onkeydown = event => {
        if (event.key === 'Escape') { event.preventDefault(); close(); }
        if (event.key === 'Tab') {
            const targets = [...container.querySelectorAll('button,input,canvas[tabindex],summary')].filter(node => node.offsetParent !== null);
            if (event.shiftKey && document.activeElement === targets[0]) { event.preventDefault(); targets.at(-1).focus(); }
            else if (!event.shiftKey && document.activeElement === targets.at(-1)) { event.preventDefault(); targets[0].focus(); }
        }
    };
    container.hidden = false; document.body.classList.add('visual-open'); document.querySelector('.app-layout').inert = true; view.frame(); canvas.focus();
    canvas.dataset.motion = view.reducedMotion ? 'reduced' : 'standard';
    return view;
}

function mountFamilyCatalog(container, select) {
    const title = document.createElement('h3'); title.textContent = 'Compound models, one family at a time'; container.append(title);
    const grid = document.createElement('div'); grid.className = 'visual-family-grid'; container.append(grid);
    const surface = document.createElement('canvas');
    let renderer;
    try { renderer = new VisualRenderer(surface); } catch { renderer = null; }
    for (const family of getVisualFamilyCatalog()) {
        const button = document.createElement('button'); button.className = 'visual-family-tile';
        const preview = document.createElement('canvas'); preview.width = 240; preview.height = 160; preview.setAttribute('aria-hidden', 'true');
        const text = document.createElement('strong'); text.textContent = family.name;
        button.append(preview, text); button.onclick = () => select(family.family); grid.append(button);
        if (renderer) {
            const options = family.specimenOptions;
            const span = Math.max(options.width ?? 8, options.depth ?? 6, (options.height ?? 3) * 1.5, 12) * 1.7;
            renderer.setScene({ id: `preview:${family.family}`, provenance: 'ILLUSTRATIVE_ONLY', width: span, depth: span * .7, thickness: 1.6,
                instances: [{ id: family.family, family: family.family, options, x: 0, y: 0 }] });
            renderer.render({ yaw: .35, pitch: .75, distance: 150, focal: 160 / span * 150, zoom: .85, panX: 0, panY: -4 }, { width: 240, height: 160 }, {});
            preview.getContext('2d').drawImage(surface, 0, 0);
        }
    }
    renderer?.dispose();
}

export function initializeVisualExplorer() {
    const container = document.querySelector('#visual-explorer'); if (!container) return;
    document.querySelector('#open-visual-proof')?.addEventListener('click', () => mountVisualExplorer(container, PROOF));
    const manifest = createIllustrativeSceneManifest();
    const open = id => {
        const view = mountVisualExplorer(container, manifest);
        if (id) { view.select(id); view.focus(id); }
        return view;
    };
    document.querySelectorAll('[data-open-sample]').forEach(button => button.addEventListener('click', () => open()));
    const preview = document.querySelector('#home-atlas-canvas');
    if (preview) {
        preview._visualView?.dispose();
        const view = new BoardView(preview, { onSelect: id => {
            if (!id) return;
            open(id);
            // This preview launches an inspector; release its selection so
            // Enter can launch again when Escape returns focus to the preview.
            view.select(null);
        } });
        preview._visualView = view;
        view.options.showLabels = false; view.options.showSilk = true;
        view.options.frameHeightFraction = .92; view.options.quality = 'low';
        view.setBoard(visualBoard(manifest));
        view.camera.yaw = 25 * Math.PI / 180; view.camera.pitch = 43 * Math.PI / 180; view.frame();
        document.querySelector('#home-atlas-count').textContent = `${manifest.instances.length} modeled bodies · ${getVisualFamilyCatalog().length} visual families`;
        if (!view.available) document.querySelector('#home-atlas-help').textContent = 'Preview unavailable. Open the explorer to use its component list.';
    }
    if (location.hash === '#visual-proof') mountVisualExplorer(container, PROOF);
    if (location.hash === '#sample-board') open();
}
