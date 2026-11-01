import random

import pytest

import bench
import sudoku


def dead_end_grid():
    grid = [["."] * 9 for _ in range(9)]
    grid[0] = list("12345678.")
    grid[1][8] = "9"
    return grid


def test_load_named_puzzles():
    puzzles = bench.load_named_puzzles()
    assert list(puzzles) == ["puzzle1", "puzzle2", "puzzle3"]
    assert all(len(g) == 9 and all(len(r) == 9 for r in g) for g in puzzles.values())


def test_load_hard_puzzles_missing(tmp_path):
    assert bench.load_hard_puzzles(tmp_path / "no.txt") == []


def test_load_hard_puzzles_present(tmp_path):
    path = tmp_path / "hard.txt"
    path.write_text("x")
    with pytest.raises(NotImplementedError):
        bench.load_hard_puzzles(path)


def test_generated_puzzles_deterministic():
    first = bench.generated_puzzles(3)
    assert first == bench.generated_puzzles(3)
    assert [n for n, _ in first] == ["gen0", "gen1", "gen2"]
    assert all(sum(row.count(".") for row in g) == 51 for _, g in first)


def test_generated_puzzles_keeps_random_state():
    state = random.getstate()
    bench.generated_puzzles(2)
    assert random.getstate() == state


def test_collect_puzzles():
    names = [n for n, _ in bench.collect_puzzles(generated=2)]
    assert names == ["puzzle1", "puzzle2", "puzzle3", "gen0", "gen1"]


def test_time_min():
    calls = []
    assert bench.time_min(lambda: calls.append(1), 4) >= 0
    assert len(calls) == 4


def test_time_min_runs_at_least_once():
    calls = []
    bench.time_min(lambda: calls.append(1), 0)
    assert len(calls) == 1


def test_bench_naive_solved(puzzle1_grid):
    row = bench.bench_naive("p1", puzzle1_grid, repeat=1)
    assert row.seconds is not None and row.nodes > 0 and row.note == ""


def test_bench_naive_skipped(puzzle1_grid):
    row = bench.bench_naive("p1", puzzle1_grid, repeat=1, max_steps=5)
    assert row.seconds is None
    assert row.nodes == 6
    assert "пропуск" in row.note


def test_bench_naive_no_solution():
    row = bench.bench_naive("dead", dead_end_grid(), repeat=1)
    assert row.seconds is None and row.note == "нет решения"


def test_fmt():
    assert bench._fmt(None) == "-"
    assert bench._fmt(1.5, ".2f") == "1.50"
    assert bench._fmt(7) == "7"


def test_format_table():
    rows = [bench.BenchRow("a", nodes=10, seconds=0.002), bench.BenchRow("b", note="пропуск")]
    lines = bench.format_table(rows).splitlines()
    assert len(lines) == 3
    assert "2.00" in lines[1] and lines[1].startswith("a")
    assert "-" in lines[2] and "пропуск" in lines[2]


def test_run_benchmark():
    rows = bench.run_benchmark(repeat=1, max_steps=50, generated=2)
    assert [r.puzzle for r in rows] == ["puzzle1", "puzzle2", "puzzle3", "gen0", "gen1"]


def test_profile_call():
    assert "function calls" in bench.profile_call(lambda: sum(range(10)), top=3)

def test_bench_solver_solved(puzzle1_grid):
    row = bench.bench_solver("p1", puzzle1_grid, repeat=1)
    assert row.seconds is not None and row.nodes >= 1 and row.memo_hits >= 0
    assert row.note == ""


def test_bench_solver_input_contradiction():
    row = bench.bench_solver("dead", dead_end_grid(), repeat=1)
    assert row.seconds is None and row.note == "противоречие во входе"


def test_bench_solver_no_solution(monkeypatch, puzzle1_grid):
    monkeypatch.setattr(bench, "solve_board", lambda board, cfg=None, stats=None: None)
    row = bench.bench_solver("p1", puzzle1_grid, repeat=1)
    assert row.seconds is None and row.note == "нет решения"
    assert row.nodes == 0 and row.memo_hits == 0


def test_run_solver_benchmark():
    rows = bench.run_solver_benchmark(repeat=1, generated=2)
    assert [r.puzzle for r in rows] == ["puzzle1", "puzzle2", "puzzle3", "gen0", "gen1"]
    assert all(r.seconds is not None for r in rows)