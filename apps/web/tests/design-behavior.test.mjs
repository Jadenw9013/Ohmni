import test from 'node:test';
import assert from 'node:assert/strict';
import { designRunModel, designResultHtml, designPanelHtml, statusTone, statusLabel } from '../design-behavior.js';

const SCOPE = 'Runs your circuit with the sourced reference model bound to each part.';
const binding = (ref, extra = {}) => ({ ref, part_id: `PART-${ref}`, package: '0603', candidates: [], entry_id: null,
    reference_part: null, behavior_state: null, problem: null, ...extra });

const refused = () => ({
    status: 'not_run', rating_status: 'not_run', ratings: null, analysis: 'op', limitations: [], components: [],
    problems: ['R1: No sourced behavior entry is bound to this catalog part and package',
        'U1: Several sourced entries fit this part; choose one explicitly: OHM-010, OHM-011',
        'D1: The catalog part is a red LED but the bound reference is Kingbright green; it is not substituted'],
    bindings: [binding('D1', { entry_id: 'OHM-020', reference_part: 'Kingbright green', behavior_state: 'simulated', problem: 'The catalog part is a red LED but the bound reference is Kingbright green; it is not substituted' }),
        binding('R1', { problem: 'No sourced behavior entry is bound to this catalog part and package' }),
        binding('U1', { candidates: ['OHM-010', 'OHM-011'], problem: 'Several sourced entries fit this part; choose one explicitly: OHM-010, OHM-011' })],
    design_summary: null, scope: SCOPE,
});

const ran = (summaryStatus, partStatuses) => ({
    status: 'ran', rating_status: summaryStatus, analysis: 'op', problems: [], scope: SCOPE,
    limitations: ['Copper heating is not simulated.'],
    bindings: Object.keys(partStatuses).map(ref => binding(ref, { entry_id: `OHM-${ref}`, reference_part: `Bound ${ref}`, behavior_state: 'simulated' })),
    components: Object.keys(partStatuses).map(ref => ({ ref, entry_id: `OHM-${ref}`, reference_part: `Simulated ${ref}`, measurements: [] })),
    ratings: { status: summaryStatus, components: Object.entries(partStatuses).map(([ref, status]) => ({ ref, status,
        reference_checks: [{ name: `${ref} power`, status: status === 'within_model_limits' ? 'within_limit' : status === 'violation' ? 'violation' : 'unknown', reason: status === 'unknown' ? 'No ambient declared' : null, spec_names: [] }],
        class_checks: [], failure_modes: [] })) },
    design_summary: { status: summaryStatus,
        counts: { within_model_limits: Object.values(partStatuses).filter(s => s === 'within_model_limits').length,
            unknown: Object.values(partStatuses).filter(s => s !== 'within_model_limits' && s !== 'violation').length,
            violation: Object.values(partStatuses).filter(s => s === 'violation').length },
        unknown_parts: Object.keys(partStatuses).filter(r => !['within_model_limits', 'violation'].includes(partStatuses[r])),
        violating_parts: Object.keys(partStatuses).filter(r => partStatuses[r] === 'violation') },
});

// Strip everything except the elements that carry a "pass" tone, then return their text.
const passTexts = html => [...html.matchAll(/<span class="badge pass">([^<]*)<\/span>/g)].map(m => m[1]);

test('a refused design lists every problem and every refused part, and claims no result', () => {
    const result = refused();
    const html = designResultHtml(result);
    const view = designRunModel(result);
    assert.equal(view.refused, true); assert.equal(view.within, false);
    assert.match(html, /Design refused: nothing was simulated/);
    assert.match(html, /Why the run was refused \(3\)/);
    for (const problem of result.problems) assert.ok(html.includes(problem.replace(/'/g, '&#39;')), problem);
    for (const ref of ['D1', 'R1', 'U1']) assert.match(html, new RegExp(`<td>${ref}</td>`));
    assert.match(html, /Bound reference/); assert.doesNotMatch(html, /Simulated as/);
    assert.match(html, /Kingbright green/); assert.match(html, /No bound reference/);
    assert.deepEqual(passTexts(html), []);
    assert.doesNotMatch(html, /Within the checked/);
    assert.ok(html.includes(SCOPE));
});

test('unknown, not-run and unrecognised statuses are never styled or worded as a pass', () => {
    for (const status of ['unknown', 'not_run', undefined, null, '', 'within', 'PASS', 'within_limits']) {
        assert.notEqual(statusTone(status), 'pass', String(status));
        assert.doesNotMatch(statusLabel(status), /^Within|pass/i, String(status));
    }
    const html = designResultHtml(ran('unknown', { C1: 'within_model_limits', R1: 'unknown', R2: 'not_run' }));
    assert.match(html, /Simulation ran; ratings not established for every part/);
    assert.deepEqual(passTexts(html).sort(), ['Within limit', 'Within the checked limits']);
    assert.match(html, /<td><span class="badge warn">Unknown, not established<\/span>/);
    assert.match(html, /<td><span class="badge warn">Not run, not checked<\/span>/);
    assert.match(html, /Design ratings: <span class="badge warn">Unknown, not established/);
    assert.match(html, /Parts not established: R1, R2/);
    // A part the ratings omit stays unknown rather than inheriting a pass.
    const missing = ran('unknown', { C1: 'within_model_limits' });
    missing.bindings.push(binding('Q1', { entry_id: 'OHM-Q1', reference_part: 'Bound Q1' }));
    const row = designRunModel(missing).parts.find(p => p.ref === 'Q1');
    assert.equal(row.status, 'unknown');
});

test('the design reads as within limits only when design_summary says so', () => {
    const within = ran('within_model_limits', { C1: 'within_model_limits', R1: 'within_model_limits' });
    assert.equal(designRunModel(within).within, true);
    assert.match(designResultHtml(within), /<h4>Within the checked model limits<\/h4>/);
    assert.match(designResultHtml(within), /Design ratings: <span class="badge pass">/);

    // Every part within limits but the summary is not: no design-level pass.
    const contradicted = ran('within_model_limits', { C1: 'within_model_limits' });
    contradicted.design_summary = { ...contradicted.design_summary, status: 'unknown' };
    assert.equal(designRunModel(contradicted).within, false);
    assert.doesNotMatch(designResultHtml(contradicted), /Within the checked model limits|Design ratings: <span class="badge pass">/);

    // A top-level rating status alone is not enough without the summary.
    const noSummary = { ...within, design_summary: null };
    assert.equal(designRunModel(noSummary).within, false);
    assert.doesNotMatch(designResultHtml(noSummary), /Within the checked model limits/);

    // A summary on a run that did not run is not a result.
    const stale = { ...within, status: 'failed' };
    assert.equal(designRunModel(stale).within, false);
    assert.doesNotMatch(designResultHtml(stale), /Within the checked|badge pass/);
    assert.match(designResultHtml(stale), /Simulation did not complete/);

    const violation = ran('violation', { C1: 'within_model_limits', R1: 'violation' });
    assert.match(designResultHtml(violation), /<h4>Rating violation<\/h4>/);
    assert.match(designResultHtml(violation), /Violating parts: R1/);
    assert.match(designResultHtml(violation), /Design ratings: <span class="badge fail">Violation/);
});

test('a run shows the reference each part was simulated as, the scope and the limitations', () => {
    const html = designResultHtml(ran('unknown', { R1: 'unknown' }));
    assert.match(html, /Simulated as/); assert.match(html, /Simulated R1 <small>OHM-R1<\/small>/);
    assert.ok(html.includes(SCOPE)); assert.match(html, /Copper heating is not simulated\./);
    assert.match(html, /No ambient declared/);
});

test('server text is escaped everywhere it is rendered', () => {
    const evil = '<img src=x onerror=alert(1)>';
    const result = ran('unknown', { R1: 'unknown' });
    result.scope = evil; result.limitations = [evil]; result.problems = [evil];
    result.bindings[0] = { ...result.bindings[0], part_id: evil, package: evil, problem: evil };
    result.components[0].reference_part = evil;
    result.ratings.components[0].reference_checks[0] = { name: evil, status: evil, reason: evil };
    result.ratings.components[0].basis = evil;
    result.design_summary.unknown_parts = [evil];
    result.design_summary.status = evil;
    const html = designResultHtml(result);
    assert.doesNotMatch(html, /<img/);
    assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
    const refusal = refused(); refusal.problems = [evil]; refusal.bindings[0].ref = evil;
    assert.doesNotMatch(designResultHtml(refusal), /<img/);
});

test('the panel without a saved project circuit is unavailable and offers no run', () => {
    const html = designPanelHtml(false);
    assert.match(html, /Unavailable for this result/); assert.doesNotMatch(html, /data-design-run/);
    assert.match(designPanelHtml(true), /data-design-run/);
});
