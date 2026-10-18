"""Mac-side bridge for the Ohmni Stack-chan USB firmware.

Library:
    from stackchan import StackChan
    with StackChan() as bot:
        bot.face("happy"); bot.pose(yaw=30, pitch=20, ms=400)

CLI (run `python stackchan.py -h`):
    ping | state | pose YAW PITCH [--ms] | face EXPR | led R G B | tone HZ MS
    torque on|off | play DANCE.json | record OUT.json [--seconds] [--hz]
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import deque
from pathlib import Path
from typing import Self

import serial
from serial.tools import list_ports

ESPRESSIF_VID = 0x303A


def find_port() -> str:
    for p in list_ports.comports():
        if p.vid == ESPRESSIF_VID:
            return p.device
    raise RuntimeError("No Stack-chan found on USB. Is it plugged into the base and switched on?")


class StackChanError(RuntimeError):
    pass


class StackChan:
    def __init__(self, port: str | None = None, timeout: float = 2.0):
        self.port = port or find_port()
        self.timeout = timeout
        self._next_id = 1
        self._ser: serial.Serial | None = None
        self.events: list[dict] = []  # unsolicited messages, e.g. {"event": "stall", ...}
        self.audio: deque[bytes] = deque()  # microphone PCM chunks (16 kHz mono int16) while listening
        self.on_event = None  # optional callback(event_dict)

    # -- connection -------------------------------------------------------
    def open(self) -> Self:
        ser = serial.Serial()
        ser.port, ser.baudrate, ser.timeout = self.port, 115200, 0.1
        ser.dtr = ser.rts = False  # opening may still reset the ESP32-S3; we wait for it below
        ser.open()
        self._ser = ser
        self._wait_ready()
        return self

    def close(self) -> None:
        if self._ser:
            self._ser.close()
            self._ser = None

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    def _wait_ready(self, seconds: float = 8.0) -> None:
        """Wait for the boot 'ready' event, or for a ping reply if no reset happened."""
        deadline = time.monotonic() + seconds
        last_ping = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() - last_ping > 1.0:
                self._write({"cmd": "ping", "id": 0})
                last_ping = time.monotonic()
            msg = self._read_json()
            if msg and (msg.get("event") == "ready" or msg.get("id") == 0):
                if msg.get("fw") != "ohmni-stackchan":
                    raise StackChanError(f"Unexpected firmware on {self.port}: {msg}")
                self._ser.reset_input_buffer()
                return
        raise StackChanError(
            f"No reply from {self.port}. Is the Ohmni Stack-chan firmware flashed? "
            "(The factory firmware does not answer over USB.)")

    # -- transport --------------------------------------------------------
    def _write(self, obj: dict) -> None:
        self._ser.write((json.dumps(obj, separators=(",", ":")) + "\n").encode())

    def _read_json(self) -> dict | None:
        raw = self._ser.readline()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None  # boot ROM text and partial lines

    def send(self, cmd: str, **params) -> dict:
        msg_id = self._next_id
        self._next_id += 1
        self._write({"cmd": cmd, "id": msg_id, **params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            reply = self._read_json()
            if reply and "event" in reply:
                self._dispatch(reply)
            elif reply and reply.get("id") == msg_id:
                if not reply.get("ok"):
                    raise StackChanError(f"{cmd}: {reply.get('error')}")
                return reply
        raise StackChanError(f"{cmd}: no reply within {self.timeout}s")

    def _dispatch(self, event: dict) -> None:
        if event.get("event") == "audio":
            self.audio.append(base64.b64decode(event["pcm"]))
            return
        self.events.append(event)
        if self.on_event:
            self.on_event(event)

    def poll_events(self) -> list[dict]:
        """Read any pending unsolicited messages without sending a command."""
        while self._ser.in_waiting:
            msg = self._read_json()
            if msg and "event" in msg:
                self._dispatch(msg)
        events, self.events = self.events, []
        return events

    # -- commands ---------------------------------------------------------
    def ping(self) -> dict:
        return self.send("ping")

    def state(self) -> dict:
        return self.send("state")

    def pose(self, yaw: float | None = None, pitch: float | None = None, ms: int = 300) -> dict:
        params = {"ms": ms}
        if yaw is not None:
            params["yaw"] = yaw
        if pitch is not None:
            params["pitch"] = pitch
        return self.send("pose", **params)

    def face(self, expr: str | None = None, mouth: float | None = None) -> dict:
        params = {}
        if expr is not None:
            params["expr"] = expr
        if mouth is not None:
            params["mouth"] = mouth
        return self.send("face", **params)

    def led(self, r: int, g: int, b: int) -> dict:
        return self.send("led", rgb=[r, g, b])

    def leds(self, colors: list[list[int]]) -> dict:
        return self.send("led", leds=colors)

    def tone(self, hz: int = 880, ms: int = 100) -> dict:
        return self.send("tone", hz=hz, ms=ms)

    def torque(self, on: bool) -> dict:
        return self.send("torque", on=on)

    def reset_limits(self) -> dict:
        return self.send("reset_limits")

    # -- audio --------------------------------------------------------------
    SAMPLE_RATE = 16000
    PLAY_CHUNK_SAMPLES = 4096

    def listen(self, on: bool) -> dict:
        if on:
            self.audio.clear()
        return self.send("listen", on=on)

    def play_chunk(self, pcm: bytes) -> dict:
        """Queue up to 4096 samples of 16 kHz mono int16 PCM. Returns once queued (real-time pacing).

        Raises StackChanError("play: listening") if the robot is listening (e.g. after a double tap).
        """
        return self.send("play", pcm=base64.b64encode(pcm).decode())

    def play_stop(self) -> dict:
        return self.send("play_stop")

    # -- dances -----------------------------------------------------------
    def play(self, dance: dict) -> None:
        """Play a dance: {"name": ..., "steps": [{"at": ms, "yaw", "pitch", "ms", "face", "rgb", "tone"}]}"""
        start = time.monotonic()
        for step in sorted(dance["steps"], key=lambda s: s.get("at", 0)):
            wait = start + step.get("at", 0) / 1000 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            if "yaw" in step or "pitch" in step:
                self.pose(step.get("yaw"), step.get("pitch"), step.get("ms", 300))
            if "face" in step or "mouth" in step:
                self.face(step.get("face"), step.get("mouth"))
            if "rgb" in step:
                self.led(*step["rgb"])
            if "tone" in step:
                self.tone(*step["tone"])

    def record(self, seconds: float = 10.0, hz: float = 10.0) -> dict:
        """Release the servos and sample the head while you move it by hand."""
        self.torque(False)
        steps, start, period = [], time.monotonic(), 1.0 / hz
        try:
            while (elapsed := time.monotonic() - start) < seconds:
                s = self.state()
                if s.get("yaw") is not None and s.get("pitch") is not None:
                    steps.append({"at": int(elapsed * 1000), "yaw": s["yaw"],
                                  "pitch": s["pitch"], "ms": int(period * 1000)})
                time.sleep(max(0.0, start + (len(steps) + 1) * period - time.monotonic()))
        finally:
            self.torque(True)
        return {"name": "recorded", "steps": steps}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Control Stack-chan over USB")
    ap.add_argument("--port", help="serial port (default: auto-detect Espressif USB)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("state")
    p = sub.add_parser("pose"); p.add_argument("yaw", type=float); p.add_argument("pitch", type=float)
    p.add_argument("--ms", type=int, default=400)
    p = sub.add_parser("face"); p.add_argument("expr"); p.add_argument("--mouth", type=float)
    p = sub.add_parser("led"); [p.add_argument(c, type=int) for c in "rgb"]
    p = sub.add_parser("tone"); p.add_argument("hz", type=int); p.add_argument("ms", type=int)
    p = sub.add_parser("torque"); p.add_argument("state", choices=["on", "off"])
    p = sub.add_parser("play"); p.add_argument("file", type=Path)
    p = sub.add_parser("record"); p.add_argument("file", type=Path)
    p.add_argument("--seconds", type=float, default=10.0); p.add_argument("--hz", type=float, default=10.0)
    args = ap.parse_args(argv)

    try:
        with StackChan(args.port) as bot:
            bot.on_event = lambda ev: print(f"event: {json.dumps(ev)}", file=sys.stderr)
            if args.cmd == "ping":
                print(json.dumps(bot.ping()))
            elif args.cmd == "state":
                print(json.dumps(bot.state()))
            elif args.cmd == "pose":
                bot.pose(args.yaw, args.pitch, args.ms)
            elif args.cmd == "face":
                bot.face(args.expr, args.mouth)
            elif args.cmd == "led":
                bot.led(args.r, args.g, args.b)
            elif args.cmd == "tone":
                bot.tone(args.hz, args.ms)
            elif args.cmd == "torque":
                bot.torque(args.state == "on")
            elif args.cmd == "play":
                bot.play(json.loads(args.file.read_text()))
            elif args.cmd == "record":
                print(f"Recording {args.seconds:g}s: move the head by hand now.", file=sys.stderr)
                dance = bot.record(args.seconds, args.hz)
                dance["name"] = args.file.stem
                args.file.write_text(json.dumps(dance, indent=1) + "\n")
                print(f"Saved {len(dance['steps'])} steps to {args.file}", file=sys.stderr)
    except (RuntimeError, serial.SerialException) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
