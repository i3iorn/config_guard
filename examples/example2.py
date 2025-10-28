from config_guard import AppConfig, register_param

if __name__ == "__main__":
    cfg = AppConfig()  # singleton; returns existing instance
    register_param("verify", value_type=bool, default=True, description="Enable verification")

    # Set a one-time value
    cfg.use_once(reason="temp override", **{"verify": False})

    print("First read (uses one-time):", cfg.get("verify"))
    print("Second read (falls back to permanent):", cfg.get("verify"))
