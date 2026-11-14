"""Тесты задачи 1: загрузка данных, алгоритм рекомендации, режим весов и CLI.

Случаи собраны в таблицы внутри небольшого числа функций; каждый assert
подписан именем случая.
"""

import io

import pytest

from recommender.app import main, parse_watched
from recommender.catalog import Movie, MovieCatalog
from recommender.engine import Recommender
from recommender.history import ViewingHistory

EXAMPLE_MOVIES = "1,Мстители: Финал\n2,Хатико\n3,Дюна\n4,Унесенные призраками\n"
EXAMPLE_HISTORY = "2,1,3\n1,4,3\n2,2,2,2,2,3\n"
# Сценарий §4.2: обычный режим даёт фильм 4, режим весов даёт фильм 3.
WEIGHTS_MOVIES = "1,Один\n2,Два\n3,Три\n4,Четыре\n"
WEIGHTS_HISTORY = "1,2,3\n1,4\n1,4\n"


def run_main(argv, stdin_text, movies_path, history_path):
    """Запускает main на строковом вводе и возвращает (код, stdout, stderr)."""
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main(argv, io.StringIO(stdin_text), stdout, stderr, str(movies_path), str(history_path))
    return code, stdout.getvalue(), stderr.getvalue()


def test_main_with_files(tmp_path):
    """Сквозной прогон CLI на файлах: оба режима, ошибки аргументов, ввода и файлов."""
    example, weights = tmp_path / "example", tmp_path / "weights"
    for folder, movies, history in (
        (example, EXAMPLE_MOVIES, EXAMPLE_HISTORY),
        (weights, WEIGHTS_MOVIES, WEIGHTS_HISTORY),
    ):
        folder.mkdir()
        (folder / "movies.txt").write_text(movies, encoding="utf-8")
        (folder / "history.txt").write_text(history, encoding="utf-8")
    broken = tmp_path / "broken_history.txt"
    broken.write_text("1,2\n1,x\n", encoding="utf-8")
    ex_movies, ex_history = example / "movies.txt", example / "history.txt"
    w_movies, w_history = weights / "movies.txt", weights / "history.txt"
    missing = tmp_path / "missing.txt"

    # (имя, argv, ввод, файл фильмов, файл истории, код, stdout, фрагмент stderr)
    cases = [
        ("пример 2,4", [], "2,4\n", ex_movies, ex_history, 0, "Дюна\n", ""),
        ("пример 2,4 с весами", ["--weighted"], "2,4\n", ex_movies, ex_history, 0, "Дюна\n", ""),
        ("§4.2 обычный режим", [], "1,2\n", w_movies, w_history, 0, "Четыре\n", ""),
        ("§4.2 режим весов", ["--weighted"], "1,2", w_movies, w_history, 0, "Три\n", ""),
        ("всё просмотрено", [], "1,2,3,4\n", ex_movies, ex_history, 0, "Рекомендаций нет\n", ""),
        ("лишний аргумент", ["-w"], "2,4\n", ex_movies, ex_history, 1, "", "использование"),
        ("два аргумента", ["--weighted", "x"], "2,4\n", ex_movies, ex_history, 1, "",
         "использование"),
        ("пустой ввод", [], "\n", ex_movies, ex_history, 1, "", "пустой ввод"),
        ("конец ввода", [], "", ex_movies, ex_history, 1, "", "пустой ввод"),
        ("нецелый id", [], "2,abc\n", ex_movies, ex_history, 1, "", "'abc'"),
        ("id вне каталога", [], "2,9\n", ex_movies, ex_history, 1, "", "id 9 нет в каталоге"),
        ("нет файла фильмов", [], "2\n", missing, ex_history, 1, "", "missing.txt"),
        ("нет файла истории", [], "2\n", ex_movies, missing, 1, "", "missing.txt"),
        ("плохой файл истории", [], "2\n", ex_movies, broken, 1, "",
         "broken_history.txt, строка 2"),
    ]
    for name, argv, text, movies_path, history_path, code, out, err in cases:
        actual_code, actual_out, actual_err = run_main(argv, text, movies_path, history_path)
        assert actual_code == code, name
        assert actual_out == out, name
        assert err in actual_err, name
        assert actual_err.startswith("Ошибка") == (code == 1), name


def test_loading_and_input_parsing():
    """Разбор каталога, истории и ввода пользователя: корректные данные и все ошибки формата."""
    catalog = MovieCatalog.from_lines(["", "1, Мстители: Финал ", "3,Дюна, часть 1", "  "])
    assert catalog.movies == {1: Movie(1, "Мстители: Финал"), 3: Movie(3, "Дюна, часть 1")}
    assert 3 in catalog and 2 not in catalog
    history = ViewingHistory.from_lines(["3,3, 1", "", "3"], catalog)
    assert history.film_counts == [{3: 2, 1: 1}, {3: 1}], "дубли в строке истории"
    assert history.views == {3: 3, 1: 1}, "просмотры по всем строкам"
    assert parse_watched(" 3 , 1,3\n", catalog) == {1, 3}, "пробелы и повторы во вводе"

    catalog_errors = [
        ("нет запятой", ["1,А", "2 Б"], "строка 2: нет запятой"),
        ("плохой id", ["x,А"], "строка 1: id не является целым"),
        ("отрицательный id", ["-1,А"], "'-1'"),
        ("пустой id", [",А"], "пустой элемент"),
        ("пустое название", ["1, "], "пустое название"),
        ("повторный id", ["1,А", "", "1,Б"], "строка 3: повторный id 1"),
    ]
    for name, lines, fragment in catalog_errors:
        with pytest.raises(ValueError) as error:
            MovieCatalog.from_lines(lines, source="movies.txt")
        assert "movies.txt" in str(error.value), name
        assert fragment in str(error.value), name

    history_errors = [
        ("пустой элемент", ["1,,3"], "строка 1: пустой элемент"),
        ("плохой id", ["1", "1;3"], "строка 2: id не является целым"),
        ("id вне каталога", ["1,7"], "id 7 отсутствует в каталоге"),
    ]
    for name, lines, fragment in history_errors:
        with pytest.raises(ValueError) as error:
            ViewingHistory.from_lines(lines, catalog, source="history.txt")
        assert "history.txt" in str(error.value), name
        assert fragment in str(error.value), name

    for name, line, fragment in [
        ("пробелы", "   \n", "пустой ввод"),
        ("пустой элемент", "1,,3", "пустой элемент"),
        ("дробный id", "1.5", "'1.5'"),
    ]:
        with pytest.raises(ValueError) as error:
            parse_watched(line, catalog)
        assert fragment in str(error.value), name


def test_recommend_rules():
    """Правила шагов 1-3 и режима весов на маленьких каталогах из строк."""
    titles = [f"{movie_id},Фильм {movie_id}" for movie_id in range(1, 10)]
    catalog = MovieCatalog.from_lines(titles)

    # (имя, строки истории, просмотрено, режим весов, ожидаемый id или None)
    cases = [
        ("ровно половина: история отобрана", ["1,5"], {1, 2}, False, 5),
        ("меньше половины: история не отобрана", ["1,5", "2,6"], {1, 2, 3}, False, None),
        ("больше половины", ["1,2,7"], {1, 2, 3}, False, 7),
        ("просмотренное не рекомендуется", ["1,1,1,2"], {1}, False, 2),
        ("ничья: наименьший id", ["1,8,3"], {1}, False, 3),
        ("ничья в режиме весов", ["1,8,3"], {1}, True, 3),
        ("дубли в истории считаются", ["1,3,8,8"], {1}, False, 8),
        # Фильм 9 встречается только в неотобранных историях, но набирает больше просмотров.
        ("просмотры по всем историям", ["1,3,9", "9,9", "1,3"], {1, 2}, False, 9),
        ("нет кандидатов", ["1", "2,3"], {1, 4}, False, None),
        ("пустая история", [], {1}, False, None),
        ("§4.2 обычный режим", ["1,2,3", "1,4", "1,4"], {1, 2}, False, 4),
        ("§4.2 режим весов", ["1,2,3", "1,4", "1,4"], {1, 2}, True, 3),
        ("вес растёт с совпадением", ["1,2,5", "1,6", "1,6", "7,6"], {1, 2}, True, 5),
    ]
    for name, lines, watched, weighted, expected in cases:
        history = ViewingHistory.from_lines(lines, catalog)
        movie = Recommender(catalog, history).recommend(watched, weighted)
        actual = None if movie is None else movie.id
        assert actual == expected, name
