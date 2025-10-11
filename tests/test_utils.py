from types import MappingProxyType

import pytest

from config_guard.utils import (
    _checksum_of_config,
    _immutable_copy,
    _require_bypass_env,
    _stable_serialize_for_checksum,
)


class BadDeepcopy:
    def __deepcopy__(self, memo):  # pragma: no cover - used to force error path
        raise RuntimeError("nope")


def test_immutable_copy_basic_and_immutability():
    lst = [1, 2, {"a": 3}]
    dct = {"x": 1, "y": [2, 3]}

    lst_copy = _immutable_copy(lst)
    dct_copy = _immutable_copy(dct)

    assert isinstance(lst_copy, tuple)
    assert isinstance(dct_copy, MappingProxyType)

    # Mutations on original do not affect copies
    lst.append(99)
    dct["z"] = 5
    assert lst_copy != tuple(lst)
    assert "z" not in dct_copy

    # MappingProxyType must be immutable
    with pytest.raises(TypeError):
        dct_copy["new"] = 1  # type: ignore[index]


def test_immutable_copy_raises_on_bad_object():
    with pytest.raises(ValueError):
        _immutable_copy(BadDeepcopy())


def test_stable_serialize_and_checksum_are_stable():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}

    sa = _stable_serialize_for_checksum(a)
    sb = _stable_serialize_for_checksum(b)
    assert sa == sb

    ca = _checksum_of_config(a)
    cb = _checksum_of_config(b)
    assert ca == cb


def test_stable_serialize_handles_non_json_values():
    data = {"x": object()}
    # Should not raise
    _stable_serialize_for_checksum(data)


def test_require_bypass_env(monkeypatch):
    monkeypatch.delenv("ALLOW_CONFIG_BYPASS", raising=False)
    assert _require_bypass_env() is False
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    assert _require_bypass_env() is True
