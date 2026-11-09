from collections import Counter, defaultdict
from collections.abc import Callable
from functools import reduce
from typing import Any

from data_processor.data import GRADE_LEVELS, Student
from data_processor.decorators import track_operation

Predicate = Callable[[Student], bool]
Step = Callable[[list[Student]], list[Student]]


def get_unique_values(students: list[Student], field: str) -> set[Any]:
    return {student[field] for student in students}


def create_student_index(students: list[Student]) -> dict[int, Student]:
    index = {student["id"]: student for student in students}
    if len(index) != len(students):
        raise ValueError("Ідентифікатори студентів повторюються")
    return index


def find_student_linear(students: list[Student], student_id: int) -> Student | None:
    for student in students:
        if student["id"] == student_id:
            return student
    return None


@track_operation("пошук за ID")
def find_student(index: dict[int, Student], student_id: int) -> Student | None:
    return index.get(student_id)


def find_by_last_name(students: list[Student], last_name: str) -> list[Student]:
    wanted = last_name.casefold()
    return [student for student in students if student["last_name"].casefold() == wanted]


def filter_items(items: list[Student], predicate: Predicate) -> list[Student]:
    return [item for item in items if predicate(item)]


def create_grade_filter(minimum: float) -> Predicate:
    def predicate(student: Student) -> bool:
        return student["average_grade"] >= minimum

    return predicate


def create_group_filter(*groups: str) -> Predicate:
    allowed = frozenset(groups)

    def predicate(student: Student) -> bool:
        return student["group"] in allowed

    return predicate


@track_operation("фільтр за мін. балом")
def filter_by_min_grade(students: list[Student], minimum: float) -> list[Student]:
    return filter_items(students, create_grade_filter(minimum))


def filter_by_group(students: list[Student], group: str) -> list[Student]:
    return filter_items(students, create_group_filter(group))


@track_operation("групування за групою")
def group_students(students: list[Student]) -> dict[str, list[Student]]:
    groups: defaultdict[str, list[Student]] = defaultdict(list)
    for student in students:
        groups[student["group"]].append(student)
    return dict(groups)


def count_students_by_group(students: list[Student]) -> Counter[str]:
    return Counter(student["group"] for student in students)


def grade_level(student: Student) -> str:
    return next(label for threshold, label in GRADE_LEVELS if student["average_grade"] >= threshold)


def group_nested(items: list[Student], *keys: Callable[[Student], str]) -> dict[str, Any]:
    if not keys:
        raise ValueError("Потрібна хоча б одна функція групування")
    first, *rest = keys
    groups: defaultdict[str, list[Student]] = defaultdict(list)
    for item in items:
        groups[first(item)].append(item)
    if not rest:
        return dict(groups)
    return {key: group_nested(members, *rest) for key, members in groups.items()}


@track_operation("сортування за балом")
def sort_by_grade(students: list[Student], reverse: bool = True) -> list[Student]:
    return sorted(students, key=lambda student: student["average_grade"], reverse=reverse)


def sort_items(items: list[Student], *fields: str, reverse: bool = False) -> list[Student]:
    if not fields:
        raise ValueError("Потрібно вказати хоча б одне поле для сортування")
    return sorted(
        items,
        key=lambda item: tuple(item[field] for field in fields),
        reverse=reverse,
    )


def run_pipeline(items: list[Student], *steps: Step) -> list[Student]:
    return reduce(lambda data, step: step(data), steps, items)
