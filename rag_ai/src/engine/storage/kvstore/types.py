from abc import ABC, abstractmethod
from typing import Dict, Optional
import fsspec

DEFAULT_COLLECTION = "data"

# BaseKVStore是一个抽象基类（其实就是它本身啥也不是，但是继承它的那些子类都必须实现它规定的这些pass的方法，那这些子类就有统一接口的格式）
class BaseKVStore(ABC):
    """Base key-value store."""

    @abstractmethod
    def put(self, key: str, val: dict, collection: str = DEFAULT_COLLECTION) -> None:
        pass

    @abstractmethod
    def get(self, key: str, collection: str = DEFAULT_COLLECTION) -> Optional[dict]:
        pass

    @abstractmethod
    def get_all(self, collection: str = DEFAULT_COLLECTION) -> Dict[str, dict]:
        pass

    @abstractmethod
    def delete(self, key: str, collection: str = DEFAULT_COLLECTION) -> bool:
        pass


class BaseInMemoryKVStore(BaseKVStore):
    """Base in-memory key-value store."""

    @abstractmethod
    def persist(
        self, persist_path: str, fs: Optional[fsspec.AbstractFileSystem] = None
    ) -> None:
        pass

    @classmethod
    @abstractmethod
    def from_persist_path(cls, persist_path: str) -> "BaseInMemoryKVStore":
        """Create a BaseInMemoryKVStore from a persist directory."""
