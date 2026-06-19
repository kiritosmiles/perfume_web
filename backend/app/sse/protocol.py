import json
from datetime import datetime, timezone


def sse(event_type: str, data: dict | str) -> str:
    if isinstance(data, dict):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = data
    return f"event: {event_type}\ndata: {payload}\n\n"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
