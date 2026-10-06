import test from 'node:test';
import assert from 'node:assert/strict';
import { behaviorResultModel, behaviorResultHtml, behaviorMetadataHtml } from '../component-behavior.js';

test('failed and non-run responses cannot retain old measurements or passing checks', () => {
    for (const status of ['not_run','failed','timed_out','unavailable',undefined]) {
        const result={status,rating_status:'within_model_limits',components:[{ref:'STALE'}],
            ratings:{components:[{ref:'STALE',class_checks:[{name:'old',status:'within_limit'}]}]},
            transient:{series:[{name:'STALE',values:[1,2]}],time_s:[0,1]}};
        const view=behaviorResultModel(result),html=behaviorResultHtml(result);
        assert.equal(view.ran,false);assert.equal(view.rating,'Unknown / not checked');
        assert.equal(view.components.length,0);assert.equal(view.transient,null);
        assert.doesNotMatch(html,/STALE|Within the checked limits|within limit/);
        assert.match(html,/Simulation not run/);
    }
});

test('a recorded rating violation survives a successful or non-run result', () => {
    for (const status of ['ran','not_run','failed']) {
        const view=behaviorResultModel({status,rating_status:'violation'});
        assert.equal(view.violation,true);assert.equal(view.title,'Rating violation');
        assert.match(behaviorResultHtml({status,rating_status:'violation'}),/Ratings: <strong>Violation/);
    }
});

test('a completed solve with unknown conditions is not a pass', () => {
    const html=behaviorResultHtml({status:'ran',rating_status:'unknown',components:[]});
    assert.match(html,/Simulation ran/);assert.match(html,/Unknown \/ not checked/);
    assert.doesNotMatch(html,/\bpass\b/i);
});

test('blocked records retain reason and never offer an enabled run', () => {
    const html=behaviorMetadataHtml({reference_part:null,source_status:'research_required',classes:[],
        scope:'Reference only',available:false,blockers:['Missing current rating'],limitations:[]});
    assert.match(html,/Not simulable/);assert.match(html,/Missing current rating/);
    assert.match(html,/data-behavior-run disabled/);
});

test('source strings and diagnostic text are escaped', () => {
    const html=behaviorResultHtml({status:'not_run',problems:['<script>alert(1)</script>'],version_output:'<svg onload=alert(1)>'});
    assert.doesNotMatch(html,/<script>|<svg onload/);assert.match(html,/&lt;script&gt;/);
});

test('transient traces use recorded time spacing, not uniform sample indexes', () => {
    const html=behaviorResultHtml({status:'ran',rating_status:'unknown',transient:{sample_count:3,time_s:[0,.1,1],series:[{name:'out',values:[0,1,0]}]}});
    assert.match(html,/points="10,100 38,20 290,100"/);
});
