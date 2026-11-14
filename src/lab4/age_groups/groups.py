"""Возрастные группы и разбивка респондентов (задача 2).

Содержит:
    Respondent: неизменяемая запись «ФИО и возраст».
    AgeGroups: группы по списку границ, поиск группы через bisect и разбивка через groupby.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import groupby


@dataclass(frozen=True)
class Respondent:
    """Участник опроса.

    Атрибуты:
        name: ФИО без пробелов по краям, непустое.
        age: возраст в годах, целое не меньше 0.
    """

    name: str
    age: int


class AgeGroups:
    """Возрастные группы, заданные возрастающими границами.

    Границы b0 < b1 < ... < bk задают k + 2 групп: 0-b0, (b0+1)-b1, ..., (bk+1)+.
    Возраст, равный границе, входит в нижнюю группу.

    Атрибуты:
        bounds: список границ.
        labels: метки групп от младшей к старшей, labels[i] соответствует index_of() == i.

    Инварианты:
        bounds непуст, целые не меньше 0, строго возрастают (проверяет parse_bounds).
    """

    def __init__(self, bounds: Sequence[int]) -> None:
        """Создаёт группы и их метки.

        Аргументы:
            bounds: строго возрастающие целые границы не меньше 0.
        """
        self.bounds = list(bounds)
        lows = [0] + [bound + 1 for bound in self.bounds]
        self.labels = [f"{low}-{high}" for low, high in zip(lows, self.bounds)]
        self.labels.append(f"{lows[-1]}+")

    def index_of(self, age: int) -> int:
        """Возвращает номер возрастной группы для заданного возраста за O(log k).

        Аргументы:
            age: возраст в годах, целое число не меньше 0.

        Возвращает:
            Индекс группы: 0 для самой младшей, len(bounds) для самой старшей.

        Пример:
            >>> groups = AgeGroups([18, 25])
            >>> [groups.index_of(age) for age in (0, 18, 19, 25, 26)]
            [0, 0, 1, 1, 2]
        """
        return bisect.bisect_left(self.bounds, age)

    def split(self, respondents: Iterable[Respondent]) -> list[tuple[str, list[Respondent]]]:
        """Разбивает респондентов по группам от старшей к младшей, пустые группы пропускает.

        Одна сортировка по ключу (-age, name) упорядочивает и группы (индекс группы
        не возрастает), и людей внутри группы, поэтому groupby сразу выдаёт результат.
        Сложность O(n log n).

        Аргументы:
            respondents: участники опроса в любом порядке.

        Возвращает:
            Список пар (метка группы, участники по убыванию возраста, затем по ФИО).

        Пример:
            >>> people = [Respondent("Б", 18), Respondent("В", 40), Respondent("А", 18)]
            >>> for label, group in AgeGroups([18, 25]).split(people):
            ...     print(label, [person.name for person in group])
            26+ ['В']
            0-18 ['А', 'Б']
        """
        ordered = sorted(respondents, key=lambda person: (-person.age, person.name))
        grouped = groupby(ordered, key=lambda person: self.index_of(person.age))
        return [(self.labels[index], list(members)) for index, members in grouped]
