"""Замеры решателей: python bench.py [--profile] [--repeat N] [--max-steps N]."""
import argparse
import cProfile
import io
import pathlib
import platform
import pstats
import random
import time
import typing as tp
from dataclasses import dataclass

import sudoku

from board import Board
from solver import DEFAULT_CONFIG, SolveStats, SolverConfig, solve_board

ROOT = pathlib.Path(__file__).parent
Grid = tp.List[tp.List[str]]


@dataclass
class BenchRow:
    """Строка таблицы замеров."""
    puzzle: str
    nodes: tp.Optional[int] = None
    memo_hits: tp.Optional[int] = None
    seconds: tp.Optional[float] = None
    note: str = ""


def load_named_puzzles(root: pathlib.Path = ROOT) -> tp.Dict[str, Grid]:
    """Загрузить puzzle1–3 из корня проекта."""
    return {f"puzzle{i}": sudoku.read_sudoku(root / f"puzzle{i}.txt") for i in (1, 2, 3)}


def load_hard_puzzles(path: tp.Union[str, pathlib.Path]) -> tp.List[Grid]:
    """Прочитать hard_puzzles.txt. Если файла нет, вернуть пустой список."""
    path = pathlib.Path(path)
    if not path.exists():
        return []
    raise NotImplementedError("Формат hard_puzzles.txt не определён: пришлите файл")


def generated_puzzles(count: int = 20, clues: int = 30, seed: int = 0) -> tp.List[tp.Tuple[str, Grid]]:
    """Сгенерировать пазлы с фиксированными seed; глобальное состояние random сохраняется."""
    state = random.getstate()
    try:
        result = []
        for i in range(count):
            random.seed(seed + i)
            result.append((f"gen{i}", sudoku.generate_sudoku(clues)))
    finally:
        random.setstate(state)
    return result


def collect_puzzles(root: pathlib.Path = ROOT, generated: int = 20) -> tp.List[tp.Tuple[str, Grid]]:
    """Полный набор: puzzle1–3, hard_puzzles.txt (если есть), сгенерированные."""
    items: tp.List[tp.Tuple[str, Grid]] = list(load_named_puzzles(root).items())
    for i, grid in enumerate(load_hard_puzzles(root / "hard_puzzles.txt")):
        items.append((f"hard{i}", grid))
    items.extend(generated_puzzles(generated))
    return items


def time_min(func: tp.Callable[[], tp.Any], repeat: int) -> float:
    """Минимальное время (секунды) из repeat прогонов, не меньше одного."""
    best = float("inf")
    for _ in range(max(1, repeat)):
        start = time.perf_counter()
        func()
        best = min(best, time.perf_counter() - start)
    return best


def bench_naive(name: str, grid: Grid, repeat: int = 3, max_steps: int = 100_000) -> BenchRow:
    """Замерить solve_naive; при превышении max_steps пазл пропускается с пометкой."""
    steps: tp.List[int] = []
    try:
        solution = sudoku.solve_naive(grid, max_steps, steps)
    except sudoku.SearchLimitExceeded:
        return BenchRow(name, nodes=steps[0], note=f"пропуск: больше {max_steps} шагов")
    if solution is None:
        return BenchRow(name, nodes=steps[0], note="нет решения")
    seconds = time_min(lambda: sudoku.solve_naive(grid, max_steps), repeat)
    return BenchRow(name, nodes=steps[0], seconds=seconds)


def run_benchmark(repeat: int = 3, max_steps: int = 100_000, root: pathlib.Path = ROOT,
                  generated: int = 20) -> tp.List[BenchRow]:
    """Прогнать solve_naive по всему набору."""
    return [bench_naive(n, g, repeat, max_steps) for n, g in collect_puzzles(root, generated)]

def bench_solver(name: str, grid: Grid, cfg: SolverConfig = DEFAULT_CONFIG,
                 repeat: int = 3) -> BenchRow:
    """Замерить solve_board: узлы и memo_hits за один прогон, время минимум из repeat."""
    board = Board.from_grid(grid)
    if board is None:
        return BenchRow(name, note="противоречие во входе")
    stats = SolveStats()
    if solve_board(board, cfg, stats) is None:
        return BenchRow(name, nodes=stats.nodes, memo_hits=stats.memo_hits, note="нет решения")
    seconds = time_min(lambda: solve_board(board, cfg), repeat)
    return BenchRow(name, nodes=stats.nodes, memo_hits=stats.memo_hits, seconds=seconds)


def run_solver_benchmark(cfg: SolverConfig = DEFAULT_CONFIG, repeat: int = 3,
                         root: pathlib.Path = ROOT, generated: int = 20) -> tp.List[BenchRow]:
    """Прогнать solve_board с конфигурацией cfg по всему набору."""
    return [bench_solver(n, g, cfg, repeat) for n, g in collect_puzzles(root, generated)]

def _fmt(value: tp.Optional[tp.Union[int, float]], spec: str = "") -> str:
    return "-" if value is None else format(value, spec)


def format_table(rows: tp.List[BenchRow]) -> str:
    """Таблица: пазл, nodes, memo_hits, время в мс, примечание."""
    lines = [f"{'пазл':<10}{'nodes':>10}{'memo_hits':>11}{'мс':>12}  примечание"]
    for r in rows:
        ms = None if r.seconds is None else r.seconds * 1000
        lines.append(f"{r.puzzle:<10}{_fmt(r.nodes):>10}{_fmt(r.memo_hits):>11}"
                     f"{_fmt(ms, '.2f'):>12}  {r.note}")
    return "\n".join(lines)


def profile_call(func: tp.Callable[[], tp.Any], top: int = 15) -> str:
    """Профиль cProfile вызова func (сортировка по накопленному времени)."""
    profiler = cProfile.Profile()
    profiler.runcall(func)
    buf = io.StringIO()
    pstats.Stats(profiler, stream=buf).sort_stats("cumulative").print_stats(top)
    return buf.getvalue()


def main(argv: tp.Optional[tp.List[str]] = None) -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Замеры решателей судоку")
    parser.add_argument("--profile", action="store_true", help="профиль solve_board на puzzle2")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=100_000)
    args = parser.parse_args(argv)
    print(f"Python {platform.python_version()}, {platform.platform()}")
    if not (ROOT / "hard_puzzles.txt").exists():
        print("hard_puzzles.txt не найден: пропущено")
    print("solve_naive")
    print(format_table(run_benchmark(args.repeat, args.max_steps)))
    print(f"solve_board {DEFAULT_CONFIG}")
    print(format_table(run_solver_benchmark(DEFAULT_CONFIG, args.repeat)))
    if args.profile:
        board = Board.from_grid(load_named_puzzles()["puzzle2"])
        print(profile_call(lambda: solve_board(board)))


if __name__ == "__main__":
    main()