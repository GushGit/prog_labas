#!/usr/bin/env bash
# Пошаговая демонстрация проекта «Рекомендации фильмов и возрастные группы».
# Запуск из любого места: bash demo.sh   (флаг --auto пропускает паузы)
# Следующий этап начинается после ввода "yes"; "q" завершает демонстрацию.
# Файлы в data/ не изменяются: служебные данные создаются во временной папке.

cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
ROOT=$PWD

AUTO=0; [[ "$1" == "--auto" ]] && AUTO=1

if [[ -t 1 ]]; then
  B=$'\e[1m'; C=$'\e[36m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; Z=$'\e[0m'
else B=; C=; G=; Y=; R=; Z=; fi

if [[ -x .venv/bin/python ]]; then PY=$ROOT/.venv/bin/python
elif command -v python3 >/dev/null; then PY=python3
else PY=python; fi
export PY ROOT

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export TMP

STAGE=0
TOTAL=10

banner() {   # banner "Заголовок" "что покажем"
  STAGE=$((STAGE+1))
  echo
  echo "${B}${C}════════════════════════════════════════════════════════════════${Z}"
  echo "${B}${C} Этап $STAGE из $TOTAL: $1${Z}"
  echo "${C} $2${Z}"
  echo "${B}${C}════════════════════════════════════════════════════════════════${Z}"
}

run() {      # run команда... : показать и выполнить
  echo "${Y}\$ $*${Z}"
  "$@"
  local rc=$?
  if [[ $rc -eq 0 ]]; then echo "${G}[ok]${Z}"; else echo "${R}[код возврата $rc]${Z}"; fi
  return $rc
}

shell() {    # shell 'конвейер' : показать строку и выполнить её в bash (для | и <)
  echo "${Y}\$ $1${Z}"
  bash -c "$1"
  local rc=$?
  if [[ $rc -eq 0 ]]; then echo "${G}[ok]${Z}"; else echo "${R}[код возврата $rc]${Z}"; fi
  return 0
}

wait_yes() { # ждём сигнал "yes"
  [[ $AUTO -eq 1 ]] && return 0
  local ans
  while true; do
    read -r -p "${B}Следующий этап? Введите yes (или q для выхода): ${Z}" ans || exit 0
    case "${ans,,}" in
      yes|y) return 0 ;;
      q|quit|exit) echo "Демонстрация завершена."; exit 0 ;;
      *) echo "Жду \"yes\"." ;;
    esac
  done
}

make_data() { # make_data папка "movies" "history" : набор данных для задачи 1
  mkdir -p "$1/data"
  printf '%b' "$2" > "$1/data/movies.txt"
  printf '%b' "$3" > "$1/data/history.txt"
}

echo "${B}Рекомендации фильмов и возрастные группы: демонстрация проекта${Z}"
echo "Интерпретатор: $($PY --version 2>&1)  ($PY)"
if ! $PY -c "import pytest, pytest_cov" 2>/dev/null; then
  echo "${R}Не найдены pytest/pytest-cov. Установите: python -m venv .venv && .venv/bin/pip install -r requirements.txt${Z}"
fi
for f in data/movies.txt data/history.txt; do
  [[ -f $f ]] || echo "${R}Нет файла $f (нужен задаче 1)${Z}"
done
wait_yes

banner "Состав проекта" "Два пакета с ООП, тесты, инструменты проверки и документы"
shell 'git log --oneline -n 7 2>/dev/null || echo "(не git-репозиторий)"'
shell 'ls recommender/*.py age_groups/*.py tests/*.py tools/*.py; echo; wc -l recommender/*.py age_groups/*.py | tail -n 1'
wait_yes

banner "Задача 1: пример из условия" "Данные из data/, ввод 2,4 -> Дюна в обычном режиме и в режиме весов"
shell 'echo "movies.txt:"; cat data/movies.txt; echo; echo "history.txt:"; cat data/history.txt'
shell 'echo 2,4 | $PY -m recommender.app'
shell 'echo 2,4 | $PY -m recommender.app --weighted'
wait_yes

banner "Задача 1: как считается рекомендация" "Трассировка шагов 1-3 на примере: отбор историй, кандидаты, просмотры"
run $PY -I - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["ROOT"])
from recommender.catalog import MovieCatalog
from recommender.history import ViewingHistory
from recommender.engine import Recommender, overlap
catalog = MovieCatalog.from_lines(["1,Мстители: Финал", "2,Хатико", "3,Дюна", "4,Унесенные призраками"])
lines = ["2,1,3", "1,4,3", "2,2,2,2,2,3"]
history = ViewingHistory.from_lines(lines, catalog)
watched = {2, 4}
print(f"watched = {sorted(watched)}; история отбирается, если 2 * common >= {len(watched)}")
for line, counts in zip(lines, history.film_counts):
    common = overlap(watched, counts)
    chosen = 2 * common >= len(watched)
    print(f"  {line:<12} общих {common}  отобрана: {'да ' if chosen else 'нет'}"
          f"  кандидаты: {sorted(counts.keys() - watched) if chosen else '-'}")
print("Просмотры кандидатов по ВСЕМ историям:", {m: history.views[m] for m in (1, 3)})
print("Рекомендация:", Recommender(catalog, history).recommend(watched).title)
PYEOF
wait_yes

banner "Задача 1: режим весов меняет ответ" "Истории 1,2,3 / 1,4 / 1,4, ввод 1,2: обычный режим -> 4, режим весов -> 3"
make_data "$TMP/weights" '1,Один\n2,Два\n3,Три\n4,Четыре\n' '1,2,3\n1,4\n1,4\n'
shell 'cat "$TMP/weights/data/history.txt"'
shell 'cd "$TMP/weights" && echo 1,2 | PYTHONPATH="$ROOT" $PY -m recommender.app'
shell 'cd "$TMP/weights" && echo 1,2 | PYTHONPATH="$ROOT" $PY -m recommender.app --weighted'
echo "Обычный режим: у фильма 4 больше просмотров (2 против 1)."
echo "Режим весов: история 1,2,3 совпала полностью (вес 2), оценки 3 и 4 равны -> меньший id, фильм 3."
wait_yes

banner "Задача 1: ошибки ввода, аргументов и файлов" "Сообщение в stderr, код возврата 1, без трассировки Python"
make_data "$TMP/broken" '1,Один\n2,Два\n' '1,2\n1,x\n'
shell 'echo 1,2,3,4 | $PY -m recommender.app'
shell 'echo "" | $PY -m recommender.app; echo "код: $?"'
shell 'echo 2,abc | $PY -m recommender.app; echo "код: $?"'
shell 'echo 2,9 | $PY -m recommender.app; echo "код: $?"'
shell 'echo 2,4 | $PY -m recommender.app --fast; echo "код: $?"'
shell 'cd "$TMP/broken" && echo 1 | PYTHONPATH="$ROOT" $PY -m recommender.app; echo "код: $?"'
shell 'cd "$TMP" && echo 1 | PYTHONPATH="$ROOT" $PY -m recommender.app; echo "код: $?"'
wait_yes

banner "Задача 2: пример из условия" "Границы 18 25 35 45 60 80 100; группы от старшей к младшей, ровесники по ФИО"
cat > "$TMP/respondents.txt" <<'EOF'
Ярилова Розалия Трофимовна,29
Егоров Алан Петрович,7
Кошельков Захар Брониславович,105
Иванов Варлам Якунович,88
Старостин Ростислав Ермолаевич,50
Соколов Андрей Сергеевич,15
Дьячков Нисон Иринеевич,88
END
EOF
run cat "$TMP/respondents.txt"
shell '$PY -m age_groups.app 18 25 35 45 60 80 100 < "$TMP/respondents.txt"'
wait_yes

banner "Задача 2: границы групп и плохой ввод" "Возраст на границе в нижней группе, END, пропуск плохих строк, неверные границы"
shell 'printf "Ноль,0\nВосемнадцать,18\nДевятнадцать,19\nСто,100\nСто один,101\nСто двадцать три,123\nEND\nПосле END,50\n" | $PY -m age_groups.app 18 25 35 45 60 80 100'
shell 'printf "без запятой\n,5\nБорис,x\nАнна,-3\nВера,7\n" | $PY -m age_groups.app 10; echo "код: $?"'
shell 'echo | $PY -m age_groups.app 25 18; echo "код: $?"'
shell 'echo | $PY -m age_groups.app; echo "код: $?"'
wait_yes

banner "Тесты, покрытие и доктесты" "pytest: 100% строк и ветвей (fail_under = 100), затем примеры из docstring"
run $PY -m pytest -q -p no:cacheprovider
echo
run $PY -I - <<'PYEOF'
import doctest, importlib, os, sys
sys.path.insert(0, os.environ["ROOT"])
total = failed = 0
for name in ("recommender.catalog", "recommender.history", "recommender.engine",
             "recommender.app", "age_groups.groups", "age_groups.app"):
    result = doctest.testmod(importlib.import_module(name))
    total, failed = total + result.attempted, failed + result.failed
    print(f"  {name:<22} примеров {result.attempted:>2}, ошибок {result.failed}")
print(f"Итого примеров из docstring: {total}, ошибок: {failed}")
sys.exit(1 if failed else 0)
PYEOF
wait_yes

banner "Мутационное тестирование" "В копию проекта вносятся 6 поломок; тесты должны поймать каждую"
run $PY tools/mutations.py
wait_yes

banner "Единая проверка и документы" "tools/check.py: lint, tests, doctest, smoke; список PDF с числом страниц"
run $PY tools/check.py
echo
run $PY - <<'PYEOF'
import glob
try:
    import pymupdf
except ImportError:
    pymupdf = None
for path in sorted(glob.glob("docs/*.pdf")):
    pages = pymupdf.open(path).page_count if pymupdf else "?"
    print(f"  {path:<28} {pages} стр.")
PYEOF
echo
echo "${B}${G}Демонстрация завершена.${Z}"
