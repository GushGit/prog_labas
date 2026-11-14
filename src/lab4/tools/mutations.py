"""Мутационное тестирование: 6 намеренных поломок, каждую обязаны поймать тесты.

Для каждой мутации проект копируется в build/mutants/<N>/ (без .venv, build, .git),
в копии подстрока old заменяется на new (old должна встречаться ровно один раз),
и запускается pytest. Мутация убита, если pytest вернул 1 (упал тест); код 2 и
выше означает, что мутация сломала сборку, это ошибка таблицы. Рабочее дерево
не меняется. Итог пишется в build/mutations.json.

Запуск из корня проекта:
    python tools/mutations.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUTANTS = ROOT / "build" / "mutants"
IGNORE = shutil.ignore_patterns(".venv", "build", ".git", "__pycache__", ".pytest_cache",
                                ".coverage", "docs")

MUTATIONS = [
    {"id": 1, "file": "recommender/engine.py",
     "old": "2 * overlap(watched, counts) >= len(watched)",
     "new": "2 * overlap(watched, counts) > len(watched)",
     "description": "`>=` заменено на `>` в проверке половины"},
    {"id": 2, "file": "recommender/engine.py",
     "old": "candidates |= counts.keys() - watched",
     "new": "candidates |= counts.keys()",
     "description": "убрано `- watched` (просмотренные не исключаются)"},
    {"id": 3, "file": "recommender/engine.py",
     "old": "(score[movie_id], -movie_id)",
     "new": "(score[movie_id],)",
     "description": "убрано `-movie_id` из ключа `max` (ничья)"},
    {"id": 4, "file": "recommender/engine.py",
     "old": "scores[movie_id] += common * times",
     "new": "scores[movie_id] += times",
     "description": "убран множитель `common` в оценке режима весов"},
    {"id": 5, "file": "age_groups/groups.py",
     "old": "bisect.bisect_left(self.bounds, age)",
     "new": "bisect.bisect_right(self.bounds, age)",
     "description": "`bisect_left` заменён на `bisect_right`"},
    {"id": 6, "file": "age_groups/groups.py",
     "old": "(-person.age, person.name)",
     "new": "(-person.age,)",
     "description": "убрано `name` из ключа сортировки"},
]


def run_mutation(mutation: dict) -> dict:
    """Создаёт копию проекта с одной мутацией, запускает pytest и возвращает итог."""
    target = MUTANTS / str(mutation["id"])
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT, target, ignore=IGNORE)
    path = target / mutation["file"]
    source = path.read_text(encoding="utf-8")
    occurrences = source.count(mutation["old"])
    if occurrences != 1:
        raise SystemExit(f"мутация {mutation['id']}: old встречается {occurrences} раз")
    path.write_text(source.replace(mutation["old"], mutation["new"]), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "-q", "--no-cov", "-p", "no:cacheprovider"],
        cwd=target, capture_output=True, text=True, encoding="utf-8")
    output = result.stdout + result.stderr
    failed = re.search(r"^FAILED (\S+)", output, re.M)
    return {**mutation, "returncode": result.returncode, "killed": result.returncode == 1,
            "failed_test": failed.group(1) if failed else ""}


def main() -> int:
    """Прогоняет все мутации, пишет build/mutations.json и возвращает 0, если все убиты."""
    results = []
    for mutation in MUTATIONS:
        item = run_mutation(mutation)
        results.append(item)
        if item["returncode"] >= 2:
            state = f"ОШИБКА ТАБЛИЦЫ (pytest код {item['returncode']})"
        else:
            state = "убита" if item["killed"] else "ВЫЖИЛА"
        print(f"{item['id']}. {item['description']}: {state} {item['failed_test']}")
    MUTANTS.parent.mkdir(exist_ok=True)
    (MUTANTS.parent / "mutations.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    killed = sum(item["killed"] for item in results)
    print(f"убито {killed} из {len(results)}")
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
