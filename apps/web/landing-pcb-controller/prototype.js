import { BoardView, project } from '../board-view.js';
import { VisualRenderer } from '../visual-renderer.js';
import { validateLearningSource } from '../learning-model.js';

import { createControllerModelResolver, loadControllerLibraries } from './models.js';
import { normalizeControllerSource } from './projection.js';
import { createControllerMaterials, CONTROLLER_PRESENTATION, CONTROLLER_POSE } from './presentation.js';

const $ = id => document.getElementById(id);
const canvas = $('pcb-canvas'), loading = $('loading');
const DEG = Math.PI / 180;
let view, reference, inventory, selected = '', disposed = false, revealFrame = null, downloadUrl;
let motionOff = false;
try { motionOff = sessionStorage.getItem('ohmni:landing:motion') === 'off'; } catch { /* Session-only in memory. */ }
let motionQuery = matchMedia('(prefers-reduced-motion: reduce)');
const abort = new AbortController();
const listener = (target, type, fn, options = {}) => target.addEventListener(type, fn, { ...options, signal: abort.signal });

function stopReveal() {
    if (revealFrame !== null) cancelAnimationFrame(revealFrame);
    revealFrame = null;
}

function syncMotion() {
    const off = motionOff || motionQuery.matches;
    if (view) { view.reducedMotion = off; view.stopAnimation(); view.targetCamera = null; }
    stopReveal();
    $('motion').textContent = off ? 'Motion off' : 'Motion on';
    $('motion').setAttribute('aria-pressed', String(off));
    $('replay').disabled = off;
    $('replay').title = off ? 'Motion is off in this session or your device preferences.' : '';
}

function fail(error) {
    stopReveal();
    view?.dispose();
    canvas.hidden = true;
    $('poster').hidden = false;
    if (view?.overlay) view.overlay.hidden = true;
    $('view-controls').hidden = true;
    $('focus-part').disabled = true;
    $('motion').disabled = true;
    $('embed-view').disabled = true;
    $('view-help').textContent = '3D view unavailable. Component descriptions remain illustrative.';
    loading.hidden = false;
    loading.textContent = 'The 3D view is unavailable. You can still read about this circuit candidate below.';
    document.body.dataset.state = 'unavailable';
    document.body.dataset.failure = String(error?.message ?? error);
}

function selectPart(ref) {
    stopReveal(); selected = ref || '';
    $('part-select').value = selected;
    $('focus-part').disabled = !selected || !view?.available || view.disposed;
    const part = reference.components.find(item => item.ref === ref);
    $('part-title').textContent = part ? `${ref} · ${part.name?.human || part.part_id || ref}` : 'Meet the controller.';
    $('part-description').textContent = part?.purpose || part?.name?.detail
        || 'An STM32 controller, serial memory, sixteen indicators and a forty-pin expansion header. Select any part to see what it does.';
}

function pose(name = 'overview') {
    if (!view?.available || disposed) return;
    stopReveal(); view.interacted(); view.selected = null; selectPart('');
    const positions = { overview: CONTROLLER_POSE, top: { yaw: 0, pitch: 89.5 * DEG },
        side: { yaw: -14 * DEG, pitch: 15 * DEG }, underside: { yaw: -14 * DEG, pitch: -52 * DEG } };
    Object.assign(view.camera, positions[name] ?? CONTROLLER_POSE);
    view.options.showBack = view.camera.pitch < 0;
    view.setHighlight({}); view.frame();
    document.querySelectorAll('[data-pose]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.pose === name)));
}

function closeUp(ref = selected, frontal = false) {
    if (!ref || !view?.available) return;
    stopReveal(); view.select(ref); view.interacted();
    Object.assign(view.camera, frontal ? { yaw: 0, pitch: 12 * DEG } : CONTROLLER_POSE); view.frame();
    const part = view.geometry.parts.find(part => part.ref === ref);
    if (!part) return;
    const viewport = view.viewport();
    const points = [...part.top, ...part.bottom].map(point => project(point, view.camera, viewport));
    const xs = points.map(p => p.x), ys = points.map(p => p.y);
    const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
    const scale = Math.min(viewport.width * .64 / (right - left), viewport.height * .6 / (bottom - top));
    view.camera.zoom *= scale;
    view.camera.panX = (view.camera.panX + viewport.cx - (left + right) / 2) * scale;
    view.camera.panY = (view.camera.panY + viewport.cy - (top + bottom) / 2) * scale;
    // Close-ups are an explicit visual-review tool, not a changed component placement.
    view.render();
    document.querySelectorAll('[data-pose]').forEach(button => button.setAttribute('aria-pressed', 'false'));
}

function replay() {
    if (!view?.available || motionOff || motionQuery.matches || document.hidden || !view.inViewport) return;
    pose();
    const target = view.camera.yaw, start = performance.now();
    view.camera.yaw = target - 8 * DEG;
    const animate = timestamp => {
        if (disposed || motionOff || motionQuery.matches || document.hidden || !view.inViewport) { stopReveal(); return; }
        const t = Math.min(1, (timestamp - start) / 800);
        const eased = 1 - (1 - t) ** 3;
        view.camera.yaw = target - (1 - eased) * 8 * DEG;
        view.render();
        revealFrame = t < 1 ? requestAnimationFrame(animate) : null;
    };
    revealFrame = requestAnimationFrame(animate);
}

function dispose() {
    if (disposed) return;
    disposed = true; stopReveal(); abort.abort(); view?.dispose();
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
}

function describeSource() {
    for (const item of reference.board.components) {
        const detail = reference.components.find(part => part.ref === item.ref);
        $('part-select').add(new Option(`${item.ref} — ${detail?.name?.human || item.part_id}`, item.ref));
    }
    $('part-controls').hidden = false;
    $('component-count').textContent = `${reference.board.components.length} parts, each from the new circuit.`;
    const checks = reference.checks;
    $('source-detail').textContent = `Candidate capture ${reference.source.captured_on}. `
        + `ERC: ${checks.erc?.status ?? 'NOT RUN'}; DRC: ${checks.drc?.status ?? 'NOT RUN'} `
        + `(${checks.drc?.finding_count ?? 'unknown'} findings, ${checks.drc?.unconnected_count ?? 'unknown'} unconnected). `
        + `Routing: ${checks.routing?.passed === true ? 'passed' : 'incomplete'}. `
        + `Scoped topology: ${checks.topology?.status ?? 'unknown'}. `
        + 'Whole-system verification remains incomplete; no simulation, bench or manufacturing-release claim. '
        + `Artifact ${reference.board.artifact_fingerprint}. ` + reference.limitations.join(' ');
    downloadUrl = URL.createObjectURL(new Blob([JSON.stringify(inventory, null, 2)], { type: 'application/json' }));
    $('binding-download').href = downloadUrl; $('binding-download').download = 'ohmni-controller-board.json';
    $('binding-download').hidden = false;
    listener($('part-select'), 'change', event => {
        if (view?.available && !view.disposed) view.select(event.target.value || null);
        else selectPart(event.target.value || null);
    });
}

async function initialize() {
    const response = await fetch('./candidate-board.json', { signal: abort.signal });
    if (!response.ok) throw new Error('Circuit candidate unavailable');
    reference = await response.json();
    validateLearningSource(reference, { reference: false });
    const displayReference = normalizeControllerSource(reference);
    inventory = reference;
    if (disposed) return;
    // Component descriptions and check provenance remain usable without WebGL.
    describeSource();
    const libraries = await loadControllerLibraries();
    if (disposed) return;
    const finish = !new URLSearchParams(location.search).has('no-finish');
    view = new BoardView(canvas, { inputPolicy: 'landing', onSelect: selectPart, onRendererFailure: fail,
        rendererFactory: node => new VisualRenderer(node, {
            presentation: CONTROLLER_PRESENTATION, materialFactory: () => createControllerMaterials({ finish }),
            instanceModelResolver: createControllerModelResolver(displayReference, libraries),
        }) });
    if (!view.available) return;
    motionQuery = view.motionQuery;
    view.camera.distance = 220;
    view.options.showLabels = false;
    view.setBoard(displayReference.board); pose(); syncMotion();
    $('part-controls').hidden = false; $('view-controls').hidden = false; loading.hidden = true; $('poster').hidden = true;
    listener($('focus-part'), 'click', () => closeUp());
    listener($('embed-view'), 'click', event => {
        const top = event.currentTarget.textContent === 'Top view';
        pose(top ? 'top' : 'overview');
        event.currentTarget.textContent = top ? 'Angle view' : 'Top view';
    });
    for (const button of document.querySelectorAll('[data-pose]')) listener(button, 'click', () => pose(button.dataset.pose));
    listener($('replay'), 'click', replay);
    listener($('motion'), 'click', () => {
        motionOff = !motionOff;
        try { sessionStorage.setItem('ohmni:landing:motion', motionOff ? 'off' : 'on'); } catch { /* In-memory preference remains. */ }
        syncMotion();
        if (!motionOff && !motionQuery.matches) replay();
    });
    listener(motionQuery, 'change', syncMotion);
    listener(canvas, 'pointerdown', stopReveal);
    listener(canvas, 'keydown', stopReveal);
    listener(document, 'visibilitychange', () => { if (document.hidden) stopReveal(); });
    document.body.dataset.state = 'ready';
    // Explicit development-preview interface for deterministic captures. No app/project mutations.
    window.landingPrototype = { view, reference, displayReference, inventory, pose, closeUp, replay, dispose,
        stats: () => ({ triangles: Number(canvas.dataset.triangles), drawCalls: Number(canvas.dataset.drawCalls),
            refs: [...view.renderer.owners.keys()], camera: { ...view.camera },
            presentation: CONTROLLER_PRESENTATION }) };
    if (document.body.classList.contains('embedded')) replay();
}

listener(window, 'pagehide', dispose);
initialize().catch(error => { if (!disposed) fail(error); });
