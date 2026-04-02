"""Generic MCP stdio server for CLARKE.

Reads JSON-RPC 2.0 messages from stdin (one per line), dispatches to
the tool registry, and writes responses to stdout.

Entry point::

    python -m clarke.mcp.server
"""

from __future__ import annotations

import asyncio
import json
import sys

from clarke.mcp.tools import TOOL_REGISTRY


async def _handle_request(request: dict) -> dict:
    """Dispatch a single JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")

    # --- initialize ---
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "clarke-mcp", "version": "0.2.0"},
            },
        }

    # --- notifications (no response required) ---
    if method == "notifications/initialized":
        return None  # type: ignore[return-value]

    # --- tools/list ---
    if method == "tools/list":
        tools = [schema for schema, _handler in TOOL_REGISTRY.values()]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    # --- tools/call ---
    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        entry = TOOL_REGISTRY.get(tool_name)
        if entry is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True,
                },
            }

        _schema, handler = entry
        try:
            result_text = await handler(args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    # --- unknown method ---
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


async def _run_stdio() -> None:
    """Read JSON-RPC messages from stdin, write responses to stdout."""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break

        try:
            request = json.loads(line.decode())
        except json.JSONDecodeError:
            continue

        response = await _handle_request(request)
        if response is None:
            # Notification — no response needed.
            continue

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    """Entry point for ``python -m clarke.mcp.server``."""
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
