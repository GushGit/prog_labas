"""Консольное приложение задачи 1: рекомендация фильма.

Читает из stdin одну строку с id просмотренных фильмов через запятую и печатает
в stdout название рекомендованного фильма или «Рекомендаций нет».

Содержит:
    MOVIES_PATH, HISTORY_PATH: пути к данным относительно текущей папки.
    parse_watched: разбор ввода пользователя.
    parse_args: разбор аргументов командной строки.
    main: точка входа.

Запуск из корня проекта:
    echo 2,4 | python -m recommender.app
    echo 2,4 | python -m recommender.app --weighted
"""

from __future__ import annotations

import sys
from typing import TextIO

from recommender.catalog import MovieCatalog, parse_id
from recommender.engine import Recommender
from recommender.history import ViewingHistory

MOVIES_PATH = "data/movies.txt"
HISTORY_PATH = "data/history.txt"
WEIGHTED_FLAG = "--weighted"
USAGE = "использование: python -m recommender.app [--weighted]"
NO_RECOMMENDATION = "Рекомендаций нет"


def parse_watched(line: str, catalog: MovieCatalog) -> set[int]:
    """Разбирает строку пользователя с id через запятую; пробелы допустимы, повторы схлопываются.

    Аргументы:
        line: строка ввода, например «2,4».
        catalog: каталог, в котором должны быть все id.

    Возвращает:
        Множество просмотренных id.

    Исключения:
        ValueError: пустой ввод, пустой элемент, нецелый id или id вне каталога.

    Пример:
        >>> catalog = MovieCatalog.from_lines(["2,Хатико", "4,Унесенные призраками"])
        >>> sorted(parse_watched(" 4, 2 ,4\\n", catalog))
        [2, 4]
    """
    if not line.strip():
        raise ValueError("пустой ввод: ожидаются id фильмов через запятую")
    watched: set[int] = set()
    for token in line.split(","):
        movie_id = parse_id(token)
        if movie_id not in catalog:
            raise ValueError(f"фильма с id {movie_id} нет в каталоге")
        watched.add(movie_id)
    return watched


def parse_args(argv: list[str]) -> bool:
    """Разбирает аргументы командной строки без имени программы.

    Аргументы:
        argv: список аргументов; допустимы [] и ["--weighted"].

    Возвращает:
        True, если включён режим весов.

    Исключения:
        ValueError: любые другие аргументы.
    """
    if argv not in ([], [WEIGHTED_FLAG]):
        raise ValueError(f"неизвестные аргументы {' '.join(argv)!r}; {USAGE}")
    return argv == [WEIGHTED_FLAG]


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    movies_path: str = MOVIES_PATH,
    history_path: str = HISTORY_PATH,
) -> int:
    """Запускает приложение: аргументы, загрузка данных, ввод, рекомендация, вывод.

    Аргументы:
        argv: аргументы без имени программы; None означает sys.argv[1:].
        stdin: поток ввода; None означает sys.stdin.
        stdout: поток результата; None означает sys.stdout.
        stderr: поток ошибок; None означает sys.stderr.
        movies_path: путь к каталогу фильмов.
        history_path: путь к истории просмотров.

    Возвращает:
        0 при успехе, 1 при ошибке аргументов, ввода или файлов.
    """
    argv = sys.argv[1:] if argv is None else argv
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        weighted = parse_args(argv)
        catalog = MovieCatalog.from_file(movies_path)
        history = ViewingHistory.from_file(history_path, catalog)
        watched = parse_watched(stdin.readline(), catalog)
    except (ValueError, OSError) as error:
        print(f"Ошибка: {error}", file=stderr)
        return 1
    movie = Recommender(catalog, history).recommend(watched, weighted)
    print(NO_RECOMMENDATION if movie is None else movie.title, file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
