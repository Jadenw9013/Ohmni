import {escapeHtml as e} from './view-model.js';
const LABELS={normal:'Normal recording',missing_card:'Missing card',card_full:'Card full',slow_card:'Slow card / buffer overflow',card_removed:'Card removed',microphone_timeout:'Microphone timeout'};
export function recorderPanelHtml(recorder) {
    if(!recorder?.simulations?.length)return '';
    return `<section class="project-choice" data-recorder-panel><h2>Try the recorder simulation</h2><p>Digital simulation for this saved revision. Uses synthetic sound and modeled card timing; physical audio and power testing are pending.</p><label>Scenario<select data-recorder-scenario>${recorder.simulations.map(s=>`<option value="${e(s.scenario)}">${e(LABELS[s.scenario]||s.scenario)}</option>`).join('')}</select></label><div data-recorder-result aria-live="polite"></div><p>Firmware source, programming instructions and these simulation reports are included in Download build package.</p></section>`;
}
export function mountRecorderPanel(root,recorder) {
    root.innerHTML=recorderPanelHtml(recorder);root.hidden=!root.innerHTML;
    if(root.hidden)return;
    function render(){
        const result=recorder.simulations.find(s=>s.scenario===root.querySelector('[data-recorder-scenario]').value);
        const points=result.waveform.map((v,i)=>`${i*4},${40-v*30}`).join(' ');
        root.querySelector('[data-recorder-result]').innerHTML=`<p><strong>${e(result.error ? 'Modeled error: '+result.error.replaceAll('_',' ') : 'Synthetic recording finalized')}</strong></p><p>${result.sample_rate_hz.toLocaleString()} Hz · mono PCM16 · ${(result.saved_samples/result.sample_rate_hz).toFixed(2)} seconds saved in model.</p><p>Audio stream: ${result.required_write_bytes_per_second.toLocaleString()} bytes/second. Peak queued: ${result.queue_peak_bytes.toLocaleString()} of ${result.queue_capacity_bytes.toLocaleString()} bytes.</p><svg viewBox="0 0 512 80" role="img" aria-label="Synthetic test signal, not captured microphone audio"><polyline points="${points}" fill="none" stroke="currentColor" stroke-width="2"/></svg><p>${e(result.limitations.join(' '))}</p>`;
    }
    root.querySelector('[data-recorder-scenario]').addEventListener('change',render);render();
}
