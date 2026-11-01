import typing as tp
from cell import Cell

class Region:
    def __init__(self):
        self.open_cells: tp.Set[Cell] = {}
        self.notes_count: tp.List[int] = [ 0 for i in range(10) ]

    

    def __lt__(self, other: Region) -> bool:
        return min(self.notes_count[1:]) < min(self.notes_count[1:])
    
    
    
