import { BoardView, project } from '../board-view.js';
import { VisualRenderer } from '../visual-renderer.js';
import { validateLearningSource } from '../learning-model.js';
import { buildLandingBindings } from '../landing-pcb-bindings.js';
import { createLandingModelResolver } from '../landing-pcb-models.js';
import { createLandingMaterials, LANDING_PRESENTATION, LANDING_POSE } from '../landing-pcb-presentation.js';

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
    $('view-help').textContent = '3D view unavailable. Component descriptions remain illustrative.';
    loading.hidden = false;
    loading.textContent = 'The 3D view is unavailable. You can still read about this saved board below.';
    document.body.dataset.state = 'unavailable';
    document.body.dataset.failure = String(error?.message ?? error);
}

function selectPart(ref) {
    stopReveal(); selected = ref || '';
    $('part-select').value = selected;
    $('focus-part').disabled = !selected || !view?.available || view.disposed;
    const part = reference.components.find(item => item.ref === ref);
    $('part-title').textContent = part ? `${ref} · ${part.name?.human || part.part_id || ref}` : 'Sense & control';
    $('part-description').textContent = part?.purpose || part?.name?.detail
        || 'USB power, an ESP32 module and a small environmental sensor, assembled from the saved design.';
}

function pose(name = 'overview') {
    if (!view?.available || disposed) return;
    stopReveal(); view.interacted(); view.selected = null; selectPart('');
    const positions = { overview: LANDING_POSE, top: { yaw: 0, pitch: 88 * DEG },
        side: { yaw: -150 * DEG, pitch: 12 * DEG }, underside: { yaw: -150 * DEG, pitch: -40 * DEG } };
    Object.assign(view.camera, positions[name] ?? LANDING_POSE);
    view.options.showBack = view.camera.pitch < 0;
    view.setHighlight({}); view.frame();
    document.querySelectorAll('[data-pose]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.pose === name)));
}

function closeUp(ref = selected, frontal = false) {
    if (!ref || !view?.available) return;
    stopReveal(); view.select(ref); view.interacted();
    Object.assign(view.camera, frontal ? { yaw: Math.PI, pitch: 12 * DEG } : LANDING_POSE); view.frame();
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

async function initialize() {
    const response = await fetch('../reference-board.json', { signal: abort.signal });
    if (!response.ok) throw new Error('Saved reference unavailable');
    reference = await response.json();
    validateLearningSource(reference, { reference: true });
    inventory = buildLandingBindings(reference.board, reference.source);
    if (disposed) return;
    const baseline = new URLSearchParams(location.search).has('baseline');
    const finish = !new URLSearchParams(location.search).has('no-finish');
    view = new BoardView(canvas, { inputPolicy: 'landing', onSelect: selectPart, onRendererFailure: fail,
        rendererFactory: node => new VisualRenderer(node, baseline ? {} : {
            presentation: LANDING_PRESENTATION, materialFactory: () => createLandingMaterials({ finish }),
            instanceModelResolver: createLandingModelResolver(inventory),
        }) });
    if (!view.available) return;
    motionQuery = view.motionQuery;
    view.camera.distance = 190;
    view.options.showLabels = false;
    view.setBoard(reference.board); pose(); syncMotion();
    for (const item of reference.board.components) {
        const detail = reference.components.find(part => part.ref === item.ref);
        $('part-select').add(new Option(`${item.ref} — ${detail?.name?.human || item.part_id}`, item.ref));
    }
    $('part-controls').hidden = false; $('view-controls').hidden = false; loading.hidden = true; $('poster').hidden = true;
    const sourceText = `Saved capture ${reference.source.captured_on}. ${inventory.entries.length} source references. `
        + 'All visual bodies retain their declared package-approximation status; exact library compatibility is not established. '
        + 'The old saved LED pad mapping differs from the current approved binding; this study does not alter it or add a polarity mark. '
        + `Artifact ${reference.board.artifact_fingerprint}.`;
    $('source-detail').textContent = sourceText;
    downloadUrl = URL.createObjectURL(new Blob([JSON.stringify(inventory, null, 2)], { type: 'application/json' }));
    $('binding-download').href = downloadUrl; $('binding-download').download = 'landing-pcb-bindings.json';
    $('binding-download').hidden = false;
    listener($('part-select'), 'change', event => {
        if (view.available && !view.disposed) view.select(event.target.value || null);
        else selectPart(event.target.value || null);
    });
    listener($('focus-part'), 'click', () => closeUp());
    for (const button of document.querySelectorAll('[data-pose]')) listener(button, 'click', () => pose(button.dataset.pose));
    listener($('replay'), 'click', replay);
    listener($('motion'), 'click', () => {
        motionOff = !motionOff;
        try { sessionStorage.setItem('ohmni:landing:motion', motionOff ? 'off' : 'on'); } catch { /* In-memory preference remains. */ }
        syncMotion();
    });
    listener(motionQuery, 'change', syncMotion);
    listener(canvas, 'pointerdown', stopReveal);
    listener(canvas, 'keydown', stopReveal);
    listener(document, 'visibilitychange', () => { if (document.hidden) stopReveal(); });
    document.body.dataset.state = 'ready';
    // Explicit development-preview interface for deterministic captures. No app/project mutations.
    window.landingPrototype = { view, reference, inventory, pose, closeUp, replay, dispose,
        stats: () => ({ triangles: Number(canvas.dataset.triangles), drawCalls: Number(canvas.dataset.drawCalls),
            refs: [...view.renderer.owners.keys()], camera: { ...view.camera },
            presentation: baseline ? 'existing-default' : LANDING_PRESENTATION }) };
}

listener(window, 'pagehide', dispose);
initialize().catch(error => { if (!disposed) fail(error); });
