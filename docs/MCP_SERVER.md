# Local semantic MCP server

The first MCP slice exposes Ohmni's deterministic semantic verifier and bundled
catalog through the official Python MCP SDK 2.2.0. It has no model invocation,
EDA execution, SPICE simulation, artifact writing, or remote HTTP listener.

## Install and launch

Use Python 3.12 or newer in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,mcp]"
.\.venv\Scripts\python.exe -m ohmni.mcp_server
```

The equivalent installed executable is `.venv\Scripts\ohmni-mcp.exe` on Windows
or `ohmni-mcp` on other systems. The process speaks MCP on stdin/stdout; it waits
for a client and does not print an interactive welcome message. The optional SDK
is loaded only when a server is created or launched. Ordinary Ohmni imports work
without the MCP extra.

A local MCP host can launch this command with an absolute Python path:

```json
{
  "command": "C:\\Dev\\hackathon\\.venv\\Scripts\\python.exe",
  "args": ["-m", "ohmni.mcp_server"]
}
```

No provider key is needed. The package uses the SDK's low-level `Server` and
`stdio_server` APIs so that every tool has explicit strict argument validation,
including rejection of unknown top-level arguments. JSON-RPC, discovery,
transport framing and output types remain the SDK's responsibility.

## Tools

| Tool | Arguments | Result |
|---|---|---|
| `get_capabilities` | none | Semantic scope, supported tools, rule IDs, input limits, catalog/verifier hashes and limitations |
| `list_parts` | `offset=0`, `limit=25` (1–100) | Stable catalog page, total count and next offset |
| `get_part` | `part_id` | Complete server-owned component specification, including original provenance labels |
| `verify_circuit` | `circuit`, optional `requirements` | Existing `VerificationReport`, undecided rule IDs and input/catalog/verifier hashes |

Discover exact JSON input/output schemas with `tools/list`. Numeric quantities
use `{ "value": 3.3, "unit": "V" }`, with canonical SI units. The circuit uses
the existing `CircuitIR` shape with additional input bounds. Requirements use
the existing `RequirementsSpec` shape. Evidence arrays at every proposal site
must be omitted or empty. Read catalog evidence through `get_part`; it cannot
be copied into a proposal as a client attestation.

```python
import asyncio
import sys

from mcp import Client, StdioServerParameters


async def main():
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "ohmni.mcp_server"]
    )
    async with Client(server) as client:
        capabilities = await client.call_tool("get_capabilities")
        print(capabilities.structured_content)
        parts = await client.call_tool("list_parts", {"limit": 5})
        print(parts.structured_content)
        # Load your proposal objects; never supply a report or evidence flags.
        # result = await client.call_tool("verify_circuit", {
        #     "circuit": circuit_proposal, "requirements": requirements_proposal,
        # })


asyncio.run(main())
```

## Evidence and report semantics

LLMs propose; evidence grounds; deterministic systems verify. The server always
runs the complete registered semantic rule set against its private startup
catalog snapshot. The caller cannot replace the catalog, select a subset of
rules, waive findings, set status, or supply an authoritative report/hash.

An electrical violation is a successfully executed check: `isError` is false and
the report carries the findings. Missing data remains `INSUFFICIENT_DATA`, and
unsupported subsystems remain `UNSUPPORTED`. Inspect coverage, subsystem labels,
undecided rules and limitations alongside `export_blocked`; absence of blockers
does not establish complete verification or authorize manufacturing.

`requirements_supported` separately projects the existing
`RequirementsSpec.is_supported_scope` predicate: false for declared unsupported
safety domains or input limits above 12 V, and null when requirements are absent.
The electrical verifier itself does not enforce that scope gate. A false value
prohibits a validated-design claim even when the electrical report has no
blocking findings; true evaluates only the supplied declarations.

Invalid arguments and execution failures return `isError: true` with fixed public
codes (`INVALID_ARGUMENTS`, `INPUT_TOO_LARGE`, `PART_NOT_FOUND`, `UNKNOWN_TOOL`,
`INTERNAL_ERROR`). No exception values or tracebacks are returned. A rule's own
`ERROR` outcome is preserved, with `error_text` and traceback-bearing rule
limitations replaced by fixed diagnostics.

The report retains the existing verifier's identifiers and engineering content.
Its `generated_at` and evidence `recorded_at` fields are observational timestamps;
they are excluded only when testing deterministic equality. The additional
`input_hash` binds the normalized full proposal, requirements, catalog snapshot,
schema version and verifier fingerprint. The latter identifies installed domain
and verifier Python source plus the Pydantic version. These are reproducibility
identifiers, not signed attestations. Parent hashes remain untrusted history
hints; the server stores no revision lineage.

Tool arguments are limited to 1 MiB of serialized JSON, 128 components, 256 nets,
2,048 total connections and bounded strings/lists. Admission checks happen after
the SDK parses a message; this local process is not a hostile-client isolation
or multi-user authorization boundary. No caller path or executable is accepted.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_server.py
.\.venv\Scripts\python.exe scripts/verify.py fast
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe scripts/ai_state.py validate
```

The MCP tests launch a real stdio subprocess, discover schemas and compare the
golden circuit and every permanent broken fixture with direct Python reports.
They also exercise unknown parts, missing data, forged evidence, extra fields,
strict types, input limits and reproducibility. The tests skip explicitly on a
base installation without the optional SDK; install `[dev,mcp]` to run this gate.

EDA, SPICE, routing, fabrication and remote hosting require separate work. The
unresolved M10-T05 routing checkpoint is preserved in
`.ai/approvals/MCP-SEMANTIC-1.yaml` and remains parked.
