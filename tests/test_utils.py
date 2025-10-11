import pytest

from config_guard.utils import _immutable_copy, _require_bypass_env


def test_immutable_copy():
    d = {"a": 1, "b": [2, 3]}
    c = _immutable_copy(d)
    assert c == d
    assert c is not d


def test_immutable_copy_error():
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise Exception("fail")

    with pytest.raises(ValueError):
        _immutable_copy(Uncopyable())


def test_require_bypass_env_true(monkeypatch):
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    assert _require_bypass_env() is True


def test_require_bypass_env_false(monkeypatch):
    monkeypatch.delenv("ALLOW_CONFIG_BYPASS", raising=False)
    assert _require_bypass_env() is False
