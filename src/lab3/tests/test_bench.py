import random

import pytest

import bench
import sudoku
from solver import SolverConfig


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


def test_parse_puzzle_line():
    line = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    grid = bench.parse_puzzle_line(line)
    assert grid[0] == list("53..7....") and len(grid) == 9
    assert bench.parse_puzzle_line(line.replace(".", "0")) == grid  # 0 = пусто
    assert bench.parse_puzzle_line(f"7,{line},{'1' * 81}") == grid  # CSV: первый токен
    assert bench.parse_puzzle_line("id,puzzle,solution") is None
    assert bench.parse_puzzle_line(line[:80]) is None
    assert bench.parse_puzzle_line(line[:80] + "x") is None


def test_load_hard_puzzles_present(tmp_path):
    line = "." * 81
    path = tmp_path / "hard.txt"
    path.write_text(f"заголовок\n{line}\n\n1,{line}\n{line}\n")
    assert len(bench.load_hard_puzzles(path)) == 3  # мусорные строки пропущены
    assert len(bench.load_hard_puzzles(path, limit=2)) == 2
    assert bench.load_hard_puzzles(path, limit=0) == []


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

def test_collect_puzzles_with_hard(tmp_path):
    for i in (1, 2, 3):
        (tmp_path / f"puzzle{i}.txt").write_text("." * 81)
    (tmp_path / "hard_puzzles.txt").write_text(("." * 81 + "\n") * 5)
    names = [n for n, _ in bench.collect_puzzles(tmp_path, generated=1, hard_limit=2)]
    assert names == ["puzzle1", "puzzle2", "puzzle3", "hard0", "hard1", "gen0"]
    assert [n for n, _ in bench.collect_puzzles(tmp_path, generated=0)] == [
        "puzzle1", "puzzle2", "puzzle3"]


def test_bench_solver_flags_wrong_answer(monkeypatch, puzzle1_grid):
    import types
    wrong = types.SimpleNamespace(to_grid=lambda: [["."] * 9 for _ in range(9)])
    monkeypatch.setattr(bench, "solve_board", lambda board, cfg=None, stats=None: wrong)
    row = bench.bench_solver("p1", puzzle1_grid, repeat=1)
    assert row.seconds is None and row.note == "НЕВЕРНОЕ РЕШЕНИЕ"


def test_summarize():
    rows = [bench.BenchRow("a", nodes=3, seconds=0.001), bench.BenchRow("b", nodes=5, seconds=0.004),
            bench.BenchRow("c", note="нет решения")]
    text = bench.summarize(rows)
    assert "решено 2 из 3" in text and "сумма 5.0 мс" in text
    assert "худший b 4.0 мс" in text and "узлов 8" in text
    assert bench.summarize([bench.BenchRow("c", note="пропуск")]) == "решено 0 из 1"

def test_experiments_cover_expected_configs():
    assert list(bench.EXPERIMENTS) == ["singles", "+pairs", "+threes", "+pointing", "pointing only"]
    assert bench.EXPERIMENTS["+pointing"] == SolverConfig(subsets=3, pointing=True)


def test_compare_configs():
    puzzles = bench.generated_puzzles(2)
    configs = {"a": SolverConfig(), "b": SolverConfig(subsets=2)}
    lines = bench.compare_configs(configs, puzzles, repeat=1).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("a") and lines[1].startswith("b")
    assert all("решено 2 из 2" in line for line in lines)

GRID_TEXT = "53..7....\n6..195...\n.98....6.\n8...6...3\n4..8.3..1\n7...2...6\n.6....28.\n...419..5\n....8..79\n"


def test_load_puzzles_file_line_format(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text(("." * 81 + "\n") * 3)
    assert len(bench.load_puzzles_file(path)) == 3
    assert len(bench.load_puzzles_file(path, limit=2)) == 2


def test_load_puzzles_file_grid_format(tmp_path):
    path = tmp_path / "g.txt"
    path.write_text(GRID_TEXT + GRID_TEXT)
    grids = bench.load_puzzles_file(path)
    assert len(grids) == 2 and grids[0][0] == list("53..7....")
    assert bench.load_puzzles_file(path, limit=1) == grids[:1]


def test_load_puzzles_file_garbage(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("ничего похожего на пазл")
    assert bench.load_puzzles_file(path) == []


def test_load_puzzles_dir(tmp_path):
    (tmp_path / "b.txt").write_text(GRID_TEXT)
    (tmp_path / "a.txt").write_text(("." * 81 + "\n") * 2)
    (tmp_path / "_skip.txt").write_text(GRID_TEXT)
    (tmp_path / "notes.md").write_text(GRID_TEXT)
    items = bench.load_puzzles_dir(tmp_path)
    assert [n for n, _ in items] == ["a#0", "a#1", "b"]
    assert [n for n, _ in bench.load_puzzles_dir(tmp_path, limit=1)] == ["a", "b"]


def test_load_puzzles_dir_missing(tmp_path):
    assert bench.load_puzzles_dir(tmp_path / "nope") == []


def test_collect_puzzles_with_dir(tmp_path):
    for i in (1, 2, 3):
        (tmp_path / f"puzzle{i}.txt").write_text("." * 81)
    folder = tmp_path / "puzzles"
    folder.mkdir()
    (folder / "extra.txt").write_text(GRID_TEXT)
    (folder / "_old.txt").write_text(GRID_TEXT)
    names = [n for n, _ in bench.collect_puzzles(tmp_path, generated=0, use_dir=True)]
    assert names == ["puzzle1", "puzzle2", "puzzle3", "extra"]
    names = [n for n, _ in bench.collect_puzzles(tmp_path, generated=0)]
    assert names == ["puzzle1", "puzzle2", "puzzle3"]

def test_bench_solver_node_limit():
    row = bench.bench_solver("empty", [["."] * 9 for _ in range(9)],
                             SolverConfig(max_nodes=1), repeat=1)
    assert row.seconds is None and row.nodes == 1 and "лимит узлов" in row.note


def test_summarize_reports_memo_hits():
    rows = [bench.BenchRow("a", nodes=1, memo_hits=2, seconds=0.001),
            bench.BenchRow("b", nodes=1, memo_hits=3, seconds=0.001)]
    assert "memo_hits 5" in bench.summarize(rows)
    assert "memo_hits 0" in bench.summarize([bench.BenchRow("c", nodes=1, seconds=0.001)])


def test_experiment_dicts():
    assert len(bench.STRATEGY_EXPERIMENTS) == 5 and len(bench.ALL_CELLS_EXPERIMENTS) == 3
    assert all(c.branch_all_cells for k, c in bench.ALL_CELLS_EXPERIMENTS.items() if "все" in k)

def test_progress_line():
    assert bench.progress_line("x", 0, 4, "a", width=4) == "x [....] 0/4 a"
    assert bench.progress_line("x", 2, 4, "b", width=4) == "x [##..] 2/4 b"
    assert bench.progress_line("x", 4, 4, "c", width=4) == "x [####] 4/4 c"
    assert bench.progress_line("x", 0, 0, "-", width=4) == "x [####] 0/0 -"


def test_report_progress(capsys):
    bench.report_progress("lbl", 1, 3, "p1")
    err = capsys.readouterr().err
    assert err.startswith("\r") and "1/3 p1" in err and not err.endswith("\n")
    bench.report_progress("lbl", 3, 3, "готово")
    assert capsys.readouterr().err.endswith("\n")


def test_run_rows(capsys):
    seen = []
    puzzles = [("a", [["."] * 9]), ("b", [["."] * 9])]
    rows = bench.run_rows(puzzles, lambda n, g: seen.append(n) or bench.BenchRow(n))
    assert [r.puzzle for r in rows] == ["a", "b"] == seen
    assert capsys.readouterr().err == ""
    bench.run_rows(puzzles, lambda n, g: bench.BenchRow(n), "L", progress=True)
    err = capsys.readouterr().err
    assert "0/2 a" in err and "1/2 b" in err and "2/2 готово" in err


def test_compare_configs_with_progress(capsys):
    puzzles = bench.generated_puzzles(1)
    bench.compare_configs({"cfg": SolverConfig()}, puzzles, repeat=1, progress=True)
    assert "cfg" in capsys.readouterr().err