# ConfigGuard
ConfigGuard is a Python library designed to help developers manage and validate configuration settings securely and reliably. It sacrifices some speed and convenience for enhanced safety and robustness, making it ideal for applications where configuration integrity is critical.

## Features
- **Type Safety**: Ensures that configuration values are of the expected type.
- **Validation**: Provides built-in validation for common configuration types (e.g., URLs, email addresses, file paths).
- **Default Values**: Supports default values for missing configuration settings.
- **Environment Variable Support**: Easily load configuration from environment variables.
- **Immutable Configurations**: Once loaded, configurations cannot be modified, preventing accidental changes.


## Installation
TBD

## Usage
```python
from configguard import ConfigGuard, ConfigError
from configguard.validators import is_url, is_email
import os
# Define your configuration schema
schema = {
    "DATABASE_URL": is_url,
    "ADMIN_EMAIL": is_email,
    "DEBUG_MODE": bool,
    "MAX_CONNECTIONS": int,
}

# Load configuration from environment variables
config = {key: os.getenv(key) for key in schema.keys()}
# Initialize ConfigGuard
try:
    config_guard = ConfigGuard(config, schema)
    print("Configuration loaded successfully!")
    print("Database URL:", config_guard.get("DATABASE_URL"))
except ConfigError as e:
    print("Configuration error:", e)
```

## Documentation
For detailed documentation, please visit the [ConfigGuard Documentation](#).

## Contributing
Contributions are welcome! Please read the [CONTRIBUTING.md](#) for guidelines.

## License
This project is licensed under the MIT License. See the [LICENSE](#) file for details.
