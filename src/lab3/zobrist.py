from utils import get_digit_flag
from cell import Cell
import numpy as np

class Hash:
    def __init__(self):
        self.zobrist: int = 0

        np.random.seed(47)
        rng = np.random.default_rng()
        self.hash_table: np.ndarray[tuple[int, int, int], np.dtype[np.uint64]] = rng.integers(
            0, 2**64, size=(9, 9, 10), dtype=np.uint64
        )

    def __eq__(self, other: Hash):
        return self.zobrist == other.zobrist
    
    def __hash__(self):
        return self.zobrist
    
    def __ixor__(self, other: Cell):
        for i in range(10):
            if Cell.read_state(i):
                zobrist ^= (self.hash_table[Cell.get_row()][Cell.get_col()][i])
    

