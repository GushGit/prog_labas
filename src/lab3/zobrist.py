import random
import typing as tp

SEED = 47
Table = tp.Tuple[tp.Tuple[int, ...], ...]


def build_table(seed: int = SEED) -> Table:
    """Таблица 81×10 случайных 64-битных чисел; столбец = номер бита состояния."""
    rng = random.Random(seed)
    return tuple(tuple(rng.getrandbits(64) for _ in range(10)) for _ in range(81))


ZOBRIST = build_table()


def cell_hash(idx: int, state: int) -> int:
    """Хэш клетки: XOR значений таблицы по установленным битам состояния."""
    row = ZOBRIST[idx]
    h = 0
    while state:
        low = state & -state
        h ^= row[low.bit_length() - 1]
        state ^= low
    return h


def hash_state(states: tp.Sequence[int]) -> int:
    """Полный пересчёт хэша доски по списку состояний (81 int)."""
    h = 0
    for idx, state in enumerate(states):
        h ^= cell_hash(idx, state)
    return h


def hash_delta(idx: int, old: int, new: int) -> int:
    """Изменение хэша при смене состояния клетки: XOR по битам old ^ new."""
    return cell_hash(idx, old ^ new)