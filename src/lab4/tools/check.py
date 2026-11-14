"""Единая проверка проекта: lint, tests, doctest, smoke, mutations, docs.

Запуск из корня проекта:
    python tools/check.py              # lint, tests, doctest, smoke + build/facts.json
    python tools/check.py --mutations  # плюс мутационное тестирование
    python tools/check.py --docs       # плюс сборка и проверка PDF
    python tools/check.py --all        # все этапы (финальная проверка)

Каждый этап печатает одну строку OK/FAIL; полный вывод лежит в build/logs/.
Код возврата 0 только если все включённые этапы прошли.
"""

from __future__ import annotations

import ast
import datetime
import doctest
import importlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
LOGS = BUILD / "logs"
PACKAGES = ("recommender", "age_groups")
MAX_LINE = 100
MAX_TEST_FUNCTIONS = 10
EXAMPLES_REQUIRED = {
    "recommender/catalog.py": ["MovieCatalog.from_lines"],
    "recommender/app.py": ["parse_watched"],
    "recommender/engine.py": ["Recommender.recommend"],
    "age_groups/groups.py": ["AgeGroups.index_of", "AgeGroups.split"],
    "age_groups/app.py": ["parse_bounds", "parse_respondent", "format_group"],
}
EXAMPLE_MOVIES = "1,Мстители: Финал\n2,Хатико\n3,Дюна\n4,Унесенные призраками\n"
EXAMPLE_HISTORY = "2,1,3\n1,4,3\n2,2,2,2,2,3\n"
WEIGHTS_MOVIES = "1,Один\n2,Два\n3,Три\n4,Четыре\n"
WEIGHTS_HISTORY = "1,2,3\n1,4\n1,4\n"
BOUNDS = ["18", "25", "35", "45", "60", "80", "100"]
GROUPS_INPUT = (
    "Ярилова Розалия Трофимовна,29\nЕгоров Алан Петрович,7\n"
    "Кошельков Захар Брониславович,105\nИванов Варлам Якунович,88\n"
    "Старостин Ростислав Ермолаевич,50\nСоколов Андрей Сергеевич,15\n"
    "Дьячков Нисон Иринеевич,88\nEND\n"
)
GROUPS_OUTPUT = (
    "101+: Кошельков Захар Брониславович (105)\n"
    "81-100: Дьячков Нисон Иринеевич (88), Иванов Варлам Якунович (88)\n"
    "46-60: Старостин Ростислав Ермолаевич (50)\n"
    "26-35: Ярилова Розалия Трофимовна (29)\n"
    "0-18: Соколов Андрей Сергеевич (15), Егоров Алан Петрович (7)\n"
)
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
TREE_SKIP = {".venv", "build", ".git", "__pycache__", ".pytest_cache", ".coverage"}

STATE: dict = {}


def py_files(*folders: str) -> list[Path]:
    """Возвращает .py файлы в указанных папках проекта."""
    return sorted(p for folder in folders for p in (ROOT / folder).rglob("*.py"))


def rel(path: Path) -> str:
    """Возвращает путь относительно корня проекта."""
    return path.relative_to(ROOT).as_posix()


def lint_function(node: ast.FunctionDef, qualname: str, where: str) -> list[str]:
    """Проверяет docstring и аннотации одной функции или метода."""
    problems = []
    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    params = [a for a in args if a.arg not in ("self", "cls")]
    params += [a for a in (node.args.vararg, node.args.kwarg) if a]
    for arg in params:
        if arg.annotation is None:
            problems.append(f"{where}:{qualname}: нет аннотации у параметра {arg.arg}")
    if node.returns is None:
        problems.append(f"{where}:{qualname}: нет аннотации возвращаемого значения")
    if qualname.split(".")[-1].startswith("__"):
        return problems
    doc = ast.get_docstring(node)
    if not doc:
        return problems + [f"{where}:{qualname}: нет docstring"]
    first = doc.splitlines()[0]
    if len(first) > MAX_LINE or not first.endswith("."):
        problems.append(f"{where}:{qualname}: первая строка docstring длиннее 100 или без точки")
    returns_value = not (isinstance(node.returns, ast.Constant) and node.returns.value is None)
    raises = any(isinstance(n, ast.Raise) for n in walk_own(node))
    for needed, section in ((params, "Аргументы:"), (returns_value, "Возвращает:"),
                            (raises, "Исключения:")):
        if needed and section not in doc:
            problems.append(f"{where}:{qualname}: нет секции {section}")
    return problems


def walk_own(node: ast.AST) -> list[ast.AST]:
    """Обходит тело функции, не заходя во вложенные функции и классы."""
    result = []
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        result.append(child)
        stack.extend(ast.iter_child_nodes(child))
    return result


def lint_package_file(path: Path) -> list[str]:
    """Проверяет docstring модуля, классов и функций одного файла пакета по §6."""
    where = rel(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    problems = [] if ast.get_docstring(tree) else [f"{where}: нет docstring модуля"]
    docs: dict[str, str] = {}

    def visit(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                docs[prefix + node.name] = doc
                if not doc:
                    problems.append(f"{where}:{node.name}: нет docstring класса")
                elif "Атрибуты:" not in doc:
                    problems.append(f"{where}:{node.name}: нет секции Атрибуты:")
                visit(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docs[prefix + node.name] = ast.get_docstring(node) or ""
                problems.extend(lint_function(node, prefix + node.name, where))

    visit(tree.body, "")
    for name in EXAMPLES_REQUIRED.get(where, []):
        if ">>>" not in docs.get(name, ""):
            problems.append(f"{where}:{name}: нет примера >>>")
    return problems


def stage_lint() -> tuple[bool, str]:
    """Этап lint: документация, длина строк, float, число тестов, запрещённые конструкции."""
    problems = []
    for path in py_files(*PACKAGES):
        problems += lint_package_file(path)
    for path in py_files(*PACKAGES, "tests", "tools"):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if len(line) > MAX_LINE:
                problems.append(f"{rel(path)}:{no}: строка длиннее {MAX_LINE}")
    for path in py_files("recommender"):
        if re.search(r"\bfloat\b", path.read_text(encoding="utf-8")):
            problems.append(f"{rel(path)}: используется float")
    forbidden = ("param" + "etrize", "pragma: " + "no cover")
    for path in py_files(*PACKAGES, "tests"):
        text = path.read_text(encoding="utf-8")
        problems += [f"{rel(path)}: найдено {word!r}" for word in forbidden if word in text]
    count = count_test_functions()
    if count > MAX_TEST_FUNCTIONS:
        problems.append(f"тестовых функций {count} > {MAX_TEST_FUNCTIONS}")
    write_log("lint.log", "\n".join(problems) or "OK")
    if problems:
        return False, f"{len(problems)} замечаний, первое: {problems[0]}"
    return True, f"{len(py_files(*PACKAGES))} модулей, тестовых функций {count}"


def count_test_functions() -> int:
    """Считает функции def test_ в tests/."""
    return sum(len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), re.M))
               for p in py_files("tests"))


def write_log(name: str, text: str) -> None:
    """Записывает полный лог этапа в build/logs/."""
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / name).write_text(text, encoding="utf-8")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Запускает команду с захватом вывода в UTF-8."""
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kwargs)


def stage_tests() -> tuple[bool, str]:
    """Этап tests: pytest с покрытием строк и ветвей, fail_under из .coveragerc."""
    cov_json = BUILD / "coverage.json"
    result = run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                  f"--cov-report=json:{cov_json}"], cwd=ROOT)
    output = result.stdout + result.stderr
    write_log("pytest.log", output)
    passed = re.search(r"(\d+) passed", output)
    STATE["tests_passed"] = passed.group(1) if passed else "0"
    STATE["pytest_tail"] = pytest_tail(output)
    if result.returncode != 0:
        tail = output.strip().splitlines()[-1] if output.strip() else ""
        return False, f"pytest код {result.returncode}: {tail}"
    totals = json.loads(cov_json.read_text(encoding="utf-8"))["totals"]
    STATE["coverage"] = json.loads(cov_json.read_text(encoding="utf-8"))
    return True, f"{STATE['tests_passed']} passed, покрытие {totals['percent_covered_display']}%"


def pytest_tail(output: str) -> str:
    """Возвращает таблицу покрытия и итоговую строку из вывода pytest."""
    lines = output.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("Name ")), len(lines))
    return "\n".join(line for line in lines[start:]
                     if not line.startswith("Coverage JSON written")).strip()


def stage_doctest() -> tuple[bool, str]:
    """Этап doctest: doctest.testmod для каждого модуля обоих пакетов."""
    sys.path.insert(0, str(ROOT))
    failed = attempted = 0
    report = []
    for path in py_files(*PACKAGES):
        name = rel(path)[:-3].replace("/", ".").removesuffix(".__init__")
        result = doctest.testmod(importlib.import_module(name))
        failed += result.failed
        attempted += result.attempted
        report.append(f"{name}: {result.attempted} примеров, {result.failed} ошибок")
    write_log("doctest.log", "\n".join(report))
    STATE["doctest_examples"] = str(attempted)
    return failed == 0 and attempted > 0, f"{attempted} примеров, ошибок {failed}"


def run_cli(module: str, args: list[str], stdin: str, cwd: Path) -> subprocess.CompletedProcess:
    """Запускает настоящий CLI как подпроцесс с PYTHONPATH на корень проекта."""
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", module, *args], input=stdin.encode("utf-8"),
                          capture_output=True, cwd=cwd, env=env)


def smoke_block(command: str, stdin: str, stdout: str) -> str:
    """Формирует блок «команда, ввод, фактический вывод» для документов."""
    return f"$ {command}\n[ввод]\n{stdin.rstrip()}\n[вывод]\n{stdout.rstrip()}"


def stage_smoke() -> tuple[bool, str]:
    """Этап smoke: настоящие CLI через subprocess, сверка вывода побайтово."""
    example = BUILD / "example"
    (example / "data").mkdir(parents=True, exist_ok=True)
    (example / "data" / "movies.txt").write_text(EXAMPLE_MOVIES, encoding="utf-8")
    (example / "data" / "history.txt").write_text(EXAMPLE_HISTORY, encoding="utf-8")
    checks = [
        ("movies", "recommender.app", [], "2,4\n", 0, "Дюна\n"),
        ("movies_weighted", "recommender.app", ["--weighted"], "2,4\n", 0, "Дюна\n"),
        ("groups", "age_groups.app", BOUNDS, GROUPS_INPUT, 0, GROUPS_OUTPUT),
        ("movies_bad_input", "recommender.app", [], "2,x\n", 1, ""),
        ("movies_bad_args", "recommender.app", ["--fast"], "2,4\n", 1, ""),
        ("groups_bad_bounds", "age_groups.app", ["25", "18"], "", 1, ""),
    ]
    log, failures = [], []
    for name, module, args, stdin, code, expected in checks:
        result = run_cli(module, args, stdin, example)
        out = result.stdout.decode("utf-8")
        log.append(f"== {name}: код {result.returncode}\n{out}{result.stderr.decode('utf-8')}")
        if result.returncode != code or result.stdout != expected.encode("utf-8"):
            failures.append(name)
        if b"Traceback" in result.stderr:
            failures.append(f"{name}: трассировка в stderr")
        command = " ".join(["python", "-m", module, *args])
        STATE[f"smoke_{name}"] = smoke_block(command, stdin, out)
    write_log("smoke.log", "\n".join(log))
    if failures:
        return False, "не совпало: " + ", ".join(failures)
    return True, f"{len(checks)} запусков совпали побайтово"


def coverage_table(coverage: dict) -> str:
    """Строит Markdown-таблицу покрытия по файлам из coverage.json."""
    rows = ["| Файл | Операторов | Ветвей | Покрытие |", "|---|---|---|---|"]
    for name, data in sorted(coverage["files"].items()):
        summary = data["summary"]
        rows.append(f"| `{name}` | {summary['num_statements']} | {summary['num_branches']} | "
                    f"{summary['percent_covered_display']}% |")
    return "\n".join(rows)


def mutation_facts() -> dict[str, str]:
    """Читает build/mutations.json и готовит переменные о мутациях."""
    path = BUILD / "mutations.json"
    if not path.exists():
        return {"mutations_total": "0", "mutations_killed": "0",
                "mutation_table": "Мутационное тестирование не запускалось."}
    results = json.loads(path.read_text(encoding="utf-8"))
    rows = ["| № | Что изменено | Результат | Какой тест упал |", "|---|---|---|---|"]
    for item in results:
        verdict = "убита" if item["killed"] else "ВЫЖИЛА"
        rows.append(f"| {item['id']} | {item['description']} (`{item['file']}`) | {verdict} | "
                    f"`{item['failed_test'] or '-'}` |")
    return {"mutations_total": str(len(results)),
            "mutations_killed": str(sum(item["killed"] for item in results)),
            "mutation_table": "\n".join(rows)}


def project_tree() -> str:
    """Строит текстовое дерево проекта без служебных папок."""
    lines = ["."]

    def walk(folder: Path, prefix: str) -> None:
        entries = sorted((p for p in folder.iterdir() if p.name not in TREE_SKIP
                          and not p.name.endswith(".pyc")),
                         key=lambda p: (p.is_file(), p.name))
        for index, entry in enumerate(entries):
            last = index == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "│   "))

    walk(ROOT, "")
    return "\n".join(lines)


def date_ru(day: datetime.date) -> str:
    """Форматирует дату по-русски без зависимости от локали."""
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def student_line() -> str:
    """Строит строку «Студент: …, группа …» из docs/meta.json."""
    meta = json.loads((ROOT / "docs" / "meta.json").read_text(encoding="utf-8"))
    parts = []
    if meta.get("student"):
        parts.append(f"Студент: {meta['student']}")
    if meta.get("group"):
        parts.append(f"группа {meta['group']}")
    if meta.get("teacher"):
        parts.append(f"преподаватель: {meta['teacher']}")
    return ", ".join(parts)


def recommend_trace(movies: str, history_text: str, watched_line: str) -> str:
    """Строит Markdown-трассировку алгоритма рекомендации настоящими классами пакета."""
    sys.path.insert(0, str(ROOT))
    from recommender.app import parse_watched
    from recommender.catalog import MovieCatalog
    from recommender.engine import Recommender, overlap
    from recommender.history import ViewingHistory

    catalog = MovieCatalog.from_lines(movies.splitlines())
    lines = [line for line in history_text.splitlines() if line.strip()]
    history = ViewingHistory.from_lines(lines, catalog)
    watched = parse_watched(watched_line, catalog)
    engine = Recommender(catalog, history)
    rows = [f"Ввод `{watched_line}`, `watched = {sorted(watched)}`, "
            f"`len(watched) = {len(watched)}`.",
            "", "| История | Общих (`common`) | `2 * common >= len(watched)` | Даёт кандидатов |",
            "|---|---|---|---|"]
    candidates: set[int] = set()
    for line, counts in zip(lines, history.film_counts):
        common = overlap(watched, counts)
        chosen = 2 * common >= len(watched)
        new = sorted(counts.keys() - watched) if chosen else []
        candidates |= set(new)
        rows.append(f"| `{line}` | {common} | {'да' if chosen else 'нет'} | "
                    f"{', '.join(map(str, new)) or '-'} |")
    weighted = engine._weighted_scores(watched)
    rows += ["", "| Кандидат | Название | Просмотров по всем историям | Оценка режима весов |",
             "|---|---|---|---|"]
    for movie_id in sorted(candidates):
        rows.append(f"| {movie_id} | {catalog.get(movie_id).title} | {history.views[movie_id]} | "
                    f"{weighted[movie_id]} |")
    plain, heavy = engine.recommend(watched), engine.recommend(watched, weighted=True)
    rows += ["", f"Итог: обычный режим выбирает **{plain.id} «{plain.title}»**, режим весов "
                 f"выбирает **{heavy.id} «{heavy.title}»**."]
    return "\n".join(rows)


def groups_labels() -> list[str]:
    """Возвращает метки групп для границ примера §4.3."""
    sys.path.insert(0, str(ROOT))
    from age_groups.groups import AgeGroups

    return AgeGroups([int(b) for b in BOUNDS]).labels


def groups_trace() -> str:
    """Строит Markdown-трассировку разбивки примера §4.3 настоящими классами пакета."""
    sys.path.insert(0, str(ROOT))
    from age_groups.app import read_respondents
    from age_groups.groups import AgeGroups

    groups = AgeGroups([int(b) for b in BOUNDS])
    respondents, _ = read_respondents(GROUPS_INPUT.splitlines())
    rows = ["| Порядок после сортировки | Ключ `(-age, name)` | `bisect_left` | Группа |",
            "|---|---|---|---|"]
    ordered = sorted(respondents, key=lambda person: (-person.age, person.name))
    for number, person in enumerate(ordered, start=1):
        index = groups.index_of(person.age)
        rows.append(f"| {number}. {person.name} | ({-person.age}, …) | {index} | "
                    f"`{groups.labels[index]}` |")
    return "\n".join(rows)


def write_facts() -> None:
    """Собирает build/facts.json из результатов этапов tests и smoke."""
    totals = STATE["coverage"]["totals"]
    facts = {
        "python_version": platform.python_version(),
        "os_name": f"{platform.system()} {platform.release().split('-')[0]}",
        "date_ru": date_ru(datetime.date.today()),
        "tests_functions": str(count_test_functions()),
        "tests_passed": STATE["tests_passed"],
        "cov_percent": f"{totals['percent_covered_display']}%",
        "cov_statements": str(totals["num_statements"]),
        "cov_branches": str(totals["num_branches"]),
        "coverage_table": coverage_table(STATE["coverage"]),
        "tree": project_tree(),
        "pytest_tail": STATE["pytest_tail"],
        "smoke_movies": STATE["smoke_movies"],
        "smoke_movies_weighted": STATE["smoke_movies_weighted"],
        "smoke_groups": STATE["smoke_groups"],
        "student_line": student_line(),
        "doctest_examples": STATE["doctest_examples"],
        "modules_count": str(len(py_files(*PACKAGES))),
        "package_lines": str(sum(len(p.read_text(encoding="utf-8").splitlines())
                                 for p in py_files(*PACKAGES))),
    }
    facts["trace_example"] = recommend_trace(EXAMPLE_MOVIES, EXAMPLE_HISTORY, "2,4")
    facts["trace_weights"] = recommend_trace(WEIGHTS_MOVIES, WEIGHTS_HISTORY, "1,2")
    facts["trace_groups"] = groups_trace()
    facts["group_labels"] = ", ".join(f"`{label}`" for label in groups_labels())
    facts.update(mutation_facts())
    BUILD.mkdir(exist_ok=True)
    (BUILD / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def stage_tool(script: str, log: str) -> tuple[bool, str]:
    """Запускает tools/<script> и возвращает последнюю строку его вывода."""
    result = run([sys.executable, str(ROOT / "tools" / script)], cwd=ROOT)
    output = result.stdout + result.stderr
    write_log(log, output)
    lines = output.strip().splitlines()
    return result.returncode == 0, lines[-1] if lines else f"код {result.returncode}"


def main(argv: list[str]) -> int:
    """Запускает этапы по флагам и возвращает 0, только если все прошли."""
    unknown = set(argv) - {"--mutations", "--docs", "--all"}
    if unknown:
        print(f"неизвестные флаги: {' '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    stages = [("lint", stage_lint), ("tests", stage_tests), ("doctest", stage_doctest),
              ("smoke", stage_smoke)]
    if "--mutations" in argv or "--all" in argv:
        stages.append(("mutations", lambda: stage_tool("mutations.py", "mutations.log")))
    if "--docs" in argv or "--all" in argv:
        stages.append(("docs", lambda: stage_tool("build_docs.py", "docs.log")))
    all_ok = True
    for name, stage in stages:
        if name in ("mutations", "docs") and all_ok:
            write_facts()
        ok, message = stage()
        all_ok &= ok
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {message}")
        if name == "smoke" and all_ok:
            write_facts()
    if all_ok and len(stages) > 4:
        write_facts()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
