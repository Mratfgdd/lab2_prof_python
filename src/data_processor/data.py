import random
from typing import Any

Student = dict[str, Any]

GROUPS: tuple[str, ...] = ("PI-21", "PI-22", "PI-23", "PI-24", "PI-25")

GRADE_LEVELS: tuple[tuple[float, str], ...] = (
    (90.0, "excellent"),
    (75.0, "good"),
    (60.0, "satisfactory"),
    (0.0, "failing"),
)

LEVEL_LABELS: dict[str, str] = {
    "excellent": "відмінно",
    "good": "добре",
    "satisfactory": "задовільно",
    "failing": "незадовільно",
}

REQUIRED_FIELDS: tuple[str, ...] = ("id", "first_name", "last_name", "group", "average_grade")

STUDENT_ROWS: tuple[tuple[int, str, str, str, float], ...] = (
    (1, "Анна", "Коваль", "PI-21", 91.5),
    (2, "Олег", "Мельник", "PI-21", 84.0),
    (3, "Ірина", "Бондар", "PI-22", 95.2),
    (4, "Андрій", "Шевченко", "PI-21", 88.7),
    (5, "Марія", "Бойко", "PI-22", 79.3),
    (6, "Тарас", "Гриценко", "PI-23", 72.4),
    (7, "Софія", "Гнатюк", "PI-22", 66.8),
    (8, "Дмитро", "Ткаченко", "PI-23", 58.9),
    (9, "Катерина", "Лисенко", "PI-23", 93.1),
    (10, "Максим", "Мельник", "PI-21", 70.6),
)


def full_name(student: Student) -> str:
    return f"{student['first_name']} {student['last_name']}"


def create_student(**fields: Any) -> Student:
    missing = [name for name in REQUIRED_FIELDS if name not in fields]
    if missing:
        raise ValueError(f"Відсутні поля: {', '.join(missing)}")
    if not str(fields["group"]).strip():
        raise ValueError("Група не може бути порожньою")
    if not 0 <= fields["average_grade"] <= 100:
        raise ValueError("Середній бал має бути в межах 0-100")
    return dict(fields)


def generate_students(count: int, seed: int = 42) -> list[Student]:
    rng = random.Random(seed)
    return [
        {
            "id": index,
            "first_name": f"Студент{index}",
            "last_name": f"Прізвище{index}",
            "group": rng.choice(GROUPS),
            "average_grade": round(rng.uniform(30, 100), 1),
        }
        for index in range(1, count + 1)
    ]


students: list[Student] = [
    create_student(
        id=student_id, first_name=first, last_name=last, group=group, average_grade=grade
    )
    for student_id, first, last, group, grade in STUDENT_ROWS
]
