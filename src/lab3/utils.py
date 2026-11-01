import typing as tp


def get_digit_flag(digit: int) -> int:
    """Флаг цифры в состоянии клетки: бит digit (бит 0 — pen, биты 1..9 — цифры)."""
    return 1 << digit


def lowest_bit_index(mask: int) -> int:
    """Индекс младшего установленного бита непустой маски."""
    if mask <= 0:
        raise ValueError("Маска должна быть положительной")
    return (mask & -mask).bit_length() - 1


def iter_bits(mask: int) -> tp.Iterator[int]:
    """Индексы установленных бит по возрастанию."""
    while mask:
        low = mask & -mask  # младший бит
        yield low.bit_length() - 1
        mask ^= low


def mask_from_indices(indices: tp.Iterable[int]) -> int:
    """Маска с установленными битами по индексам."""
    mask = 0
    for i in indices:
        mask |= 1 << i
    return mask