import typing as tp
from region import Region
from cell import Cell
from zobrist import Hash
from heap import MinHeap
from utils import get_digit_flag
from itertools import combinations, product

class Board:
    def __init__(self):
        self.hash_board = Hash()
        self.grid: tp.List[List[Cell]] = [ 
            [ 
                Cell((row, col)) for col in range(9)
            ] for row in range(9)
        ]

        self.available_cells: tp.Set[tp.Tuple[int, int]] = {}

        for pos in combinations(range(9), 2):
            available_cells.add(pos)
    
    def clear(self):
        self.__init__()

    def get_cell(self, pos: tp.Typing[int, int]) -> Cell:
        return self.grid[pos[0]][pos[1]]

    def set_cell(self, pos: tp.Tuple[int, int], d: int, mark_mode: bool = False) -> bool:
        """
        Флип цифры d клетки на pos, 
        обновляя внутренний хэш таблицы, 
        поддерживая available_cells 
        и обновляя все заметки клеток в смежных регионах
        """

        hash_board ^= self.get_cell(pos)
        self.get_cell(pos).write_state(d, mark_mode)
        hash_board ^= self.get_cell(pos)

        if mark_mode:
            available_cells.remove(self.get_cell(pos))
            for row in range(9):
                new_pos: tp.Tuple[int, int] = (row, pos[1])
                if self.get_cell(new_pos).read_state(0) or not self.get_cell(new_pos).read_state(d):
                    continue
                
                self.set_cell(new_pos, d)
            
            for col in range(9):
                new_pos: tp.Tuple[int, int] = (pos[0], col)
                if self.get_cell(new_pos).read_state(0) or not self.get_cell(new_pos).read_state(d):
                    continue
                
                self.set_cell(new_pos, d)
            
            for new_pos in product(range(pos[0] // 3 * 3, pos[0] // 3 * 3 + 3), range(pos[1] // 3 * 3, pos[1] // 3 * 3 + 3)):
                if self.get_cell(new_pos).read_state(0) or not self.get_cell(new_pos).read_state(d):
                    continue
                
                self.set_cell(new_pos, d)
