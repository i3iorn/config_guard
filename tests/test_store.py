from types import MappingProxyType

import pytest

from config_guard.params import resolve_param_name
from config_guard.store import ConfigStore


def test_configstore_set_get_and_use_once_with_immutable_copy():
    store = ConfigStore()
    key = resolve_param_name("VERIFY")

    orig = [1, 2, 3]
    store.set(key, orig, permanent=True)
    v = store.get(key)
    assert isinstance(v, tuple)
    # Mutate original, stored should be unaffected
    orig.append(4)
    assert store.get(key) == (1, 2, 3)

    # use_once path
    store.set(key, 99, permanent=False)
    assert store.get(key) == 99
    assert store.get(key, 0) == (1, 2, 3)


def test_configstore_rejects_switching_types_when_not_allowed():
    store = ConfigStore(mutable_types=False)
    key = resolve_param_name("VERIFY")

    store.set(key, [1, 2], permanent=True)  # becomes tuple
    # switching to dict (becomes MappingProxyType) should fail
    with pytest.raises(ValueError):
        store.set(key, {"a": 1}, permanent=True)


def test_configstore_snapshots_and_restore_and_clear():
    store = ConfigStore()
    key = resolve_param_name("MAX_CONCURRENCY")
    store.set(key, 5, permanent=True)

    internal = store.snapshot_internal()
    public = store.snapshot_public()
    assert isinstance(public, MappingProxyType)
    assert internal[key] == 5 and public[key] == 5

    store.restore({key: 7})
    assert store.get(key) == 7

    store.clear()
    assert store.snapshot_internal() == {}
