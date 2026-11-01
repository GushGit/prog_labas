import random

import zobrist
from zobrist import ZOBRIST, cell_hash, hash_delta, hash_state


def test_build_table_shape_and_range():
    table = zobrist.build_table()
    assert len(table) == 81 and all(len(row) == 10 for row in table)
    assert all(0 <= v < 2 ** 64 for row in table for v in row)
    assert len({v for row in table for v in row}) == 810


def test_build_table_is_reproducible():  # дефект Z2
    assert zobrist.build_table(47) == zobrist.build_table(47) == ZOBRIST
    assert zobrist.build_table(1) != ZOBRIST


def test_cell_hash_basic():
    assert cell_hash(5, 0) == 0
    assert cell_hash(5, 1 << 3) == ZOBRIST[5][3]
    assert cell_hash(5, 0b1010) == ZOBRIST[5][1] ^ ZOBRIST[5][3]
    assert cell_hash(0, 0b10) != cell_hash(1, 0b10)  # зависит от позиции


def test_cell_hash_is_xor_linear():
    rng = random.Random(1)
    for _ in range(50):
        idx, a, b = rng.randrange(81), rng.randrange(1024), rng.randrange(1024)
        assert cell_hash(idx, a ^ b) == cell_hash(idx, a) ^ cell_hash(idx, b)


def test_hash_state():
    assert hash_state([0] * 81) == 0
    states = [1022] * 81
    expected = 0
    for idx in range(81):
        expected ^= cell_hash(idx, 1022)
    assert hash_state(states) == expected
    changed = states[:]
    changed[10] = 1022 ^ (1 << 4)
    assert hash_state(changed) != hash_state(states)


def test_hash_delta_updates_incrementally():
    rng = random.Random(7)
    states = [rng.randrange(1024) for _ in range(81)]
    h = hash_state(states)
    for _ in range(100):
        idx, new = rng.randrange(81), rng.randrange(1024)
        h ^= hash_delta(idx, states[idx], new)
        states[idx] = new
        assert h == hash_state(states)


def test_hash_delta_single_note_is_one_xor():
    assert hash_delta(3, 1022, 1022 ^ (1 << 5)) == ZOBRIST[3][5]
    assert hash_delta(3, 77, 77) == 0

def test_no_collisions_on_random_walk():
    """Случайное блуждание по надмножеству достижимых позиций: разные позиции дают разные хэши."""
    rng = random.Random(2024)
    states = [1022] * 81
    h = hash_state(states)
    seen = {h: tuple(states)}
    distinct = 1
    for step in range(20000):
        idx = rng.randrange(81)
        old = states[idx]
        if rng.random() < 0.7:
            new = old ^ (1 << rng.randint(1, 9))  # флип заметки, любое состояние допустимо
        else:
            new = 1 | (1 << rng.randint(1, 9))  # «вписать» цифру без чистки заметок
        h ^= hash_delta(idx, old, new)
        states[idx] = new
        if step % 500 == 0:
            assert h == hash_state(states)
        key = tuple(states)
        if h in seen:
            assert seen[h] == key  # тот же хэш допустим только у той же позиции
        else:
            seen[h] = key
            distinct += 1
    assert distinct > 15000
    assert len(seen) == distinct