"""Conversation proposes; deterministic policy and immutable receipts control saving."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import patch

import pytest

from ohmni.application.conversation import BoardPlan, ConversationPlanner, PlanUnavailable
from ohmni.application.project_store import ProjectStore
from ohmni.synthesis import SynthesisBrief


class Provider:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.requests = []

    def generate_structured(self, request, schema):
        assert schema is BoardPlan
        self.requests.append(request)
        return deepcopy(self.outputs.pop(0))


def output(**overrides):
    return {"brief": SynthesisBrief().model_dump(mode="json"), "stated": [], "questions": [], **overrides}


def planner(tmp_path, *outputs, **kwargs):
    return ConversationPlanner(Provider(*outputs), ProjectStore(tmp_path), **kwargs)


def test_confirm_saves_exact_plan_once_without_another_model_call(tmp_path):
    service = planner(tmp_path, output(stated=[{"field": "status_led_count", "quote": "one light"}]))
    plan = service.propose("A USB temperature board with one light")
    assert plan["ready"] and "status_led_count" not in plan["assumed_fields"]
    assert "board_width_mm" in plan["assumed_fields"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        projects = list(pool.map(lambda _: service.confirm(plan["plan_id"]), range(3)))
    assert len({p["project_id"] for p in projects}) == 1
    assert len(service.provider.requests) == 1
    stored = ProjectStore(tmp_path).get(projects[0]["project_id"])
    assert len(stored["revisions"]) == 1
    revision = stored["revisions"][0]
    assert revision["brief"] == plan["brief"]
    assert revision["brief_fingerprint"] == plan["brief_fingerprint"]
    assert revision["planning_receipt"]["messages"] == plan["messages"]
    assert revision["job_id"] is None  # No engineering run is fabricated by confirmation.


def test_questions_block_save_and_short_answer_keeps_context(tmp_path):
    service = planner(tmp_path, output(questions=["USB power only is supported. Is that acceptable?"]), output())
    first = service.propose("I would like a battery powered sensor")
    with pytest.raises(PlanUnavailable, match="unresolved"):
        service.confirm(first["plan_id"])
    assert service.projects.list_projects() == []
    second = service.propose("Yes", first["plan_id"])
    request = service.provider.requests[-1]
    assert request.data["messages"] == ["I would like a battery powered sensor", "Yes"]
    assert request.data["previous_questions"] == first["questions"]
    with pytest.raises(PlanUnavailable):
        service.confirm(first["plan_id"])
    assert service.confirm(second["plan_id"])


def test_unsupported_electrical_choice_cannot_be_confirmed(tmp_path):
    proposed = output()
    proposed["brief"]["input_power"] = "battery"
    service = planner(tmp_path, proposed)
    plan = service.propose("A battery powered sensor board")
    assert not plan["ready"] and plan["questions"] and plan["preview"] is None
    with pytest.raises(PlanUnavailable):
        service.confirm(plan["plan_id"])
    assert not service.projects.list_projects()


@pytest.mark.parametrize("mutation", [
    {"stated": [{"field": "status_led_count", "quote": "invented quote"}]},
    {"stated": [{"field": "verified", "quote": "temperature"}]},
    {"stated": [{"field": "status_led_count", "quote": "temperature"}]*2},
    {"questions": [""]}, {"questions": ["x"*1001]}, {"verified": True},
])
def test_invalid_or_fabricated_attribution_is_rejected(tmp_path, mutation):
    service = planner(tmp_path, output(**mutation))
    with pytest.raises(ValueError):
        service.propose("A temperature sensing board")
    assert not service.projects.list_projects()


def test_model_string_booleans_are_not_coerced(tmp_path):
    proposed = output()
    proposed["brief"]["include_programming_header"] = "false"
    with pytest.raises(ValueError):
        BoardPlan.model_validate(proposed)
    with pytest.raises(ValueError):
        planner(tmp_path, proposed).propose("A temperature sensing board")


def test_returned_plan_mutation_cannot_change_confirmed_input(tmp_path):
    service = planner(tmp_path, output())
    plan = service.propose("A temperature sensing board")
    plan["brief"]["status_led_count"] = 99
    project = service.confirm(plan["plan_id"])
    assert project["revisions"][0]["brief"]["status_led_count"] == 1


def test_expiry_and_capacity_do_not_evict_a_live_review(tmp_path):
    now = [0]
    service = planner(tmp_path, output(), output(), clock=lambda: now[0], ttl=10, capacity=1)
    first = service.propose("A temperature sensing board")
    with pytest.raises(PlanUnavailable, match="busy"):
        service.propose("A second temperature board")
    now[0] = 11
    with pytest.raises(PlanUnavailable, match="expired"):
        service.confirm(first["plan_id"])
    assert service.propose("A second temperature board")


def test_confirm_rechecks_policy_and_failure_does_not_save(tmp_path):
    service = planner(tmp_path, output())
    plan = service.propose("A temperature sensing board")
    with (patch("ohmni.application.conversation.preview_project", side_effect=ValueError("policy changed")),
          pytest.raises(ValueError, match="policy changed")):
        service.confirm(plan["plan_id"])
    assert service.projects.list_projects() == []


def test_confirmed_plan_cannot_be_refined(tmp_path):
    service = planner(tmp_path, output())
    plan = service.propose("A temperature sensing board")
    service.confirm(plan["plan_id"])
    with pytest.raises(PlanUnavailable, match="already saved"):
        service.propose("Make the board narrower", plan["plan_id"])
    assert len(service.provider.requests) == 1


def test_unavailable_provider_and_empty_answer_fail_closed(tmp_path):
    service = ConversationPlanner(None, ProjectStore(tmp_path))
    with pytest.raises(PlanUnavailable):
        service.propose("A temperature sensing board")
    service = planner(tmp_path, output(questions=["Which supported family?"]))
    first = service.propose("A useful board with some parts")
    with pytest.raises(ValueError):
        service.propose(" ", first["plan_id"])
