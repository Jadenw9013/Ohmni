"""Workspace narration and grounded questions, with a fake page and robot (no hardware)."""
from collections import deque

import pytest
from voice import (
    VoiceSession,
    choose_candidate,
    part_name,
    resolve_part,
    segments_from_context,
    spoken_answer,
)

COMPONENTS = [
    {"ref": "U2", "name": "3.3 V voltage regulator", "part_id": "AP2112K-3.3TRG1"},
    {"ref": "U3", "name": "Temperature, humidity and pressure sensor", "part_id": "BME280"},
    {"ref": "C1", "name": "Decoupling capacitor", "part_id": "C_100n"},
    {"ref": "C2", "name": "Decoupling capacitor", "part_id": "C_100n"},
]


@pytest.mark.parametrize("text,ref,candidates", [
    ("Why does the regulator get warm?", "U2", ["U2"]),
    ("what does U3 do", "U3", ["U3"]),
    ("Tell me about the BME280", "U3", ["U3"]),
    ("why is this capacitor here", None, ["C1", "C2"]),
    ("how does it work", "C2", []),       # nothing named: the selected part
])
def test_resolve_part(text, ref, candidates):
    found, options = resolve_part(text, COMPONENTS, selected="C2" if "how does" in text else None)
    assert found == ref
    assert sorted(options) == candidates


def test_resolve_part_without_selection_asks():
    assert resolve_part("how does it work", COMPONENTS) == (None, [])


def test_spoken_answer_is_labelled_and_keeps_unknowns():
    text = spoken_answer({"explanation": "It makes 3.3 volts.", "unknowns": ["Thermal behaviour was not measured."],
                          "next_questions": ["What happens at full load?", "Why this package?"]})
    assert text == ("Here's Ohmni's explanation, based on your board's records. It makes 3.3 volts."
                    " Not yet known: Thermal behaviour was not measured. You could ask: What happens at full load?")
    assert spoken_answer({"explanation": "  "}) == "Ohmni didn't return an explanation for that."
    assert part_name(COMPONENTS, "U2") == "3.3 V voltage regulator"
    assert part_name(COMPONENTS, "Z9") == "Z9"


def test_segments_come_from_the_deterministic_tour():
    context = {"tour": [{"title": "Power", "narration": "USB becomes 3.3 V.", "component_refs": ["U2"]},
                        {"title": "Empty", "narration": ""}]}
    segments = segments_from_context(context)
    assert [(s.title, s.refs, s.tour_index) for s in segments] == [("Power", ["U2"], 0)]


class FakePage:
    def __init__(self, context=None, answer=None):
        self.context = context
        self.events = deque()
        self.connected = True
        self.calls = []
        self.answer = answer or {"explanation": "It regulates.", "unknowns": [], "next_questions": []}

    def command(self, name, timeout=10.0, **args):
        self.calls.append((name, args))
        return self.answer if name == "ask" else None


class FakeBot:
    def __init__(self):
        self.audio = deque()
        self.on_event = None
        self.faces = []

    def face(self, expr=None, mouth=None):
        self.faces.append(expr)

    def poll_events(self):
        return []


def session(page):
    s = VoiceSession(FakeBot(), transcriber=None, page=page, log=lambda *_: None)
    s.spoken = []
    s.say = lambda text, face="happy": s.spoken.append(text) or True
    return s


def test_questions_go_through_the_page_tutor_for_the_named_part():
    page = FakePage({"job_id": "j1", "components": COMPONENTS, "tour": []})
    s = session(page)
    s.answer("Why does the regulator get warm?")
    assert page.calls == [("ask", {"ref": "U2", "question": "Why does the regulator get warm?"})]
    assert s.spoken[-1] == "Here's Ohmni's explanation, based on your board's records. It regulates."


def test_ambiguous_or_unknown_parts_get_a_question_back_not_a_guess():
    page = FakePage({"job_id": "j1", "components": COMPONENTS, "tour": []})
    s = session(page)
    s.answer("why is this capacitor here")
    assert page.calls == []
    assert "C1" in s.spoken[-1] and "C2" in s.spoken[-1]
    s.answer("how does it work")
    assert page.calls == []
    assert "Which part" in s.spoken[-1]


def test_without_the_workspace_questions_are_declined():
    s = session(None)
    s.answer("Why does the regulator get warm?")
    assert "Ohmni workspace" in s.spoken[-1]


def test_a_new_board_starts_its_tour_and_narration_highlights_each_step(monkeypatch):
    page = FakePage({"job_id": "j1", "selected": None, "components": COMPONENTS,
                     "tour": [{"title": "Power", "narration": "USB becomes 3.3 V.", "component_refs": ["U2"]}]})
    s = session(page)
    s.sync_page()
    assert s.narrating and len(s.segments) == 1
    monkeypatch.setattr("voice.synthesize", lambda text, voice=None: b"")
    s._play = lambda pcm: True
    s.narrate_step()
    assert page.calls == [("tour", {"index": 0})]
    page.events.append({"type": "selected", "ref": "U3", "by": "user"})
    s.sync_page()
    assert s.selected == "U3"


@pytest.mark.parametrize("text,selected,ref", [
    ("what voltage does it run at", "U3", "U3"),      # review F3: pronoun -> what is on screen
    ("why is this capacitor here", "C2", "C2"),       # selected is among the tied candidates
    ("Why does the regulator get warm?", "C1", "U2"), # a clearly named part still wins
])
def test_selection_beats_weak_matches(text, selected, ref):
    assert resolve_part(text, COMPONENTS, selected)[0] == ref


def test_choose_candidate_by_reference_name_or_ordinal():
    assert choose_candidate("C2", ["C1", "C2"], COMPONENTS) == "C2"
    assert choose_candidate("the second one", ["C1", "C2"], COMPONENTS) == "C2"
    assert choose_candidate("the regulator", ["U2", "U3"], COMPONENTS) == "U2"
    assert choose_candidate("never mind", ["C1", "C2"], COMPONENTS) is None


def test_clarifying_question_is_remembered_for_the_answer():
    page = FakePage({"job_id": "j1", "components": COMPONENTS, "tour": []})
    s = session(page)
    s.answer("why is this capacitor here")
    assert s.pending_question == ("why is this capacitor here", ["C1", "C2"])
    assert s._answer_pending_choice("the second one")
    assert page.calls == [("ask", {"ref": "C2", "question": "why is this capacitor here"})]
    assert s.pending_question is None


def test_repeat_replays_the_last_answer_when_not_narrating():
    page = FakePage({"job_id": "j1", "components": COMPONENTS, "tour": []})
    s = session(page)
    s.answer("Why does the regulator get warm?")
    s.dispatch("repeat", "repeat")
    assert s.spoken[-1] == s.spoken[-2] == s.last_answer


def test_narration_pauses_when_the_page_disconnects():
    page = FakePage({"job_id": "j1", "selected": None, "components": COMPONENTS,
                     "tour": [{"title": "Power", "narration": "USB becomes 3.3 V.", "component_refs": ["U2"]}]})
    s = session(page)
    s.sync_page()
    assert s.narrating
    page.connected = False
    s.sync_page()
    assert not s.narrating and s.board_id is None and page.context is None
