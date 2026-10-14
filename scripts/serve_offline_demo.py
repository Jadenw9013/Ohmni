#!/usr/bin/env python3
"""Serve the saved hackathon demonstration locally with no API key and no internet.

    python scripts/serve_offline_demo.py            # http://127.0.0.1:8765/

Read-only static server bound to 127.0.0.1. It serves the existing viewer
modules from apps/web and the saved capture from examples/hackathon-demo under
/hackathon-demo/. There is no API, no model, no job and no upload route, and
it never contacts Fly, Vercel or a CDN. Everything shown is a recorded receipt.
"""

from __future__ import annotations

import argparse
import mimetypes
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
CAPTURE = ROOT / "examples" / "hackathon-demo"
TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
    ".ico": "image/x-icon", ".zip": "application/zip", ".kicad_pcb": "text/plain; charset=utf-8",
    ".kicad_sch": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
}


def resolve(url_path: str, web: Path = WEB, capture: Path = CAPTURE) -> Path | None:
    """Map a request path to a contained, allowlisted file, or None."""
    path = unquote(urlsplit(url_path).path)
    if path in {"", "/"}:
        path = "/hackathon-demo.html"
    if "\\" in path or "\x00" in path:
        return None
    base, relative = (capture, path[len("/hackathon-demo/"):]) if path.startswith("/hackathon-demo/") \
        else (web, path.lstrip("/"))
    parts = Path(relative).parts
    if not parts or any(part in {"..", "."} or part.startswith(".") for part in parts):
        return None
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
        return None
    if base == web and "tests" in parts:
        return None
    suffix = ".kicad_pcb" if candidate.name.endswith(".kicad_pcb") else candidate.suffix.lower()
    return candidate if suffix in TYPES else None


class OfflineDemoHandler(BaseHTTPRequestHandler):
    server_version = "OhmniOfflineDemo"
    sys_version = ""

    def __init__(self, *args, web: Path = WEB, capture: Path = CAPTURE, **kwargs):
        self.web, self.capture = web, capture
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        return

    def _send(self, head_only: bool) -> None:
        target = resolve(self.path, self.web, self.capture)
        if target is None:
            body = b"Not found\n"
            self.send_response(HTTPStatus.NOT_FOUND)
            content_type = "text/plain; charset=utf-8"
        else:
            body = target.read_bytes()
            if target == (self.web / "hackathon-demo.html").resolve():
                # This standalone server has no project/API routes. Keep the
                # same page, but do not advertise navigation into that workflow.
                body = body.replace(b'data-host="site"', b'data-host="offline"')
            self.send_response(HTTPStatus.OK)
            suffix = ".kicad_pcb" if target.name.endswith(".kicad_pcb") else target.suffix.lower()
            content_type = TYPES.get(suffix) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                         "connect-src 'self'; object-src 'none'; base-uri 'none'")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def do_GET(self):
        self._send(False)

    def do_HEAD(self):
        self._send(True)


def make_server(port: int = 8765, *, web: Path = WEB, capture: Path = CAPTURE) -> ThreadingHTTPServer:
    if not (capture / "demo.json").is_file():
        raise SystemExit("The saved capture is missing: examples/hackathon-demo/demo.json")
    return ThreadingHTTPServer(("127.0.0.1", port), partial(OfflineDemoHandler, web=web, capture=capture))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = make_server(args.port)
    print(f"Ohmni saved demonstration (offline): http://127.0.0.1:{server.server_address[1]}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
