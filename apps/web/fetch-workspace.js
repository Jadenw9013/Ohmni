import { BoardView } from './board-view.js';
import { mountBoardControls } from './board-controls.js';

const $ = selector => document.querySelector(selector);
const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
};

export function accessToken(location, storage) {
    const fromLink = new URLSearchParams(location.hash.slice(1)).get('access');
    const token = fromLink || storage?.getItem('ohmni-workspace-access');
    if (!/^[A-Za-z0-9_-]{43}$/.test(token || '')) throw new Error('Open the private “Open your board in Ohmni” link from Fetch chat. Send OPEN there to get one.');
    // The token never enters a query string, referrer, analytics or a server access log.
    if (fromLink) { try { storage?.setItem('ohmni-workspace-access', token); } catch { /* Fragment remains reloadable. */ } }
    return token;
}

export function validateBoard(data) {
    if (!data || !/^[a-f0-9]{12}$/.test(data.job_id || '') || !data.experience?.board
        || !Array.isArray(data.experience.components) || !Array.isArray(data.experience.board.components)
        || !data.experience.components.length) throw new Error('The build did not provide an interactive board. Ask Fetch chat for STATUS.');
    const refs = new Set(data.experience.board.components.map(x => x.ref));
    if (data.experience.components.some(x => !refs.has(x.ref))) throw new Error('The component list does not match this board. Ask Fetch chat for STATUS.');
    return data;
}

export async function mountWorkspace({fetcher = globalThis.fetch, View = BoardView} = {}) {
    let token, data, view, controls, selected = null, busy = false;
    const threads = new Map();
    const status = text => { $('#teaching-status').textContent = text; };
    async function api(path, payload) {
        const response = await fetcher(`/workspace/api/${path}`, {
            method: payload ? 'POST' : 'GET', cache: 'no-store',
            headers: {Authorization: `Bearer ${token}`, ...(payload ? {'Content-Type': 'application/json'} : {})},
            ...(payload ? {body: JSON.stringify(payload)} : {}),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ohmni is unavailable. Try again; your saved design has not changed.');
        }
        return response;
    }
    function transcript() {
        const container = $('#conversation'); container.replaceChildren();
        for (const entry of threads.get(selected) || []) {
            const box = node('article', undefined, `message ${entry.role}`);
            box.append(node('h3', entry.role === 'user' ? 'You' : `Ohmni · ${entry.component}`), node('div', entry.text));
            if (entry.answer) {
                if (entry.answer.unknowns.length) box.append(node('p', 'Still unknown: ' + entry.answer.unknowns.join(' ')));
                box.append(node('p', entry.answer.notice, 'fine'));
                const details = node('details'); details.append(node('summary', 'Records used in this explanation'));
                for (const source of entry.answer.sources) details.append(node('h4', source.label), node('pre', JSON.stringify(source.value, null, 2)));
                box.append(details);
                const followups = node('div', undefined, 'followups');
                for (const question of entry.answer.next_questions) {
                    const button = node('button', question); button.type = 'button';
                    button.addEventListener('click', () => { $('#question').value = question; $('#question').focus(); });
                    followups.append(button);
                }
                box.append(followups);
            }
            container.append(box);
        }
        container.scrollTop = container.scrollHeight;
    }
    function select(ref) {
        const card = data.experience.components.find(x => x.ref === ref);
        selected = card ? ref : null;
        $('#selection').replaceChildren();
        for (const button of $('#parts').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.ref === selected));
        $('#starters').hidden = !card;
        $('#question').disabled = !card || busy; $('#send').disabled = !card || busy;
        $('#question').value = ''; status('');
        if (!card) { $('#selection').append(node('h2', 'Every part has a purpose.'), node('p', 'Select a component to learn about it.')); transcript(); return; }
        const placed = data.experience.board.components.find(x => x.ref === ref);
        $('#selection').append(node('h2', card.name?.human || ref), node('p', `${ref} · ${card.part_id}`, 'fine'), node('p', card.purpose));
        const dl = node('dl');
        for (const [label, value] of [['Value', card.value], ['Connections', placed.net_names?.join(' · ')], ['Assembly', card.assembly_reason || card.assembly_difficulty]]) {
            if (value) dl.append(node('dt', label), node('dd', value));
        }
        $('#selection').append(dl); transcript();
    }
    function parts(filter = '') {
        const list = $('#parts'); list.replaceChildren();
        for (const card of data.experience.components) {
            if (!`${card.ref} ${card.part_id} ${card.name?.human}`.toLowerCase().includes(filter.toLowerCase())) continue;
            const button = node('button'); button.type = 'button'; button.dataset.ref = card.ref;
            button.setAttribute('aria-pressed', String(selected === card.ref));
            button.append(node('strong', `${card.ref} · ${card.name?.human || card.part_id}`), node('span', card.part_id));
            button.addEventListener('click', () => view ? view.select(card.ref) : select(card.ref));
            list.append(button);
        }
        if (!list.children.length) list.append(node('p', 'No matching components.'));
    }
    try {
        let storage; try { storage = globalThis.sessionStorage; } catch { /* Private browser may deny storage. */ }
        token = accessToken(globalThis.location, storage);
        data = validateBoard(await (await api('board')).json());
        for (const [ref, messages] of Object.entries(data.conversations || {})) {
            if (data.experience.components.some(x => x.ref === ref)) threads.set(ref, messages.map(x => ({...x, component: ref})));
        }
        $('#title').textContent = data.brief.project_name;
        $('#identity').textContent = `Build ${data.job_id} · Revision ${data.revision_number} · ${data.brief.board_width_mm} × ${data.brief.board_height_mm} mm`;
        const unknown = data.requirements.filter(x => x.status === 'UNKNOWN').length;
        const violated = data.requirements.filter(x => x.status === 'VIOLATED').length;
        $('#outcome').textContent = `${String(data.outcome).replaceAll('_', ' ')} · ${violated} unmet · ${unknown} not yet verified. Firmware and physical testing are separate.`;
        $('#loading').hidden = true; $('#workspace').hidden = false;
        try {
            view = new View($('#board'), {onSelect: select});
            view.setBoard(data.experience.board);
            controls = mountBoardControls($('#controls'), view, {stage: $('.board-stage'), fullscreen: true});
            if (view.available === false) $('#renderer-note').textContent = '3D is unavailable in this browser. Component selection and teaching remain available below.';
        } catch {
            view = null;
            $('#renderer-note').textContent = '3D could not start. Try a browser with WebGL enabled; you can still explore the component list.';
        }
        parts();
        const results = node('ul');
        for (const item of data.verification) results.append(node('li', `${item.stage}: ${item.status}. ${item.detail || ''}`));
        for (const item of data.requirements.filter(x => x.status !== 'MET')) results.append(node('li', `${item.label}: ${item.status}. ${item.detail || item.display_value || ''}`));
        $('#findings').append(results);
        $('#search').addEventListener('input', event => parts(event.target.value));
        $('#starters').addEventListener('click', event => {
            const question = event.target.closest('[data-question]')?.dataset.question;
            if (question) { $('#question').value = question; $('#question').focus(); }
        });
        $('#ask').addEventListener('submit', async event => {
            event.preventDefault();
            if (!selected || busy || !$('#question').value.trim()) return;
            const component = selected, question = $('#question').value.trim();
            busy = true; $('#send').disabled = true; $('#question').disabled = true; status('Ohmni is preparing an explanation…');
            try {
                const answer = await (await api('teach', {component, question})).json();
                if (answer.job_id !== data.job_id || answer.component !== component || !Array.isArray(answer.sources)) throw new Error('This answer does not match your selected build. Please try again.');
                threads.set(component, [...(threads.get(component) || []), {role: 'user', text: question}, {role: 'assistant', text: answer.explanation, component, answer}]);
                if (selected === component) { transcript(); $('#question').value = ''; }
                status(selected === component ? '' : `The answer for ${component} is ready. Select that component to read it.`);
            } catch (error) { status(error.message); }
            finally { busy = false; $('#send').disabled = !selected; $('#question').disabled = !selected; }
        });
        $('#download').addEventListener('click', async () => {
            $('#download').disabled = true;
            try {
                const blob = await (await api('download')).blob();
                const url = URL.createObjectURL(blob), link = node('a'); link.href = url; link.download = `ohmni-${data.job_id}.zip`; link.click();
                setTimeout(() => URL.revokeObjectURL(url), 10000);
            } catch (error) { status(error.message); }
            finally { $('#download').disabled = false; }
        });
        const resize = () => view?.frame(); globalThis.addEventListener('resize', resize);
        return {data, select, view, dispose: () => { controls?.dispose(); view?.dispose?.(); globalThis.removeEventListener('resize', resize); }};
    } catch (error) {
        $('#loading').hidden = true; $('#error').hidden = false; $('#error').textContent = error.message;
        const retry = node('button', 'Try again'); retry.addEventListener('click', () => globalThis.location.reload()); $('#error').append(node('p', 'Return to your original Fetch conversation and send OPEN for a fresh private link.'), retry);
        return null;
    }
}

if (typeof document !== 'undefined' && document.querySelector('#workspace')) void mountWorkspace();
