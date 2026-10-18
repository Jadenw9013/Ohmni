"""Spoken view commands and on-screen selection acknowledgement (ST-T04)."""
from collections import deque

import pytest
from voice import VoiceSession, classify, view_intent

COMPONENTS = [
    {"ref": "U2", "name": "3.3 V voltage regulator", "part_id": "AP2112K-3.3TRG1", "purpose": "Turns 5 V into 3.3 V. It also limits current."},
    {"ref": "C1", "name": "Decoupling capacitor", "part_id": "C_100n", "purpose": "Steadies the supply."},
    {"ref": "C2", "name": "Decoupling capacitor", "part_id": "C_100n", "purpose": "Steadies the supply."},
]


@pytest.mark.parametrize("text,intent", [
    ("Show me the regulator", "focus"),
    ("zoom in on U2", "focus"),
    ("Where is the regulator?", "focus"),
    ("Isolate it", "isolate"),
    ("show only the regulator", "isolate"),
    ("What does it connect to?", "trace"),
    ("What is the regulator connected to?", "trace"),
    ("Zoom out", "frame"),
    ("Show me everything", "show_all"),
    ("Flip it over", "camera_back"),
    ("Show me the underside", "camera_back"),
    ("top view please", "camera_top"),
    ("Go back", None),
    ("Tell me more", None),
    ("Show me more", None),
    ("Why does the regulator get warm?", None),
    ("What does the regulator do?", None),
])
def test_view_intent(text, intent):
    assert view_intent(text) == intent


def test_narration_commands_still_classify_when_not_view_commands():
    assert classify("Go back")[0] == "back"
    assert classify("Tell me more")[0] == "more"


class FakePage:
    def __init__(self):
        self.context = {"job_id": "j1", "components": COMPONENTS, "tour": [], "selected": None}
        self.events = deque()
        self.connected = True
        self.calls = []

    def command(self, name, timeout=10.0, **args):
        self.calls.append((name, args))
        return {"nets": ["VBUS", "+3V3", "GND"]} if name == "trace" else None


class FakeBot:
    def __init__(self):
        self.audio = deque()
        self.on_event = None

    def face(self, expr=None, mouth=None):
        pass

    def poll_events(self):
        return []


def session():
    page = FakePage()
    s = VoiceSession(FakeBot(), transcriber=None, page=page, log=lambda *_: None)
    s.spoken = []
    s.say = lambda text, face="happy": s.spoken.append(text) or True
    s.sync_page()
    return s, page


def test_focus_isolate_trace_and_camera_commands():
    s, page = session()
    s.view_command("focus", "show me the regulator")
    assert page.calls[-1] == ("focus", {"ref": "U2"})
    assert s.spoken[-1] == "Here's the 3.3 V voltage regulator, U2."
    page.calls.clear()
    s.view_command("trace", "what is the regulator connected to")
    assert page.calls == [("focus", {"ref": "U2"}), ("trace", {"ref": "U2"})]
    assert "VBUS, +3V3, GND" in s.spoken[-1]
    s.selected = "U2"
    page.calls.clear()
    s.view_command("isolate", "isolate it")
    assert page.calls == [("focus", {"ref": "U2"}), ("isolate", {"ref": "U2"})]
    page.calls.clear()
    s.view_command("show_all", "show everything")
    s.view_command("camera_back", "flip it over")
    s.view_command("frame", "zoom out")
    assert page.calls == [("isolate", {"ref": None}), ("camera", {"preset": "back"}), ("frame", {})]


def test_ambiguous_or_missing_part_asks_instead_of_guessing():
    s, page = session()
    s.view_command("focus", "show me the capacitor")
    assert page.calls == []
    assert "C1" in s.spoken[-1] and "C2" in s.spoken[-1]
    s.view_command("isolate", "isolate it")
    assert page.calls == []
    assert "Which part" in s.spoken[-1]


def test_on_screen_selection_is_acknowledged_once_but_robot_selections_are_not():
    s, page = session()
    page.events.extend([{"type": "selected", "ref": "C1", "by": "user"},
                        {"type": "selected", "ref": "U2", "by": "user"}])
    s.sync_page()
    s.acknowledge_selection()
    assert s.spoken == ["That's the 3.3 V voltage regulator, U2. Turns 5 V into 3.3 V."]
    page.events.append({"type": "selected", "ref": "C1", "by": "robot"})
    s.sync_page()
    assert s.pending_ack is None and s.selected == "C1"
    page.events.append({"type": "selected", "ref": "U2", "by": "user"})
    s.sync_page()
    s.acknowledge_selection()
    assert len(s.spoken) == 1, "the same part is not announced twice in a row"


def test_choosing_after_which_one_runs_the_remembered_view_command():
    s, page = session()
    s.view_command("isolate", "isolate the capacitor")
    assert s.pending_view == ("isolate", ["C1", "C2"])
    assert s._answer_pending_choice("the first one")
    assert page.calls == [("focus", {"ref": "C1"}), ("isolate", {"ref": "C1"})]
    assert s.pending_view is None
