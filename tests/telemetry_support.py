"""Shared offline harness for the telemetry suites.

Every helper here keeps telemetry traffic in memory. ``offline_telemetry``
clears inherited SENTRY*/OHMNI_TELEMETRY* variables without reading or printing
them, installs a network guard that fails the test on any non-loopback
connection, and enables the real pinned SDK only with an explicit recording
transport and a synthetic ``.invalid`` DSN.
"""

from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager

import sentry_sdk  # imported unconditionally: a missing SDK must fail, not skip

from ohmni.adapters import telemetry

SYNTHETIC_DSN = "https://" + "0123456789abcdef" * 2 + "@o0.ingest.invalid/42"
assert sentry_sdk.VERSION == telemetry.PINNED_SDK_VERSION


def isolate_environment(monkeypatch) -> None:
    for name in list(os.environ):
        if name.startswith(("SENTRY", "OHMNI_TELEMETRY")) or name in {"OHMNI_ENV", "OHMNI_TRACE_SAMPLE_RATE"}:
            monkeypatch.delenv(name, raising=False)


class NetworkGuard:
    """Records and refuses every non-loopback connection attempt."""

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def install(self, monkeypatch) -> None:
        real_connect = socket.socket.connect
        real_connect_ex = socket.socket.connect_ex
        guard = self

        def allowed(address) -> bool:
            host = address[0] if isinstance(address, tuple) and address else address
            return isinstance(host, str) and host in {"127.0.0.1", "::1", "localhost"}

        def connect(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and not allowed(address):
                guard.attempts.append("blocked")
                raise ConnectionRefusedError("telemetry tests deny outbound network")
            return real_connect(sock, address)

        def connect_ex(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and not allowed(address):
                guard.attempts.append("blocked")
                return 111
            return real_connect_ex(sock, address)

        def getaddrinfo(host, *args, **kwargs):
            if host not in {"127.0.0.1", "::1", "localhost", None}:
                guard.attempts.append("resolve")
                raise socket.gaierror("telemetry tests deny name resolution")
            return real_getaddrinfo(host, *args, **kwargs)

        real_getaddrinfo = socket.getaddrinfo
        monkeypatch.setattr(socket.socket, "connect", connect)
        monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
        monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


def config(**overrides) -> telemetry.TelemetryConfig:
    values = {
        "OHMNI_TELEMETRY_ENABLED": "1", "SENTRY_DSN": SYNTHETIC_DSN, "OHMNI_ENV": "local",
        "SENTRY_RELEASE": "ohmni@0000000", "OHMNI_TRACE_SAMPLE_RATE": "1",
        "OHMNI_TELEMETRY_METRICS": "1", "OHMNI_TELEMETRY_LOGS": "0",
    }
    values.update(overrides)
    return telemetry.configure_from_environment({k: v for k, v in values.items() if v is not None})


@contextmanager
def offline_telemetry(monkeypatch, **overrides):
    """Enable the real SDK against a recording transport; always shut down."""
    isolate_environment(monkeypatch)
    guard = NetworkGuard()
    guard.install(monkeypatch)
    telemetry.shutdown(0)
    transport = telemetry.recording_transport()
    assert telemetry.initialize(config(**overrides), transport=transport)
    try:
        yield Recorder(transport)
    finally:
        telemetry.shutdown(1.0)
        assert guard.attempts == [], "an unexpected network path was attempted"
        assert transport.rejected_item_types == [], transport.rejected_item_types


class Recorder:
    def __init__(self, transport) -> None:
        self.transport = transport

    def flush(self) -> Recorder:
        telemetry.flush(2.0)
        return self

    def raw(self) -> bytes:
        self.flush()
        return b"\n".join(self.transport.envelopes)

    def items(self) -> list[tuple[str, dict]]:
        self.flush()
        result = []
        for envelope in self.transport.envelopes:
            lines = envelope.split(b"\n")
            index = 1
            while index + 1 < len(lines):
                header = json.loads(lines[index])
                result.append((header["type"], json.loads(lines[index + 1])))
                index += 2
        return result

    def events(self) -> list[dict]:
        return [payload for kind, payload in self.items() if kind == "event"]

    def transactions(self) -> list[dict]:
        return [payload for kind, payload in self.items() if kind == "transaction"]

    def metrics(self) -> list[dict]:
        return [metric for kind, payload in self.items() if kind == "trace_metric"
                for metric in payload["items"]]

    def failure_values(self) -> list[str]:
        return [event["exception"]["values"][0]["value"] for event in self.events()]

    def metric_count(self, name: str, **attributes) -> float:
        total = 0.0
        for metric in self.metrics():
            if metric["name"] != name:
                continue
            values = {key: entry["value"] for key, entry in metric["attributes"].items()}
            if all(values.get(key) == value for key, value in attributes.items()):
                total += metric["value"]
        return total
