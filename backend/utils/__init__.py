"""
Utility functions comune pentru backend RIS.
Re-exporta safe_json_loads pentru compatibilitate cu imports existente.
"""
import json
from typing import Any


def safe_json_loads(data: str | None, default: Any = None) -> Any:
    """Parse JSON string safely, return default on error."""
    if not data:
        return default if default is not None else {}
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
