"""Voice layer for Stack-chan: narration through the robot, double-tap to talk.

Flow:
  - Narrator speaks segments (e.g. component explanations) through the robot's
    speaker using macOS text-to-speech, one sentence at a time.
  - Double-tapping the head makes the robot stop speaking and stream its
    microphone. We detect the end of speech, transcribe locally with Whisper,
    and act on it: a fixed command (resume, stop, next, back, repeat, more), or
    anything else is a question answered by Claude (needs ANTHROPIC_API_KEY or
    an `ant auth login` profile; costs per question).

Run:  python voice.py demo            # example narration about an I2C sensor board
      python voice.py listen-test     # double-tap, speak, print the transcript
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from stackchan import StackChan, StackChanError

SAMPLE_RATE = StackChan.SAMPLE_RATE
CHUNK_MS = 32  # firmware microphone chunk: 512 samples


# ----------------------------------------------------------- text to speech

def synthesize(text: str, voice: str | None = None, rate_wpm: int | None = None) -> bytes:
    """Speak `text` with macOS `say` into 16 kHz mono int16 PCM."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "speech.wav"
        cmd = ["say", "-o", str(out), "--data-format=LEI16@16000"]
        if voice:
            cmd += ["-v", voice]
        if rate_wpm:
            cmd += ["-r", str(rate_wpm)]
        subprocess.run(cmd + [text], check=True)
        with wave.open(str(out)) as w:
            return w.readframes(w.getnframes())


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


# ----------------------------------------------------------- speech to text

# Whisper invents these from silence or noise; never treat them as commands.
HALLUCINATIONS = {"", "you", "thank you", "thanks for watching", "bye", "okay"}


class Transcriber:
    def __init__(self, model: str = "mlx-community/whisper-base.en-mlx"):
        self.model = model
        import mlx_whisper  # imported lazily: slow to load
        self._whisper = mlx_whisper
        self.transcribe(np.zeros(SAMPLE_RATE // 2, dtype=np.int16).tobytes())  # warm up / download

    def transcribe(self, pcm: bytes) -> str:
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        result = self._whisper.transcribe(audio, path_or_hf_repo=self.model, language="en",
                                          condition_on_previous_text=False)
        return result["text"].strip()


@dataclass
class Endpointing:
    """Energy-based voice activity detection on the robot's 32 ms chunks."""
    min_threshold: float = 300.0     # RMS; a quiet room measured ~85 on this robot
    noise_factor: float = 3.0
    start_chunks: int = 3            # ~100 ms of speech to count as speaking
    end_silence_ms: int = 800        # stop after this much silence once speech started
    skip_chunks: int = 3             # ignore the mic's start-up click (~100 ms)
    no_speech_timeout_s: float = 5.0
    max_utterance_s: float = 12.0


def chunk_rms(pcm: bytes) -> float:
    a = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    return float(np.sqrt(np.mean(a * a))) if len(a) else 0.0


# ------------------------------------------------------------------ intents

COMMANDS = {
    "resume": r"\b(resume|continue|go on|keep going|carry on|play)\b",
    "stop": r"\b(stop|cancel|never ?mind|quiet|that'?s all|be quiet)\b",
    "next": r"\b(next|skip)\b",
    "back": r"\b(back|previous|last one)\b",
    "repeat": r"\b(repeat|again|say that again|what did you say)\b",
    "more": r"\b(more|tell me more|explain more|go deeper|elaborate|details?)\b",
}
FILLER = r"\b(hey|ok|okay|um+|uh+|please|stack ?-?chan|stackchan|robot|the|that|one|can you|could you)\b"


def classify(text: str) -> tuple[str, str]:
    """Return (intent, text). Short utterances can be commands; anything longer is a question."""
    t = re.sub(r"[^\w\s']", " ", text.lower()).strip()
    core = re.sub(FILLER, " ", t)
    core_words = core.split()
    if len(core_words) <= 3:
        for name, pattern in COMMANDS.items():
            if re.search(pattern, t):
                return name, text
    if not core_words:
        return "unclear", text
    return "question", text


# ---------------------------------------------------------- Claude answers

SYSTEM_PROMPT = """You are Stack-chan, a small desk robot that is the voice of Ohmni, an AI electronics \
engineering mentor that helps people design circuits and printed circuit boards.

Your reply is spoken aloud through a small speaker, so:
- Answer in one to three short sentences of plain spoken English.
- No markdown, lists, symbols or code. Say units in words ("four point seven kilo-ohms", "three point three volts").
- If the question is about what is currently being explained, use the context you are given.

Be an honest teacher. You explain; you do not verify. Never say a board or design passed a check, \
is safe, or is ready to manufacture unless the context explicitly says that check ran and passed. \
If you are unsure, say so briefly."""


class Assistant:
    def __init__(self, model: str = "claude-opus-5-5"):
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.history: list[dict] = []

    def ask(self, question: str, context: str | None) -> str:
        anthropic = self._anthropic
        content = question if not context else f"Currently explaining:\n{context}\n\nQuestion: {question}"
        messages = self.history[-6:] + [{"role": "user", "content": content}]
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_config={"effort": "low"},  # short spoken answers; keep latency down
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            return "I can't answer questions yet, because no Anthropic API key is set up."
        except anthropic.RateLimitError:
            return "I'm being rate limited right now. Please ask again in a minute."
        except anthropic.APIStatusError as e:
            return f"Sorry, the answer service returned an error, code {e.status_code}."
        except anthropic.APIConnectionError:
            return "Sorry, I couldn't reach the answer service. Check the internet connection."

        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        answer = " ".join(b.text for b in response.content if b.type == "text").strip()
        if not answer:
            return "Sorry, I don't have an answer for that."
        self.history += [{"role": "user", "content": content}, {"role": "assistant", "content": answer}]
        return answer


def has_claude_credentials() -> bool:
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic").exists())


# ----------------------------------------------------------------- session

@dataclass
class Segment:
    title: str
    text: str
    more: str | None = None


@dataclass
class VoiceSession:
    bot: StackChan
    transcriber: Transcriber
    assistant: Assistant | None = None
    segments: list[Segment] = field(default_factory=list)
    voice: str | None = None
    endpointing: Endpointing = field(default_factory=Endpointing)
    log: callable = print

    index: int = 0
    sentence: int = 0
    narrating: bool = False  # True while narration should be playing (not paused/stopped)
    listen_pending: bool = False    # robot started listening (double tap)
    listen_ended: str | None = None  # robot stopped listening on its own: "touch" or "timeout"
    last_levels: list = field(default_factory=list)  # RMS per chunk of the last capture, for tuning

    def __post_init__(self) -> None:
        self.bot.on_event = self._on_event

    def _on_event(self, ev: dict) -> None:
        kind = ev.get("event")
        if kind == "listen":
            if ev.get("on"):
                self.listen_pending, self.listen_ended = True, None
            elif ev.get("reason") != "host":
                self.listen_ended = ev.get("reason")
        elif kind == "touch":
            self.log(f"[touch] {ev.get('gesture')}")
        elif kind == "stall":
            self.log(f"[stall] {ev}")

    # -- speaking -----------------------------------------------------------
    def say(self, text: str, face: str = "happy") -> bool:
        """Speak text through the robot. Returns False if interrupted by a double tap."""
        self.bot.face(face)
        for sentence in split_sentences(text):
            if not self._play(synthesize(sentence, self.voice)):
                return False
        return True

    def _play(self, pcm: bytes) -> bool:
        step = StackChan.PLAY_CHUNK_SAMPLES * 2
        for i in range(0, len(pcm), step):
            try:
                self.bot.play_chunk(pcm[i:i + step])
            except StackChanError as e:
                if "listening" in str(e):
                    return False
                raise
            if self._listen_requested():
                return False
        return True

    def _listen_requested(self) -> bool:
        return self.listen_pending

    # -- narration ----------------------------------------------------------
    @property
    def current(self) -> Segment | None:
        return self.segments[self.index] if 0 <= self.index < len(self.segments) else None

    def narrate_step(self) -> None:
        """Speak the next sentence of the current segment, advancing when it ends."""
        seg = self.current
        if seg is None:
            self.narrating = False
            self.say("That's everything for this board.", face="happy")
            return
        sentences = split_sentences(seg.text)
        if self.sentence == 0:
            self.log(f"[narrate] {seg.title}")
            self.bot.face("happy")
        if self.sentence >= len(sentences):
            self.index += 1
            self.sentence = 0
            return
        if self._play(synthesize(sentences[self.sentence], self.voice)):
            self.sentence += 1  # an interrupted sentence restarts on resume

    # -- listening ----------------------------------------------------------
    def capture_utterance(self) -> bytes | None:
        """Collect microphone audio until end of speech. None if nothing was said or cancelled."""
        ep = self.endpointing
        chunks: list[bytes] = []
        levels: list[float] = []
        started = False
        speech_run = silence_run = 0
        speech_start = 0
        t0 = time.monotonic()
        end_chunks = ep.end_silence_ms // CHUNK_MS
        while True:
            self.bot.poll_events()
            if self.listen_ended:
                self.log(f"[listen] ended by robot: {self.listen_ended}")
                return None  # double-tapped again, or firmware timeout
            while self.bot.audio:
                pcm = self.bot.audio.popleft()
                chunks.append(pcm)
                if len(chunks) <= ep.skip_chunks:
                    continue
                level = chunk_rms(pcm)
                levels.append(level)
                self.last_levels = levels
                floor = float(np.median(levels[:8])) if len(levels) >= 4 else 0.0
                threshold = max(ep.min_threshold, floor * ep.noise_factor)
                if level >= threshold:
                    speech_run += 1
                    silence_run = 0
                    if not started and speech_run >= ep.start_chunks:
                        started = True
                        speech_start = max(ep.skip_chunks, len(chunks) - speech_run - 10)  # ~300 ms lead-in, never the click
                else:
                    speech_run = 0
                    silence_run += 1
                if started and silence_run >= end_chunks:
                    return b"".join(chunks[speech_start:])
            elapsed = time.monotonic() - t0
            if not started and elapsed > ep.no_speech_timeout_s:
                return None
            if elapsed > ep.max_utterance_s:
                return b"".join(chunks[speech_start:]) if started else None
            time.sleep(0.01)

    def handle_listen(self) -> None:
        self.listen_pending = False
        was_narrating = self.narrating
        self.narrating = False
        self.log("[listen] listening...")
        pcm = self.capture_utterance()
        try:
            self.bot.listen(False)
        except StackChanError:
            pass
        if pcm is None:
            # Nothing said (or cancelled): carry on as before.
            self.log("[listen] heard nothing")
            self.bot.face("neutral")
            self.narrating = was_narrating
            return

        self.bot.face("thinking")
        t = time.monotonic()
        text = self.transcriber.transcribe(pcm)
        self.log(f"[heard] {text!r} ({len(pcm) / 2 / SAMPLE_RATE:.1f}s audio, {time.monotonic() - t:.1f}s to transcribe)")
        if re.sub(r"[^\w\s]", "", text.lower()).strip() in HALLUCINATIONS:
            intent = "unclear"
        else:
            intent, text = classify(text)
        self.log(f"[intent] {intent}")
        self.dispatch(intent, text)
        if intent == "unclear":
            self.narrating = was_narrating

    def dispatch(self, intent: str, text: str) -> None:
        seg = self.current
        if intent == "resume":
            self.narrating = True
        elif intent == "stop":
            self.narrating = False
            self.say("Okay, stopping.", face="neutral")
        elif intent == "next":
            self.index, self.sentence, self.narrating = min(self.index + 1, len(self.segments)), 0, True
        elif intent == "back":
            self.index, self.sentence, self.narrating = max(self.index - 1, 0), 0, True
        elif intent == "repeat":
            self.sentence, self.narrating = 0, True
        elif intent == "more":
            if seg and seg.more:
                self.say(seg.more)
            else:
                self.answer(f"Tell me more about {seg.title}." if seg else text)
        elif intent == "question":
            self.answer(text)
        else:
            self.say("Sorry, I didn't catch that.", face="sad")

    def answer(self, question: str) -> None:
        if self.assistant is None:
            self.say("I can only follow commands like resume, next, or repeat right now. "
                     "Questions need an Anthropic API key.", face="sad")
            return
        self.bot.face("thinking")
        seg = self.current
        context = f"{seg.title}: {seg.text}" if seg else None
        t = time.monotonic()
        reply = self.assistant.ask(question, context)
        self.log(f"[claude] {reply!r} ({time.monotonic() - t:.1f}s)")
        self.say(reply)

    # -- main loop ------------------------------------------------------------
    def run(self) -> None:
        self.log("Double-tap the robot's head to talk. Ctrl+C to quit.")
        while True:
            self.bot.poll_events()
            if self._listen_requested():
                self.handle_listen()
            elif self.narrating:
                self.narrate_step()
            else:
                time.sleep(0.02)


# ------------------------------------------------------------------ example

DEMO_SEGMENTS = [
    Segment("Overview",
            "This example board is an ESP32 weather sensor. It is powered over USB and reads "
            "temperature, humidity and pressure from a BME280 sensor over I2C. "
            "Double tap my head any time to ask me something.",
            "The board has four jobs: take five volts from USB, turn it into three point three volts, "
            "run the ESP32, and talk to the sensor over two shared wires."),
    Segment("Voltage regulator",
            "USB gives five volts, but the ESP32 and the sensor need three point three volts. "
            "A low dropout regulator makes that lower voltage and keeps it steady when the radio "
            "suddenly draws more current."),
    Segment("Decoupling capacitors",
            "Small capacitors sit right next to each chip's power pins. They act like tiny local "
            "batteries, supplying quick bursts of current so the supply voltage does not dip."),
    Segment("I2C pull-up resistors",
            "The I2C bus uses two wires, clock and data. Devices only pull them low, so two resistors "
            "pull them back up to three point three volts when nobody is talking. Four point seven "
            "kilo-ohms is a common value."),
    Segment("BME280 sensor",
            "The BME280 measures temperature, humidity and air pressure. It answers at its own address "
            "on the I2C bus, so other sensors can share the same two wires."),
]


def load_segments(path: Path) -> list[Segment]:
    return [Segment(**s) for s in json.loads(path.read_text())]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stack-chan voice: narration + double-tap to talk")
    ap.add_argument("mode", choices=["demo", "listen-test"])
    ap.add_argument("--segments", type=Path, help="JSON list of {title, text, more?}")
    ap.add_argument("--voice", help="macOS voice name (see `say -v ?`)")
    ap.add_argument("--whisper-model", default="mlx-community/whisper-base.en-mlx")
    ap.add_argument("--port")
    ap.add_argument("--once", action="store_true", help="listen-test: exit after one utterance")
    args = ap.parse_args(argv)

    print("Loading speech recognition...", file=sys.stderr)
    transcriber = Transcriber(args.whisper_model)
    assistant = None
    if args.mode == "demo":
        if has_claude_credentials():
            assistant = Assistant()
        else:
            print("No Anthropic credentials found: commands work, free questions are disabled.", file=sys.stderr)

    with StackChan(args.port, timeout=3.0) as bot:
        session = VoiceSession(bot, transcriber, assistant, voice=args.voice,
                               log=lambda m: print(m, file=sys.stderr))
        try:
            if args.mode == "listen-test":
                session.log("Double-tap the head, then say something.")
                while True:
                    bot.poll_events()
                    if session._listen_requested():
                        session.listen_pending = False
                        pcm = session.capture_utterance()
                        bot.listen(False)
                        text = transcriber.transcribe(pcm) if pcm else None
                        lv = np.array(session.last_levels or [0])
                        session.log(f"[levels] room ~{np.median(lv[:8]):.0f} rms, loudest {lv.max():.0f} rms "
                                    f"(speech threshold {session.endpointing.min_threshold:.0f})")
                        session.log(f"[heard] {text!r} -> {classify(text)[0] if text else '-'}")
                        bot.face("neutral")
                        if args.once:
                            break
                    time.sleep(0.02)
            else:
                session.segments = load_segments(args.segments) if args.segments else DEMO_SEGMENTS
                session.narrating = True
                session.run()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                bot.listen(False)
                bot.face("neutral")
            except StackChanError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
