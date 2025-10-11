from config_guard import AppConfig, register_param
from config_guard.exceptions import ConfigValidationError

if __name__ == "__main__":
    cfg = AppConfig()
    register_param(
        "your_param_name",
        default=42,
        type=int,
        bounds=(0, 1000),
        description="An example integer parameter",
    )

    def on_change(snapshot):
        print("Config changed. Keys:", list(snapshot.keys()))

    cfg.register_post_update_hook(on_change)

    try:
        cfg.update(reason="enable feature", **{"your_param_name": 123})
    except ConfigValidationError as exc:
        print("Validation errors:", exc.errors)

    try:
        print("Current value:", cfg.get("your_param_name", default=None))
    except ConfigValidationError as exc:
        print("Error getting value:", exc.errors)

    print("Public snapshot:", dict(cfg.snapshot()))
    print("Integrity OK:", cfg.verify_integrity())
