import os
from typing import Optional

import fsspec

from engine.storage.task_step_store.keyval_task_step_store import KVTaskStepStore
from engine.storage.task_step_store.types import (
    DEFAULT_PERSIST_DIR, DEFAULT_PERSIST_FNAME, DEFAULT_PERSIST_PATH
)
from engine.storage.kvstore.simple_kvstore import SimpleKVStore
from engine.storage.kvstore.types import BaseInMemoryKVStore
from engine.utils import concat_dirs


class SimpleTaskStepStore(KVTaskStepStore):
    """Simple TaskStep (Node) store.

    An in-memory store for TaskStep and Node objects.

    Args:
        simple_kvstore (SimpleKVStore): simple key-value store
        namespace (str): namespace for the task_step_store

    """

    def __init__(
        self,
        simple_kvstore: Optional[SimpleKVStore] = None,  
        namespace: Optional[str] = None,
    ) -> None:
        """Init a SimpleTaskStepStore."""
        simple_kvstore = simple_kvstore or SimpleKVStore()  # 默认内存存储
        super().__init__(simple_kvstore, namespace)

    @classmethod
    def from_persist_dir(
        cls,
        persist_dir: str = DEFAULT_PERSIST_DIR,
        namespace: Optional[str] = None,
        fs: Optional[fsspec.AbstractFileSystem] = None,
    ) -> "SimpleTaskStepStore":
        """Create a SimpleTaskStepStore from a persist directory.

        Args:
            persist_dir (str): directory to persist the store
            namespace (Optional[str]): namespace for the task_step_store
            fs (Optional[fsspec.AbstractFileSystem]): filesystem to use

        """
        # 构建完整路径：./storage/task_step_store.json
        if fs is not None:
            persist_path = concat_dirs(persist_dir, DEFAULT_PERSIST_FNAME)
        else:
            persist_path = os.path.join(persist_dir, DEFAULT_PERSIST_FNAME)
        return cls.from_persist_path(persist_path, namespace=namespace, fs=fs)

    @classmethod
    def from_persist_path(
        cls,
        persist_path: str,
        namespace: Optional[str] = None,
        fs: Optional[fsspec.AbstractFileSystem] = None,
    ) -> "SimpleTaskStepStore":
        """Create a SimpleTaskStepStore from a persist path.

        Args:
            persist_path (str): Path to persist the store
            namespace (Optional[str]): namespace for the task_step_store
            fs (Optional[fsspec.AbstractFileSystem]): filesystem to use

        """
        # 从磁盘加载KV存储
        simple_kvstore = SimpleKVStore.from_persist_path(persist_path, fs=fs)
        return cls(simple_kvstore, namespace)

    def persist(
        self,
        persist_path: str = DEFAULT_PERSIST_PATH,
        fs: Optional[fsspec.AbstractFileSystem] = None,
    ) -> None:
        """Persist the store."""
        # 只持久化内存型存储（BaseInMemoryKVStore的子类）
        if isinstance(self._kvstore, BaseInMemoryKVStore):
            self._kvstore.persist(persist_path, fs=fs)

    @classmethod
    def from_dict(
        cls, save_dict: dict, namespace: Optional[str] = None
    ) -> "SimpleTaskStepStore":
        simple_kvstore = SimpleKVStore.from_dict(save_dict)  # 字典转存储
        return cls(simple_kvstore, namespace)

    def to_dict(self) -> dict:
        assert isinstance(self._kvstore, SimpleKVStore)  # 存储转字典
        return self._kvstore.to_dict()


# alias for backwards compatibility
TaskStepStore = SimpleTaskStepStore
