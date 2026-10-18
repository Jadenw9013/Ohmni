"""Serial protocol framing for the companion, against a fake robot (no hardware)."""
import base64
import json

import pytest
from stackchan import StackChan, StackChanError


class FakeSerial:
    """Scripted robot: replies to each command via `responder(cmd) -> list[dict]`."""

    def __init__(self, responder, preamble=()):
        self.responder = responder
        self.written: list[dict] = []
        self.lines: list[bytes] = [json.dumps(m).encode() + b"\n" if isinstance(m, dict) else m
                                   for m in preamble]

    @property
    def in_waiting(self):
        return len(self.lines)

    def write(self, data: bytes):
        msg = json.loads(data)
        self.written.append(msg)
        for reply in self.responder(msg):
            self.lines.append(json.dumps(reply).encode() + b"\n")

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def reset_input_buffer(self):
        self.lines.clear()

    def close(self):
        pass


def ok(msg, **extra):
    return [{"id": msg["id"], "ok": True, **extra}]


def bot_with(responder, preamble=()):
    bot = StackChan(port="/dev/null", timeout=0.2)
    bot._ser = FakeSerial(responder, preamble)
    return bot


def test_send_matches_reply_by_id_and_skips_noise():
    def responder(msg):
        return [{"id": 999, "ok": True}, {"id": msg["id"], "ok": True, "fw": "ohmni-stackchan"}]

    bot = bot_with(responder, preamble=[b"ESP-ROM:esp32s3 boot text\n", b"{partial"])
    assert bot.ping()["fw"] == "ohmni-stackchan"
    assert bot._ser.written[0]["cmd"] == "ping"


def test_error_reply_raises_with_command_name():
    bot = bot_with(lambda msg: [{"id": msg["id"], "ok": False, "error": "unknown expr"}])
    with pytest.raises(StackChanError, match="face: unknown expr"):
        bot.face("grumpy")


def test_missing_reply_times_out():
    bot = bot_with(lambda msg: [])
    with pytest.raises(StackChanError, match="no reply"):
        bot.state()


def test_events_are_dispatched_and_audio_is_queued_separately():
    pcm = b"\x01\x00\x02\x00"
    seen = []

    def responder(msg):
        return [{"event": "touch", "gesture": "double_tap"},
                {"event": "audio", "seq": 0, "pcm": base64.b64encode(pcm).decode()},
                *ok(msg)]

    bot = bot_with(responder)
    bot.on_event = seen.append
    bot.state()
    assert seen == [{"event": "touch", "gesture": "double_tap"}]
    assert list(bot.audio) == [pcm]
    assert bot.poll_events() == [{"event": "touch", "gesture": "double_tap"}]
    assert bot.events == []


def test_play_chunk_encodes_pcm_and_reports_listening():
    replies = iter([True, False])

    def responder(msg):
        if next(replies):
            return ok(msg)
        return [{"id": msg["id"], "ok": False, "error": "listening"}]

    bot = bot_with(responder)
    bot.play_chunk(b"\x00\x01" * 4)
    assert base64.b64decode(bot._ser.written[0]["pcm"]) == b"\x00\x01" * 4
    with pytest.raises(StackChanError, match="listening"):
        bot.play_chunk(b"\x00\x00")


def test_wait_ready_accepts_boot_event_and_rejects_other_firmware():
    bot = bot_with(lambda msg: [], preamble=[{"event": "ready", "fw": "ohmni-stackchan"}])
    bot._wait_ready(seconds=0.5)

    other = bot_with(lambda msg: [], preamble=[{"event": "ready", "fw": "factory"}])
    with pytest.raises(StackChanError, match="Unexpected firmware"):
        other._wait_ready(seconds=0.5)


def test_pose_only_sends_given_axes():
    bot = bot_with(ok)
    bot.pose(pitch=20, ms=500)
    assert bot._ser.written[0] == {"cmd": "pose", "id": 1, "ms": 500, "pitch": 20}


def test_volume_command():
    bot = bot_with(lambda msg: ok(msg, volume=msg["level"]))
    assert bot.volume(200)["volume"] == 200
    assert bot._ser.written[0] == {"cmd": "volume", "id": 1, "level": 200}
