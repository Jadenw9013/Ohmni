from collections import Counter
from pathlib import Path

import pytest

from ohmni.application.component_behavior import BehaviorRunBusy, ComponentBehaviorService

ROOT=Path(__file__).resolve().parents[1]


class NotRunAdapter:
    def __init__(self):self.calls=0

    def behavior_circuit(self,compilation,**kwargs):
        self.calls+=1
        return {'status':'not_run','rating_status':'not_run','analysis':compilation.analysis,
                'problems':['Simulator unavailable'],'operating_point':None,'transient':None,
                'version_output':'','ratings':None}


@pytest.fixture(scope='module')
def service(tmp_path_factory):
    return ComponentBehaviorService(ROOT,tmp_path_factory.mktemp('behavior-service'),adapter=NotRunAdapter())


def test_all_180_entries_expose_behavior_status_and_bound_or_blocked_reasons(service):
    rows=[service.describe(f'OHM-{n:03}') for n in range(1,181)]
    assert sum(r['available'] for r in rows)==96
    assert all(r['blockers'] for r in rows if not r['available'])
    assert Counter(r['source_status'] for r in rows)=={'complete':18,'partial':144,'research_required':18}
    assert service.describe('OHM-004')['reference_part']=='Scoped 0603 reference'
    assert all(c['fidelity'] in {'ideal_components','behavioural_approximation','vendor_model'} for r in rows for c in r['classes'])


def test_blocked_reference_never_invokes_simulator(service):
    before=service.adapter.calls;result=service.run('OHM-083')
    assert result['status']=='not_run' and result['problems']
    assert service.adapter.calls==before


def test_simulator_non_run_is_exposed_with_no_measurements(service):
    result=service.run('OHM-004')
    assert result['status']=='not_run' and result['rating_status']=='not_run'
    assert result['transient'] is None
    assert all(not c['measurements'] for c in result['components'])
    assert 'stdout' not in result and 'stderr' not in result


def test_parallel_reference_runs_are_bounded(service):
    service._run_lock.acquire()
    try:
        with pytest.raises(BehaviorRunBusy):service.run('OHM-004')
    finally:service._run_lock.release()
