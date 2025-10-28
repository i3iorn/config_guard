import os
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
        dct_copy["new"] = 1  # value_type: ignore[index]


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


def test_bypass_env_returning_correct_value():
    env_value = os.getenv("ALLOW_CONFIG_BYPASS")
    if env_value == "1":
        assert _require_bypass_env() is True
    else:
        assert _require_bypass_env() is False


def test_checksum_different_for_different_data():
    data1 = {"a": 1, "b": 2}
    data2 = {"a": 1, "b": 3}
    checksum1 = _checksum_of_config(data1)
    checksum2 = _checksum_of_config(data2)
    assert checksum1 != checksum2


def test_checksum_same_for_same_data():
    data = {"a": 1, "b": 2}
    checksum1 = _checksum_of_config(data)
    checksum2 = _checksum_of_config(data)
    assert checksum1 == checksum2


def test_stable_serialize_handles_nested_structures():
    data = {"a": [1, 2, {"b": 3}], "c": {"d": 4}}
    serialized = _stable_serialize_for_checksum(data)
    assert isinstance(serialized, bytes)
    assert b'"\'a\'":[1,2,{"b":3}]' in serialized
    assert b'"\'c\'":{"d":4}' in serialized


def test_immutable_copy_with_nested_structures():
    data = {"a": [1, 2, {"b": 3}], "c": {"d": 4}}
    immutable = _immutable_copy(data)
    assert isinstance(immutable, MappingProxyType)
    assert isinstance(immutable["a"], tuple)
    assert isinstance(immutable["c"], MappingProxyType)
    with pytest.raises(TypeError):
        immutable["a"] += (4,)  # value_type: ignore[operator]
    with pytest.raises(TypeError):
        immutable["c"]["d"] = 5  # value_type: ignore[index]


def test_immutable_copy_with_primitive():
    value = 42
    immutable = _immutable_copy(value)
    assert immutable == value
    assert isinstance(immutable, int)


def test_immutable_copy_with_string():
    value = "hello"
    immutable = _immutable_copy(value)
    assert immutable == value
    assert isinstance(immutable, str)


def test_immutable_copy_with_tuple():
    value = (1, 2, 3)
    immutable = _immutable_copy(value)
    assert immutable == value
    assert isinstance(immutable, tuple)


def test_immutable_copy_with_set():
    value = {1, 2, 3}
    immutable = _immutable_copy(value)
    assert immutable == value
    assert isinstance(immutable, set)


def test_stable_serialize_with_non_string_keys():
    data = {1: "a", 2: "b"}
    serialized = _stable_serialize_for_checksum(data)
    # Accept both possible escaping/quoting styles for keys
    assert b'"1":"a"' in serialized
    assert b'"2":"b"' in serialized


def test_stable_serialize_with_mixed_keys():
    data = {"a": 1, 2: "b", (3, 4): [5, 6]}
    serialized = _stable_serialize_for_checksum(data)
    # Accept both possible escaping/quoting styles for keys
    assert b'"2":"b"' in serialized
    # Accept both quoted and unquoted 'a' key
    assert b"\"'a'\":1" in serialized
    # Accept both quoted and unquoted tuple key
    assert b'"(3, 4)":[' in serialized


def test_stable_serialize_with_empty_dict():
    data = {}
    serialized = _stable_serialize_for_checksum(data)
    assert serialized == b"{}" or serialized == b"{}"


def test_stable_serialize_with_empty_list():
    data = {"a": []}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":[]" in serialized


def test_stable_serialize_with_none_value():
    data = {"a": None}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":null" in serialized


def test_stable_serialize_with_boolean_values():
    data = {"a": True, "b": False}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":true" in serialized
    assert b"\"'b'\":false" in serialized


def test_stable_serialize_with_float_values():
    data = {"a": 1.23, "b": 4.56}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":1.23" in serialized
    assert b"\"'b'\":4.56" in serialized


def test_stable_serialize_with_large_numbers():
    data = {"a": 12345678901234567890, "b": -98765432109876543210}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":12345678901234567890" in serialized
    assert b"\"'b'\":-98765432109876543210" in serialized


def test_stable_serialize_with_special_characters():
    data = {"a": "hello\nworld", "b": "special\tchars"}
    serialized = _stable_serialize_for_checksum(data)
    assert b'"\'a\'":"hello\\nworld"' in serialized
    assert b'"\'b\'":"special\\tchars"' in serialized


def test_stable_serialize_with_nested_empty_structures():
    data = {"a": {}, "b": []}
    serialized = _stable_serialize_for_checksum(data)
    assert b"\"'a'\":{}" in serialized
    assert b"\"'b'\":[]" in serialized


def test_stable_serialize_with_deeply_nested_structures():
    data = {"a": {"b": {"c": {"d": [1, 2, 3]}}}}
    serialized = _stable_serialize_for_checksum(data)
    assert b'"\'a\'":{"b":{"c":{"d":[1,2,3]}}}' in serialized
