"""Run the opt-in, read-only ACP connectivity milestone. No model or EDA calls."""
from __future__ import annotations

import asyncio
import os
import time
from collections import OrderedDict
from datetime import UTC, datetime
from importlib.metadata import version
from uuid import uuid4

from .service import supported_options_reply


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


def build_agent(seed: str, endpoint: str, port: int = 8080):
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
                  description="Discover supported USB-powered ESP32 board options with Ohmni.",
                  store_message_history=False, report_events=False,
                  metadata={"scope": "read_only_connectivity", "software_version": "0.1.0"})
    protocol = Protocol(spec=chat_protocol_spec)
    window = MessageWindow()

    class Health(Model):
        status: str
        address: str
        mode: str

    @agent.on_rest_get("/health", Health)
    async def health(_ctx):
        return Health(status="ready", address=agent.address, mode="read_only_connectivity")

    @protocol.on_message(ChatMessage)
    async def receive(ctx, sender, msg):
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(UTC),
                                                   acknowledged_msg_id=msg.msg_id))
        if not window.accept(sender, msg.msg_id):
            return
        text = "\n".join(item.text for item in msg.content if isinstance(item, TextContent))
        if not text.strip():
            return
        reply = supported_options_reply(text)
        await ctx.send(sender, ChatMessage(timestamp=datetime.now(UTC), msg_id=uuid4(),
                                         content=[TextContent(type="text", text=reply)]))
        ctx.logger.info("Supported-options reply sent; no model or build was invoked.")

    @protocol.on_message(ChatAcknowledgement)
    async def acknowledged(_ctx, _sender, _msg):
        pass

    agent.include(protocol, publish_manifest=True)
    return agent


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    agent = build_agent(os.environ.get("FETCH_AGENT_SEED", ""),
                        os.environ.get("FETCH_AGENT_ENDPOINT", ""),
                        int(os.environ.get("PORT", "8080")))
    agent.run()


if __name__ == "__main__":
    main()
