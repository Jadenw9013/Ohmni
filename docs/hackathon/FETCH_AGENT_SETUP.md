# Ohmni in ASI:One

[Open Ohmni PCB Guide](https://asi1.ai/ai/agent1qvzucpk72r48d4gys9npx2an8jjj5mqpzwfjz4yt6a7mnqyag5gzqm5dc32)
(`@ohmni-pcb-guide`). Describe an idea, answer any clarification questions,
review the proposed board and reply with its exact `CONFIRM` code. The agent
saves that brief, starts a fresh build, sends its actual findings in chat, and
provides a private ZIP link when the existing release checks allow it.

## Presenter flow

1. Open the profile above and describe a USB-powered ESP32 idea.
2. Resolve unsupported requests or conflicts. For example, smell identification
   is unsupported; the agent must ask before substituting another function.
3. Review power, sensors, buttons, LEDs, programming access, dimensions, assembly
   preference, assumptions and limitations. Changes invalidate the old code.
4. Reply `CONFIRM <displayed-code>` to save and build. A general “yes” cannot
   start a build. The code belongs to the current sender/conversation and expires
   after 30 minutes.
5. Watch the acknowledgement and automatic progress/result messages. `STATUS`
   checks the latest run without another model call or rebuild.
6. Open **Open your board in Ohmni — 3D view and component tutor** in the result.
   It loads that exact generated revision in Ohmni’s interactive 3D viewer. Click
   a component (or choose it from the searchable list), then ask the tutor about
   its role, connections, or general electronics concepts. Each component keeps
   its own conversation. Answers are labeled AI explanations, never new checks.
   The link is private, lasts 24 hours, and grants viewing and shared-quota tutor
   access to anyone who possesses it. Send `OPEN` in the original Fetch conversation
   for a fresh link; `VIEW` and `WORKSPACE` also work.
7. Download the ZIP from the result or the workspace. It includes KiCad schematic and board,
   fabrication files, BOM, confirmed brief, revision receipt, report, and assembly
   guide. Link possession grants download access for one hour; share deliberately.
8. Ask a follow-up question to select grounded facts from the actual run, or ask
   for a change. A changed revision always needs a fresh reviewed confirmation.

`HELP`/`OPTIONS` lists supported choices; `FINDINGS`, `FILES` or `DOWNLOAD` reads
the latest result. `RETRY` explicitly retries a failed confirmed revision.
`NEW <combined requirements>` starts a separate plan. Keep the agent selected in
ASI's **To** field. In group chats, mention `@ohmni-pcb-guide`; otherwise ASI may
route the message to your personal AI. The transport strips only this agent's
own leading mention before matching commands.

The qualified demo is USB-C 5 V, ESP32, one momentary input button, one indicator
LED, no sensors, no programming header, default 100 × 70 mm board. If reflow is
acceptable, state that explicitly; do not silently relax a hand-soldering goal.
These are engineering design files for human review. No firmware, physical
measurements, safety qualification, RF/EMC guarantee or verified total cost is
provided. Manufacturing readiness does not establish that every requirement is
met: the result preserves VIOLATED and UNKNOWN counts.

## Local setup

Run from this repository's root with Python 3.13, the pinned Fetch extra, KiCad
10.0.5 and libraries. See [engineering setup](../LOCAL_ENGINEERING_SETUP.md).

```sh
python -m pip install -e '.[dev,fetch]'
# Set these privately in the process environment, never in a committed file:
# FETCH_AGENT_SEED: stable private seed, at least 32 characters
# FETCH_AGENT_ENDPOINT: https://YOUR-HOST/submit
# ANTHROPIC_API_KEY: your planner provider key
# OHMNI_FETCH_OUTPUT_DIR: a private, persistent, per-process directory
python -m ohmni.integrations.fetch_ai.agent
```

The main entry point does not load `.env` automatically. A local seed backup
`.env.fetch.local` is ignored and should be mode 600. Keep the seed stable: it
determines the registered address. Never put keys in chat, a public profile,
commits, screenshots or shell arguments. No Agentverse account API key is needed
at runtime. Ctrl+C shuts down the service and marks active jobs interrupted.

## Production deployment

`Dockerfile.agent` reuses the pinned, qualified production KiCad/ngspice engine
image and installs this checkout with its exact `uagents==0.26.1` and
`uagents-core==0.4.12` extra. It includes repository `scripts/` because the adapter
reuses `scripts.demo_server.JobStore` directly. It **does not start the demo HTTP
server** or expose its unauthenticated project API. Updating the underlying
engine requires rebuilding the main Dockerfile and overriding
`OHMNI_ENGINE_IMAGE` with the new verified image reference.

`fly.agent.toml` uses a separate 2 GB, one-worker machine and persistent volume.
Keep one process and one writer to its workspace. Configure private Fly secrets
for the agent seed and planner key. Keep automatic stop disabled during judging.
The gateway listens on `PORT` (8080); the SDK listens on internal port 8081.
Expose only the gateway. The gateway also serves `/workspace/`, a fixed allowlist
of frontend assets, and three capability-authenticated workspace operations:
read the pinned board, ask its component tutor, and download its checked package.
The browser sends its fragment token in an Authorization header; tokens are
stored hashed, never logged, and private responses are not cached. No arbitrary
project listing, mutation or rebuild API is exposed. The existing board renderer
is reused; its component bodies are illustrative and not a simulation. Teaching
uses the deployed Anthropic provider and the same durable request budget as chat.
A stale board or mismatched geometry blocks the workspace instead of substituting
a demo. A stale manufacturing package blocks download.
 `/connect`, `/disconnect`, `/messages`, demo API routes
and arbitrary paths are blocked; forwarding loopback requests must never make
SDK inspector administration public. `/health` reports readiness and mode;
`/agent_info` exposes public identity and protocol metadata only.

Budget admission persists across restart: at most 50 planning/assistant/build
starts per UTC day combined, one billed call in flight, six admissions per minute
and one active build. Provider requests have a 20-second transport timeout, no
hidden transport retries, and at most two structured attempts. Failed calls count.
This is a request quota, not a dollar guarantee. Status/download requests do not
call a model or generate a new board. Conversation capacity is 128, with 4,096
message receipts per day; duplicate messages cannot spend again or start a second
job. In-memory transport traffic is additionally bounded per sender/session.

Sessions are owned by the signed ACP sender **and** the SDK conversation UUID.
The planner, report selection and job IDs are not authentication mechanisms.
Confirmation associations are persisted before a worker starts. On restart,
JobStore marks interrupted jobs failed; completed artifacts are revalidated.
Unconfirmed drafts last 30 minutes. Unapplied assistant change proposals may
expire on restart; prepare a fresh proposal rather than bypassing confirmation.
Download tokens are random, stored as digests, job-bound, valid one hour, served
with no-store/no-referrer headers and never placed in access logs. Every download
rechecks the existing artifact lineage/release gates; stale files are withheld.

## Onboarding and troubleshooting

Follow the [official uAgents onboarding guide](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents).
The original browser onboarding attempted a local identity check on port 8080
and reported reason 9 when no matching local agent was running. A same-identity
retry then stalled. The SDK ownership-registration fallback succeeded using a
locally held, explicitly approved one-hour Agentverse account key. The seed was
used locally to sign the ownership challenge, never sent to Agentverse.
Do not expose inspector routes or copy browser session tokens to bypass setup.

After registration, that temporary key was deleted in Agentverse's UI and its
local file removed. A follow-up request still returned HTTP 200: immediate token
revocation was not verified. Treat such a key as valid until its configured
expiry. This account key is not stored in the runtime or required to chat/build.

If the agent is silent, verify the selected recipient, `/health`, configured
secrets and machine logs. If a quota is hit, wait for the stated window; there is
no public reset/bypass. If a build fails, inspect its recorded failure and ask a
follow-up question before retrying. If a link expires, ask `FILES` for a new one.
Do not advertise firmware, physical tests, arbitrary components or unsupported
sensors to recover a demo. Do not share private links in public submission text.

## Verification

```sh
python -m pytest -q tests/test_fetch_agent.py tests/test_fetch_bridge.py tests/test_fetch_workspace.py tests/test_anthropic_provider.py
python -m ruff check src/ohmni/integrations tests/test_fetch_agent.py tests/test_fetch_bridge.py
python scripts/verify.py fast
```

CI has a separate Fetch job that installs the pinned SDK and exercises its real
manifest construction and loopback gateway without credentials or registration.
Mocks do not establish ASI:One acceptance. The October 17 live rehearsal used an
unsupported smell-detection idea, clarification to the qualified button/LED board,
review and exact confirmation, fresh job `ade4b4faf792`, and a real ASI ZIP
download. Its 20 entries included nine fabrication files plus their manifest;
all ten hashes matched the report. The result reported zero violated requirements,
14 unknowns, complete 35-connection routing, and zero DRC violations/unrouted.
The exact receipt and regression outcomes are in `.ai/verification/FETCH-T02.yaml`.
