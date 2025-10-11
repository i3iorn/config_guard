import pytest

from config_guard.hooks import HookBus


def test_hookbus_register_and_run():
    bus = HookBus()
    called = []

    def hook(data):
        called.append(data)

    bus.register(hook)
    bus.run({"foo": 1})
    assert called == [{"foo": 1}]


def test_hookbus_clear():
    bus = HookBus()
    bus.register(lambda x: x)
    bus.clear()
    assert not bus._hooks


def test_hookbus_register_error():
    bus = HookBus()
    with pytest.raises(TypeError):
        bus.register(123)  # Not callable


def test_hookbus_run_no_hooks():
    bus = HookBus()
    # Should not raise, but nothing happens
    bus.run({"bar": 2})
    assert bus._hooks == []
