import { API_BASE, fetchHealth, pollHeaders, sameIdentity } from './client-contract.js';

const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const friendly = value => String(value ?? 'Unknown').replaceAll('_',' ');
const valueText = value => value && Number.isFinite(value.value) ? `${Number(value.value.toPrecision(6))} ${value.unit}` : 'Unknown';

export function behaviorResultModel(result) {
    const ran = result?.status === 'ran';
    const violation = result?.rating_status === 'violation';
    return {
        title: violation ? 'Rating violation' : ran ? 'Simulation ran' : 'Simulation not run',
        ran, violation,
        rating: violation ? 'Violation' : ran && result?.rating_status === 'within_model_limits' ? 'Within the checked limits' : 'Unknown / not checked',
        components: ran && Array.isArray(result?.components) ? result.components : [],
        transient: ran ? result?.transient : null,
        problems: Array.isArray(result?.problems) ? result.problems : [],
    };
}

export function behaviorMetadataHtml(data) {
    return `<p class="behavior-reference">${escape(data.reference_part ?? 'No bound reference')}</p>
        <div class="behavior-badges"><span>Source: ${escape(friendly(data.source_status))}</span>${data.classes.map(c =>
            `<span>${escape(friendly(c.fidelity))}</span><span>Model confidence: ${escape(c.confidence?.model ?? 'Unknown')}</span>`).join('')}</div>
        <p class="story-muted">${escape(data.scope)}</p>
        ${data.available ? `<p>${escape(data.package)} · ${data.analysis === 'tran' ? 'Transient response' : 'DC operating point'}</p>` : `<div class="behavior-blocked"><strong>Not simulable</strong><ul>${data.blockers.map(reason => `<li>${escape(reason)}</li>`).join('')}</ul></div>`}
        <button type="button" class="behavior-run" data-behavior-run ${data.available ? '' : 'disabled'}>Run reference circuit</button>
        <p class="behavior-run-status" role="status" aria-live="polite" data-behavior-run-status>Not run.</p>
        <div data-behavior-results></div>
        ${data.limitations.length ? `<details><summary>Model scope and limitations</summary><ul>${data.limitations.map(value => `<li>${escape(value)}</li>`).join('')}</ul></details>` : ''}`;
}

function traceHtml(curve) {
    if (!curve?.series?.length || !curve.time_s?.length) return '';
    return `<div class="behavior-traces">${curve.series.map(series => {
        const values=series.values;
        if (!Array.isArray(values) || !values.length || values.some(v => !Number.isFinite(v))) return '';
        if (curve.time_s.length!==values.length || curve.time_s.some(t => !Number.isFinite(t))) return '';
        const min=Math.min(...values),max=Math.max(...values),span=max-min || 1;
        const start=curve.time_s[0],duration=curve.time_s.at(-1)-start || 1;
        const points=values.map((v,i) => `${10+280*(curve.time_s[i]-start)/duration},${100-80*(v-min)/span}`).join(' ');
        return `<figure><figcaption>${escape(series.name)} · ${escape(Number(min.toPrecision(5)))} to ${escape(Number(max.toPrecision(5)))} V</figcaption><svg viewBox="0 0 300 115" role="img" aria-label="${escape(series.name)} transient trace"><polyline points="${points}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></figure>`;
    }).join('')}</div><p class="story-muted">${escape(curve.sample_count)} display samples · ${escape(curve.time_s.at(-1))} seconds. Display sampling does not establish pulse or timing limits.</p>`;
}

export function behaviorResultHtml(result) {
    const view=behaviorResultModel(result);
    const ratings=view.ran ? (result?.ratings?.components ?? []) : [];
    return `<section class="behavior-result ${view.violation ? 'has-violation' : ''}" aria-label="Simulation result">
        <h4>${escape(view.title)}</h4><p>${view.ran ? 'ngspice returned observations.' : 'No successful simulation observations are available.'} Ratings: <strong>${escape(view.rating)}</strong>.</p>
        ${view.problems.length ? `<ul>${view.problems.map(p => `<li>${escape(p)}</li>`).join('')}</ul>` : ''}
        ${view.components.map(component => `<h5>${escape(component.ref)} · ${escape(component.reference_part ?? component.entry_id)}</h5>
            <p class="story-muted">${escape(friendly(component.fidelity))} · source ${escape(component.source_status)} · model confidence ${escape(component.confidence)}</p>
            ${component.measurements?.length ? `<table><thead><tr><th>Role</th><th>Voltage</th><th>Current into pin</th></tr></thead><tbody>${component.measurements.map(m => `<tr><td>${escape(m.role)}</td><td>${escape(valueText(m.voltage))}</td><td>${escape(valueText(m.current_into_pin))}</td></tr>`).join('')}</tbody></table>` : ''}`).join('')}
        ${traceHtml(view.transient)}
        ${ratings.map(component => `<details><summary>${escape(component.ref)} checks · ${escape(friendly(component.status))}</summary>
            <ul>${[...(component.reference_checks ?? []),...(component.class_checks ?? [])].map(check => `<li><strong>${escape(check.name)}: ${escape(friendly(check.status))}</strong>${check.reason ? `<br>${escape(check.reason)}` : ''}</li>`).join('')}</ul>
            <h5>Failure responses</h5><ul>${(component.failure_modes ?? []).map(f => `<li>${escape(f.id)}: ${escape(friendly(f.status))}. ${escape(f.applied_response ?? f.reason ?? '')}${f.unresolved_response ? ` ${escape(f.unresolved_response)}` : ''}</li>`).join('')}</ul></details>`).join('')}
        ${result?.failure_rerun ? `<p>Separate failure approximation: ${escape(friendly(result.failure_rerun.status))}. ${escape(result.failure_rerun.limitation)}</p>` : ''}
        <p class="story-muted">A numerical result is not a safety, manufacturing or physical-fit approval.</p>
        ${result?.version_output ? `<details><summary>Simulator version and run identity</summary><pre>${escape(result.version_output)}</pre><p>${escape(result.netlist_sha256)}</p></details>` : ''}
    </section>`;
}

export function mountBehaviorPanel(container, entryId) {
    const controller=new AbortController();let disposed=false;
    const fetcher=(url,options={}) => fetch(url,{...options,signal:controller.signal});
    container.innerHTML='<h4>Electrical behavior</h4><p role="status">Loading the reference model…</p>';
    async function load() {
        try {
            const identity=await fetchHealth(fetcher);
            const response=await fetcher(`${API_BASE}/api/behavior/${encodeURIComponent(entryId)}`,{cache:'no-store',headers:pollHeaders(identity)});
            if (!response.ok) throw new Error('unavailable');
            const payload=await response.json();
            if (!sameIdentity(payload,identity) || payload.component?.entry_id!==entryId) throw new Error('mismatch');
            if (disposed) return;
            container.innerHTML='<h4>Electrical behavior</h4>'+behaviorMetadataHtml(payload.component);
            const button=container.querySelector('[data-behavior-run]');
            button.onclick=async () => {
                button.disabled=true;
                const output=container.querySelector('[data-behavior-results]');output.replaceChildren();
                const status=container.querySelector('[data-behavior-run-status]');status.textContent='Running the reference circuit…';
                try {
                    const run=await fetcher(`${API_BASE}/api/behavior/${encodeURIComponent(entryId)}/run`,{method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({api_version:identity.api_version,server_instance_id:identity.server_instance_id,ui_version:identity.ui_version})});
                    if (!run.ok) throw new Error('not_run');
                    const payload=await run.json();
                    if (!sameIdentity(payload,identity) || payload.result?.entry_id!==entryId) throw new Error('mismatch');
                    if (disposed) return;
                    output.innerHTML=behaviorResultHtml(payload.result);
                    status.textContent=behaviorResultModel(payload.result).title+'.';
                } catch {
                    if (disposed) return;
                    output.innerHTML=behaviorResultHtml({status:'not_run',problems:['The reference run is unavailable. Retry after checking the local simulator or active run.']});
                    status.textContent='Simulation not run.';
                } finally { if (!disposed) button.disabled=false; }
            };
        } catch {
            if (!disposed) container.innerHTML='<h4>Electrical behavior unavailable</h4><p>No simulation ran. The local behavior service could not be loaded.</p><button type="button" data-behavior-retry>Retry</button>';
            container.querySelector('[data-behavior-retry]')?.addEventListener('click',load,{once:true});
        }
    }
    void load();
    return () => { disposed=true;controller.abort(); };
}
