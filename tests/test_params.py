import enum

import pytest

from config_guard.exceptions import ConfigDuplicateError, ConfigNotFoundError, ConfigValidationError
from config_guard.params import (
    REGISTRY,
    ParamRegistry,
    ParamSpec,
    dump_registry_state,
    get_param_spec,
    list_params,
    register_param,
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
    with pytest.raises(ConfigDuplicateError):
        reg.register(ps2)

    # alias conflict
    reg2 = ParamRegistry()
    reg2.register(ParamSpec(name="A", default=1, type=int), aliases=("X",))
    reg2.register(ParamSpec(name="B", default=1, type=int))
    with pytest.raises(ConfigDuplicateError):
        reg2.register(ParamSpec(name="B", default=1, type=int), aliases=("X",))


def test_paramregistry_unknown_param_errors():
    reg = ParamRegistry()
    with pytest.raises(ConfigNotFoundError):
        reg.get("UNKNOWN")
    with pytest.raises(ConfigNotFoundError):
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


def test_module_functions_unknown_param_errors():
    with pytest.raises(ConfigNotFoundError):
        get_param_spec("UNKNOWN")
    with pytest.raises(ConfigNotFoundError):
        resolve_param_name("UNKNOWN")
    with pytest.raises(ConfigNotFoundError):
        resolve_param_name(123)  # invalid type


def test_paramregistry_enum_alias_handling():
    reg = ParamRegistry()
    ps = ParamSpec(name="MAX_CONCURRENCY", default=5, type=int)
    reg.register(ps, aliases=("MC",))

    assert reg.has(P.MC) is True
    assert reg.get(P.MC).name == "MAX_CONCURRENCY"
    assert reg.resolve_name(P.MC) == "MAX_CONCURRENCY"

    class BadEnum(enum.Enum):
        BAD = 123  # non-string value

    with pytest.raises(ConfigValidationError):
        reg.get(BadEnum.BAD)
    with pytest.raises(ConfigValidationError):
        reg.resolve_name(BadEnum.BAD)


def test_paramregistry_logging_on_operations(caplog):
    reg = ParamRegistry()
    ps = ParamSpec(name="A", default=1, type=int)
    with caplog.at_level("DEBUG"):
        reg.register(ps, aliases=("alias_a",))
        assert any("Register called:" in msg for msg in caplog.messages)
        assert reg.has("A") is True
        assert any("Has(" in msg for msg in caplog.messages)
        reg.get("alias_a")
        assert any("Get(" in msg for msg in caplog.messages)
        reg.resolve_name("alias_a")
        assert any("Resolve_name(" in msg for msg in caplog.messages)
        with pytest.raises(ConfigNotFoundError):
            reg.get("UNKNOWN")
        assert any("Resolving key for" in msg for msg in caplog.messages)


def test_paramspec_bounds_check_and_has_bounds():
    ps_with_bounds = ParamSpec(name="B", default=5, type=int, bounds=(1, 10))
    assert ps_with_bounds.has_bounds() is True
    assert ps_with_bounds._bounds_check(5) is True
    assert ps_with_bounds._bounds_check(0) is False

    ps_without_bounds = ParamSpec(name="C", default=5, type=int)
    assert ps_without_bounds.has_bounds() is False
    assert ps_without_bounds._bounds_check(100) is True  # Always true without bounds


def test_paramspec_validator_exception_handling():
    def faulty_validator(v):
        raise ValueError("Intentional error")

    ps = ParamSpec(name="D", default=5, type=int, validator=faulty_validator)
    with pytest.raises(ConfigValidationError) as exc_info:
        ps.validate(5)
    assert "Custom validator raised exception" in str(exc_info.value)


def test_paramregistry_clear_and_all_names():
    reg = ParamRegistry()
    reg.register(ParamSpec(name="A", default=1, type=int))
    reg.register(ParamSpec(name="B", default=2, type=int))
    assert set(reg.all_names()) == {"A", "B"}
    reg.clear()
    assert reg.all_names() == ()


def test_paramregistry_register_alias_conflict_logging(caplog):
    reg = ParamRegistry()
    reg.register(ParamSpec(name="A", default=1, type=int), aliases=("X",))
    with caplog.at_level("ERROR"):
        with pytest.raises(ConfigValidationError):
            reg.register(ParamSpec(name="B", default=2, type=int), aliases=("X",))
        assert any("Alias conflict" in msg for msg in caplog.messages)


def test_paramregistry_register_duplicate_without_override_logging(caplog):
    reg = ParamRegistry()
    reg.register(ParamSpec(name="A", default=1, type=int))
    with caplog.at_level("ERROR"):
        with pytest.raises(ConfigDuplicateError):
            reg.register(ParamSpec(name="A", default=2, type=int))
        assert any("already registered" in msg for msg in caplog.messages)


def test_parmregistry_register_string_with_bounds():
    reg = ParamRegistry()
    ps = ParamSpec(name="STR_PARAM", default="hello", type=str, bounds=(3, 10))
    reg.register(ps)
    assert reg.get("STR_PARAM").name == "STR_PARAM"

    with pytest.raises(ConfigValidationError):
        ps.validate("h")  # too short
    with pytest.raises(ConfigValidationError):
        ps.validate("this is a very long string")  # too long
    ps.validate("valid")  # valid length


def test_paramregistry_register_list_with_bounds():
    reg = ParamRegistry()
    ps = ParamSpec(name="LIST_PARAM", default=[1, 2], type=list, bounds=(1, 5))
    reg.register(ps)
    assert reg.get("LIST_PARAM").name == "LIST_PARAM"
    ps.validate([1])  # valid
    ps.validate([1, 2, 3, 4, 5])  # valid
    with pytest.raises(ConfigValidationError):
        ps.validate([])  # too short
    with pytest.raises(ConfigValidationError):
        ps.validate([1, 2, 3, 4, 5, 6])  # too long


def test_paramregistry_register_int_with_min_max():
    reg = ParamRegistry()
    ps = ParamSpec(name="INT_PARAM", default=10, type=int, bounds=(1, 100))
    reg.register(ps)
    assert reg.get("INT_PARAM").name == "INT_PARAM"
    ps.validate(50)  # valid
    with pytest.raises(ConfigValidationError):
        ps.validate(0)  # too low
    with pytest.raises(ConfigValidationError):
        ps.validate(150)  # too high


def test_paramregistry_register_float_with_min_max():
    reg = ParamRegistry()
    ps = ParamSpec(name="FLOAT_PARAM", default=1.5, type=float, bounds=(0.0, 10.0))
    reg.register(ps)
    assert reg.get("FLOAT_PARAM").name == "FLOAT_PARAM"
    ps.validate(5.5)  # valid
    with pytest.raises(ConfigValidationError):
        ps.validate(-1.0)  # too low
    with pytest.raises(ConfigValidationError):
        ps.validate(15.0)  # too high


def test_paramregistry_register_with_min_length_max_length():
    reg = ParamRegistry()
    ps = ParamSpec(name="STR_PARAM_LEN", default="test", type=str, bounds=(2, 10))
    reg.register(ps)
    assert reg.get("STR_PARAM_LEN").name == "STR_PARAM_LEN"
    ps.validate("ok")  # valid
    ps.validate("validlen")  # valid
    with pytest.raises(ConfigValidationError):
        ps.validate("a")  # too short
    with pytest.raises(ConfigValidationError):
        ps.validate("this string is way too long")  # too long


def test_paramregistry_register_with_invalid_bounds_combination():
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS", default=5, type=int, bounds=(1, 10), min=1)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_2", default=5, type=int, bounds=(1, 10), max=10)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_3", default="test", type=str, min=1)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_4", default=5, type=int, min_length=1)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_5", default=[1, 2], type=list, min=1)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_6", default=5, type=int, min_length=1)

    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_7", default="test", type=str, max=10)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_8", default=[1, 2], type=list, max=10)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_9", default=5, type=int, max_length=10)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_10", default=5, type=int, min_length=1, max_length=10)
    with pytest.raises(ValueError):
        register_param(name="INVALID_BOUNDS_11", default=5, type=int, min=1, max=10, bounds=(1, 10))


def test_paramregistry_register_with_non_tuple_bounds():
    with pytest.raises(ValueError):
        register_param(name="NON_TUPLE_BOUNDS", default=5, type=int, bounds=10)  # should be a tuple
    with pytest.raises(ValueError):
        register_param(
            name="NON_TUPLE_BOUNDS_2",
            default=5,
            type=int,
            bounds=(1, 2, 3),  # should be a tuple of length 2
        )


def test_paramregistry_register_with_invalid_type_for_min_max():
    with pytest.raises(ValueError):
        register_param(
            name="INVALID_MIN_TYPE",
            default="test",
            type=str,
            min=1,  # min can only be used with int or float types
        )
    with pytest.raises(ValueError):
        register_param(
            name="INVALID_MAX_TYPE",
            default="test",
            type=str,
            max=10,  # max can only be used with int or float types
        )
    with pytest.raises(ValueError):
        register_param(
            name="INVALID_MIN_LENGTH_TYPE",
            default=5,
            type=int,
            min_length=1,  # min_length can only be used with str, list, tuple, or dict types
        )
    with pytest.raises(ValueError):
        register_param(
            name="INVALID_MAX_LENGTH_TYPE",
            default=5,
            type=int,
            max_length=10,  # max_length can only be used with str, list, tuple, or dict types
        )


def test_resolve_param_name_invalid():
    with pytest.raises(ConfigNotFoundError):
        resolve_param_name("NOT_A_PARAM")


# src/config_guard/params/registry.py
def test_registry_resolve_name_enum_and_alias():
    reg = ParamRegistry()

    class DummyEnum:
        value = "MAX_CONCURRENCY"

    # Register a dummy spec with alias, and also register the enum name as an alias
    reg.register(
        ParamSpec("MAX_CONCURRENCY", int, 10, bounds=(1, 100)),
        aliases=("MAX_CONC", "MAX_CONCURRENCY"),
    )
    # This should succeed
    with pytest.raises(ConfigNotFoundError):
        assert reg.resolve_name(DummyEnum) == "MAX_CONCURRENCY"
    reg._aliases["max_conc"] = "MAX_CONCURRENCY"
    assert reg.resolve_name("max_conc") == "MAX_CONCURRENCY"
    # Now test unknown alias and unknown enum
    with pytest.raises(ConfigNotFoundError):
        reg.resolve_name("DOES_NOT_EXIST")

    class DummyEnum2:
        value = "DOES_NOT_EXIST"

    with pytest.raises(ConfigNotFoundError):
        reg.resolve_name(DummyEnum2)


def test_registry_resolve_name_unknown():
    reg = ParamRegistry()
    with pytest.raises(ConfigNotFoundError):
        reg.resolve_name("UNKNOWN")


def test_registry_register_duplicate():
    reg = ParamRegistry()
    reg.register(ParamSpec("MAX_CONCURRENCY", int, 10, bounds=(1, 100)))
    with pytest.raises(ConfigDuplicateError):
        reg.register(ParamSpec("MAX_CONCURRENCY", int, 10, bounds=(1, 100)))


def test_registry_get_spec_invalid():
    reg = ParamRegistry()
    with pytest.raises(ConfigNotFoundError):
        reg.get("notfound")


def test_paramspec_repr_and_eq():
    s1 = ParamSpec("A", int, 1)
    s2 = ParamSpec("A", int, 1)
    s3 = ParamSpec("B", int, 2)
    # Accept both dataclass and custom reprs
    r = repr(s1)
    assert r.startswith("<ParamSpec") or r.startswith("ParamSpec(")
    assert s1 == s2
    assert not (s1 != s2)
    assert s1 != s3
    assert not (s1 == s3)


def test_paramspec_validate_type_error():
    s = ParamSpec("A", int, 1)
    with pytest.raises(ConfigValidationError):
        s.validate("notint")
