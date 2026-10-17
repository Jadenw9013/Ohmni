"""Run the ACP board-generation adapter and private Ohmni learning workspace."""
from __future__ import annotations

import asyncio
import os
import re
import time
from collections import OrderedDict
from datetime import UTC, datetime
from importlib.metadata import version
from uuid import uuid4

from .service import supported_options_reply


def strip_recipient(text: str, address: str) -> str:
    """ASI includes its addressed handle in TextContent; remove only our prefix."""
    return re.sub(r"^\s*@(?:ohmni-pcb-guide|" + re.escape(address) + r")\s+", "", text, count=1).strip()


class MessageWindow:
    """Bound duplicate acknowledgements and sender traffic without storing message text."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.seen = OrderedDict()
        self.senders = {}

    def accept(self, sender, message_id):
        now = self.clock()
        while self.seen and next(iter(self.seen.values())) < now - 1800:
            self.seen.popitem(last=False)
        key = (sender, str(message_id))
        if key in self.seen:
            return False
        if len(self.seen) >= 1024:
            self.seen.popitem(last=False)
        self.seen[key] = now
        self.senders = {key: value for key, value in self.senders.items() if value[0] > now - 60}
        if sender not in self.senders and len(self.senders) >= 128:
            return False
        start, count = self.senders.get(sender, (now, 0))
        self.senders[sender] = (start, count + 1)
        return count < 10


def build_agent(seed: str, endpoint: str, port: int = 8080, *, bridge=None):
    if not seed or len(seed) < 32:
        raise ValueError("Set a private FETCH_AGENT_SEED with at least 32 characters.")
    if not endpoint.startswith("https://") or not endpoint.endswith("/submit"):
        raise ValueError("FETCH_AGENT_ENDPOINT must be the HTTPS /submit endpoint.")
    if version("uagents") != "0.26.1" or version("uagents-core") != "0.4.12":
        raise RuntimeError("Install the repository's pinned fetch extra before running this agent.")
    from uagents import Agent, Model, Protocol
    from uagents.registration import AlmanacApiRegistrationPolicy
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        TextContent,
        chat_protocol_spec,
    )

    agent = Agent(name="Ohmni PCB Guide", seed=seed, port=port, endpoint=endpoint,
                  registration_policy=AlmanacApiRegistrationPolicy(),
                  description="Build supported USB-powered ESP32 boards, explore them in 3D, and learn about their components with Ohmni.",
                  store_message_history=False, report_events=False,
                  metadata={"scope": "confirmed_board_generation" if bridge else "read_only_connectivity", "software_version": "0.4.0"})
    protocol = Protocol(spec=chat_protocol_spec)
    window = MessageWindow()
    monitors = set()

    async def monitor(ctx, sender, owner, job_id):
        try:
            for tick in range(600):
                await asyncio.sleep(3)
                if bridge.latest_job(owner) != job_id:
                    return
                job = await asyncio.to_thread(bridge.jobs.get, job_id)
                terminal = job is None or job['status'] in {'complete', 'failed'}
                if terminal or (tick and tick % 10 == 0):
                    reply = await asyncio.to_thread(bridge.result, owner)
                    await ctx.send(sender, ChatMessage(timestamp=datetime.now(UTC), msg_id=uuid4(),
                        content=[TextContent(type="text", text=reply)]))
                if terminal:
                    return
        finally:
            monitors.discard(job_id)

    class Health(Model):
        status: str
        address: str
        mode: str

    @agent.on_rest_get("/health", Health)
    async def health(_ctx):
        return Health(status="ready", address=agent.address, mode="confirmed_board_generation" if bridge else "read_only_connectivity")

    @protocol.on_message(ChatMessage)
    async def receive(ctx, sender, msg):
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(UTC),
                                                   acknowledged_msg_id=msg.msg_id))
        if not window.accept(sender + str(ctx.session), msg.msg_id):
            return
        text = "\n".join(item.text for item in msg.content if isinstance(item, TextContent))
        if not text.strip():
            return
        text = strip_recipient(text, agent.address)
        try:
            reply = (await asyncio.to_thread(bridge.handle, sender, str(ctx.session), str(msg.msg_id), text)
                     if bridge else supported_options_reply(text))
        except Exception:  # noqa: BLE001 - never expose private persistence/provider failures
            reply = "The service could not complete this request. No unreviewed design will be built. Please try STATUS or retry shortly."
            ctx.logger.warning("Chat operation unavailable.")
        await ctx.send(sender, ChatMessage(timestamp=datetime.now(UTC), msg_id=uuid4(),
                                         content=[TextContent(type="text", text=reply)]))
        if bridge:
            from .bridge import owner_key
            owner = owner_key(sender, str(ctx.session))
            ctx.logger.info("Owned chat reply prepared; conversation=%s", owner[:12])
            job_id = bridge.latest_job(owner)
            if job_id and job_id not in monitors and bridge.jobs.get(job_id)['status'] in {'queued', 'running'}:
                monitors.add(job_id)
                asyncio.create_task(monitor(ctx, sender, owner, job_id))
        else:
            ctx.logger.info("Supported-options reply sent; no model or build was invoked.")

    @protocol.on_message(ChatAcknowledgement)
    async def acknowledged(_ctx, _sender, _msg):
        pass

    agent.include(protocol, publish_manifest=True)
    return agent


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    from pathlib import Path
    from urllib.parse import urlsplit

    from ohmni.adapters import AnthropicProvider

    from .bridge import ChatBridge
    from .http import start_gateway

    endpoint = os.environ.get("FETCH_AGENT_ENDPOINT", "")
    public = urlsplit(endpoint)
    bridge = ChatBridge(Path(os.environ.get("OHMNI_FETCH_OUTPUT_DIR", "/data/fetch-jobs")),
                        AnthropicProvider(max_attempts=2, timeout_seconds=20), f"{public.scheme}://{public.netloc}")
    agent = build_agent(os.environ.get("FETCH_AGENT_SEED", ""), endpoint, 8081, bridge=bridge)
    gateway = []

    @agent.on_event("startup")
    async def startup(_ctx):
        gateway.extend(await start_gateway(bridge, int(os.environ.get("PORT", "8080")), 8081))

    @agent.on_event("shutdown")
    async def shutdown(_ctx):
        if gateway:
            await gateway[0].cleanup()
            await gateway[1].close()
        bridge.close()

    agent.run()


if __name__ == "__main__":
    main()
