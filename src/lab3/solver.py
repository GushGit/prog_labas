from __future__ import annotations

import typing as tp
from dataclasses import dataclass

from board import REGION_MASKS, Board
from cell import notes_of

from patterns import process_region
from region import CELL_REGIONS, REGIONS

@dataclass
class SolveStats:
    """Счётчики на уровне узлов поиска."""

    nodes: int = 0
    memo_hits: int = 0
    region_visits: int = 0
    max_depth: int = 0


def select_cell_mrv(board: Board) -> int:
    """Клетка с наименьшим числом заметок (>= 2); при ничьей младший индекс."""
    for count in range(2, 10):
        mask = board.buckets[count]
        if mask:
            return (mask & -mask).bit_length() - 1  # индекс младшего бита
    raise ValueError("Нет клетки для ветвления")


def branch_asc(board: Board, idx: int) -> tp.List[int]:
    """Цифры клетки по возрастанию."""
    return notes_of(board.states[idx])


class NodeLimitExceeded(Exception):
    """Поиск превысил SolverConfig.max_nodes."""


AREA_MASK = tuple(REGION_MASKS[a] | REGION_MASKS[b] | REGION_MASKS[c] for a, b, c in CELL_REGIONS)


def select_cell_mrv_degree(board: Board) -> int:
    """Как mrv, но при ничьей берётся клетка с меньшей суммой открытых клеток в её регионах."""
    for count in range(2, 10):
        mask = board.buckets[count]
        if not mask:
            continue
        best, best_key = -1, 1 << 30
        while mask:
            low = mask & -mask
            idx = low.bit_length() - 1
            mask ^= low
            key = sum((board.empty_mask & REGION_MASKS[r]).bit_count() for r in CELL_REGIONS[idx])
            if key < best_key:  # строго меньше: при равенстве остаётся младший индекс
                best, best_key = idx, key
        return best
    raise ValueError("Нет клетки для ветвления")


def select_cell_digit_min(board: Board) -> int:
    """Клетка, содержащая цифру с наименьшим числом кандидатов на всей доске (младший индекс)."""
    best_d, best_count = 0, 82
    for d in range(1, 10):
        count = board.digit_cells[d].bit_count()
        if 0 < count < best_count:
            best_d, best_count = d, count
    if not best_d:
        raise ValueError("Нет клетки для ветвления")
    mask = board.digit_cells[best_d]
    return (mask & -mask).bit_length() - 1


def branch_rare_first(board: Board, idx: int) -> tp.List[int]:
    """Цифры клетки по возрастанию числа кандидатов цифры в трёх её регионах."""
    area = AREA_MASK[idx]
    return sorted(notes_of(board.states[idx]), key=lambda d: (board.digit_cells[d] & area).bit_count())


def candidate_cells(board: Board) -> tp.List[int]:
    """Все клетки с >= 2 заметок: по возрастанию числа заметок, затем индекса."""
    cells: tp.List[int] = []
    for count in range(2, 10):
        mask = board.buckets[count]
        while mask:
            low = mask & -mask
            cells.append(low.bit_length() - 1)
            mask ^= low
    return cells


CELL_STRATEGIES: tp.Dict[str, tp.Callable[[Board], int]] = {
    "mrv": select_cell_mrv,
    "mrv_degree": select_cell_mrv_degree,
    "digit_min": select_cell_digit_min,
}
BRANCH_STRATEGIES: tp.Dict[str, tp.Callable[[Board, int], tp.List[int]]] = {
    "asc": branch_asc,
    "rare_first": branch_rare_first,
}


@dataclass(frozen=True)
class SolverConfig:
    """Настройки решателя. subsets: 0 (выкл.), 2 (пары) или 3 (пары и тройки).

    branch_all_cells: перебор нескольких клеток по схеме студента (только для замеров memo).
    max_nodes: лимит узлов поиска, 0 = без лимита (NodeLimitExceeded).
    """

    memo: bool = True
    cell_strategy: str = "mrv"
    branch_strategy: str = "asc"
    subsets: int = 0
    pointing: bool = False
    branch_all_cells: bool = False
    max_nodes: int = 0

    def __post_init__(self) -> None:
        if self.cell_strategy not in CELL_STRATEGIES:
            raise ValueError(f"Неизвестная стратегия клетки: {self.cell_strategy!r}")
        if self.branch_strategy not in BRANCH_STRATEGIES:
            raise ValueError(f"Неизвестная стратегия ветки: {self.branch_strategy!r}")
        if self.subsets not in (0, 2, 3):
            raise ValueError(f"subsets должен быть 0, 2 или 3, а не {self.subsets!r}")
        if self.max_nodes < 0:
            raise ValueError("max_nodes не может быть отрицательным")


DEFAULT_CONFIG = SolverConfig()

def obvious_singles(board: Board) -> bool:
    """Ставит клетки с единственной заметкой до исчерпания. False: противоречие."""
    buckets = board.buckets
    while buckets[1]:
        mask = buckets[1]
        idx = (mask & -mask).bit_length() - 1
        # у клетки одна заметка, значит state = 1 << d и d = bit_length - 1
        d = board.states[idx].bit_length() - 1
        if not board.place(idx, d):
            return False
    return True


def hidden_singles(board: Board) -> bool:
    """Разбирает pending: цифра, у которой в регионе осталась одна клетка. False: противоречие."""
    pending = board.pending
    while pending:
        idx, d = pending.pop()
        state = board.states[idx]
        # запись устарела, если клетку уже поставили или заметку сняли:
        # заметки не возвращаются, поэтому живая запись остаётся верной
        if state & 1 or not state >> d & 1:
            continue
        if not board.place(idx, d):
            return False
    return True


def propagate(
    board: Board,
    cfg: SolverConfig = DEFAULT_CONFIG,
    stats: tp.Optional[SolveStats] = None,
) -> bool:
    """Распространение до неподвижной точки. False: противоречие.

    Singles работают событийно. Когда они исчерпаны, по одному берутся «грязные» регионы
    (где менялись заметки), и каждый разбирается паттернами. Результативный проход
    возвращает цикл к singles.
    """
    patterns_on = cfg.subsets >= 2 or cfg.pointing
    while True:
        while board.buckets[1] or board.pending:
            if not obvious_singles(board) or not hidden_singles(board):
                return False
        if not patterns_on:
            return True
        changed = False
        while board.dirty and not changed:
            low = board.dirty & -board.dirty
            board.dirty ^= low
            if stats is not None:
                stats.region_visits += 1
            result = process_region(board, REGIONS[low.bit_length() - 1], cfg)
            if result is None:
                return False
            changed = result
        if not changed:
            return True


def search(
    board: Board,
    cfg: SolverConfig,
    stats: SolveStats,
    visited: tp.Set[int],
    depth: int = 0,
) -> tp.Optional[Board]:
    """DFS. Доска мутируется (передавайте копию). Возвращает решённую доску или None."""
    stats.nodes += 1
    if cfg.max_nodes and stats.nodes > cfg.max_nodes:
        raise NodeLimitExceeded
    if depth > stats.max_depth:
        stats.max_depth = depth
    if cfg.memo:
        key = board.zobrist
        if key in visited:
            stats.memo_hits += 1
            return None
        visited.add(key)
    if not propagate(board, cfg, stats):
        return None
    if not board.empty_mask:
        return board
    if cfg.branch_all_cells:
        cells = candidate_cells(board)
    else:
        cells = [CELL_STRATEGIES[cfg.cell_strategy](board)]
    branch = BRANCH_STRATEGIES[cfg.branch_strategy]
    for idx in cells:
        for d in branch(board, idx):
            child = board.copy()
            if not child.place(idx, d):
                continue
            result = search(child, cfg, stats, visited, depth + 1)
            if result is not None:
                return result
    return None


def solve_board(
    board: Board,
    cfg: SolverConfig = DEFAULT_CONFIG,
    stats: tp.Optional[SolveStats] = None,
) -> tp.Optional[Board]:
    """Решить доску. Вход не меняется; нет решения: None. Глобального состояния нет."""
    if stats is None:
        stats = SolveStats()
    return search(board.copy(), cfg, stats, set())

def _count(board: Board, cfg: SolverConfig, stats: SolveStats, limit: int) -> int:
    """Число решений доски (мутирует её), поиск прекращается при достижении limit."""
    stats.nodes += 1
    if not propagate(board, cfg, stats):
        return 0
    if not board.empty_mask:
        return 1
    idx = CELL_STRATEGIES[cfg.cell_strategy](board)
    total = 0
    for d in BRANCH_STRATEGIES[cfg.branch_strategy](board, idx):
        child = board.copy()
        if not child.place(idx, d):
            continue
        total += _count(child, cfg, stats, limit - total)
        if total >= limit:
            break
    return total


def count_solutions(
    board: Board,
    limit: int = 2,
    cfg: SolverConfig = DEFAULT_CONFIG,
    stats: tp.Optional[SolveStats] = None,
) -> int:
    """Число решений, но не больше limit (по умолчанию 2: «0, 1 или несколько»). Вход не меняется."""
    if limit < 1:
        raise ValueError("limit должен быть не меньше 1")
    return _count(board.copy(), cfg, stats or SolveStats(), limit)