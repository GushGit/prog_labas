import contextlib
import copy
import io
import pathlib
import random
import unittest

import sudoku

ROOT = pathlib.Path(__file__).parent
PUZZLE1_SOLUTION = [
    list(row)
    for row in (
        "534678912", "672195348", "198342567",
        "859761423", "426853791", "713924856",
        "961537284", "287419635", "345286179",
    )
]


def empty_grid():
    return [["."] * 9 for _ in range(9)]


def count_dots(grid):
    return sum(1 for row in grid for e in row if e == ".")


class SudokuTestCase(unittest.TestCase):
    def setUp(self):
        self.puzzle1 = sudoku.read_sudoku(ROOT / "puzzle1.txt")

    def test_group(self):
        self.assertEqual(sudoku.group([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
        self.assertEqual(sudoku.group([1, 2, 3, 4, 5, 6, 7, 8], 4), [[1, 2, 3, 4], [5, 6, 7, 8]])
        self.assertEqual(sudoku.group([1, 2, 3, 4, 5, 6, 7, 8, 9], 3), [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(sudoku.group([], 3), [])

    def test_get_row(self):
        self.assertEqual(sudoku.get_row([["1", "2", "."], ["4", "5", "6"], ["7", "8", "9"]], (0, 0)),
                         ["1", "2", "."])
        self.assertEqual(sudoku.get_row(self.puzzle1, (8, 3)), list("....8..79"))

    def test_get_row_returns_copy(self):
        row = sudoku.get_row(self.puzzle1, (0, 0))
        row[0] = "X"
        self.assertEqual(self.puzzle1[0][0], "5")

    def test_get_col(self):
        grid = [["1", "2", "3"], ["4", ".", "6"], ["7", "8", "9"]]
        self.assertEqual(sudoku.get_col(grid, (0, 1)), ["2", ".", "8"])
        self.assertEqual(sudoku.get_col(self.puzzle1, (5, 8)), [row[8] for row in self.puzzle1])

    def test_get_block(self):
        self.assertEqual(sudoku.get_block(self.puzzle1, (0, 1)),
                         ["5", "3", ".", "6", ".", ".", ".", "9", "8"])
        self.assertEqual(sudoku.get_block(self.puzzle1, (4, 7)),
                         [".", ".", "3", ".", ".", "1", ".", ".", "6"])
        self.assertEqual(sudoku.get_block(self.puzzle1, (8, 8)),
                         ["2", "8", ".", ".", ".", "5", ".", "7", "9"])

    def test_find_empty_positions(self):
        self.assertEqual(sudoku.find_empty_positions([["1", "2", "."], ["4", "5", "6"], ["7", "8", "9"]]),
                         (0, 2))
        self.assertEqual(sudoku.find_empty_positions([["1", "2", "3"], ["4", "5", "6"], [".", "8", "9"]]),
                         (2, 0))
        self.assertEqual(sudoku.find_empty_positions(self.puzzle1), (0, 2))
        self.assertIsNone(sudoku.find_empty_positions(PUZZLE1_SOLUTION))

    def test_find_possible_values(self):
        self.assertEqual(sudoku.find_possible_values(self.puzzle1, (0, 2)), {"1", "2", "4"})
        self.assertEqual(sudoku.find_possible_values(self.puzzle1, (4, 7)), {"2", "5", "9"})
        self.assertEqual(sudoku.find_possible_values(empty_grid(), (4, 4)), set("123456789"))
        grid = empty_grid()
        grid[0] = list("12345678.")
        grid[1][8] = "9"
        self.assertEqual(sudoku.find_possible_values(grid, (0, 8)), set())

    def test_solve(self):
        original = copy.deepcopy(self.puzzle1)
        solution = sudoku.solve(self.puzzle1)
        self.assertEqual(solution, PUZZLE1_SOLUTION)
        self.assertTrue(sudoku.check_solution(solution))
        self.assertEqual(self.puzzle1, original)  # вход не мутируется

    def test_solve_special_inputs(self):
        solved = sudoku.solve(empty_grid())
        self.assertTrue(sudoku.check_solution(solved))
        full = sudoku.solve(PUZZLE1_SOLUTION)
        self.assertEqual(full, PUZZLE1_SOLUTION)
        self.assertIsNot(full, PUZZLE1_SOLUTION)
        wrong = copy.deepcopy(PUZZLE1_SOLUTION)
        wrong[0][0], wrong[0][1] = wrong[0][1], wrong[0][0]
        self.assertIsNone(sudoku.solve(wrong))

    def test_solve_unsolvable(self):
        dead_end = empty_grid()
        dead_end[0] = list("12345678.")
        dead_end[1][8] = "9"
        self.assertIsNone(sudoku.solve(dead_end))
        duplicates = empty_grid()
        duplicates[0][0] = duplicates[0][1] = "5"
        self.assertIsNone(sudoku.solve(duplicates))

    def test_check_solution(self):
        self.assertTrue(sudoku.check_solution(PUZZLE1_SOLUTION))
        self.assertFalse(sudoku.check_solution(None))
        self.assertFalse(sudoku.check_solution([]))
        self.assertFalse(sudoku.check_solution(self.puzzle1))  # есть точки
        swapped = copy.deepcopy(PUZZLE1_SOLUTION)
        swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
        self.assertFalse(sudoku.check_solution(swapped))  # ломаются столбцы
        self.assertFalse(sudoku.check_solution(PUZZLE1_SOLUTION[:8]))  # 8 строк
        short_row = copy.deepcopy(PUZZLE1_SOLUTION)
        short_row[3] = short_row[3][:8]
        self.assertFalse(sudoku.check_solution(short_row))
        # строки и столбцы верны, блоки нет
        shifted = [[str((r * 1 + c) % 9 + 1) for c in range(9)] for r in range(9)]
        self.assertFalse(sudoku.check_solution(shifted))

    def test_generate_sudoku(self):
        random.seed(1)
        for n, dots in ((0, 81), (40, 41), (1000, 0), (81, 0), (-5, 81)):
            grid = sudoku.generate_sudoku(n)
            self.assertEqual(len(grid), 9)
            self.assertTrue(all(len(row) == 9 for row in grid))
            self.assertEqual(count_dots(grid), dots)
        grid = sudoku.generate_sudoku(40)
        solution = sudoku.solve(grid)
        self.assertTrue(sudoku.check_solution(solution))
        for r in range(9):
            for c in range(9):
                if grid[r][c] != ".":
                    self.assertEqual(grid[r][c], solution[r][c])

    def test_generate_sudoku_template_is_valid(self):
        for seed in range(20):
            random.seed(seed)
            self.assertTrue(sudoku.check_solution(sudoku.generate_sudoku(81)))

    def test_read_sudoku(self):
        self.assertEqual(self.puzzle1[0], list("53..7...."))
        self.assertEqual(len(self.puzzle1), 9)
        self.assertEqual(sudoku.read_sudoku(str(ROOT / "puzzle1.txt")), self.puzzle1)

    def test_create_grid(self):
        text = "53..7....\n" * 9
        grid = sudoku.create_grid(text)
        self.assertEqual(len(grid), 9)
        self.assertEqual(grid[8], list("53..7...."))
        self.assertEqual(sudoku.create_grid("12 3x"), [])  # меньше 9 символов: нет полных строк

    def test_display(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sudoku.display(self.puzzle1)
        text = buf.getvalue()
        self.assertEqual(text.count("\n"), 12)
        self.assertEqual(text.splitlines().count("------+------+------"), 2)

    def test_has_conflicts(self):
        self.assertFalse(sudoku.has_conflicts(self.puzzle1))
        self.assertFalse(sudoku.has_conflicts(empty_grid()))
        row = empty_grid()
        row[0][0] = row[0][8] = "7"
        self.assertTrue(sudoku.has_conflicts(row))
        col = empty_grid()
        col[0][4] = col[8][4] = "7"
        self.assertTrue(sudoku.has_conflicts(col))
        block = empty_grid()
        block[3][3] = block[5][5] = "7"
        self.assertTrue(sudoku.has_conflicts(block))

    def test_solve_naive_limit_and_steps(self):
        with self.assertRaises(sudoku.SearchLimitExceeded):
            sudoku.solve_naive(empty_grid(), max_steps=3)
        out = []
        self.assertIsNotNone(sudoku.solve_naive(self.puzzle1, steps_out=out))
        self.assertGreaterEqual(out[0], count_dots(self.puzzle1) + 1)
        out = []
        with self.assertRaises(sudoku.SearchLimitExceeded):
            sudoku.solve_naive(empty_grid(), 3, out)
        self.assertEqual(out, [4])
        out = []
        bad = empty_grid()
        bad[0][0] = bad[0][1] = "5"
        self.assertIsNone(sudoku.solve_naive(bad, steps_out=out))
        self.assertEqual(out, [0])


if __name__ == "__main__":
    unittest.main()