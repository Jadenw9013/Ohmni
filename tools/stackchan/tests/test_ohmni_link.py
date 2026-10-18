"""Loopback page link: origin allowlist, context, selection events and command round trips."""
import json
import threading

import pytest
from ohmni_link import PageError, PageLink, normalize_origin
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


def test_origins_are_normalized_like_browser_origin_headers():
    assert normalize_origin("https://Ohmni.Example/app/") == "https://ohmni.example"
    assert normalize_origin("http://127.0.0.1:8765") == "http://127.0.0.1:8765"
    with pytest.raises(ValueError):
        normalize_origin("ohmni.example")


def test_non_object_messages_are_ignored(link):
    with connect(url(link), origin=ORIGIN) as page:
        page.send("[1, 2]")
        page.send("42")
        page.send(json.dumps({"type": "result", "id": [1], "ok": True}))
        page.send(json.dumps({"type": "context", "job_id": "b" * 12, "components": [], "tour": []}))
        assert link.wait_for_context(timeout=5)["job_id"] == "b" * 12
        assert link.connected, "malformed messages do not drop the connection"


def test_a_newer_tab_replaces_the_old_one_and_fails_its_commands_at_once(link):
    from websockets.exceptions import ConnectionClosed
    with connect(url(link), origin=ORIGIN) as first:
        for _ in range(100):
            if link.connected:
                break
            threading.Event().wait(0.01)
        errors = []
        worker = threading.Thread(target=lambda: errors.append(pytest.raises(PageError, link.command, "ask", timeout=30)))
        worker.start()
        first.recv(timeout=5)  # the ask reached the first tab, which never answers
        with connect(url(link), origin=ORIGIN):
            worker.join(5)
            assert not worker.is_alive(), "the replaced tab's command failed immediately"
            assert "replaced" in str(errors[0].value)
            with pytest.raises(ConnectionClosed) as closed:
                first.recv(timeout=5)
            assert closed.value.rcvd.code == 4001


def test_a_page_closing_mid_send_raises_page_error_not_connection_closed(link):
    with connect(url(link), origin=ORIGIN) as page:
        for _ in range(100):
            if link.connected:
                break
            threading.Event().wait(0.01)
        page.close()
        for _ in range(100):
            try:
                link.command("frame", timeout=1)
            except PageError:
                break
        assert not link._pending or all(not v for v in link._pending.values())
