import dataclasses

import pytest

import region
from region import ALL_CELLS, CELL_REGIONS, DIRTY_BITS, PEER_MASK, REGIONS, Region
from region_key import RegionKey
from utils import iter_bits, mask_from_indices


def test_region_key_values():
    assert [k.value for k in RegionKey] == [0, 1, 2]
    assert [k.name for k in RegionKey] == ["ROW", "COL", "BOX"]


def test_all_cells():
    assert ALL_CELLS == (1 << 81) - 1
    assert ALL_CELLS.bit_count() == 81


def test_of_tables():
    assert len(region.ROW_OF) == len(region.COL_OF) == len(region.BOX_OF) == 81
    assert (region.ROW_OF[40], region.COL_OF[40], region.BOX_OF[40]) == (4, 4, 4)
    assert (region.ROW_OF[80], region.COL_OF[80], region.BOX_OF[80]) == (8, 8, 8)
    assert region.BOX_OF[7] == 2


def test_region_cells():
    assert region.region_cells(RegionKey.ROW, 2) == tuple(range(18, 27))
    assert region.region_cells(RegionKey.COL, 3) == tuple(range(3, 81, 9))
    assert region.region_cells(RegionKey.BOX, 4) == (30, 31, 32, 39, 40, 41, 48, 49, 50)
    assert region.region_cells(RegionKey.BOX, 2) == (6, 7, 8, 15, 16, 17, 24, 25, 26)


def test_build_regions():
    regions = region.build_regions()
    assert len(regions) == 27
    assert regions == REGIONS
    for rid, reg in enumerate(regions):
        assert reg.region_id == rid
        assert len(reg.cells) == 9
        assert reg.mask.bit_count() == 9
        assert reg.mask == mask_from_indices(reg.cells)
    assert [r.key for r in regions[:9]] == [RegionKey.ROW] * 9
    assert [r.key for r in regions[18:]] == [RegionKey.BOX] * 9


def test_regions_partition_each_kind():
    for start in (0, 9, 18):
        masks = [REGIONS[start + i].mask for i in range(9)]
        assert sum(masks) == ALL_CELLS  # маски не пересекаются и покрывают все 81 клетку


def test_region_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        REGIONS[0].index = 5
    assert isinstance(REGIONS[0], Region)


def test_cell_regions():
    assert CELL_REGIONS[0] == (0, 9, 18)
    assert CELL_REGIONS[80] == (8, 17, 26)
    assert CELL_REGIONS[40] == (4, 13, 22)
    for idx in range(81):
        assert CELL_REGIONS[idx] == (region.ROW_OF[idx], 9 + region.COL_OF[idx],
                                     18 + region.BOX_OF[idx])
        assert all(idx in REGIONS[rid].cells for rid in CELL_REGIONS[idx])
    assert region.build_cell_regions(REGIONS) == CELL_REGIONS


def test_peer_mask():
    expected = ({1, 2, 3, 4, 5, 6, 7, 8} | {9, 18, 27, 36, 45, 54, 63, 72} | {10, 11, 19, 20})
    assert set(iter_bits(PEER_MASK[0])) == expected
    for idx in range(81):
        assert PEER_MASK[idx].bit_count() == 20
        assert not PEER_MASK[idx] >> idx & 1
        for other in iter_bits(PEER_MASK[idx]):
            assert PEER_MASK[other] >> idx & 1  # симметрия
    assert region.build_peer_masks(REGIONS, CELL_REGIONS) == PEER_MASK


def test_dirty_bits():
    assert DIRTY_BITS[0] == 1 | (1 << 9) | (1 << 18)
    for idx in range(81):
        assert DIRTY_BITS[idx].bit_count() == 3
        assert DIRTY_BITS[idx] < 1 << 27
    assert region.build_dirty_bits(CELL_REGIONS) == DIRTY_BITS