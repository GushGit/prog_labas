import pytest

from heap import MinHeap


class Item:
    """Элемент с изменяемым ключом (как клетка с меняющимся числом заметок)."""

    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        return self.v < other.v


def test_len_and_push():
    h = MinHeap()
    assert len(h) == 0
    h.push(3)
    h.push(1)
    assert len(h) == 2


def test_pop_order():
    h = MinHeap()
    for v in (5, 1, 3):
        h.push(v)
    assert [h.pop(), h.pop(), h.pop()] == [1, 3, 5]
    assert len(h) == 0


def test_top_does_not_remove():  # дефект H1: top без self
    h = MinHeap()
    h.push(4)
    h.push(2)
    assert h.top() == 2
    assert len(h) == 2


def test_empty_heap_raises():
    h = MinHeap()
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(IndexError):
        h.top()


def test_heapify_restores_invariant_after_key_change():  # дефект H2
    a, b, c = Item(1), Item(5), Item(3)
    h = MinHeap()
    for item in (a, b, c):
        h.push(item)
    a.v = 10  # ключ изменился снаружи
    assert h.top() is a  # куча устарела: настоящий минимум c
    h.heapify()
    assert h.top() is c
    assert [h.pop().v for _ in range(3)] == [3, 5, 10]