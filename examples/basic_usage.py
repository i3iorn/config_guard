# python
import logging

from config_guard import AppConfig, get_param_spec, register_param, resolve_param_name

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    register_param(
        name="REQUEST_TIMEOUT",
        default=5.0,
        value_type=(int, float),
        bounds=(0.1, 60.0),
        description="Default request timeout in seconds",
        aliases=("request_timeout",),
        require_reason=True,
    )

    config = AppConfig()
    param = resolve_param_name("request_timeout")
    print("Default:", get_param_spec(param).default)
    config.update(**{param: 10.0}, reason="Increase timeout for slow API")
    print("Updated:", config.get(param))
    print("Last reason:", config.last_change)
