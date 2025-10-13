from typing import Protocol

from typing_extensions import runtime_checkable


@runtime_checkable
class PersistanceAdapterProtocol(Protocol):
    def save(self, config: dict) -> None: ...

    def load(self) -> dict: ...
