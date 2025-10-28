# python
import pytest

from config_guard.params import REGISTRY, register_param


@pytest.fixture(autouse=True)
def seed_registry():
    REGISTRY.clear()
    register_param(
        name="MAX_CONCURRENCY",
        default=10,
        value_type=int,
        bounds=(1, 1000),
        description="Max concurrent operations",
        aliases=("max_concurrency",),
        override=True,
    )
    register_param(
        name="ALLOWED_SCHEMES",
        default=["https", "http"],
        value_type=(list, tuple),
        validator=lambda v: isinstance(v, (list, tuple)) and all(x in ("http", "https") for x in v),
        description="Allowed URL schemes",
        aliases=("allowed_schemes",),
        override=True,
    )
    register_param(
        name="VERIFY",
        default=True,
        value_type=bool,
        description="Whether to verify TLS",
        aliases=("verify",),
        override=True,
    )
    yield
    REGISTRY.clear()
