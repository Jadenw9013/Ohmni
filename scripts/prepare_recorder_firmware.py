"""Export the real revision-bound recorder source for SDK compilation in CI/local use.

This does not fabricate a successful hardware run, native PCB check or firmware
compile receipt. Compile the resulting firmware directory with ESP-IDF v5.4.2.
"""
import argparse
import json
from pathlib import Path

from ohmni.application.recorder import firmware_files
from ohmni.synthesis import synthesize
from ohmni.synthesis.a4 import recorder_brief


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sample-rate',type=int,choices=(32000,48000),default=32000)
    parser.add_argument('--max-seconds',type=int,default=300)
    args=parser.parse_args()
    brief=recorder_brief(recorder_sample_rate_hz=args.sample_rate,recorder_max_seconds=args.max_seconds)
    result=synthesize(brief)
    if not result.accepted:raise SystemExit('Recorder configuration refused')
    files=firmware_files(brief,result.circuit.content_hash)
    args.output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        target=args.output/name
        if target.is_symlink():raise SystemExit('Refusing a symlinked output file')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'firmware_directory':str((args.output/'firmware').resolve()),
        'brief_fingerprint':brief.fingerprint,'circuit_hash':result.circuit.content_hash,
        'sample_rate_hz':args.sample_rate,'max_seconds':args.max_seconds,'physical_testing':'NOT_PERFORMED'}))


if __name__=='__main__':main()
