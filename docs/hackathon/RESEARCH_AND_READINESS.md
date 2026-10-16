# October hackathon research and readiness

Checked October 16, 2026. Read this with the [implementation guide](FETCH_AI_IMPLEMENTATION_PLAN.md)
and the upstream [core demo runbook](CORE_DEMO_RUNBOOK.md). This adds preparation
and acceptance requirements; it does not start the Fetch runtime implementation.

## Decisions before the event

| Decision | Recommendation | Action |
|---|---|---|
| Competition entry | Agentverse / Fetch.ai; Applied Intelligence fallback | Confirm whether a main track and company challenge can be entered together |
| Existing project eligibility | Disclose Ohmni and isolate weekend additions | Ask organizers to confirm reuse eligibility; record their answer |
| Project license | No root license was found in this checkout | Owner chooses licensing with contributor consent as needed; do not insert a license automatically |
| Primary workflow | One supported board request completed in chat | Keep the website optional for Fetch judging |
| Connection route | Test mailbox and external endpoint options before choosing | Use the first supported route that passes the real ASI:One round trip |
| Runtime host | One qualified host with persistent storage | Measure fresh builds before relying on it for judging |

The [competition rules](https://la-ai-hackathon-2026.devpost.com/rules) permit
pre-existing open-source work and require disclosure of new features; only new
functionality is judged. They also cap teams at four. Public code visibility
alone does not settle the event's reuse requirement. Resolve that with organizers
before presenting the existing engine as an eligible foundation.

Do preparatory research, account checks and environment installation before the
event. Implement competition functionality during its authorized build window.
Record the starting commit at hacking start, rather than treating today's commit
as the immutable competition baseline if main changes again.

## Fetch requirements that affect the design

The [event hackpack](https://innovationlab.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack)
requires the primary workflow in ASI:One and both submission paths. It lists
multi-agent collaboration, payments and interactive cards as bonuses rather than
minimum requirements. Reliability is a useful bonus that also improves the demo.
Prioritize one complete agent over additional agents or payment integration.

The [submission instructions](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0/edit)
add an important team step: the lead creates the submission, receives a Team ID,
and every teammate joins it. The status becomes Submitted only after all members
have joined. Prepare the public GitHub, Devpost and video URLs. Also capture the
agent profile and a shared ASI:One chat; the form labels those optional bonuses,
but they are strong evidence that the mandatory workflow actually works.

The event and sponsor pages disagree on video duration; prepare a three-minute
cut and confirm requirements. The Devpost rules have a stale April deadline.
Use Sunday noon as the planning cutoff and confirm the actual submission deadline
with organizers. See [Devpost overview](https://la-ai-hackathon-2026.devpost.com/).

Questions to take to check-in or the Fetch workshop:

1. Is this existing public repository eligible, and what license/disclosure is required?
2. Can we enter Agentverse and Applied Intelligence together?
3. Which submission cutoff and video length govern?
4. Does the sponsor recommend mailbox or a public endpoint for this SDK version?
5. Can a long engineering job send a later response in the same conversation,
   or should the user request status? What are the effective session limits?
6. Is there a sponsor-specific registration deadline or review step before judging?

## Networking and SDK compatibility

The [external integration guide](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents)
describes a reachable public ACP endpoint. The sponsor's [uAgent creation guide](https://innovationlab.fetch.ai/resources/docs/agent-creation/uagent-creation)
also documents local agents connected through Agentverse mailboxes. These are
different onboarding routes. A mailbox is worth testing first on venue Wi-Fi;
its actual ASI:One behavior must be proven before choosing it. Do not expose
Ohmni's local project API to solve a connectivity issue.

That creation guide recommends Python 3.10–3.13 and warns against 3.14. Ohmni's
development environment already uses 3.13, so keep it. Test the chosen SDK in an
isolated environment, then pin the tested version and record dependency resolution.
Do not upgrade the shared venv's Pydantic or SDKs casually during integration.

The [session memory documentation](https://docs.agentverse.ai/documentation/advanced-usages/session-memory)
warns that message history is not automatic. Persist session ownership and
explicit plan state; do not depend on the model remembering a previous brief.
The [streaming guide](https://docs.agentverse.ai/documentation/advanced-usages/streaming-and-chunking)
documents progressive responses but does not establish an unlimited background
job lifetime. Acknowledge promptly and test completion/status behavior live.

Use an environment-supplied stable seed. The [official package documentation](https://pypi.org/project/uagents/)
describes a generated `private_keys.json` when a seed is omitted. Git, Docker and
Vercel exclusions now cover that filename. Keep public agent identity separate
from private seed material and never paste the latter into model handoffs.

The [discovery guide](https://docs.agentverse.ai/documentation/agent-discovery/setup-guide)
emphasizes a useful README, accurate description and a running agent. Test
discovery early rather than first trying it in front of judges. Review account
[quotas](https://docs.agentverse.ai/documentation/advanced-usages/agentverse-subscriptions-and-quotas)
before rehearsal and confirm event credit offers in the hackpack; do not assume
an advertised offer has been activated on your account.

## Repository execution improvements

Use [the cross-assistant workflow](ASSISTANT_WORKFLOW.md) for Codex, Claude and
Antigravity. Keep a single integration owner and one `.ai` ledger writer.
Use the [submission template](SUBMISSION_TEMPLATE.md) and [team handoff template](TEAM_HANDOFF_TEMPLATE.md)
for consistent evidence; consult [troubleshooting](TROUBLESHOOTING.md) before changing dependencies.
The repo was synchronized to `origin/main` at `527bc9dc` during this preparation;
later handoffs must fetch and inspect again. Existing upstream demo rehearsal
and chat improvements should be reused rather than independently rebuilt.

Run the new read-only readiness command from the activated project venv:

```sh
python scripts/hackathon_preflight.py
python scripts/hackathon_preflight.py --board --json
```

Exit 0 means the requested local setup checks passed, with warnings still visible.
Exit 2 means blocked. Neither exit establishes a live agent or qualified board.
Run the qualification harness and core rehearsal separately. No key is read or
transmitted by the preflight command.

Keep the existing CI gates. Add a focused offline adapter test command when its
code exists; avoid spending every local edit cycle rerunning unrelated suites.
Before integration, run the relevant existing boundary tests; before final review,
run the repository fast gate and required native/browser gates. Record skips.
Use a dependency snapshot from the verified host as evidence, not a speculative
lockfile copied from a different architecture.

## Handoff and submission evidence

Maintain one small private handoff note with: owner, branch, base and head commits,
allowed files, command/results, next step and blocker. Store public evidence under
the repo's existing conventions. Before submission, list weekend commits and
features separately from pre-existing functionality. Keep a three-minute demo
that shows input, confirmation, tool execution, an actual result and its limits.
Retain a clearly labeled saved demo in case venue connectivity fails.

Account access, licensing, track-entry policy and acceptance of the submitted
project remain owner/organizer decisions; an AI should not guess their answers.
