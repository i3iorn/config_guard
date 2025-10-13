from __future__ import annotations

from typing import Dict


class ConfigError(Exception):
    """Base config exception."""


class ConfigValidationError(ConfigError):
    """Raised when validation fails for one or more parameters."""

    def __init__(
        self, errors: Dict[str, str], key: str | None = None, value: object | None = None
    ) -> None:
        self.errors = errors
        self.key = key
        self.value = value
        msg = f"Validation errors: {errors}"
        if key is not None and value is not None:
            msg += f" (key: {key}, value: {value})"
        super().__init__(msg)


class ConfigLockedError(ConfigError):
    """Raised when attempting mutation while config is locked."""


class ConfigBypassError(ConfigError):
    """Raised when bypass is attempted without required environment approval."""


class ConfigTornDownError(ConfigError):
    """Raised if operations are attempted after teardown."""


class ConfigNotFoundError(ConfigError):
    """Raised when a requested configuration parameter is not found."""


class ConfigDuplicateError(ConfigError):
    """Raised when attempting to register a duplicate configuration parameter."""
