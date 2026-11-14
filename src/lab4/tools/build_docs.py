"""Сборка и проверка четырёх PDF из docs/src/*.md и build/facts.json.

Подставляет {{переменные}} из build/facts.json, верстает подмножество Markdown
через reportlab (DejaVu Sans), затем проверяет результат: число страниц, отсутствие
плейсхолдеров, наличие всех символов в шрифтах, извлекаемый текст (pymupdf),
длину строк в блоках кода и ссылки на код вида `путь.py:Имя`. Каждая страница
рендерится в build/png/<документ>-<N>.png.

Запуск из корня проекта (после python tools/check.py):
    python tools/build_docs.py
"""

from __future__ import annotations

import ast
import glob
import json
import re
import sys
from pathlib import Path

import pymupdf
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "src"
FACTS = ROOT / "build" / "facts.json"
PNG = ROOT / "build" / "png"
BLUE = colors.HexColor("#1F4E8C")
GREY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#EEF3FA")
CODE_BG = colors.HexColor("#F4F5F7")
LINE = colors.HexColor("#C9D3E0")
FOOTER = "Рекомендации и возрастные группы"
MAX_CODE_LINE = 95
CODE_CHUNK = 45

# документ -> (тип для колонтитула, мин. страниц, макс. страниц, ключевые слова)
DOCUMENTS = {
    "report": ("отчёт", 2, 3, ["Что сделано", "Проверка корректности", "мутаци",
                                 "Принятые решения", "Ограничения", "Дюна"]),
    "elevator_pitch": ("elevator pitch", 2, 2, ["За 30 секунд", "Карта проекта",
                                                 "тонких места", "тестов"]),
    "tech_passport": ("технический паспорт", 1, 99, ["Обзор и запуск", "Режим весов",
                                                      "Обработка ошибок", "Журнал решений",
                                                      "Ограничения"]),
    "cheatsheet": ("шпаргалка", 1, 99, ["Вопрос", "Ответ", "ООП", "Каверзные"]),
}
FONT_FILES = {
    "DejaVuSans": "DejaVuSans.ttf",
    "DejaVuSans-Bold": "DejaVuSans-Bold.ttf",
    "DejaVuSans-Oblique": "DejaVuSans-Oblique.ttf",
    "DejaVuSans-BoldOblique": "DejaVuSans-BoldOblique.ttf",
    "DejaVuSansMono": "DejaVuSansMono.ttf",
}
CODE_REF = re.compile(r"`([\w/]+\.py):([A-Za-z_][\w.]*)`")


def find_font(file_name: str) -> str:
    """Ищет файл шрифта в системных папках или в mpl-data/fonts из .venv."""
    patterns = [f"/usr/share/fonts/**/{file_name}",
                str(ROOT / ".venv" / "lib" / "python*" / "site-packages" / "matplotlib"
                    / "mpl-data" / "fonts" / "ttf" / file_name)]
    for pattern in patterns:
        found = sorted(glob.glob(pattern, recursive=True))
        if found:
            return found[0]
    raise SystemExit(f"шрифт {file_name} не найден")


def register_fonts() -> None:
    """Регистрирует DejaVu Sans и DejaVu Sans Mono в reportlab."""
    for name, file_name in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, find_font(file_name)))
    pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
                                  italic="DejaVuSans-Oblique",
                                  boldItalic="DejaVuSans-BoldOblique")


def make_styles() -> dict[str, ParagraphStyle]:
    """Создаёт стили абзацев по §10.0."""
    base = ParagraphStyle("body", fontName="DejaVuSans", fontSize=10, leading=14,
                          alignment=TA_LEFT, spaceAfter=4)
    return {
        "body": base,
        "title": ParagraphStyle("title", parent=base, fontName="DejaVuSans-Bold", fontSize=22,
                                leading=27, textColor=BLUE, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base, textColor=GREY, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName="DejaVuSans-Bold", fontSize=14,
                             leading=18, textColor=BLUE, spaceBefore=10, spaceAfter=5,
                             keepWithNext=True),
        "h3": ParagraphStyle("h3", parent=base, fontName="DejaVuSans-Bold", fontSize=11,
                             leading=15, spaceBefore=6, spaceAfter=3, keepWithNext=True),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=14, bulletIndent=3,
                                 spaceAfter=2),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.5, leading=11, spaceAfter=0),
        "head": ParagraphStyle("head", parent=base, fontName="DejaVuSans-Bold", fontSize=8.5,
                               leading=11, textColor=colors.white, spaceAfter=0),
        "code": ParagraphStyle("code", parent=base, fontName="DejaVuSansMono", fontSize=8,
                               leading=10.2, spaceAfter=0),
    }


def escape(text: str) -> str:
    """Экранирует символы XML для reportlab."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Переводит `код`, **жирный** и *курсив* в разметку reportlab."""
    parts = text.split("`")
    result = []
    for index, part in enumerate(parts):
        if index % 2:
            result.append(f'<font name="DejaVuSansMono">{escape(part)}</font>')
        else:
            part = escape(part)
            part = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", part)
            part = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", part)
            result.append(part)
    return "".join(result)


def substitute(text: str, facts: dict[str, str], name: str) -> str:
    """Подставляет {{переменные}}; неизвестная переменная или остаток {{ — ошибка."""
    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in facts:
            raise SystemExit(f"{name}: неизвестная переменная {{{{{key}}}}}")
        return facts[key]

    result = re.sub(r"\{\{(\w+)\}\}", replace, text)
    if "{{" in result:
        raise SystemExit(f"{name}: после подстановки остался '{{{{'")
    return result


def split_row(line: str) -> list[str]:
    """Делит строку Markdown-таблицы на ячейки, учитывая `|` внутри обратных кавычек."""
    cells, current, in_code = [], "", False
    for char in line.strip().strip("|"):
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append(current.strip())
            current = ""
        else:
            current += char
    cells.append(current.strip())
    return cells


def longest_word(cell: str) -> float:
    """Возвращает ширину самого длинного неразрывного слова ячейки в пунктах."""
    best = 0.0
    for index, part in enumerate(cell.split("`")):
        font = "DejaVuSansMono" if index % 2 else "DejaVuSans-Bold"
        for word in part.split():
            best = max(best, pdfmetrics.stringWidth(word, font, 8.5))
    return best


def fit_widths(weights: list[float], minimums: list[float], width: float) -> list[float]:
    """Делит ширину по весам, не опуская столбец ниже ширины его самого длинного слова."""
    widths = [width * w / sum(weights) for w in weights]
    fixed: set[int] = set()
    for _ in weights:
        short = [i for i, w in enumerate(widths) if w < minimums[i] and i not in fixed]
        if not short:
            break
        fixed.update(short)
        free = width - sum(minimums[i] for i in fixed)
        rest = sum(weights[i] for i in range(len(weights)) if i not in fixed)
        if not rest:
            break
        widths = [minimums[i] if i in fixed else free * weights[i] / rest
                  for i in range(len(weights))]
    return widths


def make_table(rows: list[list[str]], styles: dict, width: float) -> Table:
    """Верстает таблицу: тёмно-синяя шапка, чередующаяся подкраска, переносы в ячейках."""
    count = len(rows[0])
    weights, minimums = [], []
    for col in range(count):
        cells = [re.sub(r"[*]", "", row[col]) for row in rows if col < len(row)]
        weights.append(min(max(max(len(c) for c in cells), 6), 70) ** 0.8)
        minimums.append(max(longest_word(c) for c in cells) + 10)
    widths = fit_widths(weights, minimums, width)
    data = [[Paragraph(inline(cell), styles["head" if r == 0 else "cell"])
             for cell in row + [""] * (count - len(row))] for r, row in enumerate(rows)]
    table = Table(data, colWidths=widths, repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    commands += [("BACKGROUND", (0, r), (-1, r), LIGHT) for r in range(2, len(rows), 2)]
    table.setStyle(TableStyle(commands))
    return table


def code_block(lines: list[str], styles: dict, width: float, name: str) -> list:
    """Верстает блок кода кусками на светлом фоне; строки длиннее 95 — ошибка."""
    for line in lines:
        if len(line) > MAX_CODE_LINE:
            raise SystemExit(f"{name}: строка кода длиннее {MAX_CODE_LINE}: {line!r}")
    blocks = []
    for start in range(0, len(lines), CODE_CHUNK):
        chunk = "\n".join(lines[start:start + CODE_CHUNK])
        table = Table([[Preformatted(chunk, styles["code"])]], colWidths=[width])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                                   ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        blocks.append(table)
    blocks.append(Spacer(1, 6))
    return blocks


def parse_markdown(text: str, styles: dict, width: float, name: str) -> list:
    """Переводит поддерживаемое подмножество Markdown в flowables reportlab."""
    story: list = []
    lines = text.splitlines()
    i = 0
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), styles["body"]))
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            story += code_block(lines[i + 1:j], styles, width, name)
            i = j + 1
            continue
        if stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = split_row(lines[i])
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            story += [make_table(rows, styles, width), Spacer(1, 6)]
            continue
        if not stripped:
            flush()
        elif stripped == "---":
            flush()
            story.append(PageBreak())
        elif stripped.startswith("### "):
            flush()
            story.append(Paragraph(inline(stripped[4:]), styles["h3"]))
        elif stripped.startswith("## "):
            flush()
            story.append(Paragraph(inline(stripped[3:]), styles["h2"]))
        elif stripped.startswith("# "):
            flush()
            story.append(Paragraph(inline(stripped[2:]), styles["title"]))
        elif stripped.startswith(">"):
            flush()
            content = stripped[1:].strip()
            if content:
                story.append(Paragraph(inline(content), styles["subtitle"]))
        elif stripped.startswith("- "):
            flush()
            story.append(Paragraph(inline(stripped[2:]), styles["bullet"], bulletText="•"))
        elif re.match(r"\d+\. ", stripped):
            flush()
            number, rest = stripped.split(" ", 1)
            story.append(Paragraph(inline(rest), styles["bullet"], bulletText=number))
        else:
            paragraph.append(stripped)
        i += 1
    flush()
    return keep_headings(story)


def keep_headings(story: list) -> list:
    """Склеивает заголовок со следующим блоком, чтобы он не остался внизу страницы один."""
    result = []
    i = 0
    while i < len(story):
        item = story[i]
        is_heading = isinstance(item, Paragraph) and item.style.name in ("h2", "h3")
        if is_heading and i + 1 < len(story) and not isinstance(story[i + 1], PageBreak):
            group = [item]
            i += 1
            while (i < len(story) and isinstance(story[i], Paragraph)
                   and story[i].style.name in ("h2", "h3")):
                group.append(story[i])
                i += 1
            if i < len(story) and not isinstance(story[i], PageBreak):
                group.append(story[i])
                i += 1
            result.append(KeepTogether(group))
        else:
            result.append(item)
            i += 1
    return result


def check_fonts(text: str, name: str) -> None:
    """Проверяет, что каждый символ текста есть в cmap обычного и моноширинного шрифтов."""
    for font_name in ("DejaVuSans", "DejaVuSansMono"):
        cmap = pdfmetrics.getFont(font_name).face.charToGlyph
        missing = sorted({ch for ch in text if ch not in "\n\r\t" and ord(ch) not in cmap})
        if missing:
            raise SystemExit(f"{name}: символов нет в {font_name}: {missing}")


def check_code_refs(text: str, name: str) -> int:
    """Проверяет ссылки `путь.py:Имя` и `путь.py:Класс.метод` по AST."""
    count = 0
    for path_text, qualname in CODE_REF.findall(text):
        path = ROOT / path_text
        if not path.exists():
            raise SystemExit(f"{name}: ссылка на несуществующий файл {path_text}")
        if qualname not in definitions(path):
            raise SystemExit(f"{name}: в {path_text} нет определения {qualname}")
        count += 1
    return count


def definitions(path: Path) -> set[str]:
    """Возвращает имена классов, функций, методов и констант модуля."""
    names: set[str] = set()

    def visit(body: list, prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(prefix + node.name)
                visit(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names.update(prefix + t.id for t in targets if isinstance(t, ast.Name))

    visit(ast.parse(path.read_text(encoding="utf-8")).body, "")
    return names


def build(name: str, facts: dict[str, str]) -> str:
    """Собирает один PDF, проверяет его и рендерит страницы в PNG."""
    kind, min_pages, max_pages, keywords = DOCUMENTS[name]
    source = (SRC / f"{name}.md").read_text(encoding="utf-8")
    text = substitute(source, facts, name)
    check_fonts(text, name)
    refs = check_code_refs(text, name)
    styles = make_styles()
    output = ROOT / "docs" / f"{name}.pdf"
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm, title=name,
                            author=FOOTER)

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("DejaVuSans", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(2 * cm, 1.1 * cm, f"{FOOTER} · {kind}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"стр. {document.page}")
        canvas.restoreState()

    doc.build(parse_markdown(text, styles, doc.width, name), onFirstPage=footer,
              onLaterPages=footer)

    pdf = pymupdf.open(output)
    pages = pdf.page_count
    if not min_pages <= pages <= max_pages:
        raise SystemExit(f"{name}: {pages} стр., нужно {min_pages}-{max_pages}")
    extracted = "".join(page.get_text() for page in pdf)
    flat = " ".join(extracted.split()).lower()
    for word in keywords:
        if word.lower() not in flat:
            raise SystemExit(f"{name}: в тексте PDF нет ключевого слова {word!r}")
    for bad in ("(cid:", "�", "TODO", "FIXME", "{{"):
        if bad in extracted:
            raise SystemExit(f"{name}: в тексте PDF найдено {bad!r}")
    PNG.mkdir(parents=True, exist_ok=True)
    for old in PNG.glob(f"{name}-*.png"):
        old.unlink()
    for number, page in enumerate(pdf, start=1):
        page.get_pixmap(dpi=150).save(PNG / f"{name}-{number}.png")
        if not page.get_text().strip():
            raise SystemExit(f"{name}: пустая страница {number}")
    return f"{name}.pdf: {pages} стр., ссылок на код {refs}"


def main(argv: list[str]) -> int:
    """Собирает все документы (или перечисленные в argv) и печатает итог."""
    if not FACTS.exists():
        raise SystemExit("нет build/facts.json: сначала запустите python tools/check.py")
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    register_fonts()
    names = argv or [n for n in DOCUMENTS if (SRC / f"{n}.md").exists()]
    summary = [build(name, facts) for name in names]
    for line in summary:
        print(line)
    missing = [n for n in DOCUMENTS if not (SRC / f"{n}.md").exists()]
    if missing:
        print(f"нет исходников: {', '.join(missing)}")
        return 1
    print("; ".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
