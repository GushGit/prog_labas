from __future__ import annotations

import typing as tp

from region_key import RegionKey
from utils import get_digit_flag

PEN_FLAG = 1
NOTES_MASK = get_digit_flag(10) - 2  # 0b1111111110: биты цифр 1..9
DEFAULT_STATE = NOTES_MASK


def is_pen(state: int) -> bool:
    """Клетка содержит поставленную цифру (флаг pen)."""
    return bool(state & PEN_FLAG)


def count_notes(state: int) -> int:
    """Число заметок; для pen-клетки 0 (её цифра лежит в тех же битах)."""
    if state & PEN_FLAG:
        return 0
    return (state & NOTES_MASK).bit_count()


def notes_of(state: int) -> tp.List[int]:
    """Цифры-заметки по возрастанию. Для pen-клетки ValueError."""
    if state & PEN_FLAG:
        raise ValueError("Requested notes from a pen-digit Cell")
    return [d for d in range(1, 10) if state & (1 << d)]


def pen_digit(state: int) -> int:
    """Поставленная цифра pen-клетки; 0, если клетка не pen или цифры нет."""
    if not state & PEN_FLAG:
        return 0
    digits = state & NOTES_MASK
    return digits.bit_length() - 1 if digits else 0


def make_pen(digit: int) -> int:
    """Состояние pen-клетки с цифрой digit (1..9)."""
    if not 1 <= digit <= 9:
        raise ValueError("Цифра должна быть от 1 до 9")
    return PEN_FLAG | (1 << digit)


class Cell:
    """Неизменяемый снимок клетки: позиция (row, col) и состояние-int.

    Методы-«мутаторы» возвращают новую клетку. Горячий путь решателя работает
    с int-состояниями напрямую (см. функции выше), а не с объектами Cell.
    """

    __slots__ = ("_pos", "_state")
    DEFAULT_STATE: int = DEFAULT_STATE

    def __init__(self, pos: tp.Tuple[int, int], state: int = DEFAULT_STATE) -> None:
        self._pos = pos
        self._state = state

    @property
    def pos(self) -> tp.Tuple[int, int]:
        return self._pos

    @property
    def state(self) -> int:
        return self._state

    @property
    def idx(self) -> int:
        """Плоский индекс row*9 + col."""
        return self._pos[0] * 9 + self._pos[1]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cell):
            return NotImplemented
        return self._state == other._state and self._pos == other._pos

    def __hash__(self) -> int:
        return hash((self._pos, self._state))

    def __lt__(self, other: Cell) -> bool:
        if not isinstance(other, Cell):
            return NotImplemented
        return (count_notes(self._state), self._pos) < (count_notes(other._state), other._pos)

    def __repr__(self) -> str:
        return f"Cell(pos={self._pos}, state={self._state:#b})"

    def __and__(self, other: Cell) -> int:
        return self._state & other._state

    def __xor__(self, other: Cell) -> int:
        return self._state ^ other._state

    def __or__(self, other: Cell) -> int:
        return self._state | other._state

    def __getitem__(self, key: RegionKey) -> int:
        """Номер региона данного вида (строка, столбец или блок), в котором лежит клетка."""
        match key:
            case RegionKey.ROW:
                return self._pos[0]
            case RegionKey.COL:
                return self._pos[1]
            case RegionKey.BOX:
                return (self._pos[0] // 3 * 3) + (self._pos[1] // 3)
            case _:
                raise KeyError("Unexpected RegionKey")

    def __floordiv__(self, other: Cell) -> bool:
        """Коллинеарность: общая строка или общий столбец."""
        return (
            self[RegionKey.ROW] == other[RegionKey.ROW]
            or self[RegionKey.COL] == other[RegionKey.COL]
        )

    def __truediv__(self, other: Cell) -> bool:
        """Принадлежность одному региону: строка, столбец или блок."""
        return self // other or self[RegionKey.BOX] == other[RegionKey.BOX]

    def is_pen(self) -> bool:
        return is_pen(self._state)

    def pen_digit(self) -> int:
        return pen_digit(self._state)

    def count_notes(self) -> int:
        return count_notes(self._state)

    def get_notes(self) -> tp.List[int]:
        return notes_of(self._state)

    def clear_notes(self) -> Cell:
        """Клетка без заметок (противоречие). Pen-клетка возвращается как есть."""
        if is_pen(self._state):
            return self
        return Cell(self._pos, 0)

    def read_state(self, digit: int) -> bool:
        """Бит состояния по цифре; digit = 0 читает флаг pen."""
        if not 0 <= digit <= 9:
            raise ValueError("Цифра должна быть от 0 до 9")
        return bool(self._state & get_digit_flag(digit))

    def write_state(self, digit: int, mark_mode: bool = False) -> Cell:
        """Новая клетка: mark_mode=True ставит цифру (pen), иначе переворачивает заметку."""
        if not 1 <= digit <= 9:
            raise ValueError("Цифра должна быть от 1 до 9")
        if mark_mode:
            return Cell(self._pos, make_pen(digit))
        if is_pen(self._state):
            raise ValueError("Нельзя менять заметки pen-клетки")
        return Cell(self._pos, self._state ^ get_digit_flag(digit))