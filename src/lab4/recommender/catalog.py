"""Каталог фильмов задачи 1.

Содержит:
    Movie: неизменяемая запись «id и название».
    MovieCatalog: словарь фильмов по id, загрузка из строк и из файла.
    parse_id: разбор одного id фильма из текста.
    located_error: ошибка разбора с именем источника и номером строки.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Movie:
    """Фильм из каталога.

    Атрибуты:
        id: числовой идентификатор фильма, целое не меньше 0.
        title: название фильма без пробелов по краям.
    """

    id: int
    title: str


def parse_id(text: str) -> int:
    """Разбирает id фильма: непустую строку из ASCII-цифр, пробелы по краям допустимы.

    Аргументы:
        text: фрагмент строки, например элемент между запятыми.

    Возвращает:
        Id как целое число не меньше 0.

    Исключения:
        ValueError: если фрагмент пуст или не является целым неотрицательным числом.

    Пример:
        >>> parse_id(" 42 ")
        42
    """
    token = text.strip()
    if not token:
        raise ValueError("пустой элемент")
    if not (token.isascii() and token.isdigit()):
        raise ValueError(f"id не является целым неотрицательным числом: {token!r}")
    return int(token)


def located_error(source: str, line_no: int, error: ValueError) -> ValueError:
    """Создаёт ValueError с указанием источника и номера строки.

    Аргументы:
        source: имя файла или условное имя источника строк.
        line_no: номер строки, начиная с 1.
        error: исходная ошибка разбора.

    Возвращает:
        Новое исключение с текстом «источник, строка N: причина».
    """
    return ValueError(f"{source}, строка {line_no}: {error}")


class MovieCatalog:
    """Каталог фильмов с доступом по id.

    Атрибуты:
        movies: словарь id -> Movie.

    Инварианты:
        Ключ словаря совпадает с полем id фильма, id в каталоге уникальны.
    """

    def __init__(self, movies: dict[int, Movie]) -> None:
        """Создаёт каталог из готового словаря фильмов.

        Аргументы:
            movies: словарь id -> Movie.
        """
        self.movies = movies

    @classmethod
    def from_lines(cls, lines: Iterable[str], source: str = "<строки>") -> MovieCatalog:
        """Строит каталог из строк вида «id,название», пустые строки пропускает.

        Строка делится по первой запятой, поэтому запятые в названии допустимы.

        Аргументы:
            lines: строки каталога.
            source: имя источника для сообщений об ошибках.

        Возвращает:
            Заполненный каталог.

        Исключения:
            ValueError: нет запятой, плохой id, пустое название или повторный id;
                в тексте указаны источник и номер строки.

        Пример:
            >>> catalog = MovieCatalog.from_lines(["1,Мстители: Финал", "", "3,Дюна, часть 1"])
            >>> catalog.get(3)
            Movie(id=3, title='Дюна, часть 1')
            >>> 2 in catalog
            False
        """
        movies: dict[int, Movie] = {}
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            id_text, comma, title = line.partition(",")
            try:
                if not comma:
                    raise ValueError("нет запятой между id и названием")
                movie_id = parse_id(id_text)
                if not title.strip():
                    raise ValueError("пустое название")
                if movie_id in movies:
                    raise ValueError(f"повторный id {movie_id}")
            except ValueError as error:
                raise located_error(source, line_no, error) from None
            movies[movie_id] = Movie(movie_id, title.strip())
        return cls(movies)

    @classmethod
    def from_file(cls, path: str) -> MovieCatalog:
        """Читает каталог из файла в UTF-8 и передаёт строки в from_lines.

        Аргументы:
            path: путь к файлу каталога.

        Возвращает:
            Заполненный каталог.

        Исключения:
            OSError: файл не удалось открыть или прочитать.
            ValueError: ошибка формата (см. from_lines).
        """
        with open(path, encoding="utf-8") as file:
            return cls.from_lines(file, source=path)

    def get(self, movie_id: int) -> Movie:
        """Возвращает фильм по id; отсутствующий id даёт KeyError.

        Аргументы:
            movie_id: id фильма из каталога.

        Возвращает:
            Фильм с этим id.
        """
        return self.movies[movie_id]

    def __contains__(self, movie_id: object) -> bool:
        """Проверяет, есть ли фильм с таким id в каталоге."""
        return movie_id in self.movies
