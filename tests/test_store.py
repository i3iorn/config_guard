from types import MappingProxyType

import pytest

from config_guard import ConfigNotFoundError, ConfigValidationError, register_param
from config_guard.params import resolve_param_name
from config_guard.store import ConfigStore, PersistanceAdapterProtocol


def test_configstore_set_get_and_use_once_with_immutable_copy():
    store = ConfigStore()

    register_param(
        "FRUIT_LIST",
        default=["apple", "banana"],
        value_type=tuple,
        description="A list of fruits",
    )
    key = resolve_param_name("FRUIT_LIST")
    fruits = ["orange", "grape"]
    store.set(key, fruits, permanent=False)
    assert store.get(key) == ("orange", "grape")  # becomes tuple
    assert store.get(key) is None  # now gone
    assert store.snapshot_internal() == {}
    assert store.snapshot_public() == MappingProxyType({})
    fruits.append("kiwi")
    assert store.get(key) is None  # still gone
    store.set(key, fruits, permanent=True)
    assert store.get(key) == ("orange", "grape", "kiwi")
    fruits.append("mango")
    assert store.get(key) == ("orange", "grape", "kiwi")


def test_configstore_rejects_switching_types_when_not_allowed():
    store = ConfigStore(mutable_types=False)
    key = resolve_param_name("MAX_CONCURRENCY")
    store.set(key, 5, permanent=True)
    with pytest.raises(ValueError):
        store.set(key, "not an int", permanent=True)
    assert store.get(key) == 5  # still the original


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


def test_configstore_persistance_adapter_protocol():
    class SampleAdapter:
        def __init__(self):
            self._storage = {}

        def save(self, config: dict) -> None:
            self._storage = config

        def load(self) -> dict:
            return self._storage

    adapter = SampleAdapter()

    # Ensure adapter conforms to PersistanceAdapterProtocol
    assert isinstance(adapter, PersistanceAdapterProtocol)

    # Test saving and loading
    test_config = {"MAX_CONCURRENCY": 10, "VERIFY": True}
    adapter.save(test_config)
    loaded_config = adapter.load()
    assert loaded_config == test_config

    # Test invalid adapter (missing methods)
    class InvalidAdapter:
        def save(self, config: dict) -> None:
            pass

    invalid_adapter = InvalidAdapter()
    assert not isinstance(invalid_adapter, PersistanceAdapterProtocol)


def test_configstore_load_save_with_adapter():
    class InMemoryAdapter:
        def __init__(self):
            self._data = {}

        def save(self, config: dict) -> None:
            self._data = config

        def load(self) -> dict:
            return self._data

    adapter = InMemoryAdapter()

    register_param(
        "KEY1",
        default="default1",
        value_type=str,
        description="A test key 1",
    )
    register_param(
        "KEY2",
        default=0,
        value_type=int,
        description="A test key 2",
    )

    store = ConfigStore(persistance_adapter=adapter)

    # Initially empty
    assert store.snapshot_internal() == {}

    # Set some values and save
    store.set("KEY1", "value1", permanent=True)
    store.set("KEY2", 42, permanent=True)
    store.save()

    # Adapter should have the saved values
    assert adapter.load() == {"KEY1": "value1", "KEY2": 42}

    # Create a new store and load from adapter
    new_store = ConfigStore(persistance_adapter=adapter)
    new_store.load()
    print(new_store.snapshot_public())
    assert new_store.get("KEY1") == "value1"
    assert new_store.get("KEY2") == 42

    # Clear and ensure loading again works
    new_store.clear()
    assert new_store.snapshot_internal() == {}
    new_store.load()
    assert new_store.get("KEY1") == "value1"
    assert new_store.get("KEY2") == 42


def test_configstore_load_without_adapter_raises():
    store = ConfigStore()
    with pytest.raises(RuntimeError):
        store.load()


def test_configstore_save_without_adapter_raises():
    with pytest.raises(RuntimeError):
        store = ConfigStore()
        store.save()


def test_configstore_adapter_load_returns_non_dict_raises():
    class BadAdapter:
        def save(self, config: dict) -> None:
            pass

        def load(self) -> dict:
            return "not a dict"  # Incorrect return value_type

    adapter = BadAdapter()
    with pytest.raises(ValueError):
        store = ConfigStore(persistance_adapter=adapter)
        store.load()


def test_configstore_adapter_load_raises_propagates():
    class FailingAdapter:
        def save(self, config: dict) -> None:
            pass

        def load(self) -> dict:
            raise RuntimeError("Load failed")

    adapter = FailingAdapter()
    with pytest.raises(RuntimeError):
        store = ConfigStore(persistance_adapter=adapter)
        store.load()


def test_configstore_adapter_save_raises_propagates():
    class FailingAdapter:
        def save(self, config: dict) -> None:
            raise RuntimeError("Save failed")

        def load(self) -> dict:
            return {}

    adapter = FailingAdapter()
    with pytest.raises(RuntimeError):
        store = ConfigStore(persistance_adapter=adapter)
        store.save()


def test_configstore_set_with_unregistered_param():
    store = ConfigStore()
    with pytest.raises(ConfigNotFoundError):
        store.set("UNREGISTERED_PARAM", 123, permanent=True)


def test_configstore_set_with_invalid_type():
    register_param(
        "TEST_PARAM",
        default=10,
        value_type=int,
        description="A test parameter",
    )
    store = ConfigStore()
    with pytest.raises(ConfigValidationError):
        store.set("TEST_PARAM", "not an int", permanent=True)


def test_configstore_set_with_validator():
    def positive_validator(value) -> bool:
        if value <= 0:
            return False
        return True

    register_param(
        "POSITIVE_PARAM",
        default=1,
        value_type=int,
        validator=positive_validator,
        description="A positive integer parameter",
    )
    store = ConfigStore()
    store.set("POSITIVE_PARAM", 5, permanent=True)  # Valid
    with pytest.raises(ConfigValidationError):
        store.set("POSITIVE_PARAM", -3, permanent=True)  # Invalid


def test_configstore_set_with_bounds():
    register_param(
        "BOUNDED_PARAM",
        default=5,
        value_type=int,
        bounds=(1, 10),
        description="An integer parameter with bounds",
    )
    store = ConfigStore()
    store.set("BOUNDED_PARAM", 7, permanent=True)  # Within bounds
    with pytest.raises(ValueError):
        store.set("BOUNDED_PARAM", 0, permanent=True)  # Below lower bound
    with pytest.raises(ValueError):
        store.set("BOUNDED_PARAM", 11, permanent=True)  # Above upper bound


def test_configstore_snapshot_public_is_immutable():
    store = ConfigStore()
    store.set("MAX_CONCURRENCY", 5, permanent=True)
    public_snapshot = store.snapshot_public()
    with pytest.raises(TypeError):
        public_snapshot["MAX_CONCURRENCY"] = 10  # Attempt to mutate should fail


def test_configstore_set_with_invalid_value_type():
    register_param(
        "LIST_PARAM",
        default=[1, 2, 3],
        value_type=tuple,
        description="A list parameter",
    )
    store = ConfigStore()
    with pytest.raises(ConfigValidationError):
        store.set("LIST_PARAM", "not a list", permanent=True)  # Invalid value_type


def test_configstore_allows_mutable_types():
    store = ConfigStore(mutable_types=True)
    assert store.allows_mutable_types() is True


def test_configstore_disallows_mutable_types():
    store = ConfigStore(mutable_types=False)
    assert store.allows_mutable_types() is False


def test_configstore_set_with_none_value():
    register_param(
        "OPTIONAL_PARAM",
        default=None,
        value_type=int,
        description="An optional integer parameter",
    )
    store = ConfigStore()
    store.set("OPTIONAL_PARAM", None, permanent=True)  # Should be allowed
    assert store.get("OPTIONAL_PARAM") is None
    store.set("OPTIONAL_PARAM", 10, permanent=True)  # Valid integer
    assert store.get("OPTIONAL_PARAM") == 10


def test_configstore_check_type_change():
    store = ConfigStore()
    store.set("MAX_CONCURRENCY", 10, permanent=True)
    with pytest.raises(ValueError):
        store.set("MAX_CONCURRENCY", "notint", permanent=True)


def test_configstore_check_bounds():
    store = ConfigStore()
    with pytest.raises(ValueError):
        store.set("MAX_CONCURRENCY", 0, permanent=True)


def test_configstore_load_adapter_error():
    class BadAdapter:
        def load(self):
            return "notadict"

    with pytest.raises(ValueError):
        store = ConfigStore(persistance_adapter=BadAdapter())
        store.load()


def test_configstore_save_adapter_error():
    class BadAdapter:
        def save(self, config):
            raise RuntimeError("fail")

        def load(self):
            return {}

    store = ConfigStore(persistance_adapter=BadAdapter())
    with pytest.raises(RuntimeError):
        store.save()
