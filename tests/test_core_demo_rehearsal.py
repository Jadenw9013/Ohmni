"""Demo rehearsal gates must not certify absent checks or stale downloaded bytes."""
import hashlib
import io
import json
import zipfile
from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts.rehearse_core_demo import FAMILIES, STEPS, qualified, verify_package
from scripts.rehearse_live_plan import SinglePlanProvider, main, validate_plan


def clean_result():
    return {'status': 'PASS', 'provider_calls': 0, 'external_requests': 0, 'page_errors': 0,
            'planner_recovery': True, 'restart_recovery': True, 'families': {family: dict.fromkeys(STEPS, True) for family in FAMILIES}}


def test_core_gate_requires_every_family_and_named_check():
    process = {'exit_code': 0, 'timed_out': False}
    assert qualified(clean_result(), process)
    for family in FAMILIES:
        result = clean_result()
        del result['families'][family]
        assert not qualified(result, process)
        for step in STEPS:
            result = clean_result()
            del result['families'][family][step]
            assert not qualified(result, process)
            result['families'][family][step] = False
            assert not qualified(result, process)
    for field in ('provider_calls', 'external_requests', 'page_errors'):
        result = clean_result()
        result[field] = 1
        assert not qualified(result, process)
    assert not qualified(clean_result(), {'exit_code': 2, 'timed_out': False})
    assert not qualified(clean_result(), {'exit_code': 0, 'timed_out': True})
    assert not qualified({}, process)
    result = clean_result()
    result['planner_recovery'] = False
    assert not qualified(result, process)
    result = clean_result()
    result['restart_recovery'] = False
    assert not qualified(result, process)


def package():
    digest = lambda value: hashlib.sha256(value).hexdigest()
    files = {'golden.kicad_pcb': b'pcb', 'golden.kicad_sch': b'schematic',
             'fabrication/top.gtl': b'copper', 'fabrication/manifest.json': b'manifest'}
    report = {'pcb': {'current': True, 'drc_status': 'PASS', 'fingerprint': digest(b'pcb')},
              'schematic': {'current': True, 'erc_status': 'PASS_WITH_WARNINGS',
                            'fingerprint': digest(b'schematic')},
              'release': {'current': True, 'status': 'READY_FOR_MANUFACTURING_REVIEW',
                          'package_fingerprint': 'package',
                          'files': [{'relative_path': 'top.gtl', 'size_bytes': 6,
                                     'sha256': digest(b'copper')}],
                          'manifest': {'relative_path': 'manifest.json', 'size_bytes': 8,
                                       'sha256': digest(b'manifest')}}}
    revision = {'revision_id': 'revision', 'job_id': 'job', 'brief_fingerprint': 'brief',
                'brief': {'archetype': 'example'}}
    files['report.json'] = json.dumps(report).encode()
    files['confirmed-brief.json'] = json.dumps(revision['brief']).encode()
    files['project-revision.json'] = json.dumps({**revision, 'package_fingerprint': 'package'}).encode()
    return files, report, revision


def zip_bytes(files):
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return target.getvalue()


def test_package_verifies_actual_bytes_and_saved_input():
    files, report, revision = package()
    verify_package(zip_bytes(files), report, revision)
    for name in files:
        changed = dict(files)
        changed[name] = b'{}'
        with pytest.raises((ValueError, KeyError)):
            verify_package(zip_bytes(changed), report, revision)
    for section in ('release', 'schematic', 'pcb'):
        stale = deepcopy(report)
        stale[section]['current'] = False
        with pytest.raises(ValueError, match='release_not_current'):
            verify_package(zip_bytes(files), stale, revision)
    different = {**revision, 'job_id': 'other-job'}
    with pytest.raises(ValueError, match='revision_mismatch'):
        verify_package(zip_bytes(files), report, different)


class FakeProvider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def generate_structured(self, request, schema):
        self.calls += 1
        if self.fail:
            raise ValueError('provider unavailable')
        return {'plan': 'example'}

    def last_call_usage(self):
        return None


@pytest.mark.parametrize('fail', [True, False])
def test_live_wrapper_never_retries_even_after_failure(fail):
    raw = FakeProvider(fail)
    wrapper = SinglePlanProvider(raw)
    request = SimpleNamespace(request_type='project_plan')
    if fail:
        with pytest.raises(ValueError):
            wrapper.generate_structured(request, dict)
    else:
        assert wrapper.generate_structured(request, dict) == {'plan': 'example'}
    with pytest.raises(ValueError, match='rehearsal_call_limit'):
        wrapper.generate_structured(request, dict)
    assert wrapper.calls == raw.calls == 1


def test_live_wrapper_refuses_other_operations_before_provider():
    raw = FakeProvider()
    wrapper = SinglePlanProvider(raw)
    with pytest.raises(ValueError, match='rehearsal_call_limit'):
        wrapper.generate_structured(SimpleNamespace(request_type='design'), dict)
    assert raw.calls == wrapper.calls == 0


def test_live_rehearsal_default_reads_no_credentials_and_creates_no_workspace(tmp_path):
    destination = tmp_path / 'must-not-exist'
    assert main(['--env-file', str(tmp_path / 'missing.env'), '--output', str(destination)]) == 2
    assert not destination.exists()


def test_live_plan_must_match_the_prequalified_electrical_brief():
    from ohmni.application.hackathon_demo import DEMO_BRIEF
    plan = {'ready': True, 'questions': [], 'brief': DEMO_BRIEF.model_dump(mode='json')}
    validate_plan(plan)
    plan['brief']['project_name'] = 'Model-suggested name'
    validate_plan(plan)
    plan['brief']['include_programming_header'] = True
    with pytest.raises(ValueError, match='plan_differs'):
        validate_plan(plan)
    plan['ready'] = False
    with pytest.raises(ValueError, match='clarification'):
        validate_plan(plan)


def test_live_provider_disables_both_retry_layers_and_caps_output(monkeypatch):
    from ohmni.adapters import anthropic_provider
    from scripts.rehearse_live_plan import configured_provider
    recorded = {}

    class Client:
        def with_options(self, **kwargs):
            recorded['sdk'] = kwargs
            return self

    class Provider:
        def __init__(self, **kwargs):
            recorded['provider'] = kwargs
            self._client = Client()

    monkeypatch.setattr(anthropic_provider, 'AnthropicProvider', Provider)
    assert isinstance(configured_provider(), SinglePlanProvider)
    assert recorded == {'provider': {'max_attempts': 1, 'max_tokens': 4096},
                        'sdk': {'max_retries': 0, 'timeout': 45}}
