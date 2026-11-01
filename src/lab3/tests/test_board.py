import random

import pytest

import sudoku
from board import Board
from cell import DEFAULT_STATE, PEN_FLAG, Cell, make_pen
from region import ALL_CELLS, DIRTY_BITS, PEER_MASK, REGIONS
from zobrist import ZOBRIST, hash_state

ROW0 = REGIONS[0].mask


def snapshot(board):
    return (list(board.states), list(board.digit_cells), list(board.placed), list(board.buckets),
            board.empty_mask, board.zobrist, board.dirty, list(board.pending))


def resync(board):
    """Пересчитать производные поля из states, чтобы проверить отдельные ветки validate."""
    board.digit_cells, board.placed, board.buckets, board.empty_mask = Board._derive(board.states)
    board.zobrist = hash_state(board.states)


def hide_nine_in_row0(board):
    """Цифра 9 в строке 0 остаётся только в клетке 0."""
    for c in range(1, 9):
        assert board.eliminate(c, 9)


def test_init_is_empty_board():
    b = Board()
    assert b.states == [DEFAULT_STATE] * 81
    assert b.digit_cells == [0] + [ALL_CELLS] * 9
    assert b.placed == [0] * 10
    assert b.buckets[9] == ALL_CELLS and sum(b.buckets[:9]) == 0
    assert b.empty_mask == ALL_CELLS
    assert b.zobrist == hash_state(b.states)
    assert b.dirty == 0 and b.pending == []
    b.validate()


def test_clear_resets_board():
    b = Board()
    assert b.place(0, 5)
    b.clear()
    assert snapshot(b) == snapshot(Board())


def test_from_grid_puzzle1(puzzle1_grid):
    b = Board.from_grid(puzzle1_grid)
    assert b is not None
    b.validate()
    assert b.to_grid() == puzzle1_grid
    assert sum(1 for s in b.states if s & PEN_FLAG) == 30
    assert b.empty_mask.bit_count() == 51
    assert b.zobrist == hash_state(b.states)


def test_from_grid_solved_and_wrong(puzzle1_solution):
    b = Board.from_grid(puzzle1_solution)
    assert b is not None and b.empty_mask == 0
    assert b.to_grid() == puzzle1_solution
    b.validate()
    wrong = [row[:] for row in puzzle1_solution]
    wrong[0][0], wrong[0][1] = wrong[0][1], wrong[0][0]
    assert Board.from_grid(wrong) is None


def test_from_grid_empty_grid():
    b = Board.from_grid([["."] * 9 for _ in range(9)])
    assert snapshot(b) == snapshot(Board())


def test_from_grid_duplicates_give_none():
    for r1, c1, r2, c2 in ((0, 0, 0, 8), (0, 4, 8, 4), (3, 3, 5, 5)):  # строка, столбец, блок
        grid = [["."] * 9 for _ in range(9)]
        grid[r1][c1] = grid[r2][c2] = "7"
        assert Board.from_grid(grid) is None


def test_from_grid_cell_without_candidates_gives_none():
    grid = [["."] * 9 for _ in range(9)]
    grid[0] = list("12345678.")
    grid[1][8] = "9"
    assert Board.from_grid(grid) is None


def test_from_grid_rejects_bad_shape_and_chars():
    with pytest.raises(ValueError):
        Board.from_grid([["."] * 9 for _ in range(8)])
    with pytest.raises(ValueError):
        Board.from_grid([["."] * 8 for _ in range(9)])
    grid = [["."] * 9 for _ in range(9)]
    grid[4][4] = "0"
    with pytest.raises(ValueError):
        Board.from_grid(grid)
    grid[4][4] = "12"
    with pytest.raises(ValueError):
        Board.from_grid(grid)


def test_to_grid_roundtrip_generated():
    for seed in range(5):
        random.seed(seed)
        grid = sudoku.generate_sudoku(30)
        b = Board.from_grid(grid)
        assert b is not None and b.to_grid() == grid


def test_copy_is_independent():
    b = Board()
    assert b.place(0, 5)
    before = snapshot(b)
    c = b.copy()
    assert snapshot(c) == before
    assert c.place(40, 3) and c.eliminate(10, 7)
    assert snapshot(b) == before
    assert snapshot(c) != before
    b.pending.append((1, 1))
    assert (1, 1) not in c.pending


def test_get_cell_is_snapshot():
    b = Board()
    cell = b.get_cell((1, 2))
    assert cell == Cell((1, 2), DEFAULT_STATE)
    assert b.place(11, 4)
    assert cell.state == DEFAULT_STATE  # старый снимок не изменился
    assert b.get_cell((1, 2)) == Cell((1, 2), make_pen(4))


def test_place_updates_all_structures():
    b = Board()
    before = b.zobrist
    assert b.place(0, 5) is True
    peers = PEER_MASK[0]
    assert b.states[0] == make_pen(5)
    assert b.placed[5] == 1 and b.empty_mask == ALL_CELLS & ~1
    assert b.digit_cells[5] == ALL_CELLS & ~1 & ~peers
    assert all(b.digit_cells[e] == ALL_CELLS & ~1 for e in (1, 2, 3, 4, 6, 7, 8, 9))
    assert b.buckets[8] == peers and b.buckets[9] == ALL_CELLS & ~1 & ~peers
    assert b.buckets[0] == 0
    assert b.zobrist != before and b.zobrist == hash_state(b.states)
    assert b.dirty & DIRTY_BITS[0] == DIRTY_BITS[0]
    assert b.dirty.bit_count() == 23  # 9 строк, 9 столбцов, блоки 0,1,2,3,6
    assert b.pending == []
    b.validate()


def test_place_rejects_pen_cell_and_removed_note():
    b = Board()
    assert b.place(0, 5)
    snap = snapshot(b)
    assert b.place(0, 5) is False and b.place(0, 6) is False  # клетка занята
    assert b.place(1, 5) is False  # 5 снята с соседа по строке
    assert b.place(80, 5) is True  # 5 в другом блоке допустима
    b2 = Board()
    assert b2.eliminate(0, 5)
    snap2 = snapshot(b2)
    assert b2.place(0, 5) is False
    assert snapshot(b2) == snap2
    assert snap != snapshot(b)


def test_place_rejects_digit_out_of_range():
    b = Board()
    for bad in (0, 10, -1):
        with pytest.raises(ValueError):
            b.place(0, bad)


def test_place_detects_contradiction_in_peer():
    b = Board()
    for c in range(8):
        assert b.place(c, c + 1)
    assert b.place(17, 9) is False  # (0, 8) осталась бы без заметок


def test_place_detects_hidden_contradiction():
    b = Board()
    hide_nine_in_row0(b)
    assert b.pending == [(0, 9)]
    assert b.place(0, 5) is False  # у клетки 0 пропала бы заметка 9, и 9 некуда встать в строке


def test_eliminate_updates_structures():
    b = Board()
    before = b.zobrist
    assert b.eliminate(10, 3) is True
    assert b.states[10] == DEFAULT_STATE ^ (1 << 3)
    assert b.digit_cells[3] == ALL_CELLS & ~(1 << 10)
    assert b.buckets[8] == 1 << 10 and b.buckets[9] == ALL_CELLS & ~(1 << 10)
    assert b.zobrist == before ^ ZOBRIST[10][3]  # ровно один XOR
    assert b.dirty == DIRTY_BITS[10]
    assert b.pending == []
    b.validate()


def test_eliminate_missing_note_changes_nothing():
    b = Board()
    assert b.eliminate(10, 3)
    snap = snapshot(b)
    assert b.eliminate(10, 3) is True
    assert snapshot(b) == snap


def test_eliminate_on_pen_cell():
    b = Board()
    assert b.place(0, 5)
    snap = snapshot(b)
    assert b.eliminate(0, 3) is True  # у pen-клетки такой цифры нет
    assert snapshot(b) == snap
    assert b.eliminate(0, 5) is False  # нельзя снять поставленную цифру


def test_eliminate_last_note_is_contradiction():
    b = Board()
    for d in range(1, 9):
        assert b.eliminate(0, d)
    assert b.buckets[1] == 1
    assert b.eliminate(0, 9) is False
    assert b.states[0] == 0 and b.buckets[0] == 1


def test_eliminate_rejects_digit_out_of_range():
    b = Board()
    for bad in (0, 10, -3):
        with pytest.raises(ValueError):
            b.eliminate(0, bad)


def test_eliminate_creates_pending_hidden_single():
    b = Board()
    hide_nine_in_row0(b)
    assert b.pending == [(0, 9)]
    assert b.eliminate(0, 9) is False  # теперь цифре 9 некуда встать в строке


def test_check_digit_branches():
    b = Board()
    assert b._check_digit(0, 9) is True and b.pending == []  # много кандидатов
    assert b.place(0, 9)
    b.pending.clear()
    assert b._check_digit(0, 9) is True and b.pending == []  # цифра уже стоит в регионах клетки
    b2 = Board()
    b2.digit_cells[9] &= ~ROW0
    assert b2._check_digit(0, 9) is False  # в строке 0 для 9 нет места


def test_derive_matches_board():
    b = Board()
    assert Board._derive(b.states) == (b.digit_cells, b.placed, b.buckets, b.empty_mask)
    assert b.place(0, 5) and b.place(40, 2)
    assert Board._derive(b.states) == (b.digit_cells, b.placed, b.buckets, b.empty_mask)


@pytest.mark.parametrize("seed", range(5))
def test_random_operations_keep_invariants(seed):
    random.seed(seed)
    solution = sudoku.generate_sudoku(81)
    rng = random.Random(seed)
    b = Board()
    for step in range(250):
        idx = rng.randrange(81)
        true_digit = int(solution[idx // 9][idx % 9])
        if rng.random() < 0.15 and not b.states[idx] & PEN_FLAG:
            assert b.place(idx, true_digit)
        else:
            d = rng.choice([x for x in range(1, 10) if x != true_digit])
            assert b.eliminate(idx, d)
        b.validate()
        assert b.zobrist == hash_state(b.states)
        if step == 100:
            snap, clone = snapshot(b), b.copy()
            assert clone.eliminate(idx, 1 if true_digit != 1 else 2) in (True,)
            assert snapshot(b) == snap
    for r, row in enumerate(b.to_grid()):
        for c, v in enumerate(row):
            assert v in (".", solution[r][c])


def test_validate_detects_bad_cell_states():
    for bad in (PEN_FLAG, make_pen(2) | (1 << 3), 1 << 10):
        b = Board()
        b.states[0] = bad
        with pytest.raises(ValueError, match="Битое состояние"):
            b.validate()


def test_validate_detects_wrong_length():
    b = Board()
    b.states.pop()
    with pytest.raises(ValueError, match="81"):
        b.validate()


@pytest.mark.parametrize("field,message", [
    ("digit_cells", "Рассинхронизация digit_cells"),
    ("placed", "Рассинхронизация placed"),
    ("buckets", "Рассинхронизация buckets"),
])
def test_validate_detects_desync_of_lists(field, message):
    b = Board()
    getattr(b, field)[3] ^= 1
    with pytest.raises(ValueError, match=message):
        b.validate()


def test_validate_detects_desync_of_scalars():
    b = Board()
    b.empty_mask ^= 1
    with pytest.raises(ValueError, match="empty_mask"):
        b.validate()
    b = Board()
    b.zobrist ^= 1
    with pytest.raises(ValueError, match="zobrist"):
        b.validate()
    b = Board()
    b.dirty = 1 << 27
    with pytest.raises(ValueError, match="dirty"):
        b.validate()


def test_validate_detects_cell_without_notes():
    b = Board()
    b.states[0] = 0
    resync(b)
    with pytest.raises(ValueError, match="без заметок"):
        b.validate()


def test_validate_detects_duplicate_pen_digit():
    b = Board()
    b.states[0] = b.states[1] = make_pen(5)
    resync(b)
    with pytest.raises(ValueError, match="Повтор цифры 5"):
        b.validate()


def test_validate_detects_note_equal_to_peer_digit():
    b = Board()
    b.states[0] = make_pen(5)
    resync(b)
    with pytest.raises(ValueError, match="Заметка 5"):
        b.validate()