from __future__ import annotations

import typing as tp
from itertools import combinations

from board import Board
from region import REGIONS, Region
from utils import iter_bits

if tp.TYPE_CHECKING:
    from solver import SolverConfig

Item = tp.Tuple[int, int]
Found = tp.List[tp.Tuple[int, int]]


def build_intersections() -> tp.Tuple[tp.Tuple[int, ...], ...]:
    """Для каждого региона маски «перпендикулярных»: у блока 3 строки и 3 столбца, у линии 3 блока."""
    result = []
    for rid in range(27):
        if rid < 9:
            ids = [18 + rid // 3 * 3 + j for j in range(3)]
        elif rid < 18:
            ids = [18 + j * 3 + (rid - 9) // 3 for j in range(3)]
        else:
            b = rid - 18
            ids = [b // 3 * 3 + j for j in range(3)] + [9 + b % 3 * 3 + j for j in range(3)]
        result.append(tuple(REGIONS[i].mask for i in ids))
    return tuple(result)


INTERSECTIONS = build_intersections()


def intersection_targets(cells_d: int, src_mask: int, dst_masks: tp.Sequence[int]) -> int:
    """Pointing/claiming: клетки, где нужно снять цифру, либо 0.

    cells_d: маска клеток-кандидатов цифры; src_mask: маска региона. Если кандидаты цифры в
    регионе (их не меньше двух) целиком лежат в одной из dst_masks, цифру нужно снять у всех
    остальных кандидатов этой dst. Для блока dst это строки и столбцы (pointing),
    для линии это блоки (claiming).
    """
    s = cells_d & src_mask
    if s.bit_count() < 2:
        return 0
    for dst in dst_masks:
        if not s & ~dst:
            return cells_d & dst & ~src_mask
    return 0


def find_subset_eliminations(items: tp.Sequence[Item], k: int, m: int) -> tp.Optional[Found]:
    """Что снять по правилу подмножества размера k. None означает противоречие.

    items: пары (ключ, маска) всех m элементов региона. Одно правило описывает оба вида:
    «k элементов, у которых объединение масок ровно из k бит, занимают эти k бит целиком,
    и у остальных элементов эти биты снимаются». Naked-подмножество размера k на клетках
    равно hidden-подмножеству размера m-k на цифрах, поэтому функцию вызывают на обоих видах.
    Возвращает список (ключ, биты для снятия).
    """
    if k > m - 2:
        return []
    candidates = [it for it in items if 2 <= it[1].bit_count() <= k]
    found: Found = []
    for combo in combinations(candidates, k):
        union = 0
        for _, mask in combo:
            union |= mask
        n = union.bit_count()
        if n < k:
            return None
        if n == k:
            keys = {key for key, _ in combo}
            for key, mask in items:
                if key not in keys and mask & union:
                    found.append((key, mask & union))
    return found


def cell_items(board: Board, region: Region) -> tp.List[Item]:
    """Вид «клетки»: (idx, заметки) для не-pen клеток региона."""
    states = board.states
    return [(i, states[i]) for i in iter_bits(board.empty_mask & region.mask)]


def digit_items(board: Board, region: Region) -> tp.List[Item]:
    """Вид «цифры»: (d, маска клеток-кандидатов) для цифр, не поставленных в регионе."""
    digit_cells = board.digit_cells
    return [(d, m) for d in range(1, 10) if (m := digit_cells[d] & region.mask)]


def apply_eliminations(board: Board, found: Found, cells_view: bool) -> bool:
    """Применить результат find_subset_eliminations. False: противоречие.

    cells_view=True: пары (idx, биты цифр); иначе пары (цифра, биты клеток).
    """
    for key, bits in found:
        for b in iter_bits(bits):
            ok = board.eliminate(key, b) if cells_view else board.eliminate(b, key)
            if not ok:
                return False
    return True


def process_region(board: Board, region: Region, cfg: SolverConfig) -> tp.Optional[bool]:
    """Один заход на регион: подмножества на обоих видах, затем pointing/claiming.

    None: противоречие. True: что-то изменилось. False: изменений нет.
    """
    before = board.zobrist
    open_count = (board.empty_mask & region.mask).bit_count()
    for cells_view in (True, False):
        for k in range(2, cfg.subsets + 1):
            if k > open_count - 2:
                break
            items = cell_items(board, region) if cells_view else digit_items(board, region)
            found = find_subset_eliminations(items, k, open_count)
            if found is None or not apply_eliminations(board, found, cells_view):
                return None
    if cfg.pointing:
        dst_masks = INTERSECTIONS[region.region_id]
        for d in range(1, 10):
            targets = intersection_targets(board.digit_cells[d], region.mask, dst_masks)
            for idx in iter_bits(targets):
                if not board.eliminate(idx, d):
                    return None
    return board.zobrist != before