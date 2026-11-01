from __future__ import annotations

import heapq
import typing as tp

T = tp.TypeVar("T")


class MinHeap(tp.Generic[T]):
    """Мин-куча. Если ключи элементов меняются снаружи, вызывайте heapify()."""

    def __init__(self) -> None:
        self._data: tp.List[T] = []

    def __len__(self) -> int:
        return len(self._data)

    def push(self, val: T) -> None:
        heapq.heappush(self._data, val)

    def pop(self) -> T:
        if not self._data:
            raise IndexError("pop из пустой MinHeap")
        return heapq.heappop(self._data)

    def top(self) -> T:
        if not self._data:
            raise IndexError("top пустой MinHeap")
        return self._data[0]

    def heapify(self) -> None:
        """Восстановить инвариант после изменения ключей элементов, за O(n)."""
        heapq.heapify(self._data)