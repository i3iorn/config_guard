from typing import Any, Dict, Protocol

from typing_extensions import runtime_checkable


@runtime_checkable
class PersistanceAdapterProtocol(Protocol):
    def save(self, config: Dict[str, Any]) -> None: ...

    def load(self) -> Dict[str, Any]: ...
