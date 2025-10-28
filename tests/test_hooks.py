import logging

import pytest

from config_guard.hooks import HookBus


def test_hookbus_register_and_run_success(caplog):
    bus = HookBus()
    called = []

    def hook(snapshot):
        called.append(snapshot)

    bus.register(hook)
    bus.run({"a": 1})
    assert called and called[0]["a"] == 1


def test_hookbus_register_non_callable_raises():
    bus = HookBus()
    with pytest.raises(TypeError):
        bus.register(123)  # value_type: ignore[arg-value_type]


def test_hookbus_invalid_failure_mode():
    with pytest.raises(ValueError):
        HookBus("boom")  # value_type: ignore[arg-value_type]


def test_hookbus_run_failure_modes(caplog):
    def bad(_):
        raise RuntimeError("fail")

    # ignore: should not raise, only debug log
    caplog.set_level(logging.DEBUG, logger="app_config_secure")
    bus_ignore = HookBus("ignore")
    bus_ignore.register(bad)
    bus_ignore.run({})  # does not raise

    # log: should not raise, logs error
    bus_log = HookBus("log")
    bus_log.register(bad)
    bus_log.run({})

    # raise: should raise
    bus_raise = HookBus("raise")
    bus_raise.register(bad)
    with pytest.raises(RuntimeError):
        bus_raise.run({})


def test_hookbus_clear():
    bus = HookBus()
    bus.register(lambda s: None)
    bus.clear()
    # Running should do nothing
    bus.run({"x": 1})
