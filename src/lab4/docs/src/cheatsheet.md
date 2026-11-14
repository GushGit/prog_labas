# Вопросы преподавателя по коду
> Шпаргалка к защите · Python {{python_version}} · {{date_ru}}

Ответы короткие, в третьем столбце указано место в коде и способ показать. Все команды запускаются из корня проекта.

## 1. ООП и архитектура

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| Зачем здесь классы? | Каждый класс держит одну обязанность и свои данные: каталог, история, алгоритм, группы. Их можно создать из строк и проверить по отдельности. | `recommender/engine.py:Recommender`, `age_groups/groups.py:AgeGroups` |
| Зачем `frozen dataclass`? | `Movie` и `Respondent` — значения: их не меняют после создания, их можно сравнивать и класть в множества. `frozen=True` запрещает случайное присваивание. | `recommender/catalog.py:Movie`; в REPL `m.title = "x"` даёт `FrozenInstanceError` |
| Почему композиция, а не наследование? | `Recommender` получает каталог и историю в конструкторе и использует их; общего поведения «является» тут нет. Так проще подменять данные в тестах. | `recommender/engine.py:Recommender.__init__` |
| Зачем `classmethod` `from_file`? | Это альтернативный конструктор: открывает файл и передаёт строки в `from_lines`. Логика разбора одна, а тесты обходятся без файлов. | `recommender/catalog.py:MovieCatalog.from_file`, `recommender/history.py:ViewingHistory.from_file` |
| Зачем `main` принимает потоки параметрами? | Тест передаёт `io.StringIO` вместо stdin/stdout и проверяет вывод и код возврата без подпроцесса. По умолчанию берутся `sys.stdin` и `sys.stdout`. | `recommender/app.py:main`; тест `tests/test_recommender.py:run_main` |

## 2. Алгоритм рекомендаций

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| Покажите шаг 1. | История отбирается, если в ней не меньше половины моих разных фильмов: `2 * overlap(watched, counts) >= len(watched)`. | `recommender/engine.py:Recommender.recommend`, `recommender/engine.py:overlap` |
| Шаг 2? | Кандидаты — объединение фильмов отобранных историй минус просмотренные: `set().union(*selected) - watched`. | `recommender/engine.py:Recommender.recommend` |
| Шаг 3? | Для кандидатов берётся число просмотров по всем историям из `views`; побеждает максимум. | `recommender/history.py:ViewingHistory`; `echo 2,4 | python -m recommender.app` даёт `Дюна` |
| Почему множества? | Нужны пересечение и разность «какие фильмы», а повторы в шаге 1 значения не имеют; операции над множествами линейны. | `recommender/engine.py:overlap` |
| Зачем `Counter`? | Он сразу считает вхождения id: по одному счётчику на пользователя и общий `views`. Отсутствующий ключ даёт 0, а не ошибку. | `recommender/history.py:ViewingHistory.from_lines` |
| Какая сложность? | Загрузка O(m) по всем id истории; рекомендация линейна по суммарной длине историй на отбор плюс O(c) на максимум. | `recommender/engine.py:Recommender.recommend` |
| Два фильма с равным числом просмотров? | Ключ `max` равен `(score, -id)`, поэтому выигрывает меньший id. Условие разрешает любой, но так ответ детерминирован. | `recommender/engine.py:Recommender.recommend`; случай «ничья» в `tests/test_recommender.py:test_recommend_rules` |
| Пустой ввод? | `parse_watched` бросает `ValueError`, `main` пишет «Ошибка: пустой ввод» в stderr и возвращает 1. | `recommender/app.py:parse_watched`; `echo | python -m recommender.app; echo $?` |
| Дубли в истории `2,2,2`? | Каждое вхождение — отдельный просмотр: `Counter(ids)` их считает. | `recommender/history.py:ViewingHistory.from_lines` |
| Как поменять порог «половины»? | Поменять одну строку отбора, например `10 * overlap(...) >= 7 * len(watched)` для 70%. Порог записан один раз. | `recommender/engine.py:Recommender.recommend` |
| Как работает `--weighted`? | Шаги 1–2 те же, в шаге 3 просмотр в истории h весит `common(h)`; это вес `common/len(watched)`, умноженный на общий знаменатель. | `recommender/engine.py:Recommender._weighted_scores`; сценарий весов в `tests/test_recommender.py:test_main_with_files` |

## 3. Структуры второй задачи

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| `bisect_left` или `bisect_right`? | `bisect_left` возвращает число границ, строго меньших возраста, поэтому 18 остаётся в `0-18`. `bisect_right` отнёс бы 18 к `19-25`. | `age_groups/groups.py:AgeGroups.index_of`; мутация 5 в `tools/mutations.py:MUTATIONS` |
| Почему `groupby` требует сортировки? | Он склеивает только соседние элементы с одинаковым ключом. Без сортировки одна группа вышла бы несколько раз. | `age_groups/groups.py:AgeGroups.split` |
| Зачем ключ `(-age, name)`? | Минус даёт убывание возраста, `name` упорядочивает ровесников по возрастанию. Заодно номер группы не возрастает, и группы идут от старшей к младшей. | `age_groups/groups.py:AgeGroups.split` |
| Устойчива ли сортировка и важно ли это? | `sorted` устойчива, но здесь это не используется: ключ полный, а полных тёзок одного возраста условие исключает. | `age_groups/groups.py:AgeGroups.split` |
| Сложность? | `index_of` O(log k), разбивка O(n log n) из-за одной сортировки, `groupby` линейный. | `age_groups/groups.py:AgeGroups` |
| Где `ё` при сортировке? | Строки сравниваются по кодам символов: `Ё` (U+0401) раньше `А`, `ё` (U+0451) после `я`. Это записано в ограничениях. | `tests/test_age_groups.py:test_groups_and_parsing`, случай с «Ёлкин» |
| Почему не словарь «группа → список»? | Пришлось бы обходить группы по порядку и сортировать каждую отдельно. Одна сортировка и `groupby` проще и сразу дают нужный порядок. | `age_groups/groups.py:AgeGroups.split` |

## 4. Python

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| Зачем `with open(..., encoding="utf-8")`? | `with` закрывает файл даже при исключении; явная кодировка не зависит от настроек системы, кириллица читается одинаково. | `recommender/catalog.py:MovieCatalog.from_file` |
| Зачем аннотации типов? | Документируют контракт и проверяются линтером; на выполнение не влияют. Проверка в `tools/check.py:lint_function` требует их у всех параметров. | `recommender/engine.py:Recommender.recommend` |
| Что делает `if __name__ == "__main__"`? | Запускает `main` только при запуске модуля как программы; при импорте в тестах код не выполняется. | `age_groups/app.py:main`; `python -m age_groups.app 18` |
| Почему `ValueError`? | Это стандартное исключение «значение не того вида». Разбор бросает его с понятным текстом, `main` ловит и превращает в код 1. | `recommender/catalog.py:parse_id`, `recommender/catalog.py:located_error` |
| Как подставляется `StringIO`? | `io.StringIO` ведёт себя как файл: у него есть `readline`, по нему можно итерировать и писать в него через `print(file=...)`. | `tests/test_age_groups.py:test_main_end_to_end` |
| Как читаются аргументы? | `main` берёт `sys.argv[1:]`, если `argv` не передан; `parse_args` и `parse_bounds` разбирают список строк без `argparse`. | `recommender/app.py:parse_args`, `age_groups/app.py:parse_bounds` |
| Что такое doctest? | Примеры `>>>` в docstring выполняются как тесты; их {{doctest_examples}}, они запускаются в `tools/check.py:stage_doctest`. | `python -m doctest -v age_groups/app.py` |

## 5. Тесты

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| Что такое покрытие ветвей? | Учитывается не только каждая строка, но и оба исхода каждого `if`. Сейчас **{{cov_percent}}**: {{cov_statements}} операторов и {{cov_branches}} ветвей. | `.coveragerc`, `pytest.ini`; `python -m pytest` |
| Почему 100% покрытия не гарантирует корректность? | Строка может выполниться, а результат никто не проверит. Поэтому каждый `assert` проверяет вывод, а мутации показывают, что тесты ловят поломки. | `tools/mutations.py:run_mutation` |
| Что такое мутации? | Скрипт вносит в копию проекта маленькую ошибку и запускает тесты; если тест упал, мутация убита. Поймано **{{mutations_killed}} из {{mutations_total}}**. | `tools/mutations.py:MUTATIONS`; `python tools/mutations.py` |
| Почему тестов так мало и нет `parametrize`? | Функций {{tests_functions}}, но в каждой таблица случаев с подписанными `assert`, а сквозной вызов `main` покрывает весь путь. `parametrize` раздувал бы счётчик тестов без новых проверок. | `tests/test_recommender.py:test_recommend_rules` |
| Как запустить? | `python -m pytest` для тестов, `python tools/check.py --all` для всей проверки с мутациями и PDF. | `tools/check.py:main` |

## 6. Каверзные

| Вопрос | Ответ | Где в коде и как показать |
|---|---|---|
| А если файл истории огромный? | Сейчас всё в памяти: O(m) по числу id. Для огромных данных отбор и кандидаты считаются потоково, а `views` хранится в индексе; алгоритм не меняется. | `recommender/history.py:ViewingHistory.from_lines` |
| Почему не `float` для «половины»? | `common / len(watched) >= 0.5` работает, но дроби вносят риск округления и лишнее деление. `2 * common >= len(watched)` — то же в целых числах. | `recommender/engine.py:Recommender.recommend` |
| Два фильма с равным счётом — какой выведете? | Меньший id, в обоих режимах. Мутация, убирающая `-movie_id` из ключа, ловится тестом. | `tests/test_recommender.py:test_recommend_rules` |
| Почему в режиме весов не нужно делить? | Делитель `len(watched)` одинаков для всех историй. Умножение всех оценок на одно положительное число не меняет порядок и ничьи. | `recommender/engine.py:Recommender._weighted_scores` |
| А если вес считать только по отобранным историям? | В обычном режиме это одна строка: `self.history.views` заменяется на `sum(selected, Counter())`. В режиме весов истории с совпадением меньше половины перестанут добавлять очки. | `recommender/engine.py:Recommender.recommend` |
