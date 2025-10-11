from __future__ import annotations

import ipaddress
import ssl
from enum import Enum
from typing import Any, Dict, List, Union

from config_guard.exceptions import ConfigValidationError


def default_private_cidrs() -> List[str]:
    return [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "::1/128",
        "fc00::/7",
    ]


def _validate_ip_list(v: list[str] | tuple[str, ...]) -> bool:
    if v is None or not isinstance(v, (list, tuple)):
        return False
    try:
        for cidr in v:
            ipaddress.ip_network(cidr)
        return True
    except Exception:
        return False


def _validate_ports(v: list[int] | tuple[int, ...]) -> bool:
    if v is None or not isinstance(v, (list, tuple)):
        return False
    try:
        return all(isinstance(p, int) and 0 < p < 65536 for p in v)
    except Exception:
        return False


def _validate_schemes(v: list[str] | tuple[str, ...]) -> bool:
    if v is None or not isinstance(v, (list, tuple)):
        return False
    try:
        return all(isinstance(s, str) and s.lower() in ("http", "https") for s in v)
    except Exception:
        return False


def _validate_patterns(v: list[str] | tuple[str, ...]) -> bool:
    if v is None or not isinstance(v, (list, tuple)):
        return False
    try:
        return all(isinstance(x, str) and len(x) > 0 for x in v)
    except Exception:
        return False


# -------------------------
# Config Enum
# -------------------------
class ConfigParam(Enum):
    ALLOWED_SCHEMES = "ALLOWED_SCHEMES"
    ALLOWED_HOSTS = "ALLOWED_HOSTS"
    DENYLIST_CIDRS = "DENYLIST_CIDRS"
    ALLOW_PRIVATE_IPS = "ALLOW_PRIVATE_IPS"
    BLOCK_LOCALHOST = "BLOCK_LOCALHOST"
    ALLOWED_PORTS = "ALLOWED_PORTS"
    MAX_CONCURRENCY = "MAX_CONCURRENCY"
    PER_HOST_CONCURRENCY = "PER_HOST_CONCURRENCY"
    MAX_RESPONSE_SIZE = "MAX_RESPONSE_SIZE"
    MAX_REQUEST_SIZE = "MAX_REQUEST_SIZE"
    MAX_HEADERS = "MAX_HEADERS"
    MAX_HEADER_SIZE = "MAX_HEADER_SIZE"
    DEFAULT_TIMEOUTS = "DEFAULT_TIMEOUTS"
    REDIRECT_LIMIT = "REDIRECT_LIMIT"
    VERIFY = "VERIFY"
    SSL_CONTEXT = "SSL_CONTEXT"
    TLS_MIN_VERSION = "TLS_MIN_VERSION"
    CERTIFICATE_PINS = "CERTIFICATE_PINS"
    OCSP_CHECK = "OCSP_CHECK"
    RETRIES = "RETRIES"
    CIRCUIT_BREAKER_THRESHOLD = "CIRCUIT_BREAKER_THRESHOLD"
    CIRCUIT_BREAKER_BACKOFF_SECONDS = "CIRCUIT_BREAKER_BACKOFF_SECONDS"
    HOOK_TIMEOUT = "HOOK_TIMEOUT"
    SENSITIVE_HEADER_PATTERNS = "SENSITIVE_HEADER_PATTERNS"
    TELEMETRY_ENABLED = "TELEMETRY_ENABLED"
    AUDIT_LOG_PATH = "AUDIT_LOG_PATH"
    BYPASS_REASON = "BYPASS_REASON"
    BYPASS_TOKEN = "BYPASS_TOKEN"
    ALLOW_UNBOUNDED_REDIRECTS = "ALLOW_UNBOUNDED_REDIRECTS"
    ALLOW_CROSS_HOST_AUTH = "ALLOW_CROSS_HOST_AUTH"
    ALLOW_DNS_REBIND = "ALLOW_DNS_REBIND"
    IDEMPOTENCY_KEY = "IDEMPOTENCY_KEY"

    @classmethod
    def resolve(cls, key: Union[ConfigParam, str]) -> ConfigParam:
        """
        Resolve a key (ConfigParam or str) to a ConfigParam, case-insensitively.
        Accepts enum, exact string, or case-insensitive string match.
        """
        if isinstance(key, ConfigParam):
            return key

        elif isinstance(key, str):
            key_clean = key.strip()
            # Try direct match
            try:
                return ConfigParam(key_clean)
            except ValueError:
                pass
            # Try case-insensitive match
            for param in ConfigParam:
                if (
                    param.value.lower() == key_clean.lower()
                    or param.name.lower() == key_clean.lower()
                ):
                    return param
            raise ConfigValidationError({key: "Invalid configuration parameter name."})
        else:
            raise ConfigValidationError(
                {str(key): f"Key must be a ConfigParam or string. Not {type(key)}."}
            )


# -------------------------
# Config Specs
# -------------------------
CONFIG_SPECS: Dict[ConfigParam, Dict[str, Any]] = {
    ConfigParam.ALLOWED_SCHEMES: {
        "default": ["https", "http"],
        "type": (list, tuple),
        "validator": _validate_schemes,
    },
    ConfigParam.ALLOWED_HOSTS: {
        "default": None,
        "type": (list, type(None)),
        "validator": lambda v: all(isinstance(x, str) for x in v) if v else True,
    },
    ConfigParam.DENYLIST_CIDRS: {
        "default": default_private_cidrs(),
        "type": (list, tuple),
        "validator": _validate_ip_list,
    },
    ConfigParam.ALLOW_PRIVATE_IPS: {"default": False, "type": bool},
    ConfigParam.BLOCK_LOCALHOST: {"default": True, "type": bool},
    ConfigParam.ALLOWED_PORTS: {
        "default": [80, 443],
        "type": (list, tuple),
        "validator": _validate_ports,
    },
    ConfigParam.MAX_CONCURRENCY: {"default": 10, "type": int, "bounds": (1, 1000)},
    ConfigParam.PER_HOST_CONCURRENCY: {"default": 2, "type": int, "bounds": (1, 100)},
    ConfigParam.MAX_RESPONSE_SIZE: {
        "default": 10_000_000,
        "type": int,
        "bounds": (1_000, 1_000_000_000),
    },
    ConfigParam.MAX_REQUEST_SIZE: {
        "default": 50_000_000,
        "type": int,
        "bounds": (1_000, 1_000_000_000),
    },
    ConfigParam.MAX_HEADERS: {"default": 100, "type": int, "bounds": (1, 1000)},
    ConfigParam.MAX_HEADER_SIZE: {"default": 8192, "type": int, "bounds": (256, 65536)},
    ConfigParam.DEFAULT_TIMEOUTS: {
        "default": (5.0, 10.0),
        "type": tuple,
        "validator": lambda v: v is not None
        and len(v) == 2
        and all(isinstance(x, (int, float)) for x in v),
    },
    ConfigParam.REDIRECT_LIMIT: {"default": 3, "type": int, "bounds": (0, 20)},
    ConfigParam.VERIFY: {"default": True, "type": bool},
    ConfigParam.SSL_CONTEXT: {"default": None, "type": (ssl.SSLContext, type(None))},
    ConfigParam.TLS_MIN_VERSION: {
        "default": "TLSv1.2",
        "type": str,
        "validator": lambda v: v in ["TLSv1.2", "TLSv1.3"],
    },
    ConfigParam.CERTIFICATE_PINS: {"default": None, "type": (dict, type(None))},
    ConfigParam.OCSP_CHECK: {"default": False, "type": bool},
    ConfigParam.RETRIES: {"default": 3, "type": int, "bounds": (0, 10)},
    ConfigParam.CIRCUIT_BREAKER_THRESHOLD: {"default": 5, "type": int, "bounds": (1, 100)},
    ConfigParam.CIRCUIT_BREAKER_BACKOFF_SECONDS: {"default": 60, "type": int, "bounds": (1, 3600)},
    ConfigParam.HOOK_TIMEOUT: {"default": 2.0, "type": (int, float), "bounds": (0.1, 60.0)},
    ConfigParam.SENSITIVE_HEADER_PATTERNS: {
        "default": [
            "authorization",
            "cookie",
            "set-cookie",
            "proxy-authorization",
            "x-api-key",
            "x-amz-",
        ],
        "type": (list, tuple),
        "validator": _validate_patterns,
    },
    ConfigParam.TELEMETRY_ENABLED: {"default": False, "type": bool},
    ConfigParam.AUDIT_LOG_PATH: {
        "default": "<application-default-path>",
        "type": (str, type(None)),
    },
    ConfigParam.BYPASS_REASON: {"default": None, "type": (str, type(None))},
    ConfigParam.BYPASS_TOKEN: {"default": None, "type": (str, type(None))},
    ConfigParam.ALLOW_UNBOUNDED_REDIRECTS: {"default": False, "type": bool},
    ConfigParam.ALLOW_CROSS_HOST_AUTH: {"default": False, "type": bool},
    ConfigParam.ALLOW_DNS_REBIND: {"default": False, "type": bool},
    ConfigParam.IDEMPOTENCY_KEY: {"default": None, "type": (str, type(None))},
}
