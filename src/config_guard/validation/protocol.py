from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ValidatorProtocol(Protocol):
    def __call__(self, value: Any) -> None:  # raise ConfigValidationError on failure
        ...
