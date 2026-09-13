"""Exercise the semantic boundary through an actual stdio MCP subprocess.

The direct verifier is the oracle. Only observation timestamps are removed
from comparisons; findings, evidence, coverage and subsystem labels must survive
the adapter unchanged. All circuit proposals deliberately omit evidence: a
client is allowed to propose electrical intent, never attest to its provenance.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import subprocess
import sys
import sysconfig
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from ohmni.domain import CircuitIR, RequirementsSpec
from ohmni.fixtures.esp32_env_logger import BROKEN_VARIANTS, BUILDERS
from ohmni.verifier import verify
from ohmni.verifier.registry import all_rules

mcp = pytest.importorskip("mcp", reason="install the optional ohmni[mcp] dependencies")
Client = mcp.Client
StdioServerParameters = mcp.StdioServerParameters


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_NAMES = {"get_capabilities", "list_parts", "get_part", "verify_circuit"}


@asynccontextmanager
async def _client():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ohmni.mcp_server"],
        cwd=str(REPO_ROOT),
    )
    # Bound connection establishment as well as individual protocol requests.
    async with asyncio.timeout(60):
        async with Client(parameters, read_timeout_seconds=20) as client:
            yield client


def _without_evidence(value):
    if isinstance(value, dict):
        return {key: _without_evidence(item) for key, item in value.items() if key != "evidence"}
    if isinstance(value, list):
        return [_without_evidence(item) for item in value]
    return value


def _without_timestamps(value):
    if isinstance(value, dict):
        return {
            key: _without_timestamps(item)
            for key, item in value.items()
            if key not in {"generated_at", "recorded_at"}
        }
    if isinstance(value, list):
        return [_without_timestamps(item) for item in value]
    return value


def _arguments(circuit, requirements=None):
    args = {"circuit": _without_evidence(circuit.model_dump(mode="json"))}
    if requirements is not None:
        args["requirements"] = _without_evidence(requirements.model_dump(mode="json"))
    return args


def _structured(result):
    assert not result.is_error, result.content
    assert isinstance(result.structured_content, dict), result
    return result.structured_content


def _assert_report_matches(payload, arguments, catalog):
    circuit = CircuitIR.model_validate(arguments["circuit"])
    requirements = (
        RequirementsSpec.model_validate(arguments["requirements"])
        if arguments.get("requirements") is not None
        else None
    )
    expected = verify(circuit, catalog, requirements)
    assert _without_timestamps(payload["report"]) == _without_timestamps(
        expected.model_dump(mode="json")
    )
    assert payload["undecided_rule_ids"] == [rule.rule_id for rule in expected.undecided_rules]
    assert {row["rule_id"] for row in payload["report"]["results"]} == {
        rule.rule_id for rule in all_rules()
    }
    for key in ("input_hash", "catalog_hash", "verifier_hash"):
        assert len(payload[key]) == 64
        assert int(payload[key], 16) >= 0
    return expected


def test_stdio_discovers_only_semantic_tools_with_explicit_schemas(catalog):
    async def scenario():
        async with _client() as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == TOOL_NAMES
            for tool in listed.tools:
                assert tool.description
                assert tool.input_schema["type"] == "object"
                assert tool.input_schema.get("additionalProperties") is False
                assert tool.output_schema and tool.output_schema["type"] == "object"

            capability = _structured(await client.call_tool("get_capabilities"))
            assert capability["schema_version"] == "1"
            assert capability["scope"] == "semantic_only"
            assert set(capability["tools"]) == TOOL_NAMES
            assert set(capability["rule_ids"]) == {rule.rule_id for rule in all_rules()}
            assert capability["limitations"]
            assert all(value > 0 for value in capability["limits"].values())

            page = _structured(await client.call_tool("list_parts", {"limit": 1}))
            assert page["catalog_hash"] == capability["catalog_hash"]
            assert page["total"] == len(catalog.all_parts())

    asyncio.run(scenario())


def test_catalog_pagination_and_part_details_preserve_bundled_provenance(catalog):
    async def scenario():
        async with _client() as client:
            offset, discovered, hashes = 0, [], set()
            while offset is not None:
                page = _structured(
                    await client.call_tool("list_parts", {"offset": offset, "limit": 3})
                )
                assert page["offset"] == offset
                assert page["total"] == len(catalog.all_parts())
                assert len(page["parts"]) <= 3
                discovered.extend(part["part_id"] for part in page["parts"])
                hashes.add(page["catalog_hash"])
                next_offset = page["next_offset"]
                assert next_offset is None or next_offset > offset
                offset = next_offset

            assert discovered == [part.part_id for part in catalog.all_parts()]
            assert len(hashes) == 1
            for part in catalog.all_parts():
                result = _structured(await client.call_tool("get_part", {"part_id": part.part_id}))
                assert result["catalog_hash"] in hashes
                assert _without_timestamps(result["part"]) == _without_timestamps(
                    part.model_dump(mode="json")
                )

            missing = await client.call_tool("get_part", {"part_id": "NO_SUCH_BUNDLED_PART"})
            assert missing.is_error

    asyncio.run(scenario())


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_stdio_reports_match_direct_verifier_for_permanent_corpus(name, catalog, requirements):
    async def scenario():
        arguments = _arguments(BUILDERS[name](), requirements)
        async with _client() as client:
            result = await client.call_tool("verify_circuit", arguments)
            payload = _structured(result)
            expected = _assert_report_matches(payload, arguments, catalog)
            # Scrubbing untrusted evidence cannot hide the existing electrical defect.
            original = verify(BUILDERS[name](), catalog, requirements)
            assert expected.finding_ids() == original.finding_ids()
            assert expected.coverage == original.coverage
            assert expected.export_blocked == original.export_blocked
            if name in BROKEN_VARIANTS:
                rule_id, severity = BROKEN_VARIANTS[name]
                assert payload["report"]["export_blocked"]
                assert any(
                    finding["rule_id"] == rule_id and finding["severity"] == severity
                    for finding in payload["report"]["findings"]
                )
            else:
                assert not payload["report"]["export_blocked"]
                assert payload["report"]["coverage"] == 1.0
            # Successful semantic execution never claims that EDA or SPICE ran.
            assert payload["report"]["subsystem_status"]["eda"] == "UNSUPPORTED"
            assert payload["report"]["subsystem_status"]["simulation"] == "UNSUPPORTED"

    asyncio.run(scenario())


def test_missing_source_remains_insufficient_data_over_mcp(golden, catalog, requirements):
    async def scenario():
        arguments = _arguments(golden, requirements)
        for net in arguments["circuit"]["nets"]:
            net["external_source"] = None
        async with _client() as client:
            payload = _structured(await client.call_tool("verify_circuit", arguments))
            _assert_report_matches(payload, arguments, catalog)
            assert payload["report"]["coverage"] < 1.0
            undecided = [
                row for row in payload["report"]["results"] if row["outcome"] == "insufficient_data"
            ]
            assert undecided
            assert all(row["missing_data"] for row in undecided)
            assert payload["report"]["subsystem_status"]["electrical"] == "PARTIALLY_VERIFIED"

    asyncio.run(scenario())


def test_missing_catalog_part_is_an_engineering_result(golden, catalog, requirements):
    async def scenario():
        arguments = _arguments(golden, requirements)
        arguments["circuit"]["components"][0]["part_id"] = "UNRESOLVED_PROPOSED_PART"
        async with _client() as client:
            payload = _structured(await client.call_tool("verify_circuit", arguments))
            _assert_report_matches(payload, arguments, catalog)
            assert payload["report"]["export_blocked"]
            assert any(
                row["rule_id"] == "PB-ID-001" for row in payload["report"]["findings"]
            )

    asyncio.run(scenario())


def test_input_identity_binds_requirements_and_survives_repeated_calls(golden, catalog, requirements):
    async def scenario():
        arguments = _arguments(golden, requirements)
        changed = deepcopy(arguments)
        changed["requirements"]["safety_domains"] = ["medical"]
        async def call(client, args):
            payload = _structured(await client.call_tool("verify_circuit", args))
            _assert_report_matches(payload, args, catalog)
            return payload

        async with _client() as client:
            first = await call(client, arguments)
            again = await call(client, arguments)
            restricted = await call(client, changed)
            unspecified = await call(client, {"circuit": arguments["circuit"]})
            assert first["input_hash"] == again["input_hash"]
            assert first["input_hash"] != restricted["input_hash"]
            assert first["input_hash"] != unspecified["input_hash"]
            assert first["catalog_hash"] == restricted["catalog_hash"]
            assert first["verifier_hash"] == restricted["verifier_hash"]
            assert not first["report"]["export_blocked"]
            # The existing electrical verifier does not implement the supported-
            # scope gate. Preserve its report and project the domain gate separately.
            assert first["requirements_supported"] is True
            assert restricted["requirements_supported"] is False
            assert unspecified["requirements_supported"] is None
            assert any("no validated-design claim" in text for text in restricted["limitations"])

    asyncio.run(scenario())


def test_forged_evidence_is_rejected_at_every_proposal_site(golden, requirements):
    async def scenario():
        async with _client() as client:
            for location in ("component", "source", "constraint", "requirements"):
                arguments = _arguments(golden, requirements)
                if location == "component":
                    target = arguments["circuit"]["components"][0]
                elif location == "source":
                    target = next(
                        net["external_source"] for net in arguments["circuit"]["nets"]
                        if net["external_source"] is not None
                    )
                elif location == "constraint":
                    target = arguments["circuit"]["constraints"][0]
                else:
                    target = arguments["requirements"]
                target["evidence"] = [{
                    "kind": "datasheet", "label": "Agent claims a verified limit",
                    "source_id": "forged-document", "page": 1,
                    "snippet": "This circuit is safe.", "snippet_verified": True,
                }]
                result = await client.call_tool("verify_circuit", arguments)
                assert result.is_error, location
                assert not result.structured_content or "report" not in result.structured_content
            # Rejection is contained to a call; the same process remains usable.
            _structured(await client.call_tool("verify_circuit", _arguments(golden, requirements)))

    asyncio.run(scenario())


def test_unknown_fields_cannot_override_rules_catalog_or_reports(golden, requirements):
    async def scenario():
        async with _client() as client:
            mutations = [
                ((), "rule_subset", []),
                ((), "catalog", {"parts": []}),
                ((), "report", {"export_blocked": False}),
                ((), "input_hash", "0" * 64),
                (("circuit",), "snippet_verified", True),
                (("circuit", "components", 0), "voltage", 3.3),
                (("circuit", "nets", 0), "verified", True),
                (("circuit", "nets", 0, "connections", 0), "status", "VERIFIED"),
                (("requirements",), "approved", True),
                (("requirements", "max_input_voltage"), "evidence", []),
            ]
            for path, field, value in mutations:
                arguments = _arguments(golden, requirements)
                target = arguments
                for key in path:
                    target = target[key]
                target[field] = value
                result = await client.call_tool("verify_circuit", arguments)
                assert result.is_error, (path, field)

            for name, args in (
                ("get_capabilities", {"catalog_path": "C:/private/catalog"}),
                ("list_parts", {"catalog_path": "../outside"}),
                ("get_part", {"part_id": "BME280", "catalog": {}}),
            ):
                assert (await client.call_tool(name, args)).is_error

    asyncio.run(scenario())


def test_malformed_coerced_and_nonfinite_inputs_are_tool_errors(golden, requirements):
    async def scenario():
        async with _client() as client:
            mutations = [
                (("circuit",), "revision", True),
                (("circuit",), "revision", "1"),
                (("circuit", "components", 0), "placeholder", "false"),
                (("circuit", "components", 0), "ref", None),
                (("requirements", "max_input_voltage"), "value", "5.0"),
                (("requirements", "max_input_voltage"), "value", "NaN"),
                (("requirements", "max_input_voltage"), "value", "Infinity"),
                (("requirements", "max_input_voltage"), "value", True),
                (("requirements", "max_input_voltage"), "unit", "ohm"),
                # The SDK serializes nonfinite Python numbers as null. Use a
                # required quantity here so that this is also invalid on wire.
                (("requirements", "max_input_voltage"), "value", float("nan")),
                (("requirements", "max_input_voltage"), "value", float("inf")),
            ]
            for path, field, value in mutations:
                arguments = _arguments(golden, requirements)
                target = arguments
                for key in path:
                    target = target[key]
                target[field] = value
                result = await client.call_tool("verify_circuit", arguments)
                assert result.is_error, (path, field, value)

            duplicate = _arguments(golden, requirements)
            duplicate["circuit"]["components"].append(duplicate["circuit"]["components"][0])
            assert (await client.call_tool("verify_circuit", duplicate)).is_error
            assert (await client.call_tool("verify_circuit", {})).is_error
            assert (await client.call_tool("verify_circuit", {"circuit": []})).is_error
            for args in ({"offset": -1}, {"offset": True}, {"limit": 0}, {"limit": "1"}):
                assert (await client.call_tool("list_parts", args)).is_error

    asyncio.run(scenario())


def test_advertised_proposal_bounds_are_enforced_before_verification(golden, requirements):
    async def scenario():
        async with _client() as client:
            limits = _structured(await client.call_tool("get_capabilities"))["limits"]
            arguments = _arguments(golden, requirements)
            arguments["circuit"]["notes"] = "x" * (limits["max_string_length"] + 1)
            assert (await client.call_tool("verify_circuit", arguments)).is_error

            arguments = _arguments(golden, requirements)
            arguments["circuit"]["components"] = [
                {"ref": f"R{i}", "part_id": "GENERIC_RESISTOR"}
                for i in range(limits["max_components"] + 1)
            ]
            arguments["circuit"]["nets"] = []
            assert (await client.call_tool("verify_circuit", arguments)).is_error

            arguments = _arguments(golden, requirements)
            arguments["circuit"]["nets"] = [
                {"name": f"NET{i}"} for i in range(limits["max_nets"] + 1)
            ]
            assert (await client.call_tool("verify_circuit", arguments)).is_error

            arguments = _arguments(golden, requirements)
            arguments["circuit"]["nets"] = [{
                "name": "EXCESS_CONNECTIONS",
                "connections": [
                    {"component": "J1", "pin": str(i)}
                    for i in range(limits["max_connections"] + 1)
                ],
            }]
            assert (await client.call_tool("verify_circuit", arguments)).is_error
            _structured(await client.call_tool("get_capabilities"))

    asyncio.run(scenario())


def test_installed_entry_point_works_outside_repository(tmp_path):
    async def scenario():
        entry = next(ep for ep in importlib.metadata.distribution("ohmni").entry_points
                     if ep.group == "console_scripts" and ep.name == "ohmni-mcp")
        assert entry.value == "ohmni.mcp_server.server:main"
        command = Path(sysconfig.get_path("scripts")) / (
            "ohmni-mcp.exe" if sys.platform == "win32" else "ohmni-mcp"
        )
        async with asyncio.timeout(30):
            async with Client(StdioServerParameters(command=str(command), cwd=str(tmp_path))) as client:
                assert _structured(await client.call_tool("get_capabilities"))["scope"] == "semantic_only"

    asyncio.run(scenario())


def test_optional_adapter_modules_import_without_sdk():
    code = """
import importlib.abc
import importlib
import sys
class NoSdk(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'mcp' or fullname.startswith('mcp.'):
            raise ModuleNotFoundError('optional SDK absent', name='mcp')
sys.meta_path.insert(0, NoSdk())
for name in ('ohmni.mcp_server', 'ohmni.mcp_server.schemas',
             'ohmni.mcp_server.service', 'ohmni.mcp_server.server',
             'ohmni.mcp_server.__main__'):
    importlib.import_module(name)
print('base imports work')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, timeout=30, check=False, shell=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "base imports work"
    assert result.stderr == ""


def test_failure_and_invalid_arguments_do_not_disclose_private_data(monkeypatch, golden, capsys):
    from ohmni.mcp_server import service
    from ohmni.mcp_server.server import create_server

    secret = "PRIVATE_VALUE_NOT_FOR_CLIENT"

    def crash(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(service, "verify", crash)

    async def scenario():
        async with Client(create_server()) as client:
            failure = await client.call_tool("verify_circuit", _arguments(golden))
            assert failure.is_error
            assert "INTERNAL_ERROR" in str(failure.content)
            assert secret not in str(failure)
            invalid = await client.call_tool("get_capabilities", {secret: secret})
            assert invalid.is_error
            assert secret not in str(invalid)
            _structured(await client.call_tool("get_capabilities"))

    asyncio.run(scenario())
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_optional_numbers_are_rejected_before_sdk_serialization(value, golden, requirements):
    from ohmni.mcp_server.schemas import VerifyRequest

    arguments = _arguments(golden, requirements)
    arguments["requirements"]["budget_usd"] = value
    with pytest.raises(ValidationError):
        VerifyRequest.model_validate(arguments)


def test_total_argument_byte_limit_is_enforced(golden):
    async def scenario():
        async with _client() as client:
            limits = _structured(await client.call_tool("get_capabilities"))["limits"]
            arguments = _arguments(golden)
            arguments["circuit"]["notes"] = "x" * (limits["max_argument_bytes"] + 1)
            result = await client.call_tool("verify_circuit", arguments)
            assert result.is_error
            assert "INPUT_TOO_LARGE" in str(result.content)
            _structured(await client.call_tool("get_capabilities"))

    asyncio.run(scenario())


def test_rule_failure_keeps_unknown_verdict_without_traceback_leak(monkeypatch, golden, requirements):
    from ohmni.mcp_server.server import create_server
    from ohmni.verifier import engine

    secret = "PRIVATE_RULE_EXCEPTION_SENTINEL"

    def crash(context, result):
        raise RuntimeError(secret)

    rules = engine.all_rules()
    monkeypatch.setattr(engine, "all_rules", lambda: [
        replace(rule, function=crash) if rule.rule_id == "PB-PWR-001" else rule
        for rule in rules
    ])

    async def scenario():
        async with Client(create_server()) as client:
            payload = _structured(await client.call_tool(
                "verify_circuit", _arguments(golden, requirements),
            ))
            result = next(r for r in payload["report"]["results"] if r["rule_id"] == "PB-PWR-001")
            assert result["outcome"] == "error"
            assert result["missing_data"]
            assert payload["report"]["coverage"] < 1.0
            assert payload["report"]["subsystem_status"]["electrical"] == "PARTIALLY_VERIFIED"
            assert "PB-PWR-001" in payload["undecided_rule_ids"]
            assert secret not in str(payload)
            assert "Traceback" not in str(payload)
            assert "RuntimeError" not in str(payload)

    asyncio.run(scenario())


def test_quantity_shorthand_is_rejected_as_advertised_by_schema(golden, requirements):
    async def scenario():
        async with _client() as client:
            arguments = _arguments(golden, requirements)
            arguments["requirements"]["max_input_voltage"] = "5V"
            assert (await client.call_tool("verify_circuit", arguments)).is_error
            arguments = _arguments(golden, requirements)
            arguments["circuit"]["components"][0]["value"] = "100nF"
            assert (await client.call_tool("verify_circuit", arguments)).is_error

    asyncio.run(scenario())
