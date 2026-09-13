"""Official MCP SDK stdio server with explicit, strict tool argument validation."""

import asyncio
import json
import logging
import sys

from pydantic import ValidationError

from .schemas import (
    MAX_ARGUMENT_BYTES,
    Capabilities,
    GetPartRequest,
    InputModel,
    ListPartsRequest,
    PartDetail,
    PartPage,
    VerificationResult,
    VerifyRequest,
)
from .service import SemanticService


def create_server():
    # Keep optional SDK imports out of the base package's import path.
    from mcp import types
    from mcp.server import Server

    service = SemanticService()
    definitions = {
        "get_capabilities": (InputModel, Capabilities, service.get_capabilities,
                             "Discover semantic tools, input limits, rule IDs and limitations."),
        "list_parts": (ListPartsRequest, PartPage, service.list_parts,
                       "List the server-owned catalog in stable pages; no live supplier data."),
        "get_part": (GetPartRequest, PartDetail, service.get_part,
                     "Read a catalog part's pins, limits and original evidence labels."),
        "verify_circuit": (VerifyRequest, VerificationResult, service.verify_circuit,
                           ("Run every deterministic semantic rule on proposed CircuitIR and optional "
                           "requirements using the bundled catalog. Evidence must be empty or omitted. "
                           "Electrical faults are report findings, not tool execution errors. "
                           "No EDA or SPICE is run; inspect coverage and limitations.")),
    }

    async def list_tools(context, params):
        return types.ListToolsResult(tools=[
            types.Tool(name=name, description=description,
                       input_schema=request.model_json_schema(),
                       output_schema=response.model_json_schema(mode="serialization"),
                       annotations=types.ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                                         idempotent_hint=True, open_world_hint=False))
            for name, (request, response, _, description) in definitions.items()
        ])

    def error(code, detail):
        return types.CallToolResult(
            is_error=True, content=[types.TextContent(type="text", text=f"{code}: {detail}")],
        )

    async def call_tool(context, params):
        if params.name not in definitions:
            return error("UNKNOWN_TOOL", "Use tools/list to discover supported tools.")
        request_type, _, handler, _ = definitions[params.name]
        arguments = params.arguments if params.arguments is not None else {}
        try:
            encoded = json.dumps(arguments, ensure_ascii=True, allow_nan=False).encode("utf-8")
            if len(encoded) > MAX_ARGUMENT_BYTES:
                return error("INPUT_TOO_LARGE", "Tool arguments exceed the advertised byte limit.")
            request = request_type.model_validate(arguments)
        except ValidationError:
            # Even an error location can contain an untrusted extra-field name.
            return error("INVALID_ARGUMENTS", "Arguments do not match the published tool schema.")
        except (ValueError, TypeError, RecursionError):
            return error("INVALID_ARGUMENTS", "Expected finite JSON values within the input limits.")
        try:
            result = handler(request).model_dump(mode="json")
            serialized = json.dumps(result, allow_nan=False, ensure_ascii=True)
            return types.CallToolResult(
                structured_content=result, content=[types.TextContent(type="text", text=serialized)],
            )
        except KeyError:
            return error("PART_NOT_FOUND", "The requested part is not in the bundled catalog.")
        except Exception:  # noqa: BLE001 -- public boundary must not expose exception data
            return error("INTERNAL_ERROR", "Tool execution failed; no verification result is available.")

    return Server(
        "ohmni-semantic", version="1.0.0", on_list_tools=list_tools, on_call_tool=call_tool,
        instructions="LLMs propose; evidence grounds; deterministic systems verify. "
                     "Use only returned rule results as semantic findings. Missing checks are not PASS.",
    )


async def serve_stdio():
    from mcp.server.stdio import stdio_server

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> int:
    # SDK errors must not serialize proposal contents or internal exception values to stderr.
    logging.getLogger("mcp").addHandler(logging.NullHandler())
    logging.getLogger("mcp").propagate = False
    try:
        asyncio.run(serve_stdio())
    except ModuleNotFoundError as exc:
        if exc.name == "mcp":
            print('Install the MCP extra: python -m pip install -e ".[mcp]"', file=sys.stderr)
        else:
            print("Ohmni MCP startup failed: a required dependency is unavailable.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception:  # noqa: BLE001 -- fixed startup failure, never a traceback
        print("Ohmni MCP server failed; no verification result was produced.", file=sys.stderr)
        return 1
    return 0
