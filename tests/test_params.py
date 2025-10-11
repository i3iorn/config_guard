import enum

import pytest

from config_guard.exceptions import ConfigValidationError
from config_guard.params import (
    REGISTRY,
    ParamRegistry,
    ParamSpec,
    dump_registry_state,
    get_param_spec,
    list_params,
    resolve_param_name,
)


class P(enum.Enum):
    MC = "MAX_CONCURRENCY"
    V = "VERIFY"


def test_paramspec_validate_success_and_failures():
    ps = ParamSpec(name="X", default=5, type=int, bounds=(1, 10), validator=lambda v: v % 2 == 1)
    ps.validate(5)

    with pytest.raises(ConfigValidationError):
        ps.validate(0)  # out of bounds
    with pytest.raises(ConfigValidationError):
        ps.validate(4)  # validator fails
    with pytest.raises(ConfigValidationError):
        ps.validate("str")  # wrong type


def test_paramspec_to_mapping_contains_optionals():
    ps = ParamSpec(name="Y", default=None, type=(int, type(None)), description="desc")
    m = ps.to_mapping()
    assert m["default"] is None and m["type"]
    assert m["description"] == "desc"


def test_paramregistry_register_and_get_and_alias_and_override():
    reg = ParamRegistry()
    ps = ParamSpec(name="A", default=1, type=int)
    reg.register(ps, aliases=("alias_a",))

    assert reg.has("A") is True
    assert reg.has("alias_a") is True
    assert reg.get("alias_a").name == "A"
    assert reg.resolve_name("alias_a") == "A"

    # Override
    ps2 = ParamSpec(name="A", default=2, type=int)
    reg.register(ps2, override=True)
    assert reg.get("A").default == 2

    # duplicate without override
    with pytest.raises(ConfigValidationError):
        reg.register(ps2)

    # alias conflict
    reg2 = ParamRegistry()
    reg2.register(ParamSpec(name="A", default=1, type=int), aliases=("X",))
    reg2.register(ParamSpec(name="B", default=1, type=int))
    with pytest.raises(ConfigValidationError):
        reg2.register(ParamSpec(name="B", default=1, type=int), aliases=("X",))


def test_paramregistry_unknown_param_errors():
    reg = ParamRegistry()
    with pytest.raises(ConfigValidationError):
        reg.get("UNKNOWN")
    with pytest.raises(ConfigValidationError):
        reg.resolve_name("UNKNOWN")


def test_paramregistry_all_names_and_clear():
    reg = ParamRegistry()
    reg.register(ParamSpec(name="A", default=1, type=int))
    reg.register(ParamSpec(name="B", default=1, type=int))
    names = reg.all_names()
    assert names == ("A", "B")
    reg.clear()
    assert reg.all_names() == tuple()


def test_module_functions_and_dump_registry_state_seeded(REGISTRY=REGISTRY):
    # registry is seeded by conftest
    assert "MAX_CONCURRENCY" in list_params()
    ps = get_param_spec("max_concurrency")
    assert ps.name == "MAX_CONCURRENCY"
    assert resolve_param_name(P.MC) == "MAX_CONCURRENCY"
    state = dump_registry_state()
    assert state["specs_count"] >= 1
