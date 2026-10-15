# Tonight's demo readiness and presenter runbook

Candidate inspected: `d0b227f07ad694259de6991ad82a1eb9345437b7` (main after
PR #79). Rehearsal started on October 14, 2026 Pacific / October 15 UTC.
This report is separate from the historical
[release rehearsal](REHEARSAL_ACCEPTANCE.md). Re-run the checks after Claude's
browser-hardening PR merges; its results do not apply retroactively here.

The owner asked for independent work toward tonight's readiness while Claude
handles browser hardening. This change owns development checks and this runbook;
it does not activate a product milestone or modify the shared task ledger.

## Current disposition

The desktop saved demonstration works on the public site and on the local static
server. **The public backend is stale:** its image lacks the request-budget and
telemetry modules present on main. Live AI success and live Sentry ingestion
remain unverified. Health is green despite this deployment mismatch.

| Area | Observed result | What remains |
| --- | --- | --- |
| Public saved assets | All 20 selected files matched the candidate at `2026-10-15T04:36:01Z`, including the original board, diagnostic board and fabrication ZIP. | Repeat against the final merged candidate. |
| Public API configuration | Vercel-proxied `/api/health` reported ready, API version 2 and `free_text: true`. No model request was submitted. | Successful provider response and current budget are not proven by health. |
| Public desktop navigation | Home → Explore demo opened a separate tab. Original → Show fault → keyboard Restore original worked. Restore returned focus to Original board. Back to Ohmni → Start building opened the conversational workspace. | Mobile acceptance and the broader browser suite belong to Claude's browser-hardening work. |
| Public rendering and truthfulness | The original rendered in 3D. The fault reported the disconnected LED pad and dangling track; other checks were NOT CHECKED. Restore brought back the original warnings and download link. | This is a saved capture, not a new engineering run or an AI repair. |
| Local fallback | `serve_offline_demo.py --port 8826` served the original, fault and restored board in the browser. Site navigation was correctly absent. | This manual pass did not disconnect the computer's network or qualify download latency. |
| Expanded public alignment | At `2026-10-15T04:40:42Z`, all 20 saved-demo and 15 selected Vercel application assets matched. All six Fly static probes failed: three older files and three telemetry files returning 404. Overall result: FAIL. | Deploy an explicitly approved matching backend candidate, then repeat. |
| Fly runtime | After owner sign-in, read-only checks found one started machine, passing health, the `/data` mount and its attached 1 GB `ohmni_data` volume. KiCad 10.0.5 and ngspice-42 executed successfully. | Another unattached 1 GB volume was observed and left untouched. No storage/billing changes were made. |
| Fly release/source | Release v12 was created `2026-10-10T04:35:48Z`; no commit appeared in its release metadata. `telemetry.py` and `request_budget.py` are absent from the image. | Backend rollout is required to claim these merged protections/instrumentation are deployed. No rollout was performed in this rehearsal. |
| Direct health | The direct Fly health check also passed at `2026-10-15T04:41:56Z`. | This corroborates configuration only, not source alignment or working credentials. |
| Offline Sentry harness | Original Windows run: 7/8 checks passed, timeout check failed because a Unix shebang fixture could not spawn. Portable fixture run: 8/8 passed, including canary absence and zero outbound attempts. | This uses an in-memory recorder, not live ingestion. See the portability change below. |
| Live Sentry | NOT RUN; no DSN/account/ingestion was activated. | Owner setup and approval, then actual issue/trace/metric verification. |
| Paid AI / fresh KiCad run | NOT RUN in this rehearsal. | Explicit approval for a paid rehearsal; deployed native-tool and image verification first. |

The saved capture is the ESP32 controller with one button and one LED on a
100 × 70 mm board. It is different from the dense STM32 circuit shown on the
landing page. Do not present the landing illustration as the board whose
KiCad receipts appear in the saved demonstration.

The authenticated source comparison completed by `2026-10-15T04:42:20Z`:

| Source file | Deployed SHA-256 | Candidate Git-blob SHA-256 |
| --- | --- | --- |
| `scripts/demo_server.py` | `29b401778ce7c8fb44ac3dbe68315b8c15c9d996b2322584892b9d5c7346357a` | `7451b9723b243eda69170dfc0821b62af8fa2ac8c156e06097257691821a8c7d` |
| `src/ohmni/adapters/telemetry.py` | Absent | `23785e78ff1ed2645cfc13c233bc91c0204c7ab8b3073d30ff62abd31a31d6a3` |
| `src/ohmni/application/request_budget.py` | Absent | `ed397e0defa1773ac457fb55ee8e05d55616e9f5f8a9d1daee0fc7a308266daf` |

Comparison used `git show COMMIT:path` bytes, not Windows working-file bytes.
CI for candidate `d0b227f0` passed `fast`, `corpus`, `frontend` and `kicad-gate`:
[repository-gates run](https://github.com/Jadenw9013/Ohmni/actions/runs/38681277971).
That CI result does not repair the observed deployment mismatch.

## Repeatable release checks

Run from the intended candidate checkout using its installed Python environment.
The check reads committed Git bytes, so Windows line endings do not create false
mismatches. Reports contain hashes, counts and owned diagnostic codes, not HTTP
bodies, configuration contents, instance IDs or raw exceptions.

```powershell
python scripts/rehearse_hackathon_release.py --site https://ohmni-yvnd.vercel.app --include-app --backend-site https://ohmni-demo.fly.dev --health-url https://ohmni-yvnd.vercel.app/api/health --output build/tonight-readiness/public.json
python scripts/rehearse_hackathon_release.py --site https://ohmni-yvnd.vercel.app --health-url https://ohmni-demo.fly.dev/api/health --output build/tonight-readiness/direct-health.json
```

The default remains 20 saved-demo files. `--include-app` adds 15 selected
workspace/telemetry files; `--backend-site` checks six selected static files
served by Fly. These are bounded allowlists, not a crawl or a whole-deployment
attestation. Health, saved-demo, application and backend-static results stay
separate. A mismatch must not be hidden by the other groups passing.

Backend static assets can expose a stale frontend snapshot in the Fly image.
They cannot identify backend-only Python changes. Health's `ui_version` hashes
static files, not the application source; use the release/image and source
provenance separately. The repository CI does not deploy Fly on merge.

All requests are GETs with bounded response sizes and deadlines. No AI, tool
execution, telemetry ingestion or deployment happens in this check.

## Presenter sequence: three minutes

Prepare the public saved-demo tab, the local saved-demo tab and a verified
original fabrication ZIP before presenting. Start the local server in a terminal
that stays open:

```powershell
python scripts/serve_offline_demo.py --port 8826
```

Open `http://127.0.0.1:8826/`. If that port is occupied, choose another free port;
do not stop an unrelated process. This server has no AI/API routes. The
interactive board, recorded reports and original ZIP are local assets.

| Time | Action and words | Failure escape |
| --- | --- | --- |
| 0:00–0:20 | Show the workspace: “Describe a board in ordinary language. Ohmni proposes a plan; engineering checks decide what can proceed.” | Do not submit an unrehearsed paid request on stage. |
| 0:20–0:50 | Open Explore demo: “This is a saved successful run of an ESP32 controller. These checks ran on these exact files.” Orbit the original board. | Switch directly to the already-open local tab if the network stalls. |
| 0:50–1:25 | Show fault: point to D1, net LED1_A, and KiCad's missing connection. Explain that removing copper breaks the LED's current path. | Read the recorded finding even if 3D is unavailable; do not call an unchecked render a pass. |
| 1:25–1:45 | Restore original: “This restores the checked original; it is not an AI-generated repair.” Show the restored report. | Keep the original tab ready; do not repeatedly retry a failing service. |
| 1:45–2:10 | Show/download the original Gerber/drill ZIP. Point out zero recorded DRC errors, retained ERC warnings and the synthetic fabrication profile. | Use the previously hash-checked local ZIP. The damaged copy is never an export candidate. |
| 2:10–2:45 | Sentry segment: use the offline fault harness until live ingestion is explicitly activated and verified. Explain the distinction between an engineering rejection and a software/tool failure, and the privacy canary check. | Show a previously recorded harness result, clearly labeled, if the local test fails. Never describe a recorder as a live Sentry dashboard. |
| 2:45–3:00 | “The model proposes. Independent checks keep uncertainty visible. Here are the files and the evidence.” | Finish from the saved result instead of waiting on another generation. |

An approved, successful live AI rehearsal can replace part of the opening; it
must not remove the saved fallback. The captured board has no simulation or
bench-testing receipt. Do not promise that it was physically built, that SPICE
ran for it, or that its synthetic manufacturing profile is a supplier quote.

## Live backend gate

The owner explicitly approved “this backend rollout” of `d0b227f0`, preserving
the existing volume and keeping telemetry disabled, after being told about
remote-build charges and restart interruption. The prepared build context uses
1,426 canonical Git blobs (20,130,009 bytes), restricted to Docker inputs; no
untracked credentials or private local files are included. Its local manifest is
`build/tonight-readiness/deploy-d0b227f0.manifest.json`.

Rollout uses an image-only update of the existing machine after a build-only
registry push. The previous immutable image, retained for rollback, is
`registry.fly.io/ohmni-demo@sha256:500d7a872294d41df7cf36e99dfa7cd22ae7d50bf926c0bf9407c915be15a74d`.
Rollback would restore the old backend and its known version mismatch. It is
not a substitute for a qualified new release.

After the owner signs in, use read-only operator checks before any deployment:

```powershell
flyctl status --app ohmni-demo
flyctl releases --app ohmni-demo --image
flyctl volumes list --app ohmni-demo
```

Confirm the intended image/source, exactly one intended running machine and its
`ohmni_data` volume mounted at `/data`. `min_machines_running = 1` is a minimum,
not a maximum. Do not publish raw machine IDs, IPs, secrets, environment dumps or
application logs in readiness evidence. If release metadata does not identify
the source revision, verify selected source-file hashes in the running image;
the container omits `.git`.

Inside the running application image, check `kicad-cli --version` and
`/opt/ngspice42/bin/ngspice -v`. Neither health nor a CI run proves those tools
are present in the deployed container. Do not redeploy automatically to resolve
a mismatch: prepare the specific candidate and request deployment approval.

For a budget inspection, run `python scripts/ai_budget.py show` as the `kicad`
application user with its actual configured storage. Even “show” can initialize
SQLite; running it as root can create a file the app cannot write. Do not reset
the budget or change limits as part of a read-only readiness check.

## Paid AI rehearsal gate

Prepare one plan request with an explicit supported scope, for example:

> A USB-powered ESP32 board with one push button and one status LED, no sensors,
> no memory and no extra header. Use a 100 by 70 mm board.

Ask the owner before submitting it. Stop at reviewing the proposed plan: no
follow-up, confirmation, generation or automatic retry is authorized by this
runbook. Confirm the returned plan actually has the requested family, counts,
power and dimensions; provider success alone is not plan correctness.

One HTTP request is not a one-call or dollar cap. At this candidate the provider
permits up to three schema attempts with 16,384 output tokens per attempt; SDK
transport retries can add attempts. The browser aborts after 90 seconds while
the server may still be working. If it times out, switch to the saved demo and
inspect the server state before considering another paid call.

## Sentry activation gate

Follow [Sentry core results, owner checklist](SENTRY_CORE_RESULTS.md#4-owner-checklist-to-activate-later-two-projects).
No account, quota, billing protection or ingestion is assumed. Keep Replay,
profiling and logs off for this release. Never put a backend DSN or auth token
into the frontend or a PR.

For the existing offline proof:

```powershell
python scripts/telemetry_fault_harness.py --output build/tonight-readiness/telemetry-faults
```

It uses the actual pinned SDK with an in-memory recorder and refused outbound
sockets. Its deterministic provider/tool failures are test scenarios, not a
hardware check and not evidence of a live Sentry issue. Only after activation
approval should a real project dashboard be checked for the controlled issue,
linked browser/API/worker trace and expected metrics. Do not inject a failure
into the public production process for the presentation.

This PR makes the timeout fixture portable: the current Python executable runs
an isolated child without a shell, announces readiness, then sleeps. The actual
process adapter times out and terminates that child. The emitted tool class is
truthfully `other`; it is not a KiCad invocation. This supersedes the older
Sentry results document's description of a fake `kicad-cli` for this scenario.
The original failed report is preserved locally at
`build/tonight-readiness/telemetry-faults/summary.json`; the corrected CLI run is
`build/tonight-readiness/telemetry-faults-final/summary.json`. The standalone
harness also now guards `connect_ex`, with a regression that bypasses the test
fixture's guard to prove the harness itself refuses that outbound path.

## Freeze and handoff

1. Merge only reviewed work through PRs; select one final candidate commit.
2. Re-run selected asset/health alignment and Claude's real-browser gate on that
   candidate. Preserve failures alongside later successful runs.
3. Rehearse the actual presenter browser at projector resolution, including
   keyboard, fault/restore and the original download. Mobile CI is a separate
   acceptance check; a desktop pass does not close it.
4. Confirm backend identity and approved live AI/Sentry results, or label those
   segments unverified and use the saved/offline sequence above.
5. Keep the local fallback and checked ZIP ready. Avoid new feature changes after
   the final successful rehearsal.

## Software verification and independent review

Implementation commit: `208a8a2c`.

| Check | Result |
| --- | --- |
| `python scripts/ai_state.py validate` | VALID; shared ledger unchanged |
| `python scripts/verify.py workflow` | 12 passed |
| `python scripts/verify.py fast` | 2,692 passed, 87 skipped, 63 deselected; 464.71 s |
| Final focused readiness/harness tests | 90 passed; includes the standalone `connect_ex` regression added after the full suite collected its cases |
| Node frontend suite | 1,119 passed; zero failed/skipped |
| Changed Python files, Ruff | Passed |
| `git diff --check` | Passed |
| Final actual offline fault harness | 8/8 checks passed with SDK 2.72.0 and no outbound attempts |

Two independent agents cross-reviewed the checker and harness changes. No
BLOCKER/HIGH/MEDIUM findings remained. A pre-existing LOW `connect_ex` guard gap
was fixed and independently re-reviewed; its standalone guard regression and
all three dedicated harness tests passed. The checker reviewer independently
ran all 87 checker tests. POSIX execution is left to CI; the local runs used
Windows and Python 3.13.3.

These are software checks. Skipped tests, absent private source bundles, paid
provider calls, new hardware verification and live telemetry are not implied
passes. This report does not mark any shared ledger task complete.
