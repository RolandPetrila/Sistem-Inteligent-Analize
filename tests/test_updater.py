"""Teste updater — forma versiunii + starii (fara efecte destructive pe git)."""

from backend.services import updater


def test_running_version_shape():
    v = updater.get_running_version()
    assert set(v.keys()) >= {"sha", "date", "branch", "build"}
    assert isinstance(v["build"], str)


def test_state_shape():
    s = updater.get_state()
    for k in ("update_available", "updating", "behind", "last_check"):
        assert k in s
