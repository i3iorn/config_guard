import os
from src.config_guard import AppConfig
from src.config_guard.exceptions import ConfigLockedError

cfg = AppConfig()

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
