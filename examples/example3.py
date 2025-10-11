import os

from config_guard import AppConfig, list_params, register_param
from config_guard.exceptions import ConfigLockedError

cfg = AppConfig()
register_param(
    "verify",
    type=bool,
    default=True,
    description="Whether to verify SSL certificates",
)

print(list_params())

cfg.lock()
try:
    cfg.update(**{"verify": False})
except ConfigLockedError:
    print("Update blocked while locked")

# Allow bypassed updates
os.environ["ALLOW_CONFIG_BYPASS"] = "1"
cfg.update(_bypass=True, reason="hotfix", **{"verify": False})

print("Updated with bypass:", cfg.get("verify"))
cfg.unlock()
