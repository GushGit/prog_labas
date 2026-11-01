from __future__ import annotations

import typing as tp

from cell import DEFAULT_STATE, NOTES_MASK, PEN_FLAG, Cell, make_pen, pen_digit
from region import ALL_CELLS, CELL_REGIONS, DIRTY_BITS, PEER_MASK, REGIONS
from utils import iter_bits
from zobrist import ZOBRIST, hash_delta, hash_state

Grid = tp.List[tp.List[str]]
Pos = tp.Tuple[int, int]

REGION_MASKS = tuple(r.mask for r in REGIONS)
DIGIT_CHARS = frozenset("123456789")
ALL_DIRTY = (1 << 27) - 1
_INITIAL_HASH = hash_state([DEFAULT_STATE] * 81)


class Board:
    """Доска на плоских int-структурах (индекс клетки idx = row*9 + col).

    states[idx]    состояние клетки (бит 0 = pen, биты 1..9 = цифры или заметки)
    digit_cells[d] маска не-pen клеток с заметкой d
    placed[d]      маска pen-клеток с цифрой d
    buckets[c]     маска не-pen клеток ровно с c заметками
    empty_mask     маска не-pen клеток
    zobrist        хэш состояния доски
    dirty          27 бит: регионы, где с последнего просмотра паттернами менялись заметки
    pending        кандидаты в скрытые одиночки (idx, d); может содержать устаревшие записи

    Если place или eliminate вернули False, доску нужно выбросить: откат не делается.
    """

    __slots__ = (
        "states", "digit_cells", "placed", "buckets", "empty_mask", "zobrist", "dirty", "pending",
    )

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        """Сбросить доску в пустое состояние (во всех клетках все девять заметок)."""
        self.states: tp.List[int] = [DEFAULT_STATE] * 81
        self.digit_cells: tp.List[int] = [0] + [ALL_CELLS] * 9
        self.placed: tp.List[int] = [0] * 10
        self.buckets: tp.List[int] = [0] * 9 + [ALL_CELLS]
        self.empty_mask: int = ALL_CELLS
        self.zobrist: int = _INITIAL_HASH
        self.dirty: int = 0
        self.pending: tp.List[tp.Tuple[int, int]] = []

    @classmethod
    def from_grid(cls, grid: Grid) -> tp.Optional[Board]:
        """Доска из сетки строк ('.' = пусто). None, если во входе есть противоречие.

        Неверная форма сетки или символ вне '.123456789' дают ValueError.
        """
        if len(grid) != 9 or any(len(row) != 9 for row in grid):
            raise ValueError("Ожидается сетка 9x9")
        for r, row in enumerate(grid):
            for c, value in enumerate(row):
                if value != "." and value not in DIGIT_CHARS:
                    raise ValueError(f"Недопустимый символ {value!r} в клетке ({r}, {c})")
        board = cls()
        for r, row in enumerate(grid):
            for c, value in enumerate(row):
                if value != "." and not board.place(r * 9 + c, int(value)):
                    return None
        return board

    def to_grid(self) -> Grid:
        """Сетка строк: цифра для pen-клетки, '.' для остальных."""
        digits = [str(pen_digit(s)) if s & PEN_FLAG else "." for s in self.states]
        return [digits[r * 9:(r + 1) * 9] for r in range(9)]

    def copy(self) -> Board:
        """Независимая копия: только срезы списков и копирование int."""
        new = Board.__new__(Board)
        new.states = self.states[:]
        new.digit_cells = self.digit_cells[:]
        new.placed = self.placed[:]
        new.buckets = self.buckets[:]
        new.empty_mask = self.empty_mask
        new.zobrist = self.zobrist
        new.dirty = self.dirty
        new.pending = self.pending[:]
        return new

    def get_cell(self, pos: Pos) -> Cell:
        """Снимок клетки (не живая ссылка: позже изменённая доска снимок не меняет)."""
        return Cell(pos, self.states[pos[0] * 9 + pos[1]])

    def place(self, idx: int, d: int) -> bool:
        """Поставить цифру d в клетку idx. False: клетка занята, d нет в её заметках
        или возникло противоречие (тогда доску выбросить). Вне 1..9 ValueError."""
        if not 1 <= d <= 9:
            raise ValueError("Цифра должна быть от 1 до 9")
        state = self.states[idx]
        if state & PEN_FLAG or not state >> d & 1:
            return False
        bit = 1 << idx
        notes = state & NOTES_MASK
        digit_cells = self.digit_cells
        self.buckets[notes.bit_count()] &= ~bit
        m = notes
        while m:
            low = m & -m
            e = low.bit_length() - 1
            digit_cells[e] &= ~bit
            # у остальных цифр клетки могло не остаться места в её регионах
            if e != d and not self._check_digit(idx, e):
                return False
            m ^= low
        new = PEN_FLAG | (1 << d)
        self.states[idx] = new
        self.zobrist ^= hash_delta(idx, state, new)
        self.placed[d] |= bit
        self.empty_mask &= ~bit
        self.dirty |= DIRTY_BITS[idx]
        m = digit_cells[d] & PEER_MASK[idx]
        while m:
            low = m & -m
            if not self.eliminate(low.bit_length() - 1, d):
                return False
            m ^= low
        return True

    def eliminate(self, idx: int, d: int) -> bool:
        """Снять заметку d с клетки idx. False означает противоречие (доску выбросить).
        Если заметки нет, ничего не меняется. Вне 1..9 ValueError."""
        if not 1 <= d <= 9:
            raise ValueError("Цифра должна быть от 1 до 9")
        state = self.states[idx]
        if not state >> d & 1:
            return True
        if state & PEN_FLAG:
            return False  # снимаем поставленную цифру
        bit = 1 << idx
        new = state ^ (1 << d)
        self.states[idx] = new
        self.zobrist ^= ZOBRIST[idx][d]
        self.digit_cells[d] &= ~bit
        left = (new & NOTES_MASK).bit_count()
        self.buckets[left + 1] &= ~bit
        self.buckets[left] |= bit
        self.dirty |= DIRTY_BITS[idx]
        if left == 0:
            return False
        return self._check_digit(idx, d)

    def _check_digit(self, idx: int, d: int) -> bool:
        """После снятия заметки d с клетки idx проверить её три региона.

        Цифре некуда встать и она не поставлена: False. Осталась одна клетка:
        (клетка, d) в pending. Регионы, где d уже поставлена, пропускаются.
        """
        cells_d = self.digit_cells[d]
        placed_d = self.placed[d]
        for rid in CELL_REGIONS[idx]:
            mask = REGION_MASKS[rid]
            if placed_d & mask:
                continue
            m = cells_d & mask
            if m == 0:
                return False
            if not m & (m - 1):  # ровно один бит
                self.pending.append((m.bit_length() - 1, d))
        return True

    @staticmethod
    def _derive(
        states: tp.Sequence[int],
    ) -> tp.Tuple[tp.List[int], tp.List[int], tp.List[int], int]:
        """Пересчёт (digit_cells, placed, buckets, empty_mask) из списка состояний."""
        digit_cells = [0] * 10
        placed = [0] * 10
        buckets = [0] * 10
        empty = 0
        for idx, state in enumerate(states):
            bit = 1 << idx
            if state & PEN_FLAG:
                placed[state.bit_length() - 1] |= bit  # pen-цифра = старший бит
                continue
            empty |= bit
            buckets[state.bit_count()] |= bit
            m = state
            while m:
                low = m & -m
                digit_cells[low.bit_length() - 1] |= bit
                m ^= low
        return digit_cells, placed, buckets, empty

    def validate(self) -> None:
        """Проверка инвариантов (для тестов); при нарушении ValueError с описанием."""
        states = self.states
        if len(states) != 81:
            raise ValueError("Ожидается 81 состояние клеток")
        for idx, state in enumerate(states):
            if state & PEN_FLAG:
                d = pen_digit(state)
                bad = d == 0 or state != make_pen(d)
            else:
                bad = bool(state & ~NOTES_MASK)
            if bad:
                raise ValueError(f"Битое состояние клетки {idx}")
        digit_cells, placed, buckets, empty = self._derive(states)
        for name, have, want in (
            ("digit_cells", self.digit_cells, digit_cells),
            ("placed", self.placed, placed),
            ("buckets", self.buckets, buckets),
        ):
            if have != want:
                raise ValueError(f"Рассинхронизация {name}")
        if self.empty_mask != empty:
            raise ValueError("Рассинхронизация empty_mask")
        if self.zobrist != hash_state(states):
            raise ValueError("Рассинхронизация zobrist")
        if not 0 <= self.dirty <= ALL_DIRTY:
            raise ValueError("dirty вне 27 бит")
        if buckets[0]:
            raise ValueError("Клетка без заметок")
        for d in range(1, 10):
            if any((placed[d] & mask).bit_count() > 1 for mask in REGION_MASKS):
                raise ValueError(f"Повтор цифры {d} в регионе")
            if any(digit_cells[d] & PEER_MASK[i] for i in iter_bits(placed[d])):
                raise ValueError(f"Заметка {d} совпадает с цифрой соседа")