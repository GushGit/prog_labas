import pathlib
import random

import pytest

import solver
import sudoku
from board import Board
from cell import make_pen
from solver import DEFAULT_CONFIG, SolveStats, SolverConfig


def snapshot(board):
    return (list(board.states), list(board.digit_cells), list(board.placed),
            list(board.buckets), board.empty_mask, board.zobrist, board.dirty)


def empty_board():
    return Board.from_grid([["."] * 9 for _ in range(9)])


def hide_in_row(board, row, keep_col, d=9):
    """Цифра d в строке row остаётся только в колонке keep_col."""
    for c in range(9):
        if c != keep_col:
            assert board.eliminate(row * 9 + c, d)


def conflicting_singles_board():
    """Клетки 0 и 1 (один блок) сведены к единственной заметке 9."""
    b = empty_board()
    for idx in (0, 1):
        for d in range(1, 9):
            assert b.eliminate(idx, d)
    return b


def conflicting_hidden_board():
    """9 в строке 0 только в клетке 0, 9 в строке 1 только в клетке 10 (тот же блок)."""
    b = empty_board()
    hide_in_row(b, 0, 0)
    hide_in_row(b, 1, 1)
    return b


def test_solve_stats_defaults():
    s = SolveStats()
    assert (s.nodes, s.memo_hits, s.region_visits, s.max_depth) == (0, 0, 0, 0)


def test_config_defaults_and_frozen():
    assert DEFAULT_CONFIG == SolverConfig(memo=True, cell_strategy="mrv", branch_strategy="asc")
    with pytest.raises(Exception):
        DEFAULT_CONFIG.memo = False


def test_config_rejects_unknown_names():
    with pytest.raises(ValueError):
        SolverConfig(cell_strategy="nope")
    with pytest.raises(ValueError):
        SolverConfig(branch_strategy="nope")


def test_select_cell_mrv_prefers_fewest_notes():
    b = empty_board()
    assert solver.select_cell_mrv(b) == 0  # все по 9 заметок: младший индекс
    for d in range(1, 8):
        assert b.eliminate(5, d)  # у клетки 5 две заметки
    assert solver.select_cell_mrv(b) == 5


def test_select_cell_mrv_tie_goes_to_lowest_index():
    b = empty_board()
    for idx in (30, 7):
        for d in range(1, 8):
            assert b.eliminate(idx, d)
    assert solver.select_cell_mrv(b) == 7


def test_select_cell_mrv_without_candidates(puzzle1_solution):
    b = Board.from_grid(puzzle1_solution)
    with pytest.raises(ValueError):
        solver.select_cell_mrv(b)


def test_branch_asc():
    b = empty_board()
    for d in (2, 3, 4, 5, 6, 7, 8):
        assert b.eliminate(0, d)
    assert solver.branch_asc(b, 0) == [1, 9]


def test_obvious_singles_places_digit():
    b = empty_board()
    for d in range(1, 9):
        assert b.eliminate(0, d)
    assert solver.obvious_singles(b) is True
    assert b.states[0] == make_pen(9)
    assert b.buckets[1] == 0
    b.validate()


def test_obvious_singles_noop_when_nothing_to_do():
    b = empty_board()
    snap = snapshot(b)
    assert solver.obvious_singles(b) is True
    assert snapshot(b) == snap


def test_obvious_singles_detects_contradiction():
    assert solver.obvious_singles(conflicting_singles_board()) is False


def test_hidden_singles_places_digit():
    b = empty_board()
    hide_in_row(b, 0, 0)
    assert b.pending == [(0, 9)]
    assert solver.hidden_singles(b) is True
    assert b.states[0] == make_pen(9)
    assert b.pending == []
    b.validate()


def test_hidden_singles_skips_stale_entries():
    b = empty_board()
    assert b.place(5, 3)
    b.pending = [(5, 3)]  # клетка уже поставлена
    assert solver.hidden_singles(b) is True and b.pending == []
    b = empty_board()
    assert b.eliminate(5, 3)
    snap = snapshot(b)
    b.pending = [(5, 3)]  # заметки уже нет
    assert solver.hidden_singles(b) is True
    assert snapshot(b) == snap


def test_hidden_singles_detects_contradiction():
    assert solver.hidden_singles(conflicting_hidden_board()) is False


def test_propagate_puzzle1_stays_consistent(puzzle1_grid, puzzle1_solution):
    b = Board.from_grid(puzzle1_grid)
    assert solver.propagate(b) is True
    b.validate()
    for r, row in enumerate(b.to_grid()):
        for c, v in enumerate(row):
            assert v in (".", puzzle1_solution[r][c])
    assert b.buckets[1] == 0 and b.pending == []


def test_propagate_reports_contradiction():
    assert solver.propagate(conflicting_singles_board()) is False
    assert solver.propagate(conflicting_hidden_board()) is False


def test_search_hits_memo():
    b = empty_board()
    stats = SolveStats()
    assert solver.search(b, DEFAULT_CONFIG, stats, {b.zobrist}) is None
    assert stats.memo_hits == 1 and stats.nodes == 1


def test_search_remembers_position():
    b = empty_board()
    visited = set()
    solver.search(b.copy(), DEFAULT_CONFIG, SolveStats(), visited)
    assert b.zobrist in visited
    visited = set()
    solver.search(b.copy(), SolverConfig(memo=False), SolveStats(), visited)
    assert visited == set()


def test_search_contradiction_returns_none():
    stats = SolveStats()
    assert solver.search(conflicting_singles_board(), DEFAULT_CONFIG, stats, set()) is None
    assert stats.nodes == 1


def test_search_tracks_depth():
    stats = SolveStats()
    assert solver.search(empty_board(), DEFAULT_CONFIG, stats, set()) is not None
    assert stats.max_depth >= 1 and stats.nodes > stats.max_depth


def test_solve_board_puzzle1(puzzle1_grid, puzzle1_solution):
    b = Board.from_grid(puzzle1_grid)
    snap = snapshot(b)
    stats = SolveStats()
    solved = solver.solve_board(b, stats=stats)
    assert solved.to_grid() == puzzle1_solution
    solved.validate()
    assert snapshot(b) == snap  # вход не мутируется
    assert stats.nodes >= 1


@pytest.mark.parametrize("name", ["puzzle1", "puzzle2", "puzzle3"])
def test_solve_board_named_puzzles_are_valid(name):
    grid = sudoku.read_sudoku(f"{name}.txt")
    solved = solver.solve_board(Board.from_grid(grid))
    result = solved.to_grid()
    assert sudoku.check_solution(result)
    for r in range(9):
        for c in range(9):
            assert grid[r][c] in (".", result[r][c])


def test_solve_board_special_inputs(puzzle1_solution):
    solved = solver.solve_board(empty_board())
    assert sudoku.check_solution(solved.to_grid())
    full = solver.solve_board(Board.from_grid(puzzle1_solution))
    assert full.to_grid() == puzzle1_solution
    assert Board.from_grid([["5", "5"] + ["."] * 7] + [["."] * 9] * 8) is None


@pytest.mark.parametrize("memo", [True, False])
def test_memo_does_not_change_answer(puzzle1_grid, memo):
    stats = SolveStats()
    solved = solver.solve_board(Board.from_grid(puzzle1_grid), SolverConfig(memo=memo), stats)
    assert sudoku.check_solution(solved.to_grid())
    if not memo:
        assert stats.memo_hits == 0


@pytest.mark.parametrize("seed", range(10))
def test_matches_naive_on_generated(seed):
    random.seed(seed)
    grid = sudoku.generate_sudoku(35)
    solution = sudoku.solve(grid)
    assert solution is not None and sudoku.check_solution(solution)
    for r in range(9):
        for c in range(9):
            assert grid[r][c] in (".", solution[r][c])
    try:
        naive = sudoku.solve_naive(grid, max_steps=20000)
    except sudoku.SearchLimitExceeded:
        return  # naive не справился; сравнивать не с чем
    assert naive is not None


def test_unsolvable_puzzle_gives_none(puzzle1_grid):
    grid = [row[:] for row in puzzle1_grid]
    grid[0][2] = "1"  # допустимо локально, но у puzzle1 единственное решение с 4 здесь
    assert sudoku.solve(grid) is None
    assert sudoku.solve_naive(grid) is None


def test_sudoku_solve_edge_cases(puzzle1_grid, puzzle1_solution):
    original = [row[:] for row in puzzle1_grid]
    assert sudoku.solve(puzzle1_grid) == puzzle1_solution
    assert puzzle1_grid == original
    dup = [["."] * 9 for _ in range(9)]
    dup[0][0] = dup[0][1] = "5"
    assert sudoku.solve(dup) is None

PUZZLE_DIR = pathlib.Path(__file__).parent.parent
PATTERN_CONFIGS = [
    SolverConfig(subsets=2),
    SolverConfig(subsets=3),
    SolverConfig(pointing=True),
    SolverConfig(subsets=3, pointing=True),
    SolverConfig(subsets=3, pointing=True, memo=False),
]


def stuck_pair_board():
    """Клетки 0, 1, 2 строки 0 сведены к {1, 2}: три клетки на две цифры."""
    b = empty_board()
    for idx in (0, 1, 2):
        for d in range(3, 10):
            assert b.eliminate(idx, d)
    return b


def test_config_subsets_and_pointing_options():
    for ok in (0, 2, 3):
        assert SolverConfig(subsets=ok).subsets == ok
    for bad in (1, 4, -1):
        with pytest.raises(ValueError):
            SolverConfig(subsets=bad)
    assert DEFAULT_CONFIG.subsets == 0 and DEFAULT_CONFIG.pointing is False


def test_propagate_patterns_find_contradiction_that_singles_miss():
    b = stuck_pair_board()
    assert solver.propagate(b.copy(), DEFAULT_CONFIG) is True
    assert solver.propagate(b, SolverConfig(subsets=2)) is False


def test_propagate_counts_region_visits():
    grid = sudoku.read_sudoku(PUZZLE_DIR / "puzzle2.txt")
    stats = SolveStats()
    b = Board.from_grid(grid)
    assert solver.propagate(b, SolverConfig(subsets=3, pointing=True), stats) is True
    assert stats.region_visits > 0 and b.dirty == 0
    b.validate()
    stats = SolveStats()
    assert solver.propagate(Board.from_grid(grid), DEFAULT_CONFIG, stats) is True
    assert stats.region_visits == 0


@pytest.mark.parametrize("cfg", PATTERN_CONFIGS)
@pytest.mark.parametrize("name", ["puzzle1", "puzzle2", "puzzle3"])
def test_pattern_configs_solve_named_puzzles(cfg, name):
    grid = sudoku.read_sudoku(PUZZLE_DIR / f"{name}.txt")
    stats = SolveStats()
    solved = solver.solve_board(Board.from_grid(grid), cfg, stats)
    result = solved.to_grid()
    assert sudoku.check_solution(result)
    assert all(grid[r][c] in (".", result[r][c]) for r in range(9) for c in range(9))
    assert stats.region_visits > 0


def test_search_skips_branch_that_fails_to_place():
    b = empty_board()
    for idx in (21, 30, 39, 48, 57, 66, 75):
        assert b.eliminate(idx, 5)  # 5 в столбце 3 только в клетках 3 и 12
    for d in (1, 2, 3, 4, 7, 8, 9):
        assert b.eliminate(4, d)  # у клетки 4 остались заметки 5 и 6
    assert b.copy().place(4, 5) is False  # ставя 5, мы лишаем столбец 3 обоих кандидатов
    stats = SolveStats()
    result = solver.search(b, SolverConfig(memo=False), stats, set())
    assert result is not None and sudoku.check_solution(result.to_grid())
    assert stats.nodes >= 2  # ветка 5 отброшена, ветка 6 пройдена

def test_search_returns_none_when_all_branches_fail(monkeypatch):
    b = empty_board()
    for d in range(3, 10):
        assert b.eliminate(0, d)  # клетка 0: заметки {1, 2}
    for d in range(2, 10):
        assert b.eliminate(1, d)  # клетка 1 (строка 0): только 1
    for d in (1, 3, 4, 5, 6, 7, 8, 9):
        assert b.eliminate(9, d)  # клетка 9 (столбец 0): только 2
    monkeypatch.setattr(solver, "propagate", lambda board, cfg=None, stats=None: True)
    assert b.copy().place(0, 1) is False  # лишает клетку 1 последней заметки
    assert b.copy().place(0, 2) is False  # лишает клетку 9 последней заметки
    stats = SolveStats()
    assert solver.search(b, SolverConfig(memo=False), stats, set()) is None
    assert stats.nodes == 1  # ни одной ветки не открыто

def degree_board():
    """Клетки 8, 40, 41 имеют по две заметки {1, 2}; открытых клеток в регионах у 40 и 41 меньше."""
    b = empty_board()
    for idx in (8, 40):
        for d in range(3, 10):
            assert b.eliminate(idx, d)
    for idx, d in zip((36, 37, 38, 39, 42, 43, 44), range(3, 10)):
        assert b.place(idx, d)
    return b


def test_select_cell_mrv_degree():
    b = degree_board()
    assert solver.select_cell_mrv(b) == 8  # ничья по заметкам: младший индекс
    assert solver.select_cell_mrv_degree(b) == 40  # у 40 и 41 по 19 открытых клеток против 26
    assert solver.select_cell_mrv_degree(empty_board()) == 0


def test_select_cell_mrv_degree_without_candidates(puzzle1_solution):
    with pytest.raises(ValueError):
        solver.select_cell_mrv_degree(Board.from_grid(puzzle1_solution))


def test_select_cell_digit_min(puzzle1_solution):
    assert solver.select_cell_digit_min(empty_board()) == 0
    b = empty_board()
    for idx in (1, 2, 3, 4):
        assert b.eliminate(idx, 7)  # у цифры 7 меньше всего кандидатов
    for idx in (5, 6, 7, 8):
        assert b.eliminate(idx, 7)
    # 7 осталась только в клетке 0 строки 0 и в других строках
    idx = solver.select_cell_digit_min(b)
    counts = {d: b.digit_cells[d].bit_count() for d in range(1, 10) if b.digit_cells[d]}
    rarest = min(counts, key=counts.get)
    assert rarest == 7
    assert b.digit_cells[7] >> idx & 1 and idx == 0
    with pytest.raises(ValueError):
        solver.select_cell_digit_min(Board.from_grid(puzzle1_solution))


def test_branch_rare_first():
    b = empty_board()
    for d in range(3, 10):
        assert b.eliminate(0, d)  # у клетки 0 заметки {1, 2}
    for idx in (1, 2, 3, 4):
        assert b.eliminate(idx, 2)  # цифра 2 в областях клетки 0 стала реже
    assert solver.branch_asc(b, 0) == [1, 2]
    assert solver.branch_rare_first(b, 0) == [2, 1]


def test_candidate_cells(puzzle1_solution):
    assert solver.candidate_cells(empty_board()) == list(range(81))
    b = empty_board()
    for d in range(3, 10):
        assert b.eliminate(5, d)
    assert solver.candidate_cells(b)[:2] == [5, 0]
    assert solver.candidate_cells(Board.from_grid(puzzle1_solution)) == []


def test_config_new_options():
    assert DEFAULT_CONFIG.branch_all_cells is False and DEFAULT_CONFIG.max_nodes == 0
    with pytest.raises(ValueError):
        SolverConfig(max_nodes=-1)


@pytest.mark.parametrize("cell", ["mrv", "mrv_degree", "digit_min"])
@pytest.mark.parametrize("branch", ["asc", "rare_first"])
def test_all_strategies_solve_puzzle1(cell, branch, puzzle1_grid):
    cfg = SolverConfig(cell_strategy=cell, branch_strategy=branch)
    solved = solver.solve_board(Board.from_grid(puzzle1_grid), cfg)
    assert sudoku.check_solution(solved.to_grid())


@pytest.mark.parametrize("memo", [True, False])
def test_branch_all_cells_solves_and_rejects(memo, puzzle1_grid):
    cfg = SolverConfig(branch_all_cells=True, memo=memo)
    solved = solver.solve_board(Board.from_grid(puzzle1_grid), cfg)
    assert sudoku.check_solution(solved.to_grid())
    bad = [row[:] for row in puzzle1_grid]
    bad[0][2] = "1"
    board = Board.from_grid(bad)
    assert board is None or solver.solve_board(board, cfg) is None


def test_node_limit():
    with pytest.raises(solver.NodeLimitExceeded):
        solver.solve_board(empty_board(), SolverConfig(max_nodes=1))
    assert solver.solve_board(empty_board(), SolverConfig(max_nodes=10_000)) is not None


@pytest.mark.parametrize("name,budget", [("puzzle1", 2), ("puzzle2", 6), ("puzzle3", 4)])
def test_node_count_regression(name, budget):
    """Замер итерации 4: 1, 3 и 2 узла; бюджет с запасом x2."""
    grid = sudoku.read_sudoku(PUZZLE_DIR / f"{name}.txt")
    stats = SolveStats()
    assert solver.solve_board(Board.from_grid(grid), SolverConfig(), stats) is not None
    assert stats.nodes <= budget

def test_count_solutions_limits():
    b = empty_board()
    assert solver.count_solutions(b, limit=1) == 1
    assert solver.count_solutions(b) == 2  # у пустой доски решений больше двух
    assert solver.count_solutions(b, limit=5) == 5
    with pytest.raises(ValueError):
        solver.count_solutions(b, limit=0)


def test_count_solutions_unique_and_none(puzzle1_grid, puzzle1_solution):
    assert solver.count_solutions(Board.from_grid(puzzle1_grid)) == 1
    assert solver.count_solutions(Board.from_grid(puzzle1_solution)) == 1
    assert solver.count_solutions(conflicting_singles_board()) == 0


def test_count_solutions_does_not_mutate_and_counts_nodes(puzzle1_grid):
    b = Board.from_grid(puzzle1_grid)
    snap = snapshot(b)
    stats = SolveStats()
    solver.count_solutions(b, stats=stats)
    assert snapshot(b) == snap and stats.nodes >= 1


def test_count_solutions_with_patterns(puzzle1_grid):
    cfg = SolverConfig(subsets=3, pointing=True)
    assert solver.count_solutions(Board.from_grid(puzzle1_grid), cfg=cfg) == 1


def test_is_unique(puzzle1_grid, puzzle1_solution):
    assert sudoku.is_unique(puzzle1_grid) is True
    assert sudoku.is_unique(puzzle1_solution) is True
    one_digit = [["."] * 9 for _ in range(9)]
    one_digit[0][0] = "5"
    assert sudoku.is_unique(one_digit) is False  # много решений
    dup = [["."] * 9 for _ in range(9)]
    dup[0][0] = dup[0][1] = "5"
    assert sudoku.is_unique(dup) is False  # противоречие во входе