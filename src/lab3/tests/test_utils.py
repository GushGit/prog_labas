import pytest

import utils


def test_get_digit_flag():
    assert utils.get_digit_flag(0) == 1
    assert utils.get_digit_flag(3) == 8
    assert utils.get_digit_flag(10) == 1024


def test_lowest_bit_index():
    assert utils.lowest_bit_index(0b1000) == 3
    assert utils.lowest_bit_index(0b1010) == 1
    assert utils.lowest_bit_index(1 << 80) == 80


@pytest.mark.parametrize("bad", [0, -4])
def test_lowest_bit_index_rejects_non_positive(bad):
    with pytest.raises(ValueError):
        utils.lowest_bit_index(bad)


def test_iter_bits():
    assert list(utils.iter_bits(0)) == []
    assert list(utils.iter_bits(0b101001)) == [0, 3, 5]
    assert list(utils.iter_bits((1 << 80) | 1)) == [0, 80]


def test_mask_from_indices():
    assert utils.mask_from_indices([]) == 0
    assert utils.mask_from_indices([0, 3, 80]) == 1 | 8 | (1 << 80)
    assert utils.mask_from_indices([2, 2]) == 4