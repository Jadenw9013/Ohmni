"""Voice layer for Stack-chan: narration through the robot, double-tap to talk.

Flow:
  - The narrator speaks segments through the robot's speaker using macOS
    text-to-speech, one sentence at a time. With the Ohmni workspace connected
    (`ohmni` mode), the segments are the board's deterministic tour and the page
    highlights each step.
  - Double-tapping the head makes the robot stop speaking and stream its
    microphone. We detect the end of speech, transcribe locally with Whisper,
    and act on it: a fixed command (resume, stop, next, back, repeat, more), or
    a question. Questions go to the page, which asks Ohmni's existing component
    tutor (grounded in this board's records). The companion holds no AI key.

Run:  python voice.py ohmni           # narrate the board open in the Ohmni workspace
      python voice.py demo            # offline example narration (no questions)
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
    max_threshold: float = 900.0     # cap, so speech that starts at once is never mistaken for the floor
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

# A command must be the whole utterance once filler is removed, so "Why stop there?"
# is a question, not "stop".
COMMANDS = {
    "resume": r"resume|continue|go on|keep going|carry on|play|go ahead",
    "stop": r"stop|cancel|never ?mind|quiet|be quiet|that'?s all|pause",
    "next": r"next|skip|next step|go next",
    "back": r"back|go back|previous|last|previous step",
    "repeat": r"repeat|again|say again|say it again|repeat it|what did (?:you )?say|come again",
    "more": r"more|tell me more|explain more|go deeper|elaborate|more details?|details?",
}
FILLER = r"\b(hey|ok|okay|um+|uh+|please|stack ?-?chan|stackchan|robot|the|that|this|one|can you|could you|you)\b"


def classify(text: str) -> tuple[str, str]:
    """Return (intent, text): a narration command, "question", or "unclear"."""
    t = re.sub(r"[^\w\s']", " ", text.lower()).strip()
    core = " ".join(re.sub(FILLER, " ", t).split())
    core = re.sub(r"\b(\w+)(?: \1\b)+", r"\1", core)  # "stop stop" -> "stop"
    if not core:
        return "unclear", text
    for name, pattern in COMMANDS.items():
        if re.fullmatch(f"(?:{pattern})", core):
            return name, text
    return "question", text


# ------------------------------------------------------------ board parts

STOP_WORDS = {"the", "a", "an", "and", "of", "for", "to", "on", "in", "is", "it", "this", "that", "with",
              "part", "parts", "chip", "component", "board", "what", "why", "how", "does", "do", "my"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()) if w not in STOP_WORDS and len(w) > 1}


def resolve_part(text: str, components: list[dict], selected: str | None = None) -> tuple[str | None, list[str]]:
    """Find which part a sentence is about. Returns (ref, candidates).

    ref is None when nothing matched (fall back to `selected`, else ask) or when
    several parts match equally (candidates lists them, so the user can choose).
    """
    said = _words(text)
    compact = re.sub(r"[^a-z0-9]", "", text.lower())
    scores: dict[str, int] = {}
    for part in components:
        ref = part["ref"]
        score = 0
        if re.search(rf"\b{re.escape(ref.lower())}\b", text.lower()) or re.sub(r"[^a-z0-9]", "", ref.lower()) in compact.split():
            score += 10
        part_id = re.sub(r"[^a-z0-9]", "", str(part.get("part_id", "")).lower())
        if len(part_id) >= 4 and part_id[:6] in compact:
            score += 8
        name_words = _words(part.get("name", ""))
        if name_words and name_words <= said:
            score += 6
        score += 2 * len(name_words & said)
        if score:
            scores[ref] = score
    if not scores:
        return (selected, []) if selected else (None, [])
    best = max(scores.values())
    top = sorted(ref for ref, score in scores.items() if score == best)
    if selected and (selected in top or (best < 6 and re.search(r"\b(it|this|that|these|those|here)\b", text.lower()))):
        # "Why is this capacitor here?" with C2 on screen means C2; a weak one-word overlap
        # with another part's name does not beat what the user is looking at.
        return selected, [selected]
    return (top[0], top) if len(top) == 1 else (None, top)


ORDINALS = {"first": 0, "1st": 0, "one": 0, "second": 1, "2nd": 1, "two": 1, "third": 2, "3rd": 2, "three": 2}


def choose_candidate(text: str, candidates: list[str], components: list[dict]) -> str | None:
    """Resolve an answer to 'which one do you mean?': a reference, a name, or 'the second one'."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    for ref in candidates:
        if ref.lower() in words:
            return ref
    for word in words:
        if word in ORDINALS and ORDINALS[word] < len(candidates):
            return candidates[ORDINALS[word]]
    return resolve_part(text, [p for p in components if p["ref"] in candidates])[0]


def part_name(components: list[dict], ref: str) -> str:
    part = next((p for p in components if p["ref"] == ref), None)
    return part["name"] if part and part.get("name") else ref


def spoken_answer(answer: dict) -> str:
    """What the robot says for a tutor answer: labelled as an explanation, unknowns kept, one follow-up."""
    explanation = (answer.get("explanation") or "").strip()
    if not explanation:
        return "Ohmni didn't return an explanation for that."
    text = f"Here's Ohmni's explanation, based on your board's records. {explanation}"
    unknowns = [u.strip() for u in answer.get("unknowns") or [] if u.strip()]
    if unknowns:
        text += " Not yet known: " + " ".join(unknowns)
    follow = [q.strip() for q in answer.get("next_questions") or [] if q.strip()]
    if follow:
        text += f" You could ask: {follow[0]}"
    return text


# ----------------------------------------------------------------- session

@dataclass
class Segment:
    title: str
    text: str
    more: str | None = None
    refs: list[str] = field(default_factory=list)
    tour_index: int | None = None


def segments_from_context(context: dict) -> list[Segment]:
    return [Segment(step["title"], step["narration"], refs=list(step.get("component_refs") or []), tour_index=i)
            for i, step in enumerate(context.get("tour") or []) if step.get("narration")]


@dataclass
class VoiceSession:
    bot: StackChan
    transcriber: Transcriber
    page: object | None = None  # ohmni_link.PageLink when the workspace is connected
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
    selected: str | None = None     # part currently selected in the workspace
    board_id: str | None = None     # job id of the board being narrated
    pending_question: tuple[str, list[str]] | None = None  # asked "which one?": (question, candidates)
    last_answer: str | None = None  # what the robot last answered, so "repeat" can replay it

    def __post_init__(self) -> None:
        self.bot.on_event = self._on_event

    def _on_event(self, ev: dict) -> None:
        kind = ev.get("event")
        if kind == "listen":
            if ev.get("on"):
                self.bot.audio.clear()  # never mix in chunks from a previous capture
                self.listen_pending, self.listen_ended = True, None
            elif ev.get("reason") != "host":
                self.listen_ended = ev.get("reason")
        elif kind == "touch":
            self.log(f"[touch] {ev.get('gesture')}")
        elif kind == "stall":
            self.log(f"[stall] {ev}")

    # -- workspace ------------------------------------------------------------
    @property
    def components(self) -> list[dict]:
        return (self.page.context or {}).get("components", []) if self.page else []

    def page_command(self, name: str, timeout: float = 10.0, **args):
        """Ask the page for a view-only action. Returns data, or None if unavailable."""
        if not self.page or not self.page.connected:
            return None
        from ohmni_link import PageError
        try:
            return self.page.command(name, timeout=timeout, **args)
        except PageError as exc:
            self.log(f"[page] {exc}")
            return None

    def sync_page(self) -> None:
        """Pick up a new board and user selections from the page."""
        if not self.page:
            return
        if not self.page.connected:
            if self.board_id is not None:
                # The page went away: stop narrating; a reconnect restarts the tour.
                self.log("[page] workspace closed; narration paused")
                self.narrating = False
                self.board_id = None
                self.page.context = None
            return
        context = self.page.context
        if context and context.get("job_id") != self.board_id:
            self.board_id = context.get("job_id")
            self.segments = segments_from_context(context)
            self.index = self.sentence = 0
            self.selected = context.get("selected")
            self.narrating = bool(self.segments)
            self.log(f"[page] board {self.board_id}: {len(self.segments)} tour steps")
        while self.page.events:
            event = self.page.events.popleft()
            if event.get("type") == "selected":
                self.selected = event.get("ref")

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
            self.say("That's the whole tour. Double tap my head to ask about any part.", face="happy")
            return
        sentences = split_sentences(seg.text)
        if self.sentence == 0:
            self.log(f"[narrate] {seg.title}")
            self.bot.face("happy")
            if seg.tour_index is not None:
                self.page_command("tour", index=seg.tour_index)
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
                # The floor is the quietest tenth heard so far (pauses between words), never the speech itself.
                floor = float(np.percentile(levels, 10)) if len(levels) >= 4 else 0.0
                threshold = min(ep.max_threshold, max(ep.min_threshold, floor * ep.noise_factor))
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
        self.bot.audio.clear()
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
        elif self.pending_question and self._answer_pending_choice(text):
            return
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
            if self.last_answer and not self.narrating:
                self.say(self.last_answer)  # replay the answer (e.g. one cut short by a double tap)
            else:
                self.sentence, self.narrating = 0, True
        elif intent == "more":
            if seg and seg.more:
                self.say(seg.more)
            else:
                ref = self.selected or (seg.refs[0] if seg and seg.refs else None)
                self.answer("Tell me more about this part and why it is on this board.", ref=ref)
        elif intent == "question":
            self.answer(text)
        else:
            self.say("Sorry, I didn't catch that.", face="sad")

    def answer(self, question: str, ref: str | None = None) -> None:
        """Answer through the page's component tutor (Ohmni's teach route)."""
        if not self.page or not self.page.connected:
            self.say("Questions need your board open in the Ohmni workspace, with the desk robot connected.", face="sad")
            return
        components = self.components
        if ref is None:
            ref, candidates = resolve_part(question, components, self.selected)
            if ref is None and candidates:
                self.pending_question = (question, candidates)
                names = " or ".join(f"the {part_name(components, r)}, {r}" for r in candidates[:3])
                extra = f", or one of {len(candidates) - 3} others" if len(candidates) > 3 else ""
                self.say(f"Which one do you mean: {names}{extra}?", face="thinking")
                return
            if ref is None:
                self.say("Which part do you mean? Select it on the screen, or say its name.", face="thinking")
                return
        self.say(f"Let me check the records for the {part_name(components, ref)}.", face="thinking")
        t = time.monotonic()
        data = self.page_command("ask", timeout=100, ref=ref, question=question)
        if data is None:
            self.say("Sorry, I couldn't get an answer from Ohmni just now.", face="sad")
            return
        self.log(f"[tutor] {data.get('explanation', '')!r} ({time.monotonic() - t:.1f}s)")
        self.last_answer = spoken_answer(data)
        if not self.say(self.last_answer):
            self.log("[tutor] answer interrupted; say 'repeat' to hear it")

    def _answer_pending_choice(self, text: str) -> bool:
        """After 'which one do you mean?', treat a reference, name or ordinal as the choice."""
        question, candidates = self.pending_question
        self.pending_question = None
        ref = choose_candidate(text, candidates, self.components)
        if ref is None:
            return False
        self.log(f"[intent] choice {ref} for {question!r}")
        self.answer(question, ref=ref)
        return True

    # -- main loop ------------------------------------------------------------
    def run(self) -> None:
        self.log("Double-tap the robot's head to talk. Ctrl+C to quit.")
        while True:
            self.bot.poll_events()
            self.sync_page()
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
            "temperature, humidity and pressure from a BME280 sensor over I2C.",
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
    ap.add_argument("mode", choices=["ohmni", "demo", "listen-test"])
    ap.add_argument("--segments", type=Path, help="demo: JSON list of {title, text, more?}")
    ap.add_argument("--voice", help="macOS voice name (see `say -v ?`)")
    ap.add_argument("--whisper-model", default="mlx-community/whisper-base.en-mlx")
    ap.add_argument("--port", help="robot serial port (default: auto-detect)")
    ap.add_argument("--allow-origin", action="append", default=[],
                    help="ohmni: extra workspace origin allowed to connect (e.g. a staging URL)")
    ap.add_argument("--once", action="store_true", help="listen-test: exit after one utterance")
    args = ap.parse_args(argv)
    log = lambda m: print(m, file=sys.stderr)

    print("Loading speech recognition...", file=sys.stderr)
    transcriber = Transcriber(args.whisper_model)
    page = None
    if args.mode == "ohmni":
        from ohmni_link import DEFAULT_ORIGINS, PageLink
        page = PageLink(origins=(*DEFAULT_ORIGINS, *args.allow_origin), log=log).start()
        log(f"Waiting for the Ohmni workspace on ws://127.0.0.1:{page.port}. "
            "Open your board and click 'Desk robot'.")

    with StackChan(args.port, timeout=3.0) as bot:
        session = VoiceSession(bot, transcriber, page, voice=args.voice, log=log)
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
                if args.mode == "demo":
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
            if page:
                page.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
