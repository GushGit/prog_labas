from __future__ import annotations

import typing as tp
from dataclasses import dataclass

from region_key import RegionKey
from utils import mask_from_indices

ALL_CELLS = (1 << 81) - 1
ROW_OF = tuple(i // 9 for i in range(81))
COL_OF = tuple(i % 9 for i in range(81))
BOX_OF = tuple((i // 27) * 3 + (i % 9) // 3 for i in range(81))


@dataclass(frozen=True)
class Region:
    """Статичный регион: вид, номер внутри вида, клетки (индексы) и их 81-битная маска."""

    key: RegionKey
    index: int
    cells: tp.Tuple[int, ...]
    mask: int

    @property
    def region_id(self) -> int:
        """Сквозной номер: 0..8 строки, 9..17 столбцы, 18..26 блоки."""
        return self.key.value * 9 + self.index


def region_cells(key: RegionKey, index: int) -> tp.Tuple[int, ...]:
    """Индексы клеток региона заданного вида и номера."""
    if key == RegionKey.ROW:
        return tuple(index * 9 + c for c in range(9))
    if key == RegionKey.COL:
        return tuple(r * 9 + index for r in range(9))
    r0, c0 = index // 3 * 3, index % 3 * 3
    return tuple((r0 + dr) * 9 + c0 + dc for dr in range(3) for dc in range(3))


def build_regions() -> tp.Tuple[Region, ...]:
    """Все 27 регионов в порядке: строки, столбцы, блоки."""
    return tuple(
        Region(key, i, cells, mask_from_indices(cells))
        for key in RegionKey
        for i in range(9)
        for cells in (region_cells(key, i),)
    )


def build_cell_regions(regions: tp.Sequence[Region]) -> tp.Tuple[tp.Tuple[int, ...], ...]:
    """Для каждой клетки номера её регионов (строка, столбец, блок)."""
    ids: tp.List[tp.List[int]] = [[] for _ in range(81)]
    for rid, region in enumerate(regions):
        for idx in region.cells:
            ids[idx].append(rid)
    return tuple(tuple(x) for x in ids)


def build_peer_masks(
    regions: tp.Sequence[Region], cell_regions: tp.Sequence[tp.Sequence[int]]
) -> tp.Tuple[int, ...]:
    """Маска 20 соседей каждой клетки (без неё самой)."""
    masks = []
    for idx in range(81):
        m = 0
        for rid in cell_regions[idx]:
            m |= regions[rid].mask
        masks.append(m & ~(1 << idx))
    return tuple(masks)


def build_dirty_bits(cell_regions: tp.Sequence[tp.Sequence[int]]) -> tp.Tuple[int, ...]:
    """27-битная маска трёх регионов каждой клетки."""
    return tuple(mask_from_indices(rids) for rids in cell_regions)


REGIONS = build_regions()
CELL_REGIONS = build_cell_regions(REGIONS)
PEER_MASK = build_peer_masks(REGIONS, CELL_REGIONS)
DIRTY_BITS = build_dirty_bits(CELL_REGIONS)