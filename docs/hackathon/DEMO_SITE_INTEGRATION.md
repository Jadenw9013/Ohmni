# Saved demo on the website

The landing page's **Explore demo** and **Interactive 3D design** links open
`/hackathon-demo.html` in a new tab. The workspace also offers **Open saved demo
(new tab)** under **Explore a finished example**. Keeping the original tab open
preserves an unfinished idea, including when the user returns to Home first.

The demo displays the original board, a damaged copy with a recorded KiCad DRC
failure, and the restored original. It downloads the original Gerber/drill ZIP.
These are **saved results**, not new AI generation, live simulation, or hardware
measurements. The existing warnings, synthetic fabrication assumptions, source
fingerprints, and unverified results remain visible.

## Hosting and capture updates

Both Vercel configurations publish `apps/web`. The committed
`apps/web/hackathon-demo/` mirror contains only `demo.json`, the original PCB,
the damaged PCB, and the fabrication ZIP. The normal Python server serves the
same files through its immutable static allowlist. Raw checker reports and
other canonical capture files are not copied into the public directory.

After deliberately regenerating and qualifying `examples/hackathon-demo`, run:

```text
node scripts/sync_hackathon_demo.mjs
node scripts/sync_hackathon_demo.mjs --check
```

The synchronizer verifies the recorded PCB and ZIP hashes before writing. Its
check mode rejects missing, changed, or extra public files without modifying
them. Node tests run that check in CI. Git preserves the capture bytes on both
Windows and Linux.

The standalone fallback still uses `python scripts/serve_offline_demo.py` and
opens at `http://127.0.0.1:8765/`. It reads the canonical capture and hides
main-site navigation because that server has no project API.

Saved routing receipts also replay on Windows. The qualification harness keeps
the original JSON spelling of the capture's provenance path when hashing a
validated routing plan. Translating a Linux `/repo/...` path to backslashes
would change that hash despite unchanged evidence. Core routing hashing,
canonical files, and receipts are unchanged; path or track tampering still
fails the binding check.

## Verification and rehearsal

Run the existing workflow, fast, and frontend suites before publishing. With
the optional Python Playwright package and Chromium installed, run:

```text
python scripts/browser_check_offline_demo.py --host-mode offline
python scripts/browser_check_offline_demo.py --host-mode site
python scripts/browser_check_offline_demo.py --host-mode static
```

These isolated browser checks block non-local traffic. They check the original,
fault, restore, download hash, delayed-response handling, recovery, and mobile
layout; site modes also exercise entry/return links and draft preservation.
They do not invoke AI or KiCad. A local static check is not proof of a production
deployment: rehearse the deployed URL separately after the owner merges and
deploys the PR.
