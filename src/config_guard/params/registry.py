from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, Iterable, Tuple, Union

from config_guard.exceptions import ConfigDuplicateError, ConfigNotFoundError, ConfigValidationError

from .spec import ParamSpec

logger = logging.getLogger("config_guard.params")
logger.addHandler(logging.NullHandler())


class ParamRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ParamSpec] = {}
        self._aliases: Dict[str, str] = {}
        logger.debug(
            "ParamRegistry initialized id=%s specs=%d aliases=%d",
            hex(id(self)),
            len(self._specs),
            len(self._aliases),
        )

    @staticmethod
    def _canon(name: str) -> str:
        return name.strip().upper()

    def register(
        self, spec: ParamSpec, aliases: Iterable[str] = (), override: bool = False
    ) -> None:
        key = self._canon(spec.name)
        logger.debug(
            "Register called: name=%r canon=%r override=%s aliases=%r",
            spec.name,
            key,
            override,
            tuple(aliases),
        )
        if not override and key in self._specs:
            logger.error("Register failed: %r already registered", key)
            raise ConfigDuplicateError({spec.name: "Parameter already registered."})
        existed = key in self._specs
        self._specs[key] = spec
        if existed and override:
            logger.debug("Spec overridden for %r", key)
        self._register_aliases(aliases, key, override)
        logger.debug(
            "Register complete: specs=%d aliases=%d keys(sample)=%r",
            len(self._specs),
            len(self._aliases),
            tuple(list(self._specs.keys())[:5]),
        )

    def _register_aliases(self, aliases: Iterable[str], key: str, override: bool) -> None:
        for a in aliases:
            ak = self._canon(a)
            if not override and ak in self._aliases and self._aliases[ak] != key:
                logger.error("Alias conflict: %r already points to %r", ak, self._aliases[ak])
                raise ConfigValidationError({a: f"Alias already used for {self._aliases[ak]}."})
            self._aliases[ak] = key
            logger.debug("Alias set: %r -> %r", ak, key)

    def has(self, name_or_alias: Union[str, Enum]) -> bool:
        try:
            resolved = self._resolve_key(name_or_alias)
            logger.debug("Has(%r) -> True (resolved=%r)", name_or_alias, resolved)
            return True
        except ConfigValidationError:
            logger.debug("Has(%r) -> False", name_or_alias)
            return False

    def get(self, name_or_alias: Union[str, Enum]) -> ParamSpec:
        key = self._resolve_key(name_or_alias)
        spec = self._specs[key]
        logger.debug("Get(%r) -> key=%r spec_id=%s", name_or_alias, key, hex(id(spec)))
        return spec

    def resolve_name(self, name_or_alias: Union[str, Enum]) -> str:
        key = self._resolve_key(name_or_alias)
        logger.debug("Resolve_name(%r) -> %r", name_or_alias, key)
        return key

    def _resolve_key(self, name_or_alias: Union[str, Enum]) -> str:
        # Detailed resolution logs
        logger.debug(
            "Resolving key for: %r (%s) | specs=%d aliases=%d",
            getattr(name_or_alias, "value", name_or_alias),
            type(name_or_alias),
            len(self._specs),
            len(self._aliases),
        )
        if _is_enum(name_or_alias):
            enum_val = getattr(name_or_alias, "value", None)
            if not isinstance(enum_val, str):
                logger.error("Enum value not a string: %r -> %r", name_or_alias, enum_val)
                raise ConfigValidationError({str(name_or_alias): "Enum value must be a string."})
            canon = self._canon(enum_val)
            in_specs = canon in self._specs
            in_aliases = canon in self._aliases
            logger.debug("Enum: canon=%r in_specs=%s in_aliases=%s", canon, in_specs, in_aliases)
            if in_specs:
                return canon
            if in_aliases:
                return self._aliases[canon]
        elif isinstance(name_or_alias, str):
            k = self._canon(name_or_alias)
            in_specs = k in self._specs
            in_aliases = k in self._aliases
            logger.debug("String: canon=%r in_specs=%s in_aliases=%s", k, in_specs, in_aliases)
            if in_specs:
                return k
            if in_aliases:
                return self._aliases[k]
        # Miss path
        all_keys_sample = tuple(list(self._specs.keys())[:10])
        alias_sample = tuple(list(self._aliases.items())[:10])
        key_str = str(getattr(name_or_alias, "value", name_or_alias))
        logger.error(
            "Unknown config param: %r | specs=%d aliases=%d | specs(sample)=%r aliases(sample)=%r",
            key_str,
            len(self._specs),
            len(self._aliases),
            all_keys_sample,
            alias_sample,
        )
        raise ConfigNotFoundError({str(self._canon(key_str)): "Unknown configuration parameter."})

    def all_names(self) -> Tuple[str, ...]:
        names = tuple(sorted(self._specs.keys()))
        logger.debug("All_names() -> %d keys", len(names))
        return names

    def clear(self) -> None:
        logger.debug("Clearing registry: specs=%d aliases=%d", len(self._specs), len(self._aliases))
        self._specs.clear()
        self._aliases.clear()
        logger.debug("Registry cleared.")


def _is_enum(x: object) -> bool:
    try:
        return isinstance(x, Enum)
    except Exception:
        return False
