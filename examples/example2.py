from src.config_guard import AppConfig

cfg = AppConfig()  # singleton; returns existing instance

# Set a one-time value
cfg.use_once(reason="temp override", **{"verify": False})

print("First read (uses one-time):", cfg.get("verify"))
print("Second read (falls back to permanent):", cfg.get("verify"))
