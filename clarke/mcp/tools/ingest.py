"""clarke_ingest_document tool — ingest a document into CLARKE."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_ingest_document(args: dict) -> str:
    """Ingest a document into CLARKE for retrieval."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "filename": args["filename"],
        "content": args["content"],
    }
    for optional in ("content_type", "source_url", "metadata"):
        if args.get(optional) is not None:
            payload[optional] = args[optional]

    result = await clarke_api("POST", "/ingest", json=payload)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_ingest_document",
        "description": (
            "Ingest a document into CLARKE's knowledge base. The document will be "
            "chunked, embedded, and made available for semantic retrieval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "project_id": {"type": "string", "description": "Project ID"},
                "filename": {
                    "type": "string",
                    "description": "Original filename (used for source tracking)",
                },
                "content": {
                    "type": "string",
                    "description": "Document content to ingest",
                },
                "content_type": {
                    "type": "string",
                    "description": "MIME type (e.g., 'text/markdown', 'application/pdf')",
                },
                "source_url": {
                    "type": "string",
                    "description": "Original source URL for provenance",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata key-value pairs",
                },
            },
            "required": ["tenant_id", "project_id", "filename", "content"],
        },
    },
    handle_ingest_document,
)
