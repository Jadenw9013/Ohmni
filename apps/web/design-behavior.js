// Design-level behavior run for the saved project's own circuit.
//
// Every verdict here is copied from the server's design run. The page decides
// nothing: a design reads as within limits only when `design_summary.status`
// says `within_model_limits`, and any other value (unknown, not run, missing,
// or a status this page does not know) is shown as not established, never as a
// pass in words, colour or icon.

import { API_BASE, pollHeaders, sameIdentity } from './client-contract.js';
import { splitChecks } from './component-behavior.js';

const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const friendly = value => String(value ?? 'unknown').replaceAll('_',' ');
const list = value => Array.isArray(value) ? value : [];

// Only an exact positive status earns the pass tone; everything else is warn or fail.
export function statusTone(status) {
    if (status === 'within_model_limits' || status === 'within_limit') return 'pass';
    if (status === 'violation') return 'fail';
    return 'warn';
}

export function statusLabel(status) {
    if (status === 'within_model_limits') return 'Within the checked limits';
    if (status === 'within_limit') return 'Within limit';
    if (status === 'violation') return 'Violation';
    if (status === 'not_run') return 'Not run, not checked';
    // Any other value, including one that looks positive, is not echoed: it is not a known verdict.
    return 'Unknown, not established';
}

const statusBadge = status => `<span class="badge ${statusTone(status)}">${escape(statusLabel(status))}</span>`;

export function designRunModel(result) {
    const ran = result?.status === 'ran';
    const summary = ran && result?.design_summary && typeof result.design_summary === 'object' ? result.design_summary : null;
    const violation = summary?.status === 'violation' || result?.rating_status === 'violation';
    const within = !violation && summary?.status === 'within_model_limits';
    const problems = list(result?.problems);
    const refused = result?.status === 'not_run' && (problems.length > 0 || list(result?.bindings).some(row => row?.problem));
    const title = violation ? 'Rating violation'
        : within ? 'Within the checked model limits'
        : ran ? 'Simulation ran; ratings not established for every part'
        : refused ? 'Design refused: nothing was simulated'
        : result?.status && result.status !== 'not_run' ? 'Simulation did not complete: nothing was established'
        : 'Design not run: nothing was simulated';
    const ratings = ran ? list(result?.ratings?.components) : [];
    const byRef = new Map(ratings.map(row => [row?.ref, row]));
    const simulated = ran ? new Map(list(result?.components).map(c => [c?.ref, c])) : new Map();
    const parts = list(result?.bindings).map(row => ({
        ref: row?.ref, part_id: row?.part_id, package: row?.package, entry_id: row?.entry_id,
        // What actually ran when the design ran; otherwise only the reference it would bind to.
        reference: ran ? (simulated.get(row?.ref)?.reference_part ?? row?.reference_part) : row?.reference_part,
        problem: row?.problem,
        status: ran ? (byRef.get(row?.ref)?.status ?? 'unknown') : 'not_run',
        rating: byRef.get(row?.ref) ?? null,
    }));
    return { ran, refused, violation, within, title, problems, parts, summary,
        summaryStatus: violation ? 'violation' : within ? 'within_model_limits'
            : ran ? (summary?.status && summary.status !== 'within_model_limits' ? summary.status : 'unknown') : 'not_run' };
}

function checksHtml(rating) {
    if (!rating) return '';
    const split = splitChecks(rating);
    const rows = [...split.reference, ...split.classChecks];
    return `<details><summary>${escape(rating.ref)} checks (${rows.length})</summary>${rating.basis ? `<p class="panel-note">Basis: ${escape(rating.basis)}</p>` : ''}<ul>${rows.length
        ? rows.map(check => `<li>${statusBadge(check.status)} ${escape(friendly(check.name))}${check.reason ? `<br>${escape(check.reason)}` : ''}</li>`).join('')
        : '<li>No check is bound to this part; its ratings stay unknown.</li>'}</ul></details>`;
}

export function designResultHtml(result) {
    const view = designRunModel(result);
    const summary = view.summary;
    const counts = summary?.counts ?? {};
    const limitations = [...list(result?.limitations), ...list(result?.ac?.limitations)];
    return `<section class="design-behavior-result" aria-label="Design behavior result">
        <h4>${escape(view.title)}</h4>
        <p>Design ratings: ${statusBadge(view.summaryStatus)}</p>
        ${result?.scope ? `<p class="panel-note">${escape(result.scope)}</p>` : ''}
        ${view.problems.length ? `<div class="design-behavior-problems"><strong>${view.refused ? 'Why the run was refused' : 'Problems'} (${view.problems.length})</strong><ul>${view.problems.map(p => `<li>${escape(p)}</li>`).join('')}</ul></div>` : ''}
        ${summary ? `<dl class="design-behavior-summary"><div><dt>Within limits</dt><dd>${escape(counts.within_model_limits ?? 0)}</dd></div><div><dt>Unknown</dt><dd>${escape(counts.unknown ?? 0)}</dd></div><div><dt>Violation</dt><dd>${escape(counts.violation ?? 0)}</dd></div></dl>
            ${list(summary.violating_parts).length ? `<p>Violating parts: ${list(summary.violating_parts).map(escape).join(', ')}</p>` : ''}
            ${list(summary.unknown_parts).length ? `<p>Parts not established: ${list(summary.unknown_parts).map(escape).join(', ')}</p>` : ''}` : ''}
        ${view.parts.length ? `<table class="design-behavior-parts"><thead><tr><th>Part</th><th>Catalog part</th><th>${view.ran ? 'Simulated as' : 'Bound reference'}</th><th>Ratings</th></tr></thead><tbody>${view.parts.map(part => `<tr>
            <td>${escape(part.ref)}</td><td>${escape(part.part_id)} · ${escape(part.package)}</td>
            <td>${part.reference ? `${escape(part.reference)}${part.entry_id ? ` <small>${escape(part.entry_id)}</small>` : ''}` : 'No bound reference'}</td>
            <td>${statusBadge(part.status)}${part.problem ? `<br>${escape(part.problem)}` : ''}</td></tr>`).join('')}</tbody></table>` : ''}
        ${view.parts.map(part => checksHtml(part.rating)).join('')}
        ${limitations.length ? `<details open><summary>Limitations of this run</summary><ul>${limitations.map(l => `<li>${escape(l)}</li>`).join('')}</ul></details>` : ''}
        <p class="panel-note">A numerical result is not a safety, manufacturing or physical-fit approval.</p>
    </section>`;
}

export function designPanelHtml(available) {
    return `<h3>Run your circuit's electrical behavior</h3>
        <p class="panel-note">Simulates this project's own circuit at its DC operating point, each part on its bound sourced reference model, and checks every part's ratings together. It does not change your project.</p>
        ${available
            ? '<button type="button" class="secondary" data-design-run>Run operating point</button>'
            : '<p><strong>Unavailable for this result.</strong> Only a saved project records the circuit a design run needs; nothing was simulated.</p>'}
        <p role="status" aria-live="polite" data-design-status>${available ? 'Not run.' : 'Not run, not checked.'}</p>
        <div data-design-results></div>`;
}

const notRun = message => ({ status: 'not_run', rating_status: 'not_run', problems: [message], bindings: [], limitations: [] });

export function mountDesignBehaviorPanel(container, { jobId, identity, circuitHash, fetcher = globalThis.fetch } = {}) {
    if (!container) return () => {};
    const available = typeof jobId === 'string' && !!identity && /^[0-9a-f]{64}$/.test(circuitHash ?? '');
    container.hidden = false;
    container.innerHTML = designPanelHtml(available);
    if (!available) return () => {};
    const controller = new AbortController(); let disposed = false;
    const request = (url, options = {}) => fetcher(url, { ...options, signal: controller.signal });
    const button = container.querySelector('[data-design-run]');
    const status = container.querySelector('[data-design-status]');
    const output = container.querySelector('[data-design-results]');
    button.onclick = async () => {
        button.disabled = true; output.replaceChildren(); status.textContent = 'Running your circuit…';
        let result;
        try {
            const source = await request(`${API_BASE}/api/jobs/${encodeURIComponent(jobId)}/circuit`, { cache: 'no-store', headers: pollHeaders(identity) });
            if (!source.ok) throw new Error('circuit');
            const saved = await source.json();
            if (!sameIdentity(saved, identity) || saved.circuit_hash !== circuitHash) throw new Error('circuit');
            const run = await request(`${API_BASE}/api/behavior/design/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_version: identity.api_version, server_instance_id: identity.server_instance_id, ui_version: identity.ui_version,
                    design: { circuit: saved.circuit, analysis: 'op' } }) });
            if (run.status === 409) {
                const body = await run.json().catch(() => ({}));
                throw new Error(body?.error === 'behavior_run_busy' ? 'busy' : 'mismatch');
            }
            if (!run.ok) throw new Error('not_run');
            const payload = await run.json();
            // A result for another circuit or server is not this project's result.
            if (!sameIdentity(payload, identity) || payload.result?.circuit_hash !== circuitHash) throw new Error('mismatch');
            result = payload.result;
        } catch (error) {
            result = notRun(error?.message === 'circuit' ? "This project's saved circuit is unavailable, so nothing was simulated."
                : error?.message === 'busy' ? 'Another behavior run is active. Nothing was simulated; retry when it finishes.'
                : 'The design run is unavailable. Nothing was simulated; retry after checking the local simulator.');
        }
        if (disposed) return;
        output.innerHTML = designResultHtml(result);
        status.textContent = designRunModel(result).title + '.';
        button.disabled = false;
    };
    return () => { disposed = true; controller.abort(); };
}
