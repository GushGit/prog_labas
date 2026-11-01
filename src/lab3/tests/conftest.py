import pytest

import sudoku

PUZZLE1_TEXT = """53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79
"""

PUZZLE1_SOLUTION = [
    "534678912", "672195348", "198342567",
    "859761423", "426853791", "713924856",
    "961537284", "287419635", "345286179",
]


@pytest.fixture
def puzzle1_grid():
    """Пазл puzzle1 из задания (текст зашит на случай отсутствия файла)."""
    return sudoku.create_grid(PUZZLE1_TEXT)


@pytest.fixture
def puzzle1_solution():
    """Известное решение puzzle1."""
    return [list(row) for row in PUZZLE1_SOLUTION]