"""Loopback link to the Ohmni workspace page (apps/web/robot-link.js).

The page connects to ws://127.0.0.1:8770 after the user opts in. It sends a read-only
board context and `selected` events, and answers view-only commands. Only pages from
the configured Ohmni origins may connect, so other websites cannot reach the robot.

Thread-safe, synchronous API for the voice loop:

    link = PageLink().start()
    context = link.wait_for_context()
    link.command("focus", ref="U2")
    answer = link.command("ask", ref="U2", question="Why this regulator?", timeout=100)
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from collections import deque
from urllib.parse import urlsplit

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

PORT = 8770
REPLACED = 4001  # close code: another tab took over; robot-link.js does not reconnect on it


def normalize_origin(value: str) -> str:
    """'https://Ohmni.example/app/' -> 'https://ohmni.example', as browsers send Origin."""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError(f"not an http(s) origin: {value!r}")
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname.lower()}{port}"


DEFAULT_ORIGINS = (
    normalize_origin(os.environ.get("OHMNI_MAIN_UI_URL", "https://ohmni-yvnd.vercel.app")),
    "http://127.0.0.1:8765",  # local demo server
    "http://localhost:8765",
)


class PageError(RuntimeError):
    """The page refused a command, or no page is connected."""


class PageLink:
    def __init__(self, origins=DEFAULT_ORIGINS, host="127.0.0.1", port=PORT, log=lambda _m: None):
        self.origins = tuple(normalize_origin(origin) for origin in origins)
        self.host, self.port = host, port
        self.log = log
        self.context: dict | None = None
        self.events: deque[dict] = deque()  # e.g. {"type": "selected", "ref": "U2", "by": "user"}
        self._loop = asyncio.new_event_loop()
        self._page: ServerConnection | None = None
        # Pending commands per connection, so a replaced or closed page fails only its own.
        self._pending: dict[ServerConnection, dict[int, asyncio.Future]] = {}
        self._next_id = 1
        self._context_ready = threading.Event()
        self._server = None

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> PageLink:
        ready = threading.Event()

        async def boot():
            # Browsers always send Origin; only the listed Ohmni pages may connect.
            return await serve(self._handle, self.host, self.port, origins=list(self.origins),
                               max_size=4 * 1024 * 1024)

        def run():
            asyncio.set_event_loop(self._loop)
            try:
                self._server = self._loop.run_until_complete(boot())
            except OSError as exc:
                self.log(f"[page] cannot listen on {self.host}:{self.port}: {exc}")
                ready.set()
                return
            ready.set()
            self._loop.run_forever()

        threading.Thread(target=run, name="ohmni-page-link", daemon=True).start()
        if not ready.wait(5) or self._server is None:
            raise PageError(f"could not listen on {self.host}:{self.port} (is another companion running?)")
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    def close(self) -> None:
        async def stop():
            self._server.close()
            await self._server.wait_closed()
        if self._server is not None:
            asyncio.run_coroutine_threadsafe(stop(), self._loop).result(5)
        self._loop.call_soon_threadsafe(self._loop.stop)

    @property
    def connected(self) -> bool:
        return self._page is not None

    def wait_for_context(self, timeout: float | None = None) -> dict | None:
        self._context_ready.wait(timeout)
        return self.context

    # -- page connection (event-loop thread) ------------------------------------
    def _fail_pending(self, page: ServerConnection, reason: str) -> None:
        for future in self._pending.pop(page, {}).values():
            if not future.done():
                future.set_exception(PageError(reason))

    async def _handle(self, page: ServerConnection) -> None:
        # The tab that connected last wins; the previous one is told it was replaced and stops retrying.
        previous, self._page = self._page, page
        self._pending[page] = {}
        if previous is not None:
            self._fail_pending(previous, "the Ohmni page was replaced by another tab")
            await previous.close(REPLACED, "replaced by another tab")
        self.log(f"[page] connected from {page.request.headers.get('Origin')}")
        try:
            async for raw in page:
                try:
                    message = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                if not isinstance(message, dict):
                    continue
                kind = message.get("type")
                if kind == "context":
                    self.context = message
                    self._context_ready.set()
                elif kind == "result" and isinstance(message.get("id"), int):
                    future = self._pending.get(page, {}).pop(message["id"], None)
                    if future is not None and not future.done():
                        future.set_result(message)
                elif kind == "selected":
                    self.events.append(message)
        except ConnectionClosed:
            pass
        finally:
            self._fail_pending(page, "the Ohmni page disconnected")
            if self._page is page:
                self._page = None
                self.log("[page] disconnected")

    async def _command(self, name: str, args: dict, timeout: float) -> dict:
        page = self._page
        if page is None or page not in self._pending:
            raise PageError("no Ohmni page is connected")
        command_id, self._next_id = self._next_id, self._next_id + 1
        future = self._loop.create_future()
        self._pending[page][command_id] = future
        try:
            await page.send(json.dumps({"type": "command", "id": command_id, "name": name, "args": args}))
            return await asyncio.wait_for(future, timeout)
        except ConnectionClosed as exc:
            raise PageError("the Ohmni page disconnected") from exc
        except TimeoutError as exc:
            raise PageError(f"{name}: the page did not answer in time") from exc
        finally:
            self._pending.get(page, {}).pop(command_id, None)

    # -- synchronous API (any thread) ---------------------------------------------
    def command(self, name: str, timeout: float = 10.0, **args) -> dict | None:
        """Run a view-only command on the page; returns its data or raises PageError."""
        future = asyncio.run_coroutine_threadsafe(self._command(name, args, timeout), self._loop)
        try:
            reply = future.result(timeout + 2)  # the coroutine enforces `timeout` itself
        except TimeoutError as exc:
            future.cancel()
            raise PageError(f"{name}: the page did not answer in time") from exc
        if not reply.get("ok"):
            raise PageError(f"{name}: {reply.get('error')}")
        return reply.get("data")
