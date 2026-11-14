"""Алгоритм рекомендации фильма (задача 1).

Содержит:
    overlap: число общих фильмов пользователя и одной истории.
    Recommender: шаги 1-3 алгоритма и режим весов (--weighted).
"""

from __future__ import annotations

from collections import Counter

from recommender.catalog import Movie, MovieCatalog
from recommender.history import ViewingHistory


def overlap(watched: set[int], counts: Counter[int]) -> int:
    """Считает, сколько разных фильмов пользователя есть в одной истории.

    Аргументы:
        watched: множество id, просмотренных пользователем.
        counts: счётчик фильмов одной истории.

    Возвращает:
        Число общих id (повторы в истории не учитываются).

    Пример:
        >>> overlap({1, 2}, Counter([2, 2, 3]))
        1
    """
    return len(watched & counts.keys())


class Recommender:
    """Подбирает фильм для пользователя по историям просмотров всего сервиса.

    Атрибуты:
        catalog: каталог фильмов.
        history: истории просмотров всех пользователей.
    """

    def __init__(self, catalog: MovieCatalog, history: ViewingHistory) -> None:
        """Связывает рекомендатель с каталогом и историей.

        Аргументы:
            catalog: каталог фильмов.
            history: истории просмотров, id которых есть в каталоге.
        """
        self.catalog = catalog
        self.history = history

    def recommend(self, watched: set[int], weighted: bool = False) -> Movie | None:
        """Выбирает рекомендацию по шагам 1-3 условия.

        Шаг 1: отбираются истории, где есть хотя бы половина фильмов пользователя.
        Шаг 2: из отобранных историй берутся фильмы, которых пользователь не смотрел.
        Шаг 3: побеждает кандидат с наибольшим числом просмотров по всем историям
        сервиса; при равенстве берётся наименьший id. В режиме весов каждый
        просмотр истории h умножается на overlap(watched, h).

        Аргументы:
            watched: множество id, просмотренных пользователем.
            weighted: включить режим весов.

        Возвращает:
            Рекомендованный фильм или None, если кандидатов нет.

        Пример:
            >>> catalog = MovieCatalog.from_lines(
            ...     ["1,Мстители: Финал", "2,Хатико", "3,Дюна", "4,Унесенные призраками"])
            >>> history = ViewingHistory.from_lines(["2,1,3", "1,4,3", "2,2,2,2,2,3"], catalog)
            >>> Recommender(catalog, history).recommend({2, 4}).title
            'Дюна'
            >>> Recommender(catalog, history).recommend({1, 2, 3, 4}) is None
            True
        """
        selected = [counts for counts in self.history.film_counts
                    if 2 * overlap(watched, counts) >= len(watched)]
        candidates: set[int] = set().union(*selected) - watched
        if not candidates:
            return None
        # Шаг 3 условия считает просмотры среди всех пользователей сервиса. Чтобы считать
        # только по отобранным историям, self.history.views меняется на sum(selected, Counter()).
        score = self._weighted_scores(watched) if weighted else self.history.views
        best = max(candidates, key=lambda movie_id: (score[movie_id], -movie_id))
        return self.catalog.get(best)

    def _weighted_scores(self, watched: set[int]) -> Counter[int]:
        """Считает оценки режима весов в целых числах.

        Вес истории h равен overlap(h) / len(watched). Делитель одинаков для всех
        историй и порядок оценок не меняет, поэтому суммируется overlap(h) * вхождения.

        Аргументы:
            watched: множество id, просмотренных пользователем.

        Возвращает:
            Counter id фильма -> сумма по всем историям overlap(h) * число вхождений.
        """
        scores: Counter[int] = Counter()
        for counts in self.history.film_counts:
            common = overlap(watched, counts)
            for movie_id, times in counts.items():
                scores[movie_id] += common * times
        return scores
