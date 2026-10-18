"""Loopback page link: origin allowlist, context, selection events and command round trips."""
import json
import threading

import pytest
from ohmni_link import PageError, PageLink
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

ORIGIN = "https://ohmni.example"


@pytest.fixture
def link():
    page_link = PageLink(origins=(ORIGIN,), port=0).start()
    yield page_link
    page_link.close()


def url(link):
    return f"ws://127.0.0.1:{link.port}"


def test_allowed_page_sends_context_and_selection(link):
    with connect(url(link), origin=ORIGIN) as page:
        page.send(json.dumps({"type": "context", "job_id": "a" * 12, "components": [{"ref": "U2"}], "tour": []}))
        page.send(json.dumps({"type": "selected", "ref": "U2", "by": "user"}))
        page.send("not json")
        context = link.wait_for_context(timeout=5)
        assert context["job_id"] == "a" * 12
        for _ in range(100):
            if link.events:
                break
            threading.Event().wait(0.01)
        assert link.events.popleft() == {"type": "selected", "ref": "U2", "by": "user"}
        assert link.connected


@pytest.mark.parametrize("origin", ["https://evil.example", None])
def test_other_websites_and_originless_clients_are_refused(link, origin):
    with pytest.raises(InvalidStatus) as refused:
        connect(url(link), origin=origin).close()
    assert refused.value.response.status_code == 403
    assert not link.connected


def test_commands_round_trip_and_refusals_raise(link):
    with connect(url(link), origin=ORIGIN) as page:
        def fake_page():
            for _ in range(2):
                command = json.loads(page.recv(timeout=5))
                ok = command["name"] == "focus"
                page.send(json.dumps({"type": "result", "id": command["id"], "ok": ok,
                                      **({"data": {"ref": command["args"]["ref"]}} if ok else {"error": "unknown command: run"})}))
        worker = threading.Thread(target=fake_page)
        worker.start()
        for _ in range(100):
            if link.connected:
                break
            threading.Event().wait(0.01)
        assert link.command("focus", ref="U2") == {"ref": "U2"}
        with pytest.raises(PageError, match="run: unknown command"):
            link.command("run")
        worker.join(5)


def test_no_page_and_page_disconnect_raise(link):
    with pytest.raises(PageError, match="no Ohmni page"):
        link.command("frame")
    with connect(url(link), origin=ORIGIN) as page:
        for _ in range(100):
            if link.connected:
                break
            threading.Event().wait(0.01)
        threading.Timer(0.2, page.close).start()
        with pytest.raises(PageError, match="disconnected"):
            link.command("frame", timeout=5)
