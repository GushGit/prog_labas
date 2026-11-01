import heapq
import typing as tp

T = tp.TypeVar('T')

class MinHeap(tp.Generic[T]):
    def __init__(self) -> None:
        self._data: tp.List[T] = []
    
    def __len__(self) -> int:
        return len(self._data)

    def push(self, val: T) -> None:
        heapq.heappush(self._data, val)
    
    def pop(self) -> T:
        return heapq.heappop(self._data)
    
    def top(self) -> T:
        return _data[0]