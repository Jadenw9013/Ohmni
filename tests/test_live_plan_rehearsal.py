"""Exercise the live-rehearsal wiring with a fake provider and real browser/KiCad."""
import json

import pytest


@pytest.mark.integration
def test_plan_confirm_generate_download_without_a_paid_provider(tmp_path, monkeypatch):
    pytest.importorskip('playwright.sync_api')
    from ohmni.adapters.tools import find_kicad_cli
    from ohmni.application.hackathon_demo import DEMO_BRIEF
    from scripts import rehearse_live_plan
    from scripts.verify_hackathon_demo import kicad_version

    executable = find_kicad_cli()
    if not executable or kicad_version(executable) != '10.0.5':
        pytest.skip('requires KiCad 10.0.5')

    class FixtureProvider:
        model = 'fixture-no-network'

        def generate_structured(self, request, schema):
            assert request.request_type == 'project_plan'
            return {'brief': DEMO_BRIEF.model_dump(mode='json'), 'stated': [], 'questions': []}

        def last_call_usage(self):
            return None

    bounded = rehearse_live_plan.SinglePlanProvider(FixtureProvider())
    monkeypatch.setattr(rehearse_live_plan, 'configured_provider', lambda: bounded)
    output = tmp_path / 'plan-flow'
    assert rehearse_live_plan.main(['--execute-approved', '--output', str(output)]) == 0
    result = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
    assert result['status'] == 'PASS'
    assert result['provider_mode'] == 'fixture'
    assert result['provider_calls'] == 1
    assert result['confirmation'] == result['engineering'] == result['download'] == 'PASS'
    assert (output / 'build-package.zip').is_file()
