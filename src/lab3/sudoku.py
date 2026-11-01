import pathlib
import random
import typing as tp

T = tp.TypeVar("T")

DIGITS = set("123456789")


class SearchLimitExceeded(Exception):
    """Наивный перебор превысил заданный лимит шагов."""


def read_sudoku(path: tp.Union[str, pathlib.Path]) -> tp.List[tp.List[str]]:
    """ Прочитать Судоку из указанного файла """
    path = pathlib.Path(path)
    with path.open() as f:
        puzzle = f.read()
    return create_grid(puzzle)


def create_grid(puzzle: str) -> tp.List[tp.List[str]]:
    digits = [c for c in puzzle if c in "123456789."]
    grid = group(digits, 9)
    return grid


def group(values: tp.List[T], n: int) -> tp.List[tp.List[T]]:
    """
    Сгруппировать значения values в список, состоящий из списков по n элементов
    >>> group([1,2,3,4], 2)
    [[1, 2], [3, 4]]
    >>> group([1,2,3,4,5,6,7,8,9], 3)
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    """
    return [values[i:i + n] for i in range(0, len(values) - n + 1, n)]


def display(grid: tp.List[tp.List[str]]) -> None:
    """Вывод Судоку """
    width = 2
    line = "+".join(["-" * (width * 3)] * 3)
    for row in range(9):
        print(
            "".join(
                grid[row][col].center(width) + ("|" if str(col) in "25" else "") for col in range(9)
            )
        )
        if str(row) in "25":
            print(line)
    print()


def get_row(grid: tp.List[tp.List[str]], pos: tp.Tuple[int, int]) -> tp.List[str]:
    """Возвращает все значения для номера строки, указанной в pos
    >>> get_row([['1', '2', '.'], ['4', '5', '6'], ['7', '8', '9']], (0, 0))
    ['1', '2', '.']
    >>> get_row([['1', '2', '3'], ['4', '.', '6'], ['7', '8', '9']], (1, 0))
    ['4', '.', '6']
    >>> get_row([['1', '2', '3'], ['4', '5', '6'], ['.', '8', '9']], (2, 0))
    ['.', '8', '9']
    """
    return grid[pos[0]][:]


def get_col(grid: tp.List[tp.List[str]], pos: tp.Tuple[int, int]) -> tp.List[str]:
    """Возвращает все значения для номера столбца, указанного в pos
    >>> get_col([['1', '2', '.'], ['4', '5', '6'], ['7', '8', '9']], (0, 0))
    ['1', '4', '7']
    >>> get_col([['1', '2', '3'], ['4', '.', '6'], ['7', '8', '9']], (0, 1))
    ['2', '.', '8']
    >>> get_col([['1', '2', '3'], ['4', '5', '6'], ['.', '8', '9']], (0, 2))
    ['3', '6', '9']
    """
    return [row[pos[1]] for row in grid]


def get_block(grid: tp.List[tp.List[str]], pos: tp.Tuple[int, int]) -> tp.List[str]:
    """Возвращает все значения из квадрата, в который попадает позиция pos
    >>> grid = read_sudoku('puzzle1.txt')
    >>> get_block(grid, (0, 1))
    ['5', '3', '.', '6', '.', '.', '.', '9', '8']
    >>> get_block(grid, (4, 7))
    ['.', '.', '3', '.', '.', '1', '.', '.', '6']
    >>> get_block(grid, (8, 8))
    ['2', '8', '.', '.', '.', '5', '.', '7', '9']
    """
    r0, c0 = pos[0] // 3 * 3, pos[1] // 3 * 3
    return [grid[r][c] for r in range(r0, r0 + 3) for c in range(c0, c0 + 3)]


def find_empty_positions(grid: tp.List[tp.List[str]]) -> tp.Optional[tp.Tuple[int, int]]:
    """Найти первую свободную позицию в пазле
    >>> find_empty_positions([['1', '2', '.'], ['4', '5', '6'], ['7', '8', '9']])
    (0, 2)
    >>> find_empty_positions([['1', '2', '3'], ['4', '.', '6'], ['7', '8', '9']])
    (1, 1)
    >>> find_empty_positions([['1', '2', '3'], ['4', '5', '6'], ['.', '8', '9']])
    (2, 0)
    """
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value == ".":
                return r, c
    return None


def find_possible_values(grid: tp.List[tp.List[str]], pos: tp.Tuple[int, int]) -> tp.Set[str]:
    """Вернуть множество возможных значения для указанной позиции
    >>> grid = read_sudoku('puzzle1.txt')
    >>> values = find_possible_values(grid, (0,2))
    >>> values == {'1', '2', '4'}
    True
    >>> values = find_possible_values(grid, (4,7))
    >>> values == {'2', '5', '9'}
    True
    """
    used = set(get_row(grid, pos)) | set(get_col(grid, pos)) | set(get_block(grid, pos))
    return DIGITS - used


def has_conflicts(grid: tp.List[tp.List[str]]) -> bool:
    """True, если в какой-либо строке, столбце или блоке цифра повторяется."""
    for i in range(9):
        units = (
            get_row(grid, (i, 0)),
            get_col(grid, (0, i)),
            get_block(grid, (i // 3 * 3, i % 3 * 3)),
        )
        for unit in units:
            values = [v for v in unit if v != "."]
            if len(values) != len(set(values)):
                return True
    return False


def _backtrack(grid: tp.List[tp.List[str]], counter: tp.List[tp.Optional[int]]) -> bool:
    """Перебор с откатом на месте. counter = [число вызовов, лимит или None]."""
    counter[0] += 1
    if counter[1] is not None and counter[0] > counter[1]:
        raise SearchLimitExceeded
    pos = find_empty_positions(grid)
    if pos is None:
        return True
    r, c = pos
    for value in sorted(find_possible_values(grid, pos)):
        grid[r][c] = value
        if _backtrack(grid, counter):
            return True
    grid[r][c] = "."
    return False


def solve_naive(
    grid: tp.List[tp.List[str]],
    max_steps: tp.Optional[int] = None,
    steps_out: tp.Optional[tp.List[int]] = None,
) -> tp.Optional[tp.List[tp.List[str]]]:
    """Наивное решение из задания (первая свободная клетка, откат). Вход не меняется.

    max_steps ограничивает число вызовов перебора (иначе SearchLimitExceeded);
    steps_out, если передан, получает [число вызовов].
    """
    counter: tp.List[tp.Optional[int]] = [0, max_steps]
    try:
        work = [row[:] for row in grid]
        if has_conflicts(work):
            return None
        return work if _backtrack(work, counter) else None
    finally:
        if steps_out is not None:
            steps_out[:] = [counter[0]]


def solve(grid: tp.List[tp.List[str]]) -> tp.Optional[tp.List[tp.List[str]]]:
    """ Решение пазла, заданного в grid
    Как решать Судоку?
        1. Найти свободную позицию
        2. Найти все возможные значения, которые могут находиться на этой позиции
        3. Для каждого возможного значения:
            3.1. Поместить это значение на эту позицию
            3.2. Продолжить решать оставшуюся часть пазла
    >>> grid = read_sudoku('puzzle1.txt')
    >>> solve(grid)
    [['5', '3', '4', '6', '7', '8', '9', '1', '2'], ['6', '7', '2', '1', '9', '5', '3', '4', '8'], ['1', '9', '8', '3', '4', '2', '5', '6', '7'], ['8', '5', '9', '7', '6', '1', '4', '2', '3'], ['4', '2', '6', '8', '5', '3', '7', '9', '1'], ['7', '1', '3', '9', '2', '4', '8', '5', '6'], ['9', '6', '1', '5', '3', '7', '2', '8', '4'], ['2', '8', '7', '4', '1', '9', '6', '3', '5'], ['3', '4', '5', '2', '8', '6', '1', '7', '9']]
    """
    return solve_naive(grid)


def check_solution(solution: tp.Optional[tp.List[tp.List[str]]]) -> bool:
    """ Если решение solution верно, то вернуть True, в противном случае False
    >>> check_solution(None)
    False
    >>> check_solution(read_sudoku('puzzle1.txt'))
    False
    >>> good = solve(read_sudoku('puzzle1.txt'))
    >>> check_solution(good)
    True
    >>> good[0][0], good[0][1] = good[0][1], good[0][0]
    >>> check_solution(good)
    False
    """
    if not solution or len(solution) != 9 or any(len(row) != 9 for row in solution):
        return False
    for i in range(9):
        units = (
            get_row(solution, (i, 0)),
            get_col(solution, (0, i)),
            get_block(solution, (i // 3 * 3, i % 3 * 3)),
        )
        if any(set(unit) != DIGITS for unit in units):
            return False
    return True


def generate_sudoku(N: int) -> tp.List[tp.List[str]]:
    """Генерация судоку заполненного на N элементов
    >>> grid = generate_sudoku(40)
    >>> sum(1 for row in grid for e in row if e == '.')
    41
    >>> solution = solve(grid)
    >>> check_solution(solution)
    True
    >>> grid = generate_sudoku(1000)
    >>> sum(1 for row in grid for e in row if e == '.')
    0
    >>> solution = solve(grid)
    >>> check_solution(solution)
    True
    >>> grid = generate_sudoku(0)
    >>> sum(1 for row in grid for e in row if e == '.')
    81
    >>> solution = solve(grid)
    >>> check_solution(solution)
    True
    """
    digits = list("123456789")
    random.shuffle(digits)

    def shuffled_axis() -> tp.List[int]:
        # полосы в случайном порядке, внутри каждой полосы строки тоже
        bands = random.sample(range(3), 3)
        return [b * 3 + k for b in bands for k in random.sample(range(3), 3)]

    rows, cols = shuffled_axis(), shuffled_axis()
    grid = [[digits[(3 * (r % 3) + r // 3 + c) % 9] for c in cols] for r in rows]
    keep = max(0, min(81, N))
    for idx in random.sample(range(81), 81 - keep):
        grid[idx // 9][idx % 9] = "."
    return grid


if __name__ == "__main__":
    for fname in ["puzzle1.txt", "puzzle2.txt", "puzzle3.txt"]:
        grid = read_sudoku(fname)
        display(grid)
        solution = solve(grid)
        if not solution:
            print(f"Puzzle {fname} can't be solved")
        else:
            display(solution)
            if check_solution(solution):
                print("Solution is correct")
            else:
                print("Ooops")