"""История просмотров всех пользователей сервиса (задача 1).

Содержит:
    ViewingHistory: счётчики фильмов по каждому пользователю и общий счётчик просмотров.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from recommender.catalog import MovieCatalog, located_error, parse_id


@dataclass
class ViewingHistory:
    """Истории просмотров: одна строка файла соответствует одному пользователю.

    Атрибуты:
        film_counts: по одному Counter на пользователя, id фильма -> число его вхождений.
        views: Counter по всем строкам истории, id фильма -> суммарное число просмотров.

    Инварианты:
        views равен сумме всех film_counts; каждый id есть в каталоге.
    """

    film_counts: list[Counter[int]]
    views: Counter[int]

    @classmethod
    def from_lines(
        cls, lines: Iterable[str], catalog: MovieCatalog, source: str = "<строки>"
    ) -> ViewingHistory:
        """Строит историю из строк с id через запятую, пустые строки пропускает.

        Каждое вхождение id считается отдельным просмотром, в том числе повторы в одной строке.

        Аргументы:
            lines: строки истории.
            catalog: каталог, в котором должны быть все id.
            source: имя источника для сообщений об ошибках.

        Возвращает:
            История с заполненными film_counts и views.

        Исключения:
            ValueError: пустой элемент, плохой id или id вне каталога;
                в тексте указаны источник и номер строки.

        Пример:
            >>> catalog = MovieCatalog.from_lines(["1,А", "2,Б"])
            >>> ViewingHistory.from_lines(["2,2,1", "", "1"], catalog).views
            Counter({2: 2, 1: 2})
        """
        film_counts: list[Counter[int]] = []
        views: Counter[int] = Counter()
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                ids = [parse_id(token) for token in line.split(",")]
                for movie_id in ids:
                    if movie_id not in catalog:
                        raise ValueError(f"id {movie_id} отсутствует в каталоге")
            except ValueError as error:
                raise located_error(source, line_no, error) from None
            counts = Counter(ids)
            film_counts.append(counts)
            views.update(counts)
        return cls(film_counts, views)

    @classmethod
    def from_file(cls, path: str, catalog: MovieCatalog) -> ViewingHistory:
        """Читает историю из файла в UTF-8 и передаёт строки в from_lines.

        Аргументы:
            path: путь к файлу истории.
            catalog: каталог для проверки id.

        Возвращает:
            Загруженная история.

        Исключения:
            OSError: файл не удалось открыть или прочитать.
            ValueError: ошибка формата (см. from_lines).
        """
        with open(path, encoding="utf-8") as file:
            return cls.from_lines(file, catalog, source=path)
