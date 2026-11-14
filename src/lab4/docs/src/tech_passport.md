# Технический паспорт
> Архитектура, решения, замеры и руководство по проверке · для автора проекта
> Python {{python_version}}, {{os_name}} · {{date_ru}}

## 1. Обзор и запуск

Проект состоит из двух независимых консольных приложений на стандартной библиотеке Python и инструментов проверки. Приложения запускаются из корня проекта: пути к данным задачи 1 относительны текущей папки.

```
echo 2,4 | python -m recommender.app              # обычный режим, шаги 1-3 условия
echo 2,4 | python -m recommender.app --weighted   # режим весов (усложнение)
python -m age_groups.app 18 25 35 45 60 80 100 < respondents.txt
python tools/check.py --all                       # вся проверка, включая PDF
```

| Приложение | Вход | Выход (stdout) | Код 0 | Код 1 |
|---|---|---|---|---|
| `recommender.app` | одна строка id через запятую; файлы `data/movies.txt`, `data/history.txt` | название фильма или `Рекомендаций нет` | рекомендация выдана или кандидатов нет | неверные аргументы, плохой ввод, файл не открылся или повреждён |
| `age_groups.app` | границы в аргументах; строки `ФИО,возраст` до `END` | строки групп от старшей к младшей | всегда при верных границах, даже если строки пропущены | границы отсутствуют, не целые, отрицательные или не возрастают |

Ошибки и предупреждения пишутся только в stderr, stdout содержит только результат. Трассировка Python на плохом вводе не показывается: `main` перехватывает `ValueError` и `OSError`.

## 2. Структура проекта

```
{{tree}}
```

| Путь | Назначение |
|---|---|
| `recommender/` | задача 1: каталог, история, алгоритм, CLI |
| `age_groups/` | задача 2: группы, разбор ввода, CLI |
| `data/` | `movies.txt` и `history.txt` (пример из условия) |
| `tests/` | `test_recommender.py`, `test_age_groups.py`: сквозные и табличные тесты |
| `tools/check.py` | единая проверка: lint, tests, doctest, smoke, mutations, docs; пишет `build/facts.json` |
| `tools/mutations.py` | таблица `MUTATIONS` и запуск тестов на копиях проекта с поломками |
| `tools/build_docs.py` | сборка PDF из `docs/src/*.md` с подстановкой переменных из `build/facts.json` и проверками |
| `docs/` | `meta.json`, исходники и готовые PDF |
| `STATUS.md`, `README.md` | статус итераций и журнал решений; описание для пользователя |

## 3. Модули

### 3.1. `recommender/catalog.py`

Назначение: фильмы и их загрузка. Модуль также содержит общий разбор id, который используют история и ввод пользователя.

```
@dataclass(frozen=True)
class Movie: id: int; title: str
def parse_id(text: str) -> int
def located_error(source: str, line_no: int, error: ValueError) -> ValueError
class MovieCatalog:
    movies: dict[int, Movie]
    @classmethod from_lines(lines, source="<строки>") -> MovieCatalog
    @classmethod from_file(path: str) -> MovieCatalog
    get(movie_id: int) -> Movie
    __contains__(movie_id) -> bool
```

- Инварианты: ключ словаря равен `Movie.id`; id уникальны; названия без пробелов по краям и непустые.
- Крайние случаи: пустые строки пропускаются; строка делится по **первой** запятой (`3,Дюна, часть 1`); id только из ASCII-цифр, поэтому `-1`, `+1`, `1.5` отклоняются; повторный id даёт ошибку с номером строки.
- Сложность: загрузка O(n) по числу строк, `get` и `in` O(1).

### 3.2. `recommender/history.py`

```
@dataclass
class ViewingHistory:
    film_counts: list[Counter[int]]   # по одному на строку истории
    views: Counter[int]               # вхождения по всем строкам
    @classmethod from_lines(lines, catalog, source="<строки>") -> ViewingHistory
    @classmethod from_file(path, catalog) -> ViewingHistory
```

- Инвариант: `views` равен сумме всех `film_counts`; каждый id есть в каталоге.
- Крайние случаи: дубли в строке (`2,2,2`) считаются отдельными просмотрами; пустой элемент (`1,,3`) и id вне каталога дают `ValueError` с именем файла и номером строки.
- Сложность: O(m) по общему числу id во всех историях; `from_file` только открывает файл и делегирует `from_lines`.

### 3.3. `recommender/engine.py`

```
def overlap(watched: set[int], counts: Counter[int]) -> int
class Recommender:
    __init__(catalog: MovieCatalog, history: ViewingHistory)
    recommend(watched: set[int], weighted: bool = False) -> Movie | None
    _weighted_scores(watched: set[int]) -> Counter[int]
```

- Инвариант: в пакете нет `float`, все сравнения в целых числах.
- Сложность `recommend`: O(Σ|h|) на отбор и кандидатов плюс O(c) на выбор максимума, где c — число кандидатов. Режим весов добавляет один проход O(Σ|h|).

### 3.4. `recommender/app.py`

```
MOVIES_PATH = "data/movies.txt";  HISTORY_PATH = "data/history.txt"
def parse_watched(line: str, catalog: MovieCatalog) -> set[int]
def parse_args(argv: list[str]) -> bool
def main(argv=None, stdin=None, stdout=None, stderr=None,
         movies_path=MOVIES_PATH, history_path=HISTORY_PATH) -> int
```

- `parse_watched`: пробелы допустимы, повторы схлопываются; пустая строка или конец ввода, нецелый id, id вне каталога дают `ValueError`.
- `parse_args`: допустимы только `[]` и `["--weighted"]`, без `argparse`.
- `main` тонкая: потоки и пути приходят параметрами, поэтому тесты подставляют `io.StringIO` и временные файлы.

### 3.5. `age_groups/groups.py`

```
@dataclass(frozen=True)
class Respondent: name: str; age: int
class AgeGroups:
    bounds: list[int];  labels: list[str]
    index_of(age: int) -> int
    split(respondents) -> list[tuple[str, list[Respondent]]]
```

- Инвариант: границы непусты, целые, не меньше 0 и строго возрастают (проверяет `parse_bounds`); `labels[i]` соответствует `index_of(age) == i`.
- Метки для границ примера: {{group_labels}}.
- Сложность: `index_of` O(log k), `split` O(n log n).

### 3.6. `age_groups/app.py`

```
def parse_bounds(args: list[str]) -> list[int]
def parse_respondent(line: str) -> Respondent
def read_respondents(lines) -> tuple[list[Respondent], list[str]]
def format_group(label: str, members: list[Respondent]) -> str
def main(argv=None, stdin=None, stdout=None, stderr=None) -> int
```

- `parse_respondent` делит строку по **последней** запятой, поэтому запятая внутри ФИО допустима.
- `read_respondents` читает поток лениво и останавливается на `END` (после `strip()`, с учётом регистра); строки после `END` не читаются. Пустые строки пропускаются, плохие попадают в список предупреждений с номером строки.
- Возраст выше 123 принимается и попадает в последнюю группу.

## 4. Алгоритм рекомендаций

Обозначения: W — множество id, просмотренных пользователем; H — истории всех пользователей; для истории h через keys(h) обозначено множество её разных id, через cnt(h, m) — число вхождений фильма m в h.

1. Отбор: S = { h ∈ H : 2 · |W ∩ keys(h)| ≥ |W| }.
2. Кандидаты: C = (⋃ keys(h) по h ∈ S) \ W. Если C пусто, ответ «Рекомендаций нет».
3. Оценка: views(m) = Σ cnt(h, m) по **всем** h ∈ H. Ответ: m ∈ C с наибольшей views(m), при равенстве наименьший id (ключ `max` равен `(score, -id)`).

### 4.1. Трассировка примера условия

{{trace_example}}

### 4.2. Обоснование решений и где их менять

| Решение | Почему | Где в коде меняется одной строкой |
|---|---|---|
| Порог «хотя бы половина» в целых числах | `2 * common >= len(watched)` эквивалентно `common / len(watched) >= 0.5`, но без деления и округления | строка `2 * overlap(watched, counts) >= len(watched)` в `recommender/engine.py:Recommender.recommend` |
| Просмотры по всем историям сервиса | шаг 3 условия: «среди всех пользователей сервиса» | в строке `score = ...` метода `recommender/engine.py:Recommender.recommend` заменить `self.history.views` на `sum(selected, Counter())`, чтобы считать только по отобранным историям |
| Каждое вхождение — отдельный просмотр | строка истории — это список просмотров, повтор означает повторный просмотр | в `recommender/history.py:ViewingHistory.from_lines` заменить `Counter(ids)` на `Counter(set(ids))`, чтобы считать один просмотр на пользователя |
| Ничья — наименьший id | условие разрешает любой фильм, а тестам нужна детерминированность | ключ `(score[movie_id], -movie_id)` в `recommender/engine.py:Recommender.recommend` |
| «Хотя бы половина» по разным id | в отборе важно, *какие* фильмы совпали, а не сколько раз их смотрели | функция `recommender/engine.py:overlap` |

## 5. Режим весов

Определение: вес истории w(h) = |W ∩ keys(h)| / |W|; оценка кандидата score(m) = Σ w(h) · cnt(h, m) по всем историям. В обычном режиме вес каждого просмотра равен 1, так что режим весов — прямое обобщение шага 3. Шаги 1 и 2 в обоих режимах одинаковы.

Целочисленная форма: знаменатель |W| одинаков для всех историй, поэтому score(m) · |W| = Σ common(h) · cnt(h, m). Умножение всех оценок на одно положительное число не меняет их порядок и ничьи, поэтому `recommender/engine.py:Recommender._weighted_scores` считает сумму `common * times` в целых числах и деление не нужно.

Трассировка проверочного сценария (каталог из четырёх фильмов, истории `1,2,3` / `1,4` / `1,4`):

{{trace_weights}}

Обычный режим считает просмотры: у фильма 4 их больше. В режиме весов история `1,2,3` совпадает с пользователем полностью и поднимает фильм 3 до ничьей, а ничья решается в пользу меньшего id. Сценарий проверяют `tests/test_recommender.py:test_recommend_rules` и `tests/test_recommender.py:test_main_with_files`.

## 6. Задача 2: возрастные группы

Алгоритм: разобрать границы, прочитать респондентов до `END`, один раз отсортировать по ключу `(-age, name)`, пройти `itertools.groupby` с ключом «номер группы», для каждой группы напечатать `format_group`.

- `bisect.bisect_left(bounds, age)` возвращает число границ, строго меньших возраста. Возраст, равный границе, остаётся в нижней группе: 18 → `0-18`. `bisect_right` отнёс бы 18 к `19-25`, это одна из мутаций.
- После сортировки по `(-age, name)` возраст не возрастает, значит не возрастает и номер группы, и люди одной группы идут подряд. `groupby` объединяет только соседние элементы, поэтому без сортировки он выдал бы одну группу несколько раз.
- Внутри группы порядок уже нужный: возраст по убыванию, при равенстве ФИО по возрастанию.
- Пустые группы не появляются сами собой: `groupby` не выдаёт ключей, которых нет в данных.
- Словарь «группа → список» потребовал бы обхода всех групп по порядку и отдельной сортировки каждой; одна сортировка проще и даёт O(n log n).

Трассировка примера (границы `18 25 35 45 60 80 100`):

{{trace_groups}}

Результат запуска:

```
{{smoke_groups}}
```

## 7. Обработка ошибок

| Ситуация | Поведение | Код | Тест |
|---|---|---|---|
| Аргумент кроме `--weighted` | сообщение с использованием в stderr | 1 | `tests/test_recommender.py:test_main_with_files` |
| Пустая строка или конец ввода | «пустой ввод» в stderr | 1 | `tests/test_recommender.py:test_main_with_files` |
| Нецелый или отрицательный id во вводе | сообщение с фрагментом ввода | 1 | `tests/test_recommender.py:test_main_with_files` |
| id ввода вне каталога | «фильма с id N нет в каталоге» | 1 | `tests/test_recommender.py:test_main_with_files` |
| Файл данных не найден | текст `OSError` с путём | 1 | `tests/test_recommender.py:test_main_with_files` |
| Плохая строка `movies.txt`: нет запятой, плохой или пустой id, пустое название, повторный id | `ValueError` «файл, строка N: причина» | 1 | `tests/test_recommender.py:test_loading_and_input_parsing` |
| Плохая строка `history.txt`: пустой элемент, плохой id, id вне каталога | `ValueError` «файл, строка N: причина» | 1 | `tests/test_recommender.py:test_loading_and_input_parsing` |
| Пустые строки в файлах данных | пропускаются | 0 | `tests/test_recommender.py:test_loading_and_input_parsing` |
| Нет кандидатов | stdout: `Рекомендаций нет` | 0 | `tests/test_recommender.py:test_recommend_rules` |
| Границы: нет, не целые, отрицательные, равные или убывающие | ошибка и строка использования в stderr | 1 | `tests/test_age_groups.py:test_main_end_to_end` |
| Строка без запятой, пустое ФИО, плохой возраст | предупреждение с номером строки, строка пропущена | 0 | `tests/test_age_groups.py:test_main_end_to_end` |
| `END` в середине, конец ввода без `END`, пустой ввод | чтение останавливается; при пустом вводе вывод пуст | 0 | `tests/test_age_groups.py:test_main_end_to_end` |

## 8. Тесты

### 8.1. Карта «функция или ветка → тест»

| Код | Что проверяется | Тест |
|---|---|---|
| `recommender/app.py:main`, `recommender/app.py:parse_args` | пример `2,4` в обоих режимах, сценарий весов, все ошибки CLI и файлов | `tests/test_recommender.py:test_main_with_files` |
| `recommender/catalog.py:MovieCatalog.from_lines`, `recommender/history.py:ViewingHistory.from_lines`, `recommender/app.py:parse_watched` | разбор, пустые строки, дубли, каждая ошибка формата | `tests/test_recommender.py:test_loading_and_input_parsing` |
| `recommender/engine.py:Recommender.recommend` | ровно половина и меньше, исключение просмотренных, ничья, дубли, подсчёт по всем историям, нет кандидатов, режим весов | `tests/test_recommender.py:test_recommend_rules` |
| `age_groups/app.py:main`, `age_groups/app.py:read_respondents`, `age_groups/app.py:parse_bounds` | пример условия побайтово, `END`, плохие строки, плохие границы | `tests/test_age_groups.py:test_main_end_to_end` |
| `age_groups/groups.py:AgeGroups.index_of`, `age_groups/groups.py:AgeGroups.split`, `age_groups/app.py:parse_respondent` | возрасты 0, 18, 19, 100, 101, 123; ничья по ФИО; пустые группы; последняя запятая | `tests/test_age_groups.py:test_groups_and_parsing` |

Тестовых функций **{{tests_functions}}**, все проверки собраны в таблицы случаев, каждый `assert` подписан именем случая. Моков нет: используются только `tmp_path` и `io.StringIO`. Файловый ввод-вывод проверяет один тест с `tmp_path`.

### 8.2. Покрытие

Итог: **{{cov_percent}}** ({{cov_statements}} операторов, {{cov_branches}} ветвей), порог `fail_under = 100`.

{{coverage_table}}

### 8.3. Мутации

Тесты поймали **{{mutations_killed}} из {{mutations_total}}** намеренных поломок (`tools/mutations.py:MUTATIONS`). Мутация убита, если pytest вернул код 1.

{{mutation_table}}

### 8.4. Итог pytest

```
{{pytest_tail}}
```

## 9. Журнал решений

| Вопрос | Решение |
|---|---|
| «Хотя бы половина» | по множествам разных id, `2 * common >= len(watched)` |
| «Оставшийся список фильмов» | объединение фильмов отобранных историй минус `watched` |
| Область подсчёта в шаге 3 | все истории сервиса; счётчик `views` строится один раз при загрузке |
| Дубли в истории | каждое вхождение — отдельный просмотр |
| Ничья | наименьший id в обоих режимах |
| Кандидатов нет | `Рекомендаций нет`, код 0 |
| Ввод пользователя | id через запятую, пробелы допустимы, повторы схлопываются |
| Ошибки в файлах | `ValueError` с именем файла и номером строки; пустые строки пропускаются |
| Название с запятой | деление по первой запятой |
| Формат id и возраста | только ASCII-цифры; знак и дроби отклоняются |
| Пустое название фильма | ошибка файла |
| Вес истории | `common(h) / len(watched)`, в коде целочисленно `common(h)` |
| Аргументы задачи 1 | только `[]` и `["--weighted"]`, без `argparse` |
| Метки групп | `0-b0`, `b(i-1)+1-b(i)`, `b(last)+1+`; возраст на границе в нижней группе |
| Поиск группы | `bisect.bisect_left` |
| Сравнение ФИО | обычное сравнение строк Python, без `locale` |
| Плохая строка респондента | предупреждение в stderr, строка пропускается, код 0 |
| `END` | после `strip()`, регистр важен; конец ввода без `END` тоже завершает список |
| Возраст выше 123 | принимается, последняя группа |

## 10. Ограничения и идеи развития

- ФИО сортируются по кодам символов: `Ё` (U+0401) стоит раньше `А` (U+0410). Для алфавитного порядка нужен ключ с собственной таблицей букв.
- Все истории держатся в памяти. Для очень больших данных подойдёт однопроходный подсчёт: отбор и кандидаты считаются потоково, `views` хранится в отдельном индексе.
- Пути к данным задачи 1 относительны текущей папки, поэтому приложение запускается из корня проекта.
- Режим весов не меняет отбор шага 1: истории с совпадением меньше половины не дают кандидатов, но их просмотры входят в оценку с весом `common(h)`.
