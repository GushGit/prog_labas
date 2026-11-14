"""Консольное приложение задачи 2: разбивка респондентов по возрастным группам.

Границы групп передаются аргументами командной строки, респонденты читаются из
stdin строками «ФИО,возраст» до строки END или конца ввода, разбивка печатается в stdout.

Содержит:
    parse_bounds, parse_respondent, read_respondents, format_group, main.

Запуск из корня проекта:
    python -m age_groups.app 18 25 35 45 60 80 100 < respondents.txt
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import TextIO

from age_groups.groups import AgeGroups, Respondent

END_MARKER = "END"
USAGE = (
    "использование: python -m age_groups.app ГРАНИЦА [ГРАНИЦА ...] "
    "(целые числа >= 0 по возрастанию)"
)


def _parse_natural(text: str, what: str) -> int:
    """Разбирает целое неотрицательное число из ASCII-цифр, пробелы по краям допустимы.

    Аргументы:
        text: исходный текст.
        what: название значения для сообщения об ошибке.

    Возвращает:
        Целое число не меньше 0.

    Исключения:
        ValueError: текст не является целым неотрицательным числом.
    """
    token = text.strip()
    if not (token.isascii() and token.isdigit()):
        raise ValueError(f"{what} не является целым неотрицательным числом: {token!r}")
    return int(token)


def parse_bounds(args: list[str]) -> list[int]:
    """Разбирает границы групп из аргументов командной строки.

    Аргументы:
        args: аргументы без имени программы.

    Возвращает:
        Список границ.

    Исключения:
        ValueError: границ нет, граница не целое неотрицательное число или
            границы не возрастают строго.

    Пример:
        >>> parse_bounds(["18", "25", "35"])
        [18, 25, 35]
    """
    if not args:
        raise ValueError("не заданы границы групп")
    bounds = [_parse_natural(arg, "граница") for arg in args]
    if any(low >= high for low, high in zip(bounds, bounds[1:])):
        raise ValueError("границы должны строго возрастать")
    return bounds


def parse_respondent(line: str) -> Respondent:
    """Разбирает строку «ФИО,возраст»; делит по последней запятой.

    Аргументы:
        line: строка ввода.

    Возвращает:
        Респондент с ФИО и возрастом без пробелов по краям.

    Исключения:
        ValueError: нет запятой, пустое ФИО или возраст не целое неотрицательное число.

    Пример:
        >>> parse_respondent("Егоров Алан Петрович, 7")
        Respondent(name='Егоров Алан Петрович', age=7)
    """
    name, comma, age_text = line.rpartition(",")
    if not comma:
        raise ValueError("нет запятой между ФИО и возрастом")
    if not name.strip():
        raise ValueError("пустое ФИО")
    return Respondent(name.strip(), _parse_natural(age_text, "возраст"))


def read_respondents(lines: Iterable[str]) -> tuple[list[Respondent], list[str]]:
    """Читает респондентов до строки END или конца ввода; плохие строки пропускает.

    Аргументы:
        lines: строки ввода (например, поток stdin).

    Возвращает:
        Пару (респонденты, предупреждения с номерами пропущенных строк).
    """
    respondents: list[Respondent] = []
    warnings: list[str] = []
    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        if line == END_MARKER:
            break
        if not line:
            continue
        try:
            respondents.append(parse_respondent(line))
        except ValueError as error:
            warnings.append(f"строка {line_no} пропущена: {error}")
    return respondents, warnings


def format_group(label: str, members: list[Respondent]) -> str:
    """Форматирует строку группы «Группа: ФИО (возраст), ...».

    Аргументы:
        label: метка группы.
        members: участники группы в нужном порядке.

    Возвращает:
        Строка без перевода строки в конце.

    Пример:
        >>> format_group("0-18", [Respondent("Соколов Андрей Сергеевич", 15)])
        '0-18: Соколов Андрей Сергеевич (15)'
    """
    people = ", ".join(f"{person.name} ({person.age})" for person in members)
    return f"{label}: {people}"


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Запускает приложение: границы, чтение респондентов, разбивка, вывод.

    Аргументы:
        argv: аргументы без имени программы; None означает sys.argv[1:].
        stdin: поток ввода; None означает sys.stdin.
        stdout: поток результата; None означает sys.stdout.
        stderr: поток ошибок и предупреждений; None означает sys.stderr.

    Возвращает:
        0 при успехе (в том числе с пропущенными строками), 1 при плохих границах.
    """
    argv = sys.argv[1:] if argv is None else argv
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        groups = AgeGroups(parse_bounds(argv))
    except ValueError as error:
        print(f"Ошибка: {error}\n{USAGE}", file=stderr)
        return 1
    respondents, warnings = read_respondents(stdin)
    for warning in warnings:
        print(f"Предупреждение: {warning}", file=stderr)
    for label, members in groups.split(respondents):
        print(format_group(label, members), file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
