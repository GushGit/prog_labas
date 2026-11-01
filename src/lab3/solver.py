import typing as tp
from board import Board
from itertools import chain, combinations

class SudokuSolver:
    def __init__(self, sudoku: Board) -> None:
        self.used_boards: tp.Set[Hash] = {}
        self.sudoku: Board = sudoku
    
    def check_for_nulls(self) -> bool:
        for pos in self.sudoku.available_cells:
            if self.sudoku.get_cell(pos).count_notes() == 0:
                return True
        
        return False

    def obvious_singles(self) -> bool:
        cell_pool: tp.Set[tp.Tuple[int, int]] = self.sudoku.available_cells
        for pos in cell_pool:
            if self.sudoku.get_cell(pos).count_notes() == 1:
                digit: int = self.sudoku.get_cell(pos).get_notes()[0]
                self.sudoku.set_cell(pos, digit, True)

    
    def hidden_singles(self) -> bool:
        cell_pool: tp.Set[tp.Tuple[int, int]] = self.sudoku.available_cells
        for pos in cell_pool:
            
    
    def obvious_pairs(self) -> bool:
        pass
    
    def hidden_pairs(self) -> bool:
        pass
    
    def obvious_threes(self) -> bool:
        pass
    
    def hidden_threes(self) -> bool:
        pass

    def run_heuristics(self) -> bool:
        if (
            self.obvious_singles()
            or self.hidden_singles()
            or self.obvious_pairs()
            or self.hidden_pairs()
            or self.obvious_threes()
            or self.hidden_threes()
        ):
            return True
        
        return False
    
    def solve_dfs(self) -> bool:
        pass
    
    def solve(self) -> bool:
        if self.board.hash_board in self.used_boards:
            return False
        else:
            self.used_boards.add(self.board.hash_board)
        
        if check_for_nulls():
            return False

        while self.run_heuristics():
            pass
        self.solve_dfs()