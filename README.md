# Student Data Processor

Лабораторна робота №2 з дисципліни «Професійний Python»:
«Структури даних та функціональна декомпозиція».
Варіант 1: аналіз успішності студентів (продовження ЛР1 «Система обліку студентів»).

## Опис

Модуль обробки структурованих даних. Кожен студент - це `dict` з полями `id`, `first_name`,
`last_name`, `group`, `average_grade` (середній бал у межах 0-100).

Реалізовано:

- пошук студента за ID: лінійний у `list` (O(n)) і через dict-індекс (O(1) у середньому);
- пошук за прізвищем без урахування регістру;
- групування за групою (`defaultdict`), вкладене групування група → рівень успішності;
- середній бал, найкращий студент, статистика за групами (`NamedTuple`);
- фільтрація за мінімальним балом (closure) і універсальний фільтр;
- сортування за балом і універсальне сортування за кількома полями;
- `*args`, `**kwargs`, `lambda`, closures, декоратори (у тому числі параметризований);
- журнал останніх операцій (`deque`), лічильники (`Counter`), pipeline, експорт підсумку в JSON;
- benchmark пошуку list vs dict/set на 1 000 / 10 000 / 100 000 записів.

Бал поза межами 0-100 не допускається (`create_student` кидає `ValueError`).

## Requirements

Python 3.11+. Зовнішніх залежностей немає.

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

## Run

```
python -m data_processor.main
python -m data_processor.benchmark
```

або console commands `student-report` і `student-benchmark`.
Програма зберігає підсумок у `results/summary.json`, benchmark - у `results/benchmark.csv`.

## Tests

```
python -m unittest discover -s tests -v
```

(тести також запускаються через `pytest`).

## Project structure

```
src/data_processor/data.py         вхідні дані, константи (tuple, dict), create_student(**kwargs)
src/data_processor/decorators.py   measure_time, параметризований track_operation, deque-журнал
src/data_processor/processors.py   індекс, пошук, фільтри (closures), групування, сортування, pipeline
src/data_processor/analytics.py    середнє, найкращий студент, статистика (*args), підсумок (**kwargs), експорт
src/data_processor/benchmark.py    експериментальна частина
src/data_processor/main.py         точка входу
tests/                             модульні тести (unittest)
```

## Author

Student: Левандівський Назар
