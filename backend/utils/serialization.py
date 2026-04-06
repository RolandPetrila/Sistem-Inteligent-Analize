"""Shared JSON serialization helpers — elimina duplicarea json.dumps in 15+ locatii."""
import json
from typing import Any


def to_json(data: Any) -> str:
    """Serialize data to JSON string — handles non-serializable types via default=str."""
    return json.dumps(data, ensure_ascii=False, default=str)


def from_json(s: str | None, default: Any = None) -> Any:
    """Deserialize JSON string, returning default on failure."""
    if not s:
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default
