"""Bounded TTL cache for repeat model requests."""

import copy
import time
from collections import OrderedDict
from threading import Lock


class TTLCache:
    def __init__(self, ttl_seconds: int = 900, max_entries: int = 256):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._items: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            expires, value = item
            if expires <= time.monotonic():
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return copy.deepcopy(value)

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + self.ttl_seconds, copy.deepcopy(value))
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)
