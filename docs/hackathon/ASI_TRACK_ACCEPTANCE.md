# ASI-only track acceptance and submission readiness

Date: 2026-10-17. This is evidence and a readiness checklist, not a submitted entry
or a guarantee of prize eligibility. No custom Ohmni frontend was used to complete
the initial fresh production build below.

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

Production revalidation of these changes will be recorded before this handoff is
marked verified. Automated tests alone do not establish live ASI acceptance.

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
