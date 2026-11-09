import argparse
import ast
import csv
import html
import inspect
import os
import re
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
PDF_PATH = ROOT / "Звіт_ЛР2_Левандівський.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

sys.path.insert(0, str(ROOT / "src"))

from data_processor import analytics, data, decorators, processors

ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def num(value: float, digits: int) -> str:
    return f"{value:,.{digits}f}".replace(",", " ")


def code(source: str) -> str:
    text = source.strip()
    cls = "code keep" if text.count("\n") < 14 else "code"
    return f'<pre class="{cls}">{esc(text)}</pre>'


def strip_docstrings(source: str) -> str:
    tree = ast.parse(source)
    drop: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str) and first.end_lineno is not None:
                    drop.update(range(first.lineno, first.end_lineno + 1))
    lines = source.splitlines()
    kept = [line for number, line in enumerate(lines, 1) if number not in drop]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept))


def src(*objects: object) -> str:
    return code("\n\n".join(strip_docstrings(inspect.getsource(obj)).rstrip() for obj in objects))


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", check=False
    )


def keep_numbers_together(markup: str) -> str:
    pieces = re.split(r"(<pre.*?</pre>|<svg.*?</svg>)", markup, flags=re.S)
    return "".join(
        piece if piece.startswith(("<pre", "<svg")) else re.sub(r"(?<=\d) (?=\d{3}\b)", " ", piece)
        for piece in pieces
    )


def plural(number: int, one: str, few: str, many: str) -> str:
    if number % 10 == 1 and number % 100 != 11:
        return one
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return few
    return many


def times(value: float) -> str:
    return plural(round(value), "раз", "рази", "разів")


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def id_list(items: list[dict]) -> str:
    return ", ".join(str(item["id"]) for item in items)


class Numbering:
    def __init__(self) -> None:
        self.table = 0
        self.figure = 0

    def tcap(self, text: str) -> str:
        self.table += 1
        return f'<p class="tcap">Таблиця {self.table} – {text}</p>'

    def fcap(self, text: str) -> str:
        self.figure += 1
        return f'<p class="fcap">Рисунок {self.figure} – {text}</p>'


def program_output() -> str:
    result = run([sys.executable, "-m", "data_processor.main"])
    assert result.returncode == 0, result.stderr
    return result.stdout


def unit_tests() -> str:
    result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    assert result.returncode == 0, result.stderr
    ran = re.search(r"Ran (\d+) tests? in ([\d.]+)s", result.stderr)
    assert ran and result.stderr.rstrip().endswith("OK"), result.stderr
    return f"Ran {ran.group(1)} tests in {ran.group(2)}s — OK"


def linters(venv: Path | None) -> list[tuple[str, str]]:
    if venv is None:
        return []
    scripts = venv / "Scripts"
    checks = [
        ("ruff check src tests", [scripts / "ruff.exe", "check", "--no-cache", "src", "tests"]),
        (
            "ruff format --check src tests",
            [scripts / "ruff.exe", "format", "--check", "--no-cache", "src", "tests"],
        ),
        (
            "mypy src tests",
            [scripts / "mypy.exe", "--no-incremental", "--cache-dir=nul", "src", "tests"],
        ),
    ]
    results = []
    for title, args in checks:
        result = run([str(a) for a in args])
        assert result.returncode == 0, result.stdout + result.stderr
        lines = [ln for ln in result.stdout.splitlines() if ln and "note:" not in ln]
        results.append((title, lines[-1]))
    return results


def read_benchmark() -> list[dict[str, float]]:
    with (ROOT / "results" / "benchmark.csv").open(encoding="utf-8") as file:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(file)]


def count_functions() -> tuple[int, int]:
    modules = sorted((ROOT / "src" / "data_processor").glob("*.py"))
    total = 0
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(isinstance(node, ast.FunctionDef) for node in tree.body)
    return total, len(modules)


def project_tree() -> str:
    lines = ["Lab_02/", "├── pyproject.toml", "├── README.md", "├── .gitignore"]
    lines.append("├── src/")
    lines.append("│   └── data_processor/")
    files = sorted(p.name for p in (ROOT / "src" / "data_processor").glob("*.py"))
    files.remove("__init__.py")
    files.insert(0, "__init__.py")
    for i, name in enumerate(files):
        lines.append(f"│       {'└──' if i == len(files) - 1 else '├──'} {name}")
    lines.append("├── tests/")
    tests = sorted(p.name for p in (ROOT / "tests").glob("test_*.py"))
    for i, name in enumerate(tests):
        lines.append(f"│   {'└──' if i == len(tests) - 1 else '├──'} {name}")
    lines.append("├── results/        summary.json, benchmark.csv")
    lines.append("└── report/         build_report.py (генератор цього звіту)")
    return "\n".join(lines)


def benchmark_chart(rows: list[dict[str, float]]) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    ink, secondary, grid, axis = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Arial"],
            "font.size": 9,
        }
    )
    series = [
        ("list_search", "пошук у list (find_student_linear)", "#2a78d6", "o"),
        ("list_in", "x in list", "#eb6834", "s"),
        ("dict_search", "index.get(x) (dict)", "#1baf7a", "^"),
        ("set_in", "x in set", "#eda100", "D"),
    ]
    sizes = [row["size"] for row in rows]
    fig, ax = plt.subplots(figsize=(6.5, 2.45))
    for key, label, color, marker in series:
        values = [row[key] * 1e6 for row in rows]
        ax.plot(
            sizes,
            values,
            color=color,
            lw=1.6,
            marker=marker,
            ms=7,
            mec="white",
            mew=1.5,
            label=label,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3,
        )
    for key, fmt in (
        ("list_search", "{:.0f} мкс"),
        ("list_in", "{:.0f} мкс"),
        ("dict_search", "≈{:.2f} мкс"),
    ):
        value = rows[-1][key] * 1e6
        ax.annotate(
            fmt.format(value),
            (sizes[-1], value),
            xytext=(9, 0),
            textcoords="offset points",
            va="center",
            color=ink,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(sizes[0] / 1.6, sizes[-1] * 4.5)
    ax.set_ylim(0.005, 5000)
    ax.xaxis.set_major_locator(FixedLocator(sizes))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_locator(FixedLocator([0.01, 0.1, 1, 10, 100, 1000]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " "))
    )
    ax.set_xlabel("кількість записів (логарифмічна шкала)", color=secondary)
    ax.set_ylabel("час одного пошуку, мкс", color=secondary)
    ax.grid(True, color=grid, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(axis)
    ax.tick_params(colors=secondary, length=0)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        ncol=4,
        frameon=False,
        fontsize=8,
        labelcolor=ink,
        handlelength=1.6,
        columnspacing=1.2,
        borderaxespad=0.2,
    )
    fig.tight_layout(pad=0.4)
    buffer = StringIO()
    fig.savefig(buffer, format="svg")
    plt.close(fig)
    svg = buffer.getvalue()
    return svg[svg.index("<svg") :]


CSS = """
@page { size: A4; margin: 20mm 15mm 20mm 30mm;
  @bottom-center { content: counter(page); font: 12pt "Times New Roman", serif; } }
@page :first { @bottom-center { content: none; } }
html { background: #fff; }
body { margin: 0; color: #000; background: #fff; font-family: "Times New Roman", serif;
  font-size: 14pt; line-height: 1.2; }
p { margin: 0 0 2pt; text-indent: 1.25cm; text-align: justify; }
h1 { font-size: 14pt; text-align: center; margin: 12pt 0 6pt; break-after: avoid; }
h2 { font-size: 14pt; margin: 8pt 0 3pt; text-indent: 1.25cm; break-after: avoid; }
ul { margin: 0 0 4pt 1.25cm; padding-left: 0.6cm; }
li { text-align: justify; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.82em; }
pre.code, pre.out { font-family: Consolas, "Courier New", monospace; font-size: 9pt;
  line-height: 1.15; margin: 3pt 0 6pt; padding: 4pt 8pt; white-space: pre-wrap;
  background: #f6f6f4; border-left: 3px solid #c3c2b7; orphans: 4; widows: 4; }
pre.keep { break-inside: avoid; }
pre.out { font-size: 8.6pt; background: #fbfbfa; border: 1px solid #c3c2b7; }
pre.tree { font-size: 10pt; break-inside: avoid; }
table { width: 100%; border-collapse: collapse; font-size: 11pt; line-height: 1.15;
  margin: 2pt 0 8pt; break-inside: auto; }
th, td { border: 1px solid #000; padding: 2pt 5pt; vertical-align: top; text-align: left; }
th { background: #f0efec; font-weight: bold; }
td.n, th.n { text-align: right; white-space: nowrap; }
table.num td { text-align: right; white-space: nowrap; }
table.num td:first-child { text-align: left; }
tr { break-inside: avoid; }
.tcap { text-indent: 0; text-align: left; margin: 6pt 0 2pt; break-after: avoid; }
.fcap { text-indent: 0; text-align: center; margin: 2pt 0 8pt; }
.figure { text-align: center; break-inside: avoid; margin-top: 4pt; }
.figure svg { width: 100%; height: auto; }
.title { height: 255mm; display: flex; flex-direction: column; justify-content: space-between;
  text-align: center; break-after: page; line-height: 1.5; }
.title .head { font-size: 14pt; }
.title .main { margin-top: 30mm; }
.title .main .big { font-size: 20pt; font-weight: bold; letter-spacing: 2pt; }
.title .main .theme { font-size: 16pt; font-weight: bold; margin-top: 10pt; }
.title .sign { align-self: flex-end; text-align: left; width: 85mm; margin-top: 30mm; }
.title .city { margin-top: auto; }
"""


def build_html(venv: Path | None) -> str:
    n = Numbering()
    output = program_output()
    tests = unit_tests()
    lint = linters(venv)
    bench = read_benchmark()
    functions, modules = count_functions()

    students = data.students
    index = processors.create_student_index(students)
    average = round(sum(s["average_grade"] for s in students) / len(students), 2)
    best = analytics.find_best_student(students)
    per_group = analytics.stats_by_group(students)
    successful = processors.filter_by_min_grade(students, 85)
    ranking = processors.sort_by_grade(students)
    groups = processors.group_students(students)
    surnames = processors.find_by_last_name(students, "Мельник")
    unique_surnames = len(processors.get_unique_values(students, "last_name"))
    assert best is not None and f"{average:.2f}" in output
    assert sum(len(members) for members in groups.values()) == len(students)
    assert round(sum(s.average * s.size for s in per_group.values()) / len(students), 2) == average
    assert unique_surnames == len(students) - 1 and len(surnames) == 2

    group_list = ", ".join(f"{group} – {len(members)}" for group, members in groups.items())

    parts: list[str] = []
    add = parts.append

    add("""
<section class="title">
  <div class="head">МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ<br>
  Львівський національний університет імені Івана Франка</div>
  <div class="main">
    <div class="big">ЗВІТ</div>
    <div>до лабораторної роботи №2</div>
    <div>з дисципліни «Професійний Python»</div>
    <div class="theme">Тема: «Структури даних та функціональна декомпозиція»</div>
  </div>
  <div class="sign">Виконав:<br>студент Левандівський Назар<br><br>
  Перевірив:<br>Куньо Іван Михайлович</div>
  <div class="city">Львів – 2026</div>
</section>""")

    add("<h1>Мета роботи</h1>")
    add(
        "<p>Сформувати практичні навички використання базових і розширених структур даних "
        "Python (list, tuple, set, dict, модуль collections), навчитися обирати структуру "
        "відповідно до задачі, оцінювати складність основних операцій та декомпозувати "
        "програму на невеликі функції з чіткою відповідальністю, використовуючи *args, "
        "**kwargs, lambda, closures і decorators.</p>"
    )

    add("<h1>1. Постановка задачі</h1>")
    add(
        "<p><b>Варіант 1. Аналіз успішності студентів</b> (узгоджено з ЛР1 «Система обліку "
        "студентів»). Вхідні дані – набір студентів з полями: ім'я, прізвище, група, середній "
        "бал. Потрібно створити модуль обробки структурованих даних, який реалізує операції з "
        "таблиці 1, використовує всі основні структури даних, comprehensions, функції вищого "
        "порядку, closure і decorator, а також містить аналіз складності та benchmark "
        "пошуку.</p>"
    )
    add(n.tcap("Вимоги варіанта 1 та їх реалізація (результат на демонстраційних даних)"))
    add(
        table(
            ["Вимога", "Функція", "Результат"],
            [
                [
                    "пошук студента за ID",
                    "<code>find_student</code>",
                    f"3 → {esc(data.full_name(index[3]))}",
                ],
                [
                    "пошук за прізвищем (без урахування регістру)",
                    "<code>find_by_last_name</code>",
                    "«Мельник» → " + ", ".join(esc(data.full_name(s)) for s in surnames),
                ],
                ["групування за групою", "<code>group_students</code>", group_list],
                ["середній бал усіх студентів", "<code>calculate_average</code>", f"{average:.2f}"],
                [
                    "найкращий студент",
                    "<code>find_best_student</code>",
                    f"{esc(data.full_name(best))}, {best['average_grade']:.2f}",
                ],
                [
                    "фільтрація за мін. балом (85)",
                    "<code>filter_by_min_grade</code>",
                    "ID " + id_list(successful),
                ],
                [
                    "сортування за середнім балом",
                    "<code>sort_by_grade</code>",
                    f"ID {id_list(ranking[:3])} …",
                ],
                [
                    "dict-index за ID студента",
                    "<code>create_student_index</code>",
                    f"{len(index)} ключів",
                ],
            ],
        )
    )

    add("<h1>2. Опис структури даних</h1>")
    add(
        "<p>Один студент – це словник (dict) з п'ятьма полями (таблиця 2). Такий формат "
        "відповідає JSON-like даним, легко серіалізується і дозволяє звертатися до полів за "
        "ключем. Набір студентів зберігається у списку (list) <code>students</code> – це "
        "впорядкована колекція, яку можна фільтрувати, сортувати й групувати. Демонстраційні "
        "дані задано таблицею кортежів <code>STUDENT_ROWS</code>, з якої списком comprehension "
        "через <code>create_student</code> будуються записи; для великих наборів функція "
        "<code>generate_students(count, seed)</code> генерує відтворювані випадкові дані. "
        f"Демонстраційний набір містить {len(students)} студентів у {len(groups)} групах, "
        f"{unique_surnames} унікальних прізвищ (прізвище «Мельник» трапляється двічі, тому "
        "пошук за прізвищем повертає список).</p>"
    )
    add(n.tcap("Поля запису студента"))
    add(
        table(
            ["Ключ", "Тип", "Приклад", "Зміст"],
            [
                ["<code>id</code>", "int", "3", "ідентифікатор студента (унікальний ключ індексу)"],
                ["<code>first_name</code>", "str", '"Ірина"', "ім'я"],
                ["<code>last_name</code>", "str", '"Бондар"', "прізвище"],
                ["<code>group</code>", "str", '"PI-22"', "група (не порожня)"],
                ["<code>average_grade</code>", "float", "95.2", "середній бал, 0–100"],
            ],
        )
    )

    add("<h1>3. Вибір структур даних</h1>")
    add(n.tcap("Використані структури даних і причини вибору"))
    add(
        table(
            ["Структура", "Де використано", "Чому саме вона"],
            [
                [
                    "list",
                    "<code>students</code>, результати фільтрації та сортування",
                    "впорядкований змінюваний набір; підтримує сортування і зріз",
                ],
                [
                    "tuple",
                    "<code>STUDENT_ROWS</code>, <code>GRADE_LEVELS</code>, <code>GROUPS</code>, "
                    "ключ сортування у <code>sort_items</code>, <code>GradeStats</code> (NamedTuple)",
                    "незмінні групи значень; порівнюються лексикографічно; hashable",
                ],
                [
                    "set / frozenset",
                    "<code>get_unique_values</code>, фільтр груп у closure, "
                    "<code>options.keys() - SUMMARY_DEFAULTS.keys()</code>",
                    "унікальність і перевірка <code>in</code> за O(1); операції над множинами",
                ],
                [
                    "dict",
                    "запис студента, dict-індекс за ID, <code>LEVEL_LABELS</code>, підсумок",
                    "доступ за ключем O(1); природне представлення запису",
                ],
                [
                    "defaultdict(list)",
                    "<code>group_students</code>, <code>group_nested</code>",
                    "групування без перевірки, чи існує ключ",
                ],
                [
                    "Counter",
                    "<code>count_students_by_group</code>, <code>operation_counts</code>",
                    "підрахунок частот, <code>most_common()</code>",
                ],
                [
                    "deque(maxlen=5)",
                    "<code>operation_history</code>",
                    "журнал останніх операцій: append O(1), старі записи відкидаються",
                ],
            ],
        )
    )
    add(
        "<p>Приклад використання collections – групування з defaultdict і підрахунок з Counter:</p>"
    )
    add(src(processors.group_students, processors.count_students_by_group))

    add("<h1>4. Структура проєкту</h1>")
    add(
        "<p>Проєкт має src-layout, як у ЛР1, і встановлюється командою "
        "<code>python -m pip install -e .</code>; точки входу – "
        "<code>python -m data_processor.main</code> і "
        "<code>python -m data_processor.benchmark</code> (або console commands "
        "<code>student-report</code>, <code>student-benchmark</code>).</p>"
    )
    add(f'<pre class="code keep tree">{esc(project_tree())}</pre>')
    add(n.tcap("Призначення модулів"))
    add(
        table(
            ["Модуль", "Відповідальність"],
            [
                [
                    "<code>data.py</code>",
                    "вхідні дані, константи, <code>create_student</code>, "
                    "<code>generate_students</code>",
                ],
                [
                    "<code>decorators.py</code>",
                    "<code>measure_time</code>, параметризований "
                    "<code>track_operation</code>, журнал deque і Counter",
                ],
                [
                    "<code>processors.py</code>",
                    "індекс, пошук, фільтри (closures), групування, сортування, pipeline",
                ],
                [
                    "<code>analytics.py</code>",
                    "середнє, найкращий студент, статистика, підсумок, експорт у JSON",
                ],
                ["<code>benchmark.py</code>", "експериментальна частина: list vs dict/set"],
                ["<code>main.py</code>", "точка входу: демонстрація всіх операцій"],
            ],
        )
    )

    add("<h1>5. Основні функції</h1>")
    word = plural(functions, "функцію", "функції", "функцій")
    add(
        f"<p>Програму розбито на {functions} {word} верхнього рівня у {modules} модулях; "
        "кожна виконує одну логічну задачу (таблиця 5).</p>"
    )
    add(n.tcap("Основні функції модуля"))
    add(
        table(
            ["Функція", "Призначення", "Прийом"],
            [
                [
                    "<code>create_student_index(students)</code>",
                    "dict-індекс за ID",
                    "dict comprehension",
                ],
                [
                    "<code>find_student(index, student_id)</code>",
                    "пошук за ID",
                    "dict.get, декоратор",
                ],
                [
                    "<code>find_by_last_name(students, last_name)</code>",
                    "пошук за прізвищем",
                    "list comprehension, casefold",
                ],
                [
                    "<code>filter_items(items, predicate)</code>",
                    "універсальний фільтр",
                    "функція вищого порядку",
                ],
                ["<code>create_grade_filter(minimum)</code>", "фільтр за мін. балом", "closure"],
                [
                    "<code>create_group_filter(*groups)</code>",
                    "фільтр за групами",
                    "closure, *args",
                ],
                [
                    "<code>group_students</code>, <code>group_nested</code>",
                    "групування, вкладене групування",
                    "defaultdict, рекурсія",
                ],
                [
                    "<code>sort_by_grade</code>, <code>sort_items</code>",
                    "сортування за балом / за кількома полями",
                    "lambda, tuple-ключ",
                ],
                [
                    "<code>calculate_average</code>",
                    "середній бал",
                    "generator expression, декоратор",
                ],
                [
                    "<code>calculate_stats(*grades)</code>",
                    "статистика значень",
                    "*args, NamedTuple",
                ],
                ["<code>build_summary(students, **options)</code>", "підсумковий звіт", "**kwargs"],
                [
                    "<code>run_pipeline(items, *steps)</code>",
                    "послідовна обробка",
                    "reduce + lambda",
                ],
            ],
        )
    )

    add("<h1>6. Приклади ключових конструкцій</h1>")
    add("<h2>6.1. Comprehensions і generator expression</h2>")
    add(
        "<p>Set comprehension збирає унікальні значення поля, dict comprehension будує індекс, "
        "list comprehension фільтрує, а generator expression рахує суму без проміжного "
        "списку:</p>"
    )
    add(
        src(
            processors.get_unique_values,
            processors.create_student_index,
            processors.filter_items,
            analytics.calculate_average,
        )
    )
    add("<h2>6.2. *args</h2>")
    add(
        "<p>Функція <code>calculate_stats</code> приймає довільну кількість значень; при виклику "
        "генератор розпаковується оператором <code>*</code>: "
        '<code>calculate_stats(*(s["average_grade"] for s in students))</code>.</p>'
    )
    add(src(analytics.calculate_stats))
    add("<h2>6.3. **kwargs</h2>")
    add(
        "<p><code>create_student(**fields)</code> формує запис з іменованих аргументів і "
        "перевіряє його: усі поля на місці, група не порожня, середній бал у межах 0–100. "
        "<code>build_summary(students, **options)</code> приймає налаштування "
        "<code>top</code> і <code>min_grade</code>; невідомі ключі знаходяться різницею "
        "множин ключів і дають <code>TypeError</code>.</p>"
    )
    add(src(data.create_student))
    add("<h2>6.4. lambda</h2>")
    add(
        "<p>lambda використано як короткий ключ сортування та пошуку максимуму. У "
        "<code>sort_items</code> ключ – це tuple значень кількох полів, тому студенти "
        "впорядковуються спершу за групою, потім за середнім балом.</p>"
    )
    add(src(processors.sort_by_grade, processors.sort_items))
    add("<h2>6.5. Closure</h2>")
    add(
        "<p><code>create_grade_filter</code> повертає внутрішню функцію "
        "<code>predicate</code>, яка пам'ятає <code>minimum</code> після завершення зовнішньої "
        "функції (значення зберігається в <code>predicate.__closure__</code>, що перевіряє "
        "тест). Так само <code>create_group_filter(*groups)</code> замикає frozenset "
        "допустимих груп.</p>"
    )
    add(src(processors.create_grade_filter, processors.create_group_filter))
    add("<h2>6.6. Decorators</h2>")
    add(
        "<p><code>measure_time</code> виводить час виконання функції, не змінюючи її коду "
        "(застосовано до <code>calculate_average</code>). <code>track_operation(label)</code> – "
        "параметризований декоратор: зовнішня функція приймає параметр, повертає декоратор, "
        "а wrapper після кожного виклику записує операцію в deque та Counter. "
        "<code>functools.wraps</code> зберігає ім'я та docstring обгорнутої функції.</p>"
    )
    add(src(decorators.measure_time, decorators.track_operation))

    add("<h1>7. Результат роботи програми</h1>")
    add("<p>Вивід команди <code>python -m data_processor.main</code>:</p>")
    add(f'<pre class="out">{esc(output.rstrip())}</pre>')
    group_sums = " + ".join(num(s.average * s.size, 1) for s in per_group.values())
    total = sum(s.average * s.size for s in per_group.values())
    add(
        f"<p>Ручна перевірка: сума балів за групами {group_sums} = {num(total, 1)}, середній "
        f"бал {num(total, 1)} / {len(students)} = {average:.2f}, що збігається з виводом "
        "програми; найвищий бал у списку – "
        f"{best['average_grade']:.1f} ({esc(data.full_name(best))}).</p>"
    )

    add("<h1>8. Аналіз складності операцій</h1>")
    add(n.tcap("Часова складність операцій програми (n – кількість студентів)"))
    add(
        table(
            ["Операція", "Реалізація", "Складність"],
            [
                ["побудова dict-індексу", "<code>create_student_index</code>", "O(n)"],
                [
                    "пошук за ID у list",
                    "<code>find_student_linear</code>",
                    "O(n), у середньому n/2 порівнянь",
                ],
                [
                    "пошук за ID в індексі",
                    "<code>find_student</code> (dict.get)",
                    "O(1) у середньому",
                ],
                [
                    "перевірка <code>x in set</code>",
                    "<code>'PI-24' in groups</code>",
                    "O(1) у середньому",
                ],
                ["фільтрація", "<code>filter_by_min_grade</code>", "O(n)"],
                [
                    "групування / підрахунок",
                    "<code>group_students</code>, <code>count_students_by_group</code>",
                    "O(n)",
                ],
                ["вкладене групування", "<code>group_nested</code> (k рівнів)", "O(n·k)"],
                [
                    "середнє, максимум",
                    "<code>calculate_average</code>, <code>find_best_student</code>",
                    "O(n), пам'ять O(1)",
                ],
                [
                    "сортування",
                    "<code>sort_by_grade</code>, <code>sort_items</code>",
                    "O(n log n) (Timsort)",
                ],
                [
                    "топ-k студентів",
                    "<code>sort_by_grade(...)[:k]</code>",
                    "O(n log n); heapq.nlargest – O(n log k)",
                ],
                ["запис у журнал", "<code>deque.append</code> з maxlen", "O(1)"],
            ],
        )
    )
    add(
        "<p>Якщо пошуків за ID багато, вигідно один раз побудувати індекс за O(n) і далі "
        "шукати за O(1) замість O(n) на кожен пошук (перевірено в розділі 9).</p>"
    )

    add("<h1>9. Експериментальна частина (benchmark)</h1>")
    add(
        "<p>Для 1 000, 10 000 і 100 000 згенерованих студентів виміряно середній час пошуку "
        "200 випадкових ID (<code>timeit</code>, найкращий із 5 повторів): A – лінійний "
        "пошук у list, B – <code>index.get</code> у dict-індексі, а також <code>x in list</code>, "
        "<code>x in set</code> і час побудови індексу "
        "(<code>python -m data_processor.benchmark</code>).</p>"
    )
    add(n.tcap("Результати benchmark (Python 3.12, Windows 11)"))
    bench_rows = []
    for row in bench:
        bench_rows.append(
            [
                num(row["size"], 0),
                num(row["list_search"] * 1e6, 2),
                num(row["dict_search"] * 1e6, 3),
                num(row["list_search"] / row["dict_search"], 0),
                num(row["list_in"] * 1e6, 2),
                num(row["set_in"] * 1e6, 3),
                num(row["index_build"] * 1e3, 3),
            ]
        )
    add(
        table(
            [
                "Кількість records",
                "list search, мкс",
                "dict search, мкс",
                "dict швидше, разів",
                "x in list, мкс",
                "x in set, мкс",
                "побудова індексу, мс",
            ],
            bench_rows,
            cls="num",
        )
    )
    caption = n.fcap("Час одного пошуку залежно від кількості записів (обидві осі логарифмічні)")
    add(f'<div class="figure">{benchmark_chart(bench)}{caption}</div>')

    first, mid, last = bench
    g1 = mid["list_search"] / first["list_search"]
    g2 = last["list_search"] / mid["list_search"]
    d_spread = max(r["dict_search"] for r in bench) / min(r["dict_search"] for r in bench)
    breakeven = [r["index_build"] / (r["list_search"] - r["dict_search"]) for r in bench]
    assert 5 < g1 < 20 and 5 < g2 < 20
    assert d_spread < 2
    assert last["list_search"] > last["list_in"] > last["set_in"]
    assert abs(last["dict_search"] - last["set_in"]) < 0.5 * last["dict_search"]
    add(
        f"<p>При збільшенні кількості записів у 10 разів час пошуку в list зростає в "
        f"{num(g1, 1)} та {num(g2, 1)} раза – лінійна залежність O(n), на графіку це пряма з "
        f"нахилом 1. Час пошуку в dict майже не змінюється (≈{num(last['dict_search'] * 1e6, 2)} "
        f"мкс, розкид {num(d_spread, 1)}×) – це O(1). На 100 000 записів індекс швидший у "
        f"{num(last['list_search'] / last['dict_search'], 0)} "
        f"{times(last['list_search'] / last['dict_search'])}. "
        f"<code>x in list</code> приблизно в {num(last['list_search'] / last['list_in'], 1)} "
        f"раза швидший за <code>find_student_linear</code>, бо цикл виконується в C, але "
        f"залишається O(n); <code>x in set</code> працює так само швидко, як dict (на графіку "
        f"їхні лінії збігаються).</p>"
    )
    add(
        f"<p>Побудова індексу коштує O(n) ({num(last['index_build'] * 1e3, 1)} мс на 100 000 "
        f"записів) і окупається вже після {num(min(breakeven), 0)}–{num(max(breakeven), 0)} "
        f"пошуків. Отже, теоретична складність добре узгоджується з практичним часом: для "
        f"багаторазового пошуку за ключем потрібно використовувати dict або set.</p>"
    )

    add("<h1>10. Перевірка правильності</h1>")
    add(
        "<p>Тести (<code>tests/</code>, unittest) перевіряють пошук обома способами, межі "
        "фільтрів, closure, групування, сортування, pipeline, валідацію, агрегації, експорт JSON, "
        "декоратори і benchmark. Пакет встановлено в чисте venv через "
        "<code>pip install -e .</code>, console commands працюють.</p>"
    )
    checks = [["<code>python -m unittest discover -s tests</code>", esc(tests)]]
    checks += [[f"<code>{esc(title)}</code>", esc(line)] for title, line in lint]
    add(n.tcap("Результати перевірок"))
    add(table(["Перевірка", "Результат"], checks))
    add(
        "<p>Усі обов'язкові вимоги розділу 25 методички виконано (розділи 1–9 звіту). Із "
        "завдань підвищеної складності реалізовано всі десять: універсальні фільтрація і "
        "сортування, параметризований декоратор, closures для фільтрів, вкладене групування, "
        "Counter, deque-журнал, benchmark list vs set/dict, експорт у JSON і pipeline.</p>"
    )

    add("<h1>Висновки</h1>")
    ratio_floor = last["list_search"] / last["dict_search"] // 1000 * 1000
    add(
        "<p>Створено модуль аналізу успішності студентів (варіант 1), що продовжує ЛР1: "
        "пошук, фільтрація, групування, сортування, агрегація і статистика. Структури обрано "
        "за властивостями: list – впорядкований набір, tuple – незмінні константи і складені "
        "ключі, set – унікальність і швидка перевірка належності, dict – записи та індекс, "
        "collections – групування, підрахунок і журнал операцій. Функції вищого порядку, "
        "closures і decorators дозволили змінювати поведінку без зміни основного коду. "
        "Експеримент підтвердив теорію: час пошуку в list зростає лінійно, у dict – сталий, і "
        f"на 100 000 записів різниця перевищує {num(ratio_floor, 0)} {times(ratio_floor)}.</p>"
    )

    body = keep_numbers_together("\n".join(parts))
    return (
        "<!doctype html><html lang='uk'><head><meta charset='utf-8'>"
        "<title>Звіт ЛР2</title>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )


def print_pdf(html_path: Path, pdf_path: Path, profile: Path) -> None:
    args = [
        str(EDGE),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    subprocess.run(args, check=True, capture_output=True, timeout=120)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv", type=Path, default=None)
    parser.add_argument(
        "--profile", type=Path, default=Path(tempfile.gettempdir()) / "lab2_report_edge_profile"
    )
    args = parser.parse_args()

    html_path = REPORT_DIR / "report.html"
    html_path.write_text(build_html(args.venv), encoding="utf-8")
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    print_pdf(html_path, PDF_PATH, args.profile)

    import pymupdf

    with pymupdf.open(PDF_PATH) as document:
        print(f"PDF: {PDF_PATH} — {document.page_count} сторінок")


if __name__ == "__main__":
    main()
