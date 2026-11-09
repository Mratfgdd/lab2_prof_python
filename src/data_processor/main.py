from pathlib import Path

from data_processor.analytics import (
    build_summary,
    calculate_average,
    calculate_stats,
    export_summary,
    find_best_student,
    stats_by_group,
)
from data_processor.data import LEVEL_LABELS, Student, create_student, full_name, students
from data_processor.decorators import operation_counts, operation_history
from data_processor.processors import (
    count_students_by_group,
    create_group_filter,
    create_student_index,
    filter_by_group,
    filter_by_min_grade,
    filter_items,
    find_by_last_name,
    find_student,
    find_student_linear,
    get_unique_values,
    grade_level,
    group_nested,
    group_students,
    run_pipeline,
    sort_by_grade,
    sort_items,
)

SUMMARY_PATH = Path("results") / "summary.json"


def print_students(title: str, items: list[Student]) -> None:
    print(f"\n{title}")
    print("-" * 60)
    for student in items:
        print(
            f"{student['id']:3} {full_name(student):24} "
            f"{student['group']:8} {student['average_grade']:6.2f}"
        )


def ids(items: list[Student]) -> list[int]:
    return [student["id"] for student in items]


def show_structures() -> None:
    groups = get_unique_values(students, "group")
    last_names = get_unique_values(students, "last_name")
    print(f"\nУнікальні групи (set): {sorted(groups)}")
    print(f"Чи є група PI-24: {'PI-24' in groups}")
    print(f"Унікальних прізвищ: {len(last_names)} на {len(students)} студентів")


def show_search(index: dict[int, Student]) -> None:
    print("\nПошук за ID (dict-індекс):")
    for student_id in (3, 99):
        student = find_student(index, student_id)
        result = (
            f"{full_name(student)}, {student['group']}, {student['average_grade']}"
            if student
            else "не знайдено"
        )
        print(f"  {student_id}: {result}")
    same = find_student_linear(students, 3) is index[3]
    print(f"  Лінійний пошук у list дає той самий об'єкт: {same}")
    for last_name in ("Мельник", "бойко"):
        found = [full_name(student) for student in find_by_last_name(students, last_name)]
        print(f"Пошук за прізвищем '{last_name}': {found}")


def show_grouping() -> None:
    groups = group_students(students)
    print("\nГрупування за групою (defaultdict):")
    for group, members in groups.items():
        print(f"  {group}: {', '.join(student['last_name'] for student in members)}")

    counts = ", ".join(
        f"{group}={count}" for group, count in count_students_by_group(students).most_common()
    )
    print(f"Кількість студентів (Counter.most_common): {counts}")

    nested = group_nested(students, lambda s: s["group"], grade_level)
    print("Вкладене групування група -> рівень успішності:")
    for group, levels in nested.items():
        sizes = ", ".join(
            f"{LEVEL_LABELS[level]}={len(members)}" for level, members in levels.items()
        )
        print(f"  {group}: {sizes}")


def show_aggregation() -> None:
    average = calculate_average(students)
    print(f"\nСередній бал усіх студентів: {average:.2f}")
    best = find_best_student(students)
    if best:
        print(f"Найкращий студент: {full_name(best)} ({best['average_grade']:.2f})")

    print("\nСтатистика за групами (dict comprehension + NamedTuple):")
    print(f"  {'група':8}{'к-сть':>6}{'середній':>10}{'мін.':>8}{'макс.':>8}")
    for group, stats in sorted(stats_by_group(students).items()):
        print(
            f"  {group:8}{stats.size:>6}{stats.average:>10.2f}"
            f"{stats.minimum:>8.1f}{stats.maximum:>8.1f}"
        )


def show_filters_and_sorting() -> None:
    successful = filter_by_min_grade(students, 85)
    print(f"\nФільтр average_grade >= 85 (closure): {ids(successful)}")
    weak = filter_items(students, lambda student: student["average_grade"] < 70)
    print(f"Фільтр average_grade < 70 (lambda): {ids(weak)}")
    print(f"Студенти групи PI-22: {ids(filter_by_group(students, 'PI-22'))}")

    print_students("Рейтинг за середнім балом (спадання)", sort_by_grade(students))

    ordered = sort_items(students, "group", "average_grade", reverse=True)
    print(f"\nСортування за (group, average_grade) у зворотному порядку: {ids(ordered)}")

    top = run_pipeline(
        students,
        lambda items: filter_items(items, create_group_filter("PI-21", "PI-22")),
        sort_by_grade,
        lambda items: items[:3],
    )
    print(f"Pipeline: групи PI-21 і PI-22 -> сортування -> топ-3: {ids(top)}")


def show_args_kwargs() -> None:
    stats = calculate_stats(75, 80, 92, 96)
    print("\n*args: calculate_stats(75, 80, 92, 96) ->")
    print(f"  {stats}")

    new_student = create_student(
        id=11, first_name="Тарас", last_name="Новак", group="PI-23", average_grade=89.0
    )
    print("**kwargs: create_student(id=11, first_name=..., ..., average_grade=89.0) ->")
    print(f"  {new_student}")
    try:
        create_student(id=12, first_name="Тест", last_name="Тест", group="PI-23", average_grade=120)
    except ValueError as error:
        print(f"**kwargs з балом 120 -> ValueError: {error}")


def show_summary() -> None:
    summary = build_summary(students, top=3, min_grade=85)
    print("\nПідсумок (build_summary(**options)):")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"Експортовано у {export_summary(summary, SUMMARY_PATH)}")


def main() -> None:
    print("ЛР2, варіант 1: аналіз успішності студентів")
    print_students(f"Усі студенти ({len(students)})", students)
    show_structures()
    show_search(create_student_index(students))
    show_grouping()
    show_aggregation()
    show_filters_and_sorting()
    show_args_kwargs()
    show_summary()
    print(f"\nОстанні операції (deque, maxlen={operation_history.maxlen}):")
    print(f"  {list(operation_history)}")
    print(f"Усього викликів (Counter): {dict(operation_counts)}")


if __name__ == "__main__":
    main()
