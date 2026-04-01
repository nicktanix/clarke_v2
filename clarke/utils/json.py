"""JSON serialization utilities."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID


class ClarkeJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)


def safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=ClarkeJSONEncoder, default=str)
