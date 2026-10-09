// Landing presentation only. No engineering requests or generated verdicts.
export const homeRoute = hash => ['#workspace', '#sample-board', '#visual-proof'].includes(hash) ? 'workspace' : 'home';
export const HOME_GUIDES = Object.freeze({
    docs: { title: 'From idea to circuit', sections: [
        ['Choose a project', 'Start with a USB-powered ESP32 sensor, button controller or memory board. Pick its features and give it a name.'],
        ['Save, then inspect', 'Save a revision before generating your board. Explore its components, connections and recorded engineering checks.'],
        ['Learn as you go', 'Open Learn or select a callout to meet a component. Try a temporary layout to practice arranging parts; it does not edit a saved PCB.'],
        ['Keep your work', 'Project revisions are saved on this local server, with no cloud sync. Unsaved changes are lost on reload.']
    ] },
    checks: { title: 'Know what was actually checked', sections: [
        ['Evidence before confidence', 'A model can propose a design. Deterministic checks evaluate the circuit, and source evidence supports component facts.'],
        ['Read the result', 'Checks can pass, fail, lack enough information, be inapplicable or encounter an error. Missing evidence never counts as a pass.'],
        ['A board still needs testing', 'Geometry does not prove electrical behavior. Assembly, firmware and hardware testing remain necessary; Ohmni boards have not been bench-tested.']
    ] },
    limits: { title: 'A focused local prototype', sections: [
        ['Supported projects', 'USB-powered ESP32 sensor, button-and-light and memory boards. This is not a general-purpose PCB editor.'],
        ['Models and real data', 'The landing board is an authored controller concept with named components and recorded circuit and geometry checks. Explore demo opens the separate saved engineering example. Neither has been hardware-tested.'],
        ['Your files and revisions', 'Projects are stored on this server, not synced to the cloud. Save before reloading. Available files and release eligibility depend on the actual engineering results.']
    ] }
});

export function initializeHome({ onStart = () => {}, onDemo = () => {} } = {}) {
    const home = document.querySelector('#home'), workspace = document.querySelector('.app-layout');
    if (!home || !workspace) return;
    const info = document.querySelector('#home-info');
    let opener = null;
    function guide(kind, source) {
        const copy = HOME_GUIDES[kind]; if (!copy) return;
        opener = source;
        document.querySelector('#home-info-title').textContent = copy.title;
        const content = document.querySelector('#home-info-content'); content.replaceChildren();
        for (const [title, body] of copy.sections) {
            const heading = document.createElement('h3'), paragraph = document.createElement('p');
            heading.textContent = title; paragraph.textContent = body; content.append(heading, paragraph);
        }
        info.showModal();
    }
    function route({ focus = true } = {}) {
        if (info.open) info.close();
        const atHome = homeRoute(location.hash) === 'home';
        home.hidden = !atHome; workspace.hidden = atHome;
        document.querySelector('.skip-link').href = atHome ? '#home-title' : '#main-content';
        document.title = atHome ? 'Ohmni — Design. Understand. Build.' : 'Ohmni — Your workbench';
        if (focus) {
            const target = document.querySelector(atHome ? '#home-title' : '.stage:not([hidden]) h1');
            target?.setAttribute('tabindex', '-1'); target?.focus({ preventScroll: true });
            window.scrollTo({ top: 0, behavior: 'instant' });
        }
    }
    function enterWorkspace(event, action) {
        event.preventDefault();
        history.pushState(null, '', '#workspace'); route({ focus: false }); action();
    }
    home.querySelectorAll('[data-home-start]').forEach(button => button.addEventListener('click', event => enterWorkspace(event, onStart)));
    home.querySelectorAll('[data-home-demo]').forEach(button => button.addEventListener('click', event => enterWorkspace(event, onDemo)));
    home.querySelectorAll('[data-home-info]').forEach(button => button.addEventListener('click', () => guide(button.dataset.homeInfo, button)));
    home.querySelector('[data-home-info-close]').addEventListener('click', () => info.close());
    info.addEventListener('close', () => opener?.focus());
    window.addEventListener('hashchange', () => route());
    window.addEventListener('pageshow', event => { if (event.persisted) route({ focus: false }); });
    route({ focus: false });
}
