# Fetch.ai hackathon implementation and setup

Updated October 16, 2026. Target: October 17–18 AI Hackathon at UCLA.

Start with [research and readiness](RESEARCH_AND_READINESS.md) for submission,
eligibility and networking details, and the [assistant workflow](ASSISTANT_WORKFLOW.md)
for coordinating Codex, Claude and Antigravity. Run `python scripts/hackathon_preflight.py`
from the project venv to check the local environment without calling a model.

Choose **Agentverse / Fetch.ai** for the new weekend functionality. Use
**Applied Intelligence** as the fallback if ASI:One connectivity fails early.
Build one agent that gathers a supported ESP32 brief, asks for confirmation,
executes Ohmni tools, and returns engineering findings in the conversation.

The bounded Fetch conversation flow is now implemented; see
[run instructions and verified limits](FETCH_AGENT_SETUP.md). The remaining text
records the original plan and acceptance criteria. Pre-event
setup tooling, the pinned dependency extra and templates are implemented under
the owner's preparation request. Fetch runtime implementation, accounts and
deployment are not activated by this file. Follow [the development workflow](../AI_WORKFLOW.md)
when implementation is requested. Existing battery-motion scope is unchanged.

## Weekend scope

The minimum full-board target is the qualified USB-powered ESP32 button-and-LED
configuration in `application.hackathon_demo.DEMO_BRIEF`. Reuse that brief's
parameters; generate a fresh result for each demonstrated build. It omits the
programming header and supplies no firmware, so it is an engineering artifact
demonstration rather than a functioning programmed device.

The required conversation is: request → clarify → review assumptions → confirm
→ run → report actual findings → explain a finding. The primary result must be
available inside ASI:One. A website link is supplementary.

Keep Paper redesign, new Sentry prize work, battery-motion implementation,
arbitrary components, firmware, payments and multiple agents out of this scope.
The existing disabled Sentry core stays intact. Its [results and activation
instructions](SENTRY_CORE_RESULTS.md) remain engineering records; the
[old plan](archive/SENTRY_IMPLEMENTATION_PLAN.md) is historical only.

## Start locally with existing code

Run from the repository root. Use a separate output directory for each checkout.
Full platform details and troubleshooting are in [teammate setup](../TEAM_SETUP.md).
The [engineering setup guide](../LOCAL_ENGINEERING_SETUP.md) has exact pinned
installers, the macOS ngspice compiler workaround and the per-machine acceptance checklist.
Prefer `python3.13 scripts/setup_hackathon.py` on macOS/Linux or
`py -3.13 scripts/setup_hackathon.py` on Windows for a new teammate. Use
[troubleshooting](TROUBLESHOOTING.md), the [submission template](SUBMISSION_TEMPLATE.md)
and [team handoff template](TEAM_HANDOFF_TEMPLATE.md) as needed.
The current preparation changes and their local checks are recorded in
[preparation results](PREPARATION_RESULTS.md).

macOS or Linux:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,mcp]'
python scripts/ai_state.py validate
python scripts/demo_server.py
```

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,mcp]"
.\.venv\Scripts\python.exe scripts/ai_state.py validate
.\.venv\Scripts\python.exe scripts/demo_server.py
```

Open `http://127.0.0.1:8765/#workspace`. Guided setup needs no model key;
free-text planning requires an Anthropic key and can incur charges. Stop the
server with Ctrl+C. For an installation-free saved demonstration instead:

```sh
python scripts/serve_offline_demo.py
```

That command replays saved evidence; it does not build a fresh board.

For live planning, copy `.env.example` to `.env` without overwriting an existing
file. Set `ANTHROPIC_API_KEY` using your editor. The current demo server loads
root `.env`; other entry points do not automatically load it. The future agent
must explicitly load configuration or receive environment variables from its
process manager. Do not put credentials in commands, README examples or commits.

For fresh PCB execution, install KiCad and its libraries; the qualification
harness expects **10.0.5**. Put its CLI on PATH, then run:

```sh
python -m ohmni doctor
python scripts/verify_hackathon_demo.py --attempts 1
```

Read doctor output: a successful doctor exit does not mean tools are installed.
Harness exit 0 means qualified, 1 means failure, and 2 means blocked. For Linux
container parity, use the existing POSIX Docker wrapper instead:

```sh
scripts/run_in_kicad_image.sh python3 scripts/verify_hackathon_demo.py --attempts 1
```

Historical [qualification results](OVERNIGHT_RESULTS.md) recorded approximately
16–17 seconds per build. Measure again on the judging host. This scope does not
require ngspice or whole-board simulation. macOS and Windows native-tool
differences are documented in teammate setup.

## Existing integration points

| Existing module | Reuse |
|---|---|
| [application/conversation.py](../../src/ohmni/application/conversation.py) | `ConversationPlanner.propose` and `confirm`; bounded brief and clarification flow |
| [application/projects.py](../../src/ohmni/application/projects.py) | `project_options`, `prepare_project`, `ProjectPipeline.run` |
| [application/project_store.py](../../src/ohmni/application/project_store.py) | Saved revisions and job records; retain workspace lock semantics |
| [application/request_budget.py](../../src/ohmni/application/request_budget.py) | Admission controls for billed requests |
| [mcp_server/service.py](../../src/ohmni/mcp_server/service.py) | Catalog and semantic verification service |
| [application/hackathon_demo.py](../../src/ohmni/application/hackathon_demo.py) | Qualified brief and report qualification helpers |

The MCP server is local stdio and exposes catalog/semantic tools only. It does
not run PCB generation. Prefer direct application service calls from the new
agent adapter; do not add remote MCP hosting just for eligibility.

The planner/store currently assume a local workspace. IDs alone do not provide
authorization. Add sender/session ownership before using them through a public
agent. Keep the demo HTTP server private; expose only the intended ACP receiver.

## Implementation sequence

Implemented package: `src/ohmni/integrations/fetch_ai/`. The operation names below
describe adapter responsibilities; the installed chat commands and launch entry
point are documented in FETCH_AGENT_SETUP.md.

| Order | Deliverable | Acceptance |
|---|---|---|
| 1 | `agent.py`: supported SDK, ACP receiver, acknowledgements and manifest | ASI:One invokes a real `get_supported_options` operation and receives its result |
| 2 | `service.py`: planning and confirmation adapter | Request, clarification and exact brief confirmation work in chat |
| 3 | `sessions.py`: ownership and idempotency | Sender/session owns its plans and jobs; duplicate message cannot launch a duplicate job |
| 4 | Worker bridge and job status | Fresh `ProjectPipeline.run` completes without blocking the chat handler |
| 5 | `results.py`: deterministic report projection | Findings, warnings, unknowns and unavailable tools stay visible |
| 6 | Artifact delivery and operating guide | Result can be inspected in chat; artifact links identify the same job/revision |

Use one agent process, one bounded worker and one writable persistent workspace.
Do not create a new SQLite workspace per message or run two processes that both
claim its lock. Reuse or extract existing job orchestration rather than copying
HTTP handler code into the adapter. Persist job ownership and mark interrupted
jobs explicitly; never show a stale result as a newly completed build.

Suggested service operations:

- `get_supported_options`: return the current bounded choices.
- `propose_design(message, session)`: use the planner and return questions or a brief.
- `confirm_design(plan_id, session)`: save only the displayed, current brief.
- `start_build(project_id, revision_id, session)`: return a job ID immediately.
- `get_build_result(job_id, session)`: return progress or the authoritative result.

Validate arguments and ownership at every operation. Use a backend-generated
job directory, bounded inputs, one concurrent build initially, and bounded model
admission. Do not accept caller paths or shell commands. A status request must
not trigger another model call or rebuild. Missing keys, KiCad failure, routing
timeout and partial results must produce explicit recoverable responses.

Preserve the existing separation: a model proposes structured requirements;
deterministic tools decide engineering outcomes. Scope refusals stay refusals.
Explain reports using their actual fields; never let a generated explanation
override a verdict or imply physical testing.

## Agentverse onboarding and deployment

Planning, exact confirmation, board generation, grounded follow-ups and private
downloads are implemented. See [Fetch agent setup and verified limits](FETCH_AGENT_SETUP.md)
for deployment, onboarding troubleshooting and live ASI:One acceptance.


The current [external uAgent onboarding guide](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents)
uses a running ACP-compatible agent and a reachable endpoint. The sponsor also
documents a mailbox route for locally running agents. Test that alternative
before exposing an endpoint; see the networking section in research and readiness.
Choose one route and verify it through a real ASI:One round trip.
The preparation extra pins uAgents 0.26.1 and uagents-core 0.4.12; live protocol
compatibility still needs acceptance during implementation.

Before runtime work, have the owner prepare Agentverse and ASI:One access, a
stable agent identity, required API credentials and an agreed hosting target.
Keep identity secrets in environment/secret storage. Prefer the already
qualified KiCad container on one persistent host. Confirm architecture and native
tool compatibility before selecting a host. A laptop endpoint is acceptable for
rehearsal but depends on network access, power and sleep settings during judging.

Publish an accurate profile describing supported USB ESP32 circuit design and
verification, with example requests and limitations. Test direct agent selection
and ordinary discovery separately; registration alone does not prove discovery.
Do not invent a handle until Agentverse confirms it is available.

The implementation PR must supply a copyable agent launch command, exact SDK
pin, supported configuration keys, port/endpoint configuration, shutdown steps,
and a no-network smoke test. The agent launch command is documented in FETCH_AGENT_SETUP.md. Running the
existing demo server alone does not register or start the Fetch agent.

## Weekend schedule and reduction gates

All times below are Los Angeles time. Estimates assume one developer familiar
with the repository and prepared accounts/native tools.

| Time | Target |
|---|---|
| Saturday noon–2 p.m. | Working ASI:One → real local tool → ASI:One round trip; attend Fetch workshop as needed |
| 2–5 p.m. | Planning, clarification and confirmation |
| 5–9 p.m. | Qualified fresh board build and actual report in chat |
| 9–11 p.m. | Ownership, deduplication, bounded jobs and recovery |
| Sunday 8–10 a.m. | End-to-end rehearsal and failure tests |
| 10 a.m.–noon | Feature freeze, video, documentation and submissions |

If connectivity is still blocked at 2 p.m., prioritize Applied Intelligence and
the existing interface. Confirm track-entry rules with organizers. If full PCB
execution is unreliable at 9 p.m., narrow the advertised primary agent workflow
to live circuit synthesis, semantic verification and explanation. Demonstrate
that whole reduced workflow in ASI:One; label saved PCB evidence separately.

## Verification and handoff

Run focused existing tests before integrating; they establish the reused boundary:

```sh
python -m pytest tests/test_conversation.py tests/test_conversation_api.py tests/test_mcp_server.py tests/test_hackathon_demo.py
python scripts/ai_state.py validate
```

These tests do not prove Fetch compatibility. Add adapter tests for message
acknowledgement, two isolated sessions, duplicate delivery, expired plans,
unsupported power/functions, provider failure, worker timeout, restart recovery
and truthful report mapping. Run the repository fast gate after runtime changes.
Repeat a fresh qualified KiCad build on the actual host.

Live acceptance requires a complete ASI:One conversation, including confirmation
and a result tied to its actual job. Verify normal discovery, repeat the workflow,
and inspect failure/recovery behavior. A mocked protocol test or saved replay
cannot substitute for that acceptance.

At handoff, record commit, SDK/tool versions, commands, host, profile URL, example
prompt, latest successful job, failures and the selected fallback. Do not include
secrets or private conversation content.

## Submission checklist

Fetch requires Agentverse registration, ACP, usable ASI:One discovery, meaningful
tool execution and a primary workflow completed in chat. Submit through both
Devpost and the event's ASI:One submission agent. Its hackpack also specifies
agent README metadata/tags and a 3–5 minute video; the event overview asks for
2–3 minutes. Target three minutes and confirm upload expectations with mentors.
See the [Fetch event hackpack](https://innovationlab.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack)
and [October Devpost](https://la-ai-hackathon-2026.devpost.com/).

- Record the pre-event starting commit and clearly list only weekend additions.
- Keep the public repository and setup instructions usable by a fresh teammate.
- Include the confirmed agent profile/address and a complete chat demonstration.
- Show actual verification outcomes, including warnings and unsupported checks.
- Complete both submission paths and attend judging in person.

The [event rules](https://la-ai-hackathon-2026.devpost.com/rules) permit existing
open-source work with disclosure and judge newly added functionality. Verify
reuse/licensing eligibility before entry. The live schedule and Fetch hackpack
place hacking end at Sunday noon; Devpost's rules contain a stale April cutoff,
so confirm the deadline with organizers. Do not assume all public pages agree.

## Copyable implementation handoff

> Read AGENTS.md, docs/AI_WORKFLOW.md and this guide. Inspect Git and the ledger.
> The current deliverable is a single Fetch.ai agent exposing Ohmni's bounded
> engineering workflow inside ASI:One. Preserve existing engineering verdicts,
> workspace ownership, request budgets and unrelated changes. When explicitly
> authorized to implement, record the bounded approval under the existing
> workflow, then deliver the real ASI:One tool round trip first. Add planning,
> confirmation and the qualified button-and-LED pipeline in that order. Use the
> reduction gates above. Do not resume the retired Sentry assignment or Paper
> proposal, and do not expand battery-motion scope. Report tested commands,
> remaining live setup and evidence of a complete conversation.
