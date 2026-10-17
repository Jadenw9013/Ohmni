# Fetch agent connectivity milestone

This first release answers supported-board questions using Ohmni's real option
catalogue. It does not plan, save projects, spend model credits, generate boards,
or provide fabrication files. Those operations remain in the existing Ohmni UI
until the conversational integration has ownership and explicit confirmation.

## Run and deploy

Install the pinned optional dependencies with `python -m pip install -e '.[fetch]'`.
Set a private `FETCH_AGENT_SEED` (at least 32 characters), and
`FETCH_AGENT_ENDPOINT=https://YOUR-HOST/submit`. Run:

```sh
python -m ohmni.integrations.fetch_ai.agent
```

Keep the seed stable: it determines the agent address. Never put it in source,
chat, a screenshot, or a public profile. The local `.env.fetch.local` is ignored;
load it explicitly in your shell. Store production values using Fly secrets.
`Dockerfile.agent` and `fly.agent.toml` deploy a separate small service without
KiCad or a model key. Registration uses the off-chain Almanac API and requires
no wallet funding. `/health` reports the public address and read-only mode.

## Agentverse onboarding

Follow the [official uAgents onboarding guide](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents).
Choose External Integration → uAgents, then enter the agent name and HTTPS
`/submit` endpoint. Add at least three relevant discovery keywords.

The browser onboarding also checks `http://127.0.0.1:8080/agent_info` to prove
ownership. Temporarily run a local copy with the **same private seed** as the
public service during onboarding. Otherwise Agentverse may report that the local
agent does not match the public agent (reason 9), even when production is healthy.
Stop the local copy after registration; the deployed service handles messages.
Do not expose the SDK's local `/connect` inspector route publicly or copy a
browser session token into scripts to work around onboarding.

## Acceptance and limits

A healthy endpoint or successful Almanac registration alone does not establish
Agentverse account ownership or prove ASI:One integration. Verify the Agentverse
success page, then send a supported-options question through ASI:One and inspect
the real reply. Record the result before claiming the integration works.

Messages are acknowledged; duplicate replies are bounded by sender/message ID,
and sender traffic and cache size are bounded in memory. No chat history is
persisted. Restart resets those limits. This is a connectivity milestone, not a
production abuse-control system. UI claims must match the read-only behavior.

Run `python -m pytest -q tests/test_fetch_agent.py` and
`python -m ruff check src/ohmni/integrations tests/test_fetch_agent.py` locally.
The unit tests do not replace the real ASI:One round-trip acceptance test.

## Verified October 17 connectivity

The deployed agent is [Ohmni PCB Guide](https://asi1.ai/ai/agent1qvzucpk72r48d4gys9npx2an8jjj5mqpzwfjz4yt6a7mnqyag5gzqm5dc32),
handle `@ohmni-pcb-guide`. A real ASI:One request asking for supported boards and
smell identification returned all three application families and correctly
refused smell identification. Fly logs confirmed the real reply. It still cannot
plan or build a board through ASI:One.

Browser onboarding stalled even with matching local/public identities. The
fallback registered ownership using the pinned SDK's `register_in_agentverse`
with a locally held, explicitly approved one-hour account key. The private seed
was used locally to sign the identity challenge; it was not sent to Agentverse.
The key was deleted through Agentverse's UI after registration and its local
file removed. A subsequent authenticated request still returned HTTP 200, so
**immediate revocation was not verified**. Treat the credential as valid until
its one-hour expiry; do not assume deleting the UI entry invalidates an issued
token instantly. No credential belongs in deployment configuration or commits.
