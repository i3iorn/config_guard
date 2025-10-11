from config_guard.params import (
    CONFIG_SPECS,
    ConfigParam,
    _validate_ip_list,
    _validate_patterns,
    _validate_ports,
    _validate_schemes,
)


def test_config_param_enum():
    assert all(isinstance(p.value, str) for p in ConfigParam)


def test_config_specs():
    for param in ConfigParam:
        assert param in CONFIG_SPECS
        assert "type" in CONFIG_SPECS[param]


def test_validate_ip_list_success():
    assert _validate_ip_list(["10.0.0.0/8", "192.168.0.0/16"])
    assert _validate_ip_list(("10.0.0.0/8",))


def test_validate_ip_list_error():
    assert not _validate_ip_list(["not_a_cidr"])
    assert not _validate_ip_list(None)


def test_validate_ports_success():
    assert _validate_ports([80, 443])
    assert _validate_ports((8080,))


def test_validate_ports_error():
    assert not _validate_ports([70000])
    assert not _validate_ports(None)


def test_validate_schemes_success():
    assert _validate_schemes(["http", "https"])
    assert _validate_schemes(("http",))


def test_validate_schemes_error():
    assert not _validate_schemes(["ftp"])
    assert not _validate_schemes(None)


def test_validate_patterns_success():
    assert _validate_patterns(["foo", "bar"])
    assert _validate_patterns(("baz",))


def test_validate_patterns_error():
    assert not _validate_patterns([""])
    assert not _validate_patterns(None)
