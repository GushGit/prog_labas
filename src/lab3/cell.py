import typing as tp
from region_key import RegionKey
from utils import get_digit_flag

class Cell:
    DEFAULT_STATE: int = get_digit_flag(10) - 2

    def __init__(self, pos: tp.Tuple[int, int], state: int = DEFAULT_STATE):
        self.state: int = state
        self.pos = pos
    
    def __eq__(self, other: Cell) -> bool:
        return (
            self.state == other.state
            and self.pos == other.pos
        )
    
    def __lt__(self, other: Cell) -> bool:
        return (
            (self.count_notes(), self.pos) < (other.count_notes(), other.pos)
        )

    def __and__(self, other: Cell) -> int:
        return self.state & other.state
    
    def __xor__(self, other: Cell) -> int:
        return self.state ^ other.state
    
    def __or__(self, other: Cell) -> int:
        return self.state | other.state
    
    def __getitem__(self, key: RegionKey) -> int:
        """
        Получение региона по ключу региона
        """

        match key:
            case RegionKey.ROW:
                return self.pos[0]
            case RegionKey.COL:
                return self.pos[1]
            case RegionKey.BOX:
                return (self.pos[0] // 3 * 3) + (self.pos[1] // 3)
            case _:
                raise KeyError("Unexpected RegionKey")

    def __floordiv__(self, other: Cell) -> bool:
        """
        Проверка на коллинеарность
        """

        return (
            self[0] == other[0]
            or self[1] == other[1]
        )
    
    def __truediv__(self, other: Cell) -> bool:
        """
        Проверка на нахождение в одном регионе
        """

        return (
            self[0] == other[0]
            or self[1] == other[1]
            or self[2] == other[2]
        )
    
    def count_notes(self) -> int:
        return (self.state & DEFAULT_STATE).bit_count()
    
    def get_notes(self) -> tp.List[int]:
        if (self.state & 1):
            raise ValueError("Requested notes from a pen-digit Cell")
        return [ digit for digit in range(1, 10) if (self.state & get_digit_flag(digit)) ]
    
    def clear_notes(self) -> None:
        self.state = self.read_state(0)

    def read_state(self, digit: int) -> bool:
        """
        Прочитать бит состояния по цифре. digit = 0 даст mark_mode
        """

        return self.state & get_digit_flag(digit)

    def write_state(self, digit: int, mark_mode: bool = False) -> None:
        """
        Флипнуть цифру в клетке. mark_mode отвечает за написание ответа, а не пометки
        """

        if mark_mode:
            self.state = 1
        
        self.state = (self.state ^ get_digit_flag(digit))
