import random

import pytest

import patterns
import solver
import sudoku
from board import Board
from cell import DEFAULT_STATE, pen_digit
from region import ALL_CELLS, REGIONS
from solver import DEFAULT_CONFIG, SolverConfig
from utils import mask_from_indices

PAIRS = SolverConfig(subsets=2)
TRIPLES = SolverConfig(subsets=3)
POINTING = SolverConfig(pointing=True)
ALL_PATTERNS = SolverConfig(subsets=3, pointing=True)


def keep_only(board, idx, digits):
    """У клетки idx остаются только заметки digits."""
    for d in range(1, 10):
        if d not in digits:
            assert board.eliminate(idx, d)


def drop(board, digit, cells):
    """Снять заметку digit у клеток cells."""
    for idx in cells:
        assert board.eliminate(idx, digit)


def snapshot(board):
    return list(board.states), board.zobrist


def erased_puzzle(seed, keep):
    """Полная сетка и пазл из неё с keep подсказками."""
    random.seed(seed)
    full = sudoku.generate_sudoku(81)
    rng = random.Random(seed)
    grid = [row[:] for row in full]
    for i in rng.sample(range(81), 81 - keep):
        grid[i // 9][i % 9] = "."
    return full, grid


def assert_consistent(board, full):
    """Цифры полной сетки не потеряны: pen совпадает, заметка на месте."""
    for idx in range(81):
        d = int(full[idx // 9][idx % 9])
        state = board.states[idx]
        if state & 1:
            assert pen_digit(state) == d
        else:
            assert state >> d & 1


def total_candidates(board):
    return sum(m.bit_count() for m in board.digit_cells)


# --- чистые функции ---

def test_build_intersections():
    inter = patterns.INTERSECTIONS
    assert len(inter) == 27
    assert all(len(x) == 3 for x in inter[:18]) and all(len(x) == 6 for x in inter[18:])
    assert inter[0] == tuple(REGIONS[i].mask for i in (18, 19, 20))
    assert inter[13] == tuple(REGIONS[i].mask for i in (19, 22, 25))
    assert inter[18] == tuple(REGIONS[i].mask for i in (0, 1, 2, 9, 10, 11))
    assert inter[26] == tuple(REGIONS[i].mask for i in (6, 7, 8, 15, 16, 17))
    assert patterns.build_intersections() == inter


def test_intersection_targets():
    box0, dsts = REGIONS[18].mask, patterns.INTERSECTIONS[18]
    cells_d = ALL_CELLS & ~mask_from_indices([9, 10, 11, 18, 19, 20])
    assert patterns.intersection_targets(cells_d, box0, dsts) == mask_from_indices(range(3, 9))
    assert patterns.intersection_targets(ALL_CELLS, box0, dsts) == 0  # кандидаты не в одной линии
    assert patterns.intersection_targets(1, box0, dsts) == 0  # один кандидат: это одиночка


def test_find_subset_naked_pair():
    items = [(0, 0b110), (1, 0b110), (2, 0b1110), (3, 0b11100)]
    assert patterns.find_subset_eliminations(items, 2, 4) == [(2, 0b110), (3, 0b100)]


def test_find_subset_naked_triple_distributed():
    items = [(0, 0b110), (1, 0b1100), (2, 0b1010), (3, 0b11010), (4, 0b111000)]
    assert patterns.find_subset_eliminations(items, 3, 5) == [(3, 0b1010), (4, 0b1000)]


def test_find_subset_hidden_triple_empty_intersection():  # дефект P3
    items = [(1, 0b011), (2, 0b110), (3, 0b101), (4, 0b1111), (5, 0b11110)]
    assert patterns.find_subset_eliminations(items, 3, 5) == [(4, 0b111), (5, 0b110)]


def test_find_subset_nothing_to_remove():
    items = [(0, 0b110), (1, 0b1010), (2, 0b1100)]
    assert patterns.find_subset_eliminations(items, 2, 5) == []


def test_find_subset_not_applicable_when_k_too_big():
    items = [(0, 0b110), (1, 0b110), (2, 0b1110), (3, 0b11100)]
    assert patterns.find_subset_eliminations(items, 2, 3) == []


def test_find_subset_contradiction():
    items = [(0, 0b110), (1, 0b110), (2, 0b110)]
    assert patterns.find_subset_eliminations(items, 3, 5) is None
    assert patterns.find_subset_eliminations(items, 2, 5) is not None


def test_item_builders():
    b = Board()
    keep_only(b, 0, {1, 2})
    assert b.place(1, 7)
    cells = dict(patterns.cell_items(b, REGIONS[0]))
    assert sorted(cells) == [0, 2, 3, 4, 5, 6, 7, 8]
    assert cells[0] == 0b110 and cells[2] == DEFAULT_STATE ^ (1 << 7)
    digits = dict(patterns.digit_items(b, REGIONS[0]))
    assert 7 not in digits and len(digits) == 8
    assert digits[1] == REGIONS[0].mask & ~2


def test_apply_eliminations_cells_and_digits():
    b = Board()
    assert patterns.apply_eliminations(b, [(0, 0b110)], True) is True
    assert b.states[0] == DEFAULT_STATE ^ 0b110
    b = Board()
    assert patterns.apply_eliminations(b, [(5, mask_from_indices([0, 1]))], False) is True
    assert b.states[0] == b.states[1] == DEFAULT_STATE ^ (1 << 5)


def test_apply_eliminations_detects_contradiction():
    b = Board()
    keep_only(b, 0, {1})
    assert patterns.apply_eliminations(b, [(0, 0b10)], True) is False
    b = Board()
    keep_only(b, 0, {5})
    assert patterns.apply_eliminations(b, [(5, 1)], False) is False


# --- process_region вручную ---

def test_process_region_nothing_to_do():
    b = Board()
    snap = snapshot(b)
    for region in REGIONS:
        assert patterns.process_region(b, region, ALL_PATTERNS) is False
    assert snapshot(b) == snap


def test_process_region_full_board_breaks_early(puzzle1_solution):
    b = Board.from_grid(puzzle1_solution)
    assert patterns.process_region(b, REGIONS[0], ALL_PATTERNS) is False


def test_naked_pair():
    b = Board()
    for idx in (0, 1):
        keep_only(b, idx, {1, 2})
    assert patterns.process_region(b, REGIONS[0], PAIRS) is True
    assert b.states[0] == b.states[1] == 0b110
    assert all(b.states[c] == DEFAULT_STATE ^ 0b110 for c in range(2, 9))
    assert b.states[9] == DEFAULT_STATE  # другие регионы не тронуты
    b.validate()


def test_naked_triple_distributed():
    b = Board()
    for idx, digits in ((0, {1, 2}), (1, {2, 3}), (2, {1, 3})):
        keep_only(b, idx, digits)
    assert patterns.process_region(b, REGIONS[0], TRIPLES) is True
    assert all(b.states[c] == DEFAULT_STATE ^ 0b1110 for c in range(3, 9))
    assert [b.states[c] for c in range(3)] == [0b110, 0b1100, 0b1010]
    b.validate()


def test_hidden_pair():
    b = Board()
    for d in (1, 2):
        drop(b, d, range(2, 9))
    assert patterns.process_region(b, REGIONS[0], PAIRS) is True
    assert b.states[0] == b.states[1] == 0b110
    assert b.states[2] == DEFAULT_STATE ^ 0b110
    b.validate()


def test_hidden_triple_with_empty_intersection():  # дефект P3
    b = Board()
    drop(b, 1, range(2, 9))
    drop(b, 2, [0] + list(range(3, 9)))
    drop(b, 3, [1] + list(range(3, 9)))
    assert patterns.process_region(b, REGIONS[0], TRIPLES) is True
    assert [b.states[c] for c in range(3)] == [0b1010, 0b110, 0b1100]
    b.validate()


def test_hidden_triple_is_not_found_by_pairs_only():
    b = Board()
    drop(b, 1, range(2, 9))
    drop(b, 2, [0] + list(range(3, 9)))
    drop(b, 3, [1] + list(range(3, 9)))
    assert patterns.process_region(b, REGIONS[0], PAIRS) is False


def test_subset_contradiction():
    b = Board()
    for idx in (0, 1, 2):
        keep_only(b, idx, {1, 2})
    assert patterns.process_region(b, REGIONS[0], PAIRS) is None


def test_pointing_row():
    b = Board()
    drop(b, 5, [9, 10, 11, 18, 19, 20])
    assert patterns.process_region(b, REGIONS[18], POINTING) is True
    removed = [9, 10, 11, 18, 19, 20, 3, 4, 5, 6, 7, 8]
    assert b.digit_cells[5] == ALL_CELLS & ~mask_from_indices(removed)
    b.validate()


def test_pointing_column():
    b = Board()
    drop(b, 5, [1, 2, 10, 11, 19, 20])
    assert patterns.process_region(b, REGIONS[18], POINTING) is True
    removed = [1, 2, 10, 11, 19, 20, 27, 36, 45, 54, 63, 72]
    assert b.digit_cells[5] == ALL_CELLS & ~mask_from_indices(removed)


def test_claiming():
    b = Board()
    drop(b, 5, range(3, 9))
    assert patterns.process_region(b, REGIONS[0], POINTING) is True
    removed = list(range(3, 9)) + [9, 10, 11, 18, 19, 20]
    assert b.digit_cells[5] == ALL_CELLS & ~mask_from_indices(removed)


def test_pointing_ignores_single_candidate():
    b = Board()
    removed = [1, 2, 9, 10, 11, 18, 19, 20]
    drop(b, 5, removed)
    assert b.pending == [(0, 5)]
    assert patterns.process_region(b, REGIONS[18], POINTING) is False
    assert b.digit_cells[5] == ALL_CELLS & ~mask_from_indices(removed)


def test_pointing_contradiction():
    b = Board()
    keep_only(b, 3, {5})
    drop(b, 5, [9, 10, 11, 18, 19, 20])
    assert patterns.process_region(b, REGIONS[18], POINTING) is None


def test_pointing_disabled_by_config():
    b = Board()
    drop(b, 5, [9, 10, 11, 18, 19, 20])
    assert patterns.process_region(b, REGIONS[18], TRIPLES) is False


# --- корректность на реальных пазлах ---

@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("cfg", [PAIRS, TRIPLES, POINTING, ALL_PATTERNS],
                         ids=["pairs", "triples", "pointing", "all"])
def test_process_region_never_removes_true_digit(seed, cfg):
    full, grid = erased_puzzle(seed, 24)
    board = Board.from_grid(grid)
    assert board is not None
    for _ in range(3):
        for region in REGIONS:
            assert patterns.process_region(board, region, cfg) is not None
            assert_consistent(board, full)
    board.validate()


@pytest.mark.parametrize("seed", range(8))
def test_propagate_with_patterns_never_removes_true_digit(seed):
    full, grid = erased_puzzle(seed, 26)
    totals = {}
    for name, cfg in (("base", DEFAULT_CONFIG), ("pairs", PAIRS), ("triples", TRIPLES),
                      ("pointing", POINTING), ("all", ALL_PATTERNS)):
        board = Board.from_grid(grid)
        assert solver.propagate(board, cfg) is True
        assert_consistent(board, full)
        board.validate()
        assert board.buckets[1] == 0 and board.pending == []
        if cfg is not DEFAULT_CONFIG:
            assert board.dirty == 0
        totals[name] = total_candidates(board)
    assert totals["all"] <= totals["triples"] <= totals["pairs"] <= totals["base"]
    assert totals["all"] <= totals["pointing"] <= totals["base"]