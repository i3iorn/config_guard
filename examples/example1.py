from src.config_guard import AppConfig
from src.config_guard.exceptions import ConfigValidationError

cfg = AppConfig()  # uses defaults

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
