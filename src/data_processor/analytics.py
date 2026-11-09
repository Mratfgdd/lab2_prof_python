import json
from pathlib import Path
from typing import Any, NamedTuple

from data_processor.data import Student, full_name
from data_processor.decorators import measure_time
from data_processor.processors import (
    count_students_by_group,
    filter_by_min_grade,
    group_students,
    sort_by_grade,
)

SUMMARY_DEFAULTS: dict[str, Any] = {"top": 3, "min_grade": 85.0}


class GradeStats(NamedTuple):
    size: int
    average: float
    minimum: float
    maximum: float


@measure_time
def calculate_average(students: list[Student]) -> float:
    if not students:
        return 0.0
    return round(sum(student["average_grade"] for student in students) / len(students), 2)


def find_best_student(students: list[Student]) -> Student | None:
    if not students:
        return None
    return max(students, key=lambda student: student["average_grade"])


def calculate_stats(*grades: float) -> GradeStats:
    if not grades:
        return GradeStats(0, 0.0, 0.0, 0.0)
    return GradeStats(
        size=len(grades),
        average=round(sum(grades) / len(grades), 2),
        minimum=min(grades),
        maximum=max(grades),
    )


def stats_by_group(students: list[Student]) -> dict[str, GradeStats]:
    return {
        group: calculate_stats(*(student["average_grade"] for student in members))
        for group, members in group_students(students).items()
    }


def build_summary(students: list[Student], **options: Any) -> dict[str, Any]:
    unknown = options.keys() - SUMMARY_DEFAULTS.keys()
    if unknown:
        raise TypeError(f"Невідомі параметри: {', '.join(sorted(unknown))}")
    settings = SUMMARY_DEFAULTS | options

    stats = calculate_stats(*(student["average_grade"] for student in students))
    best = find_best_student(students)
    top = sort_by_grade(students)[: settings["top"]]
    return {
        "statistics": stats._asdict(),
        "best_student": full_name(best) if best else None,
        "students_by_group": dict(count_students_by_group(students)),
        "top_students": [student["id"] for student in top],
        "min_grade": settings["min_grade"],
        "students_above_min": len(filter_by_min_grade(students, settings["min_grade"])),
    }


def export_summary(summary: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
