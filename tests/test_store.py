from types import MappingProxyType

import pytest

from config_guard import ConfigValidationError
from config_guard.params import ConfigParam
from config_guard.store import ConfigStore


def test_store_set_get():
    store = ConfigStore()
    store.set(ConfigParam(list(ConfigParam)[0]), 123, permanent=True)
    assert store.get(ConfigParam(list(ConfigParam)[0])) == 123


def test_store_snapshot():
    store = ConfigStore()
    store.set(ConfigParam(list(ConfigParam)[0]), 1, permanent=True)
    snap = store.snapshot_public()
    assert isinstance(snap, MappingProxyType)


def test_store_get_default():
    store = ConfigStore()
    assert store.get(ConfigParam(list(ConfigParam)[0]), default=42) == 42


def test_store_restore_and_clear():
    store = ConfigStore()
    key = ConfigParam(list(ConfigParam)[0])
    store.set(key, 5, permanent=True)
    snap = store.snapshot_internal()
    store.set(key, 10, permanent=True)
    store.restore(snap)
    assert store.get(key) == 5
    store.clear()
    assert store.get(key) is None


def test_store_get_invalid_key():
    store = ConfigStore()
    with pytest.raises(ConfigValidationError):
        store.get("not_a_param")
