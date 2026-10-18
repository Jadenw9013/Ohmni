"""Intent classification and end-of-speech detection (no hardware, no Whisper)."""
from collections import deque

import numpy as np
import pytest
from voice import Endpointing, VoiceSession, chunk_rms, classify, split_sentences


@pytest.mark.parametrize("text,intent", [
    ("Resume.", "resume"),
    ("Go on please", "resume"),
    ("Next one", "next"),
    ("Hey Stack-chan, go back", "back"),
    ("Tell me more", "more"),
    ("Stop.", "stop"),
    ("Say that again", "repeat"),
    ("Can you repeat that?", "repeat"),
    ("um", "unclear"),
    ("Why do we need pull-up resistors?", "question"),
    ("What is next on the board after the regulator?", "question"),
    ("What did you say?", "repeat"),
    ("Why stop there?", "question"),          # review F7
    ("What is the last one?", "question"),
    ("Any more details?", "question"),
    ("Stop, stop!", "stop"),
])
def test_classify(text, intent):
    assert classify(text)[0] == intent


def test_split_sentences():
    assert split_sentences("One. Two? Three!  ") == ["One.", "Two?", "Three!"]


def tone(level, n=512):
    return (np.full(n, level, dtype="<i2")).tobytes()


class FakeBot:
    def __init__(self, chunks, ended_after=None):
        self.audio = deque()
        self._chunks = list(chunks)
        self.on_event = None
        self._ended_after = ended_after
        self._polls = 0

    def poll_events(self):
        self._polls += 1
        if self._chunks:
            self.audio.append(self._chunks.pop(0))
        if self._ended_after is not None and self._polls >= self._ended_after and self.on_event:
            self.on_event({"event": "listen", "on": False, "reason": "touch"})
        return []


def session(chunks, **kw):
    ep = Endpointing(no_speech_timeout_s=0.5, max_utterance_s=3.0)
    return VoiceSession(FakeBot(chunks, **kw), transcriber=None, endpointing=ep, log=lambda *_: None)


def test_chunk_rms():
    assert chunk_rms(tone(1000)) == pytest.approx(1000)
    assert chunk_rms(b"") == 0.0


def test_endpointing_returns_speech_with_lead_in():
    chunks = [tone(2000)] * 3 + [tone(60)] * 8 + [tone(2000)] * 10 + [tone(60)] * 30
    pcm = session(chunks).capture_utterance()
    assert pcm is not None
    samples = np.frombuffer(pcm, dtype="<i2")
    assert (samples == 2000).sum() == 10 * 512          # the start-up click chunks are skipped
    assert samples[0] == 60                              # keeps quiet lead-in before speech


def test_endpointing_gives_up_without_speech():
    assert session([tone(60)] * 200).capture_utterance() is None


def test_endpointing_stops_when_robot_cancels():
    assert session([tone(60)] * 200, ended_after=5).capture_utterance() is None


def test_endpointing_keeps_speech_that_starts_immediately():
    # Review F4: talking right after the double tap must not become the noise floor.
    chunks = [tone(2000)] * 3 + [tone(1500)] * 60 + [tone(60)] * 40
    pcm = session(chunks).capture_utterance()
    samples = np.frombuffer(pcm, dtype="<i2")
    assert (samples == 1500).sum() == 60 * 512


def test_listen_event_discards_stale_microphone_chunks():
    s = session([])
    s.bot.audio.append(tone(1500))
    s._on_event({"event": "listen", "on": True, "source": "touch"})
    assert not s.bot.audio and s.listen_pending
