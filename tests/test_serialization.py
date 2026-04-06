"""Teste pentru backend/utils/serialization.py."""
import pytest
from backend.utils.serialization import to_json, from_json


def test_to_json_simple():
    result = to_json({"key": "value", "num": 42})
    assert '"key": "value"' in result
    assert '"num": 42' in result


def test_to_json_non_serializable():
    from datetime import datetime
    result = to_json({"ts": datetime(2026, 1, 1, 12, 0, 0)})
    assert "2026-01-01" in result


def test_to_json_romanian_chars():
    result = to_json({"name": "Societate Comerciala SRL"})
    assert "Societate" in result


def test_from_json_valid():
    result = from_json('{"a": 1, "b": "test"}')
    assert result == {"a": 1, "b": "test"}


def test_from_json_invalid_returns_default():
    result = from_json("not valid json", default=[])
    assert result == []


def test_from_json_none_returns_default():
    result = from_json(None, default={})
    assert result == {}


def test_from_json_empty_returns_default():
    result = from_json("", default=None)
    assert result is None
