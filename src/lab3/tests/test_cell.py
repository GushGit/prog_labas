import pytest

import cell
from cell import Cell
from region_key import RegionKey


def test_constants():
    assert cell.PEN_FLAG == 1
    assert cell.NOTES_MASK == 0b1111111110
    assert cell.DEFAULT_STATE == 1022
    assert Cell.DEFAULT_STATE == 1022


def test_is_pen():
    assert cell.is_pen(1)
    assert cell.is_pen(cell.make_pen(4))
    assert not cell.is_pen(cell.DEFAULT_STATE)
    assert not cell.is_pen(0)


def test_count_notes():
    assert cell.count_notes(cell.DEFAULT_STATE) == 9
    assert cell.count_notes(0) == 0
    assert cell.count_notes(0b110) == 2
    assert cell.count_notes(cell.make_pen(5)) == 0  # дефект C3: pen не равна клетке с 1 заметкой


def test_notes_of():
    assert cell.notes_of(cell.DEFAULT_STATE) == list(range(1, 10))
    assert cell.notes_of(0b1010) == [1, 3]
    assert cell.notes_of(0) == []
    with pytest.raises(ValueError):
        cell.notes_of(cell.make_pen(2))


def test_pen_digit():
    assert cell.pen_digit(cell.make_pen(7)) == 7
    assert cell.pen_digit(cell.DEFAULT_STATE) == 0
    assert cell.pen_digit(1) == 0  # pen без цифры


def test_make_pen():
    assert cell.make_pen(3) == 1 | (1 << 3)
    for bad in (0, 10):
        with pytest.raises(ValueError):
            cell.make_pen(bad)


def test_init_and_properties():
    c = Cell((1, 2))
    assert c.pos == (1, 2)
    assert c.state == cell.DEFAULT_STATE
    assert c.idx == 11
    assert Cell((0, 0), 6).state == 6


def test_cell_is_immutable():
    c = Cell((0, 0))
    with pytest.raises(AttributeError):
        c.state = 0
    with pytest.raises(AttributeError):
        c.pos = (1, 1)


def test_eq_and_hash():
    a, b = Cell((0, 0), 6), Cell((0, 0), 6)
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1
    assert a != Cell((0, 0), 4)
    assert a != Cell((0, 1), 6)
    assert (a == 5) is False


def test_lt():
    a = Cell((0, 0), 0b110)  # 2 заметки
    b = Cell((0, 1), 0b10)   # 1 заметка
    c = Cell((0, 0), 0b10)   # 1 заметка, позиция раньше
    assert sorted([a, b, c]) == [c, b, a]
    with pytest.raises(TypeError):
        a < 5


def test_bit_operators():
    a, b = Cell((0, 0), 0b0110), Cell((0, 1), 0b0011)
    assert a & b == 0b0010
    assert a | b == 0b0111
    assert a ^ b == 0b0101


def test_repr():
    text = repr(Cell((2, 3), 0b110))
    assert "(2, 3)" in text and "0b110" in text


def test_getitem():
    c = Cell((4, 7))
    assert c[RegionKey.ROW] == 4
    assert c[RegionKey.COL] == 7
    assert c[RegionKey.BOX] == 5
    with pytest.raises(KeyError):
        c["row"]


def test_floordiv_collinear():
    assert Cell((0, 0)) // Cell((0, 5))
    assert Cell((0, 0)) // Cell((5, 0))
    assert not Cell((0, 0)) // Cell((5, 5))
    assert not Cell((0, 0)) // Cell((1, 1))  # один блок, но не коллинеарны


def test_truediv_same_region():
    assert Cell((0, 0)) / Cell((0, 8))
    assert Cell((0, 0)) / Cell((8, 0))
    assert Cell((0, 0)) / Cell((1, 1))
    assert not Cell((0, 0)) / Cell((4, 4))


def test_method_delegates():
    pen = Cell((0, 0), cell.make_pen(6))
    plain = Cell((0, 0), 0b110)
    assert pen.is_pen() and not plain.is_pen()
    assert pen.pen_digit() == 6 and plain.pen_digit() == 0
    assert plain.count_notes() == 2 and pen.count_notes() == 0
    assert plain.get_notes() == [1, 2]
    with pytest.raises(ValueError):
        pen.get_notes()


def test_read_state():
    default = Cell((0, 0))
    pen = Cell((0, 0), cell.make_pen(3))
    assert not default.read_state(0) and default.read_state(5)
    assert pen.read_state(0) and pen.read_state(3) and not pen.read_state(4)
    for bad in (-1, 10):
        with pytest.raises(ValueError):
            default.read_state(bad)


def test_write_state_flips_note():
    c = Cell((0, 0))
    off = c.write_state(5)
    assert off.state == cell.DEFAULT_STATE ^ (1 << 5)
    assert c.state == cell.DEFAULT_STATE  # оригинал не тронут
    assert off.write_state(5).state == cell.DEFAULT_STATE


def test_write_state_mark_mode():
    pen = Cell((3, 4)).write_state(5, True)
    assert pen.state == cell.make_pen(5)
    assert pen.pos == (3, 4)


def test_write_state_rejects_bad_input():
    with pytest.raises(ValueError):
        Cell((0, 0)).write_state(0)
    with pytest.raises(ValueError):
        Cell((0, 0)).write_state(10, True)
    with pytest.raises(ValueError):  # дефект C5: заметки pen-клетки менять нельзя
        Cell((0, 0), cell.make_pen(2)).write_state(3)


def test_clear_notes():
    c = Cell((0, 0))
    cleared = c.clear_notes()
    assert cleared.state == 0 and cleared.count_notes() == 0
    assert c.state == cell.DEFAULT_STATE
    pen = Cell((0, 0), cell.make_pen(4))
    assert pen.clear_notes() == pen  # дефект C5: цифра pen-клетки не теряется