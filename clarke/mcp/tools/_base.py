"""Shared HTTP helper for CLARKE MCP tools."""

import os

import httpx


async def clarke_api(
    method: str, path: str, *, json: dict | None = None, params: dict | None = None
) -> dict | str:
    """Make an HTTP request to the CLARKE API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        path: API path (e.g., "/query").
        json: Optional JSON body.
        params: Optional query parameters.

    Returns:
        Parsed JSON dict or raw text.
    """
    api_url = os.environ.get("CLARKE_API_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, f"{api_url}{path}", json=json, params=params)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        return resp.json() if "json" in ct else resp.text
