# ASI-only track acceptance and submission readiness

Date: 2026-10-17. This is evidence and a readiness checklist, not a submitted entry
or a guarantee of prize eligibility. No custom Ohmni frontend was used to complete
all three production runs below.

## Primary workflow tested

Started a fresh ASI conversation with the selected `@ohmni-pcb-guide` agent:
“I want a USB-powered board to measure the temperature and humidity in my room.”
ASI returned a BME280/ESP32 proposal without unnecessary clarification. The exact
confirmation code started a new build. Routing progress, real checks and a direct
download link arrived in the same conversation. The ZIP was downloaded through
that ASI link and inspected locally; the optional 3D website was not opened.

| Evidence | Result |
| --- | --- |
| Job | `9512d48b0dd0` |
| Project / revision | `16ca7bbfe5d24ffa` / `6f783a9d0af54818` |
| Package contents | 20 files including KiCad schematic/boards, fabrication, BOM, brief, receipt and report |
| Fabrication integrity | All nine manifest file hashes and byte sizes matched |
| Receipt lineage | Job, circuit and manufacturing-package identities checked |
| Native DRC | Zero violations and zero unrouted connections |
| Requirements | 16 MET, 0 VIOLATED, 13 UNKNOWN; unknowns retained |
| SHA-256 of downloaded ZIP | `d857745d022774d0d8bd3fba01edd26b257b348fc9926e1ad6031e920ede91ba` |

This establishes design-file generation, not firmware, assembly or measured
hardware performance. A browser link delivers the artifact outside the chat
renderer; no additional custom UI action is necessary. Organizer interpretation
of artifact downloads remains theirs.

## Issues found and fixes

- A requested 50 × 50 mm revision unnecessarily reconfirmed the requested size and
  existing assembly preference. Iteration instructions now distinguish permission
  to propose an edit from the separate host-owned save/build confirmation.
- Replying “Yes” to that clarification hit the build-confirmation guard instead
  of answering the question. Short answers now reach the planner/assistant only
  when there is an outstanding question. They never save a revision or start a job.
- Initial Fetch follow-ups previously reconstructed only user messages. Persisted
  questions and the offered proposal now accompany the next reply, including after
  restart. Old confirmation IDs remain invalid after a replacement proposal.
- Ordinary progress/results automatically issued edit-capable website links.
  Those links now require `OPEN`/`VIEW`/`WORKSPACE`; the primary outcome stays in ASI.
- Clarification during revision editing now says the existing project is unchanged,
  rather than incorrectly claiming that no project has ever been saved.

## Post-deployment revalidation

The tested implementation `676662cf160ceda46c20be06b95d6c7abfd1ecd6` was deployed
to `ohmni-agent` on 2026-10-17. Fly reported a healthy machine. Image digest:
`sha256:bc5b3d9b88e9bd29c64b5054dc0bdee03c8fcb05ea13da0ff05c7a8455f24950`.

| Live ASI case | Observed result |
| --- | --- |
| Resize existing sensor board to 50 × 50 mm | Proposed only the two dimension changes, with no unnecessary question; exact confirmation built job `5803310fb83c`, revision 2 `6b52b554d34a472e` of project `16ca7bbfe5d24ffa` |
| Repeat that exact confirmation | Returned the same completed job `5803310fb83c`; no replacement build |
| Unsupported voice diary request | Explained missing audio capability and offered a button/light controller, with a question before generation |
| Restart service, then reply “Yes” | Recovered the persisted question and offered alternative; produced a new reviewable controller plan without starting a build |
| Explicitly confirm the alternative | Built job `ae5aa211194a`, revision 1 `c1e98e722c7d4a15` of project `89833e1eeb234fa3`; one button and one LED, no claim of audio recording |
| Download both new packages from ASI | Each ZIP contained 20 entries; all nine fabrication hashes and sizes matched its manifest; receipt fingerprints matched |

Both post-deployment builds had zero native DRC violations and zero unrouted
connections. Sensor revision: 16 MET / 0 VIOLATED / 13 UNKNOWN. Controller:
14 MET / 0 VIOLATED / 14 UNKNOWN. ERC warnings, assembly limitations and unverified
bench performance remain visible. These results cover supported designs and an
explicitly accepted fallback; they do not establish arbitrary PCB generation.

Downloaded ZIP SHA-256 values:

- Sensor revision: `130b69eb21af95dcb927356216383987d5a5f1f82c1a1b1cfb2309fa154e1262`
- Controller: `77135f0515a8c102217a560e7ce455c4c989e9a3bcc0770eff62a98a8eaab8a0`

The initial downloaded ZIP was rechecked and retained its original hash and
100 × 70 mm brief. No raw session export or bearer URL is committed.

## Automated verification

- `python scripts/verify.py fast`: **2,782 passed**, 101 skipped, 70 deselected.
- Focused bridge/workspace/conversation/assistant/agent tests: **70 passed**.
- Workflow gate: **12 passed**; changed Python lint and diff whitespace checks passed.
- One initial full run exposed a workflow allowlist mismatch (fixed) and an
  intermittent gateway test failure that did not recur in focused or final full
  tests. Its root cause was not established; gateway diagnostics now log the
  exception class without exposing sensitive exception text and avoid falsely
  asserting that an operation made no changes.

See [commit-bound verification](../../.ai/verification/ASI-T01.yaml). Independent
review remains pending; the task is VERIFIED, not formally COMPLETE.

## Requirement mapping

Sources: the owner's two-page Fetch AI Track sheet,
[official hackpack](https://www.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack),
and [Submission Agent instructions](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0/edit),
reviewed on the date above.

| Requirement | Evidence / remaining action |
| --- | --- |
| Agentverse registration and ASI availability | Agentverse profile displayed Active and ASI Available; fresh ASI request reached the agent |
| ACP | Published AgentChatProtocol v0.3.0 visible in profile; `agent.py` publishes the SDK protocol manifest |
| Meaningful tool execution | Fresh native design/check pipeline and inspected ZIP above |
| Primary workflow through ASI | Plan, explicit confirmation, progress, results and download provided in ASI |
| Public repository and setup | Root README, `FETCH_AGENT_SETUP.md`, native setup and no-key regression commands |
| Agent identity and sponsor categorization | Root README and Agentverse README include identity and Innovation Lab/hackathon badges |
| Demo video | Required 3–5 minute viewable video: owner/team still needs to produce and verify it |
| Shared ASI evidence | Create and verify a `/shared-chat/` link after private capabilities expire; private chat URLs are insufficient |
| Submission | Complete Devpost and designated Submission Agent; all members must join until status is Submitted |
| Existing platform disclosure | Record actual hacking-start commit and new event work; resolve reuse eligibility with organizers |

The track sheet requests agent profiles/chats despite the submission form marking
those fields optional: include them. Multi-agent orchestration, Payment Protocol
and Interactive Cards are optional enhancements, not implemented claims. Stack-chan
is a separate planned companion and is unnecessary for the primary track workflow.

## Judge-ready rehearsal

Use the README's ASI prompt, review/confirm, show real progress, inspect one warning
or unknown, then download and open the ZIP. Demonstrate a supported revision with
a fresh confirmation and explain that the original result remains unchanged.
Keep the agent deployed during judging; recheck availability just before presenting.
Prepare an accurately labeled recording in case venue connectivity fails.

Publishing this document does not submit a project, create a public shared chat,
produce a video, verify licenses/reuse eligibility, or enter teammates' personal
details. See [submission template and exact remaining checklist](SUBMISSION_TEMPLATE.md).
Never commit session tokens, temporary private links or raw private chat exports.
