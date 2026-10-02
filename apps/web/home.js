// Presentation only. Home navigation never creates/saves engineering intent itself.
import { readComponentLibrary, storyManifest } from './component-stories.js';
import { BoardView } from './board-view.js';
import { visualBoard } from './visual-explorer.js';

export const HOME_PARTS = Object.freeze([
    { id: 'ESP32-WROOM-32E', title: 'The processor', role: 'Runs the program you write. It reads inputs and decides what your circuit does next.' },
    { id: 'BME280', title: 'The sensor', role: 'Measures temperature, humidity and air pressure. Your program turns those readings into something useful.' },
    { id: 'USB_C_RECEPTACLE_16P', title: 'The power connection', role: 'Connects a USB cable to the board. A connector is one part of a power circuit; it does not regulate voltage by itself.' },
]);
export const homeRoute = hash => ['#workspace', '#sample-board', '#visual-proof'].includes(hash) ? 'workspace' : 'home';

export function homeSpecimen(library, id) {
    const part = library?.items?.find(item => item.part_id === id);
    const variant = part?.variants.find(v => v.eligibility.eligibility === 'LEARN_ONLY' && storyManifest(part, v));
    return variant ? { manifest: storyManifest(part, variant), package: variant.record.package_variant } : null;
}

export function initializeHome({ onStart = () => {}, readLibrary = readComponentLibrary,
    createView = canvas => new BoardView(canvas) } = {}) {
    const home = document.querySelector('#home'), workspace = document.querySelector('.app-layout');
    if (!home || !workspace) return;
    const $ = selector => home.querySelector(selector);
    let library = null, view = null, controller = null, generation = 0, selected = 0;
    let interactive = false, rotating = false;
    const motion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
    const dispose = () => { generation++; controller?.abort(); controller = null; view?.dispose(); view = null; };
    const status = text => { $('#home-model-status').textContent = text; };
    function controls() {
        $('#home-orbit').disabled = !view?.renderer;
        $('#home-orbit').setAttribute('aria-pressed', String(interactive));
        $('#home-orbit').textContent = interactive ? 'Stop interacting' : 'Interact with model';
        $('#home-spin').disabled = !view?.renderer || Boolean(motion?.matches);
        $('#home-spin').setAttribute('aria-pressed', String(rotating));
        $('#home-spin').textContent = rotating ? 'Pause rotation' : 'Rotate model';
    }
    function showPart() {
        const part = HOME_PARTS[selected];
        $('#home-part-title').textContent = part.title;
        $('#home-part-role').textContent = part.role;
        $('#home-part-id').textContent = part.id;
        home.querySelectorAll('[data-home-part]').forEach((button, i) => button.setAttribute('aria-pressed', String(i === selected)));
        const specimen = homeSpecimen(library, part.id);
        $('#home-model-placeholder').hidden = Boolean(specimen);
        $('#home-model-canvas').hidden = !specimen;
        if (!specimen) {
            view?.dispose(); view = null; controls();
            if (library) status('No model is available for this part. Its role is explained below.');
            return;
        }
        try {
            if (!view) view = createView($('#home-model-canvas'));
            view.renderer?.scene.background?.set('#f5f8fb');
            view.canvas.style.touchAction = interactive ? 'none' : 'pan-y';
            view.options.showLabels = false; view.options.showCopper = false; view.options.showSilk = false;
            view.setBoard(visualBoard(specimen.manifest));
            view.setOptions({ hideBoard: true, isolate: 'specimen', autoRotate: rotating });
            view.focus('specimen');
            status(view.renderer ? `Illustrative ${specimen.package} model. Shape and dimensions are approximate.` : '3D is unavailable on this device. You can still read about each component.');
        } catch {
            view?.dispose(); view = null;
            $('#home-model-placeholder').hidden = false;
            $('#home-model-canvas').hidden = true;
            status('3D is unavailable on this device. You can still read about each component.');
        }
        controls();
    }
    async function load() {
        dispose(); const request = generation;
        library = null; controller = new AbortController();
        $('#home-model-retry').hidden = true;
        status('Loading the component library…'); showPart();
        try {
            const result = await readLibrary(globalThis.fetch, controller.signal);
            if (request !== generation || home.hidden) return;
            library = result; showPart();
        } catch (error) {
            if (request !== generation || error.name === 'AbortError') return;
            status('The component library could not load. You can retry or start a project.');
            $('#home-model-retry').hidden = false;
        }
    }
    function route({ focus = true } = {}) {
        const atHome = homeRoute(location.hash) === 'home';
        home.hidden = !atHome; workspace.hidden = atHome;
        document.querySelector('.skip-link').href = atHome ? '#home-title' : '#main-content';
        document.title = atHome ? 'Ohmni — Build circuits. Understand why.' : 'Ohmni — Your workbench';
        if (atHome) { if (!view) void load(); }
        else dispose();
        if (focus) {
            const target = atHome ? $('#home-title') : document.querySelector('.stage:not([hidden]) h1');
            target?.setAttribute('tabindex', '-1'); target?.focus({ preventScroll: true });
            window.scrollTo({ top: 0, behavior: 'instant' });
        }
    }
    home.querySelectorAll('[data-home-part]').forEach((button, i) => button.addEventListener('click', () => { selected = i; showPart(); }));
    home.querySelectorAll('[data-home-start]').forEach(button => button.addEventListener('click', event => {
        event.preventDefault();
        history.pushState(null, '', '#workspace'); route({ focus: false }); onStart();
    }));
    $('#home-orbit').addEventListener('click', () => {
        interactive = !interactive;
        const canvas = $('#home-model-canvas'); canvas.dataset.interactive = String(interactive);
        canvas.style.pointerEvents = interactive ? 'auto' : 'none'; canvas.tabIndex = interactive ? 0 : -1;
        canvas.style.touchAction = interactive ? 'none' : 'pan-y';
        controls(); if (interactive) canvas.focus();
    });
    $('#home-spin').addEventListener('click', () => {
        rotating = !rotating && !motion?.matches; view?.setOptions({ autoRotate: rotating }); controls();
    });
    motion?.addEventListener('change', () => { if (motion.matches) rotating = false; view?.setOptions({ autoRotate: rotating }); controls(); });
    $('#home-model-retry').addEventListener('click', () => void load());
    window.addEventListener('hashchange', () => route());
    // pushState above handles its own route; Back/Forward emit hashchange.
    window.addEventListener('pagehide', dispose);
    window.addEventListener('pageshow', event => { if (event.persisted) route({ focus: false }); });
    route({ focus: false });
}
