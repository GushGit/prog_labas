from __future__ import annotations

import typing as tp
from dataclasses import dataclass

from board import Board
from cell import notes_of


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


CELL_STRATEGIES: tp.Dict[str, tp.Callable[[Board], int]] = {"mrv": select_cell_mrv}
BRANCH_STRATEGIES: tp.Dict[str, tp.Callable[[Board, int], tp.List[int]]] = {"asc": branch_asc}


@dataclass(frozen=True)
class SolverConfig:
    """Настройки решателя."""

    memo: bool = True
    cell_strategy: str = "mrv"
    branch_strategy: str = "asc"

    def __post_init__(self) -> None:
        if self.cell_strategy not in CELL_STRATEGIES:
            raise ValueError(f"Неизвестная стратегия клетки: {self.cell_strategy!r}")
        if self.branch_strategy not in BRANCH_STRATEGIES:
            raise ValueError(f"Неизвестная стратегия ветки: {self.branch_strategy!r}")


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


def propagate(board: Board, cfg: SolverConfig = DEFAULT_CONFIG) -> bool:
    """Распространение до неподвижной точки. False: противоречие.

    Пока только singles; паттерны по «грязным» регионам добавятся в итерации 5.
    """
    while board.buckets[1] or board.pending:
        if not obvious_singles(board) or not hidden_singles(board):
            return False
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
    if depth > stats.max_depth:
        stats.max_depth = depth
    if cfg.memo:
        key = board.zobrist
        if key in visited:
            stats.memo_hits += 1
            return None
        visited.add(key)
    if not propagate(board, cfg):
        return None
    if not board.empty_mask:
        return board
    idx = CELL_STRATEGIES[cfg.cell_strategy](board)
    for d in BRANCH_STRATEGIES[cfg.branch_strategy](board, idx):
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