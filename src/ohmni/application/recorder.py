"""Revision-bound recorder firmware and bounded digital simulation artifacts.

The model accepts synthetic microphone samples and a deterministic card service
schedule. It does not simulate analog acoustics, transistors, RF or SD silicon.
"""
import hashlib
import io
import json
import math
import struct
import wave
from pathlib import Path

from ..domain.recorder import RECORDER_PINS
from ..synthesis.models import ArchetypeId

FIRMWARE_ROOT = Path(__file__).parents[1] / "firmware/recorder"
SCENARIOS = ("normal", "missing_card", "card_full", "slow_card", "card_removed", "microphone_timeout")
MODEL_VERSION = "recorder-digital-1"


def simulate_recorder(brief, scenario="normal"):
    if brief.archetype is not ArchetypeId.A4_USB_VOICE_RECORDER or scenario not in SCENARIOS:
        raise ValueError("Choose a supported recorder simulation scenario")
    rate = brief.recorder_sample_rate_hz
    # Bounded three-second workload, using exactly the firmware's 256-sample
    # blocks, 128-block queue, PCM16 and 64-bit stereo I2S frame settings.
    seconds = min(3, brief.recorder_max_seconds)
    target = rate * seconds
    block = 256
    queue_capacity = 128
    queue = []
    written = 0
    produced = 0
    max_queue = 0
    now = 0.0
    next_write = 0.0
    write_seconds = .001 if scenario != "slow_card" else .05
    error = None
    events = [{"time_ms":0,"event":"debounced_record_press"}]
    if scenario == "missing_card":
        error = "card_missing"
    elif scenario == "microphone_timeout":
        error = "i2s_timeout"
    else:
        while produced < target:
            count = min(block, target - produced)
            produced += count
            now = produced / rate
            if scenario == "card_removed" and now >= .5:
                error = "card_removed"; break
            if len(queue) == queue_capacity:
                error = "buffer_overflow"; break
            queue.append(count)
            max_queue = max(max_queue, len(queue))
            while queue and next_write <= now:
                if scenario == "card_full" and written >= rate // 2:
                    error = "card_write_failed"; break
                written += queue.pop(0)
                next_write = max(next_write, now - block/rate) + write_seconds
            if error: break
        if not error:
            written += sum(queue)
    events.append({"time_ms":round(now*1000), "event":error or "recording_finalized"})
    # A deterministic 440 Hz test tone exercises sample->PCM->WAV formatting;
    # it is synthetic input and must never be presented as a hardware recording.
    pcm = b"".join(struct.pack("<h",int(10000*math.sin(2*math.pi*440*i/rate))) for i in range(written))
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(pcm)
    result = {"model_version":MODEL_VERSION, "brief_fingerprint":brief.fingerprint,
        "scenario":scenario, "status":"SIMULATED", "outcome":"ERROR_HANDLED" if error else "RECORDING_FINALIZED",
        "error":error, "sample_rate_hz":rate, "channels":1, "pcm_bits":16,
        "i2s_bclk_hz":rate*64, "required_write_bytes_per_second":rate*2,
        "queue_capacity_bytes":queue_capacity*block*2, "queue_peak_bytes":max_queue*block*2,
        "modeled_card_write_seconds_per_block":write_seconds,
        "input_samples":produced, "saved_samples":written, "wav_bytes":len(stream.getvalue()),
        "duration_seconds":written/rate, "events":events,
        "waveform": [round(math.sin(2*math.pi*440*i/rate),4) for i in range(128)],
        "limitations":["Synthetic input and modeled card latency; not a recording from hardware.",
            "Digital workload model, not ESP32 instruction emulation or SPICE.",
            "Only a bounded three-second scenario is modeled. Long recording reliability, power, acoustic quality and electrical timing need physical testing.",
            "Injected faults demonstrate model outcomes; firmware tests and bench tests are separate evidence."]}
    return result, stream.getvalue()


def firmware_files(brief, circuit_hash):
    if brief.archetype is not ArchetypeId.A4_USB_VOICE_RECORDER:
        return {}
    files = {"firmware/"+p.relative_to(FIRMWARE_ROOT).as_posix():p.read_bytes()
             for p in sorted(FIRMWARE_ROOT.rglob("*")) if p.is_file() and p.suffix in {".c",".h",".txt",".defaults",".md"}}
    config = ["// Generated from this exact saved board revision. Do not copy between revisions.",
        f'#define OHMNI_BRIEF_HASH "{brief.fingerprint}"', f'#define OHMNI_CIRCUIT_HASH "{circuit_hash}"',
        f"#define OHMNI_SAMPLE_RATE {brief.recorder_sample_rate_hz}",
        f"#define OHMNI_MAX_SECONDS {brief.recorder_max_seconds}"]
    config += [f"#define OHMNI_{key.upper()} {value}" for key,value in RECORDER_PINS.items()]
    files["firmware/main/recorder_config.h"] = ("\n".join(config)+"\n").encode()
    manifest = {"schema_version":1, "brief_fingerprint":brief.fingerprint,"circuit_hash":circuit_hash,
        "framework":"ESP-IDF v5.4.2", "target":"esp32", "gpio":RECORDER_PINS,
        "sample_rate_hz":brief.recorder_sample_rate_hz, "max_seconds":brief.recorder_max_seconds,
        "physical_testing":"NOT_PERFORMED", "files":{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    files["firmware/manifest.json"] = (json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
    return files


def recorder_artifacts(brief, circuit_hash):
    files = firmware_files(brief,circuit_hash)
    scenarios = []
    for scenario in SCENARIOS:
        result, wav = simulate_recorder(brief, scenario)
        scenarios.append(result)
        files[f"simulation/{scenario}.json"] = (json.dumps(result,indent=2)+"\n").encode()
        if scenario == "normal": files["simulation/synthetic-test-tone.wav"] = wav
    return files, scenarios


def write_recorder_artifacts(destination, brief, circuit_hash):
    files, scenarios = recorder_artifacts(brief, circuit_hash)
    for name,data in files.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return {"brief_fingerprint":brief.fingerprint, "circuit_hash":circuit_hash,
        "firmware":"ESP-IDF v5.4.2 source included", "physical_testing":"NOT_PERFORMED",
        "gpio":RECORDER_PINS,"simulations":scenarios,
        "files":{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
