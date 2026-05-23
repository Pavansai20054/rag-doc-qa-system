from collections import OrderedDict
from typing import Any


class LRUCache:
    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._store.move_to_end(key)
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
