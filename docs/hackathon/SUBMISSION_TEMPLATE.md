# Hackathon submission template

Copy this into your submission draft and replace every bracketed field. Keep
private contact information in the official forms, not in this public repository.
Do not mark a check complete without evidence. This is a template, not a submitted
project or permission to publish anything.

## Project summary

**Project:** Ohmni — from a hardware idea to reviewed PCB files in ASI:One

**Company challenge:** Fetch.ai — ASI:One Agent Challenge: From Intent to Action

**Other event track:** [owner-confirmed selection, if applicable]

**Target user:** Beginners and makers who need help turning a supported electronics
idea into an inspectable design and understanding its limitations.

**Problem:** PCB design requires translating intent into components, connections,
layout and checks; chat advice alone does not produce a traceable design package.

**What we built during the event:** [one precise new capability]

**User outcome:** Review a plan, explicitly confirm generation, inspect real findings
and download design/fabrication files from ASI. Firmware and physical assembly are separate.

## Existing work and weekend contribution

| Field | Fill in |
|---|---|
| Starting commit at hacking start | [full commit hash and local time] |
| Prior public repository | [URL] |
| Reuse eligibility confirmation | [organizer answer or rule reference; no private contact data] |
| Project license decision | [owner-selected license and any reuse conditions] |
| Pre-existing capabilities | [catalog, deterministic verification, synthesis, KiCad pipeline, website, saved demo; correct this list as needed] |
| Weekend implementation | [only functionality actually added during the event] |
| Weekend commits or comparison | [links or commit range] |

Do not attribute pre-event setup, engineering receipts or the original engine to
the weekend. Explain how the new agent uses that existing platform.

## Required links and resources

- Public repository: https://github.com/Jadenw9013/Ohmni
- Run/setup instructions: https://github.com/Jadenw9013/Ohmni/blob/main/docs/hackathon/FETCH_AGENT_SETUP.md
- Devpost project: [project URL, not the event homepage]
- Demo video: [public/viewable URL; verify access signed out]
- Agentverse profile: https://agentverse.ai/agents/details/agent1qvzucpk72r48d4gys9npx2an8jjj5mqpzwfjz4yt6a7mnqyag5gzqm5dc32/profile
- Agent name/handle: Ohmni PCB Guide / `@ohmni-pcb-guide`
- Agent address: `agent1qvzucpk72r48d4gys9npx2an8jjj5mqpzwfjz4yt6a7mnqyag5gzqm5dc32`
- Shared ASI:One conversation: [public demo chat URL with synthetic/public inputs]
- Runtime requirements: Python 3.13; uagents 0.26.1; uagents-core 0.4.12; KiCad 10.0.5 and libraries; Anthropic API key; stable agent seed; HTTPS endpoint and persistent storage. Follow the setup guide for exact environment variable names.
- Known limits: supported ESP32 USB-powered families only; USB-C power only; no generated firmware, assembly or physical testing. Budget and some electrical/thermal claims remain unknown. See the acceptance report for actual checks.

For Fetch, follow the current [event hackpack](https://www.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack),
including its agent README tags. Do not publish secret seeds, tokens or customer
data in any artifact or shared chat.

## Technical explanation

**Workflow:** In ASI:One, describe an idea, answer necessary questions, review the
plan and send its exact confirmation code. Ohmni executes native generation and
checks, reports results and unknowns, and returns a downloadable ZIP. A supported
revision repeats review and confirmation in the same chat; the website is optional.

**Fetch contribution:** One Agentverse-registered Python uAgents agent implements
ACP and connects ASI messages to planning, persisted revisions, job monitoring and
artifact downloads. Native KiCad work is executed by Ohmni. Multi-agent behavior,
Payment Protocol and Interactive Cards are not claimed.

**Engineering boundary:** The three live acceptance builds passed routing and
native DRC with zero violations and zero unrouted connections. ERC warnings and
UNKNOWN requirements remain in the report. No physical performance is established.

**Architecture:** ASI supplies the user conversation and routes ACP messages to
Ohmni. Anthropic proposes supported plans and explanations. The host validates
plans and requires exact confirmation before saving/building. Deterministic
engineering tools produce the verification results and fingerprinted artifacts.

**Challenges and lessons:** A short “Yes” to a clarification was mistaken for an
unconfirmed build request. We restored the persisted question and proposed
alternative across restarts and routed short answers to the planner, while
retaining the separate exact-confirmation gate. Live ASI recovery and downloads
were verified; see [acceptance evidence](ASI_TRACK_ACCEPTANCE.md).

## Three-to-five-minute video

The official hackpack requests a 3–5 minute video. The outline below targets three
minutes; record enough to show the ASI result and actual download. Our website and
Stack-chan are optional additions, not dependencies of the primary ASI workflow.

| Time | Content |
|---|---|
| 0:00–0:25 | User and problem; disclose the existing platform |
| 0:25–0:55 | Request and confirmation inside ASI:One |
| 0:55–1:50 | Actual tool execution and result tied to the demonstrated job |
| 1:50–2:30 | Explain a real finding, warning or supported limitation |
| 2:30–3:00 | New weekend contribution, outcome and limits |

Label cuts, saved runs and fallback
footage accurately. Do not imply hardware operation, firmware generation or
whole-board simulation unless separately demonstrated.

## Final completion checklist

- [ ] Organizer questions about reuse, track selection and cutoff resolved.
- [ ] Starting commit and weekend features disclosed accurately.
- [ ] Public repo setup verified from another teammate's checkout.
- [x] Actual selected primary workflow completed inside ASI:One. (Verified 2026-10-17.)
- [x] Agent running and discoverable; profile/address recorded. (Verified 2026-10-17.)
- [x] Agentverse agent README has Innovation Lab and hackathon tags; repository README mirrors them. (Verified 2026-10-17.)
- [ ] Agent profile, shared ASI chat, project, video and setup links included even if the submission form labels some fields optional.
- [ ] All URLs opened signed out or in a separate browser profile.
- [ ] Video duration and access checked.
- [ ] Devpost submission completed.
- [ ] Lead completed Fetch's submission-agent form and recorded Team ID privately.
- [ ] Each teammate joined with that Team ID.
- [ ] Fetch submission status reads **Submitted**, not Incomplete.
- [ ] Judging attendance and presenter agreed; saved fallback ready.

Use the [official submission instructions](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0/edit).
The lead needs the team size and required project URLs; teammates enter their
personal details in the form themselves. Keep Team ID, emails and operational
notes out of public commits.

## Submission Agent procedure

The [official instructions](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0/edit)
require the lead to choose Create team, enter project/team details and links,
review, then confirm. The team size is 1–4 including the lead; table number is
optional. Each other member joins using the returned Team ID and enters their
own name/email. Verify the final status is Submitted. Devpost is a separate submission.

Use ASI's **Share chat** action to create a `/shared-chat/...` link; a private
`/chat/...` URL is not that artifact. The form describes agent/chat URL fields as
optional bonus fields, but the supplied track sheet explicitly requests them:
include both. Do not publish a conversation while it contains valid private
download or edit-access links. Wait for every such link to expire, or use an
organizer-approved sanitized demonstration. Expiry does not make sensitive user
inputs safe to publish; use synthetic prompts only. Test shared access signed out.

Refer to [current ASI acceptance](ASI_TRACK_ACCEPTANCE.md) for what was actually
tested. A finished README is not evidence that the video, shared chat or either
submission has been completed. Do not check those boxes without the actual artifacts.
