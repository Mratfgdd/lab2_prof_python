import unittest

from data_processor.data import create_student, full_name, generate_students, students
from data_processor.processors import (
    count_students_by_group,
    create_grade_filter,
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


def ids(items):
    return [item["id"] for item in items]


class SearchTests(unittest.TestCase):
    def test_index_and_linear_search_return_same_object(self):
        index = create_student_index(students)
        for student in students:
            self.assertIs(find_student(index, student["id"]), student)
            self.assertIs(find_student_linear(students, student["id"]), student)

    def test_missing_id_returns_none(self):
        index = create_student_index(students)
        self.assertIsNone(find_student(index, 999))
        self.assertIsNone(find_student_linear(students, 999))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            create_student_index([students[0], dict(students[0])])

    def test_last_name_search_ignores_case_and_returns_all_matches(self):
        self.assertEqual(ids(find_by_last_name(students, "мЕЛЬНИК")), [2, 10])
        self.assertEqual(ids(find_by_last_name(students, "Бойко")), [5])
        self.assertEqual(find_by_last_name(students, "Невідоме"), [])


class FilterTests(unittest.TestCase):
    def test_min_grade_is_inclusive(self):
        self.assertEqual(ids(filter_by_min_grade(students, 84.0)), [1, 2, 3, 4, 9])
        self.assertEqual(ids(filter_by_min_grade(students, 90)), [1, 3, 9])

    def test_closure_remembers_minimum(self):
        is_successful = create_grade_filter(85)
        self.assertEqual(is_successful.__closure__[0].cell_contents, 85)
        self.assertTrue(is_successful({"average_grade": 85}))
        self.assertFalse(is_successful({"average_grade": 84.99}))

    def test_group_filter_with_args(self):
        result = filter_items(students, create_group_filter("PI-22", "PI-23"))
        self.assertEqual(ids(result), [3, 5, 6, 7, 8, 9])
        self.assertEqual(filter_items(students, create_group_filter()), [])

    def test_filter_by_group(self):
        self.assertEqual(ids(filter_by_group(students, "PI-21")), [1, 2, 4, 10])
        self.assertEqual(filter_by_group(students, "PI-99"), [])


class GroupingTests(unittest.TestCase):
    def test_group_students_keeps_every_student(self):
        groups = group_students(students)
        self.assertEqual(sum(len(members) for members in groups.values()), len(students))
        self.assertEqual(ids(groups["PI-22"]), [3, 5, 7])

    def test_counter_matches_groups(self):
        groups = group_students(students)
        counts = count_students_by_group(students)
        self.assertEqual(dict(counts), {key: len(value) for key, value in groups.items()})
        self.assertEqual(counts.most_common(1), [("PI-21", 4)])

    def test_grade_levels_at_boundaries(self):
        expected = {
            100: "excellent",
            90: "excellent",
            89.9: "good",
            75: "good",
            74.9: "satisfactory",
            60: "satisfactory",
            59.9: "failing",
            0: "failing",
        }
        for grade, level in expected.items():
            self.assertEqual(grade_level({"average_grade": grade}), level, grade)

    def test_nested_grouping(self):
        nested = group_nested(students, lambda s: s["group"], grade_level)
        self.assertEqual(ids(nested["PI-21"]["good"]), [2, 4])
        self.assertEqual(ids(nested["PI-23"]["failing"]), [8])
        flat = group_nested(students, lambda s: s["group"])
        self.assertEqual(flat, group_students(students))
        with self.assertRaises(ValueError):
            group_nested(students)

    def test_unique_values(self):
        self.assertEqual(get_unique_values(students, "group"), {"PI-21", "PI-22", "PI-23"})
        self.assertEqual(len(get_unique_values(students, "last_name")), 9)


class SortingTests(unittest.TestCase):
    def test_sort_by_grade_descending_and_source_untouched(self):
        original = ids(students)
        result = sort_by_grade(students)
        grades = [student["average_grade"] for student in result]
        self.assertEqual(grades, sorted(grades, reverse=True))
        self.assertEqual(ids(result)[:3], [3, 9, 1])
        self.assertEqual(ids(students), original)

    def test_sort_by_grade_ascending(self):
        self.assertEqual(ids(sort_by_grade(students, reverse=False))[:2], [8, 7])

    def test_sort_items_by_several_fields(self):
        result = sort_items(students, "group", "average_grade")
        keys = [(s["group"], s["average_grade"]) for s in result]
        self.assertEqual(keys, sorted(keys))

    def test_sort_items_requires_field(self):
        with self.assertRaises(ValueError):
            sort_items(students)

    def test_pipeline_applies_steps_in_order(self):
        result = run_pipeline(
            students,
            lambda items: filter_items(items, create_group_filter("PI-21", "PI-22")),
            sort_by_grade,
            lambda items: items[:3],
        )
        self.assertEqual(ids(result), [3, 1, 4])
        self.assertEqual(run_pipeline(students), students)


class DataTests(unittest.TestCase):
    def test_create_student_validates(self):
        fields = {"id": 1, "first_name": "А", "last_name": "Б", "group": "PI-1"}
        self.assertEqual(create_student(**fields, average_grade=0)["average_grade"], 0)
        self.assertEqual(create_student(**fields, average_grade=100)["average_grade"], 100)
        with self.assertRaises(ValueError):
            create_student(**fields, average_grade=-0.1)
        with self.assertRaises(ValueError):
            create_student(**fields, average_grade=100.1)
        with self.assertRaises(ValueError):
            create_student(**{**fields, "group": "  "}, average_grade=50)
        with self.assertRaises(ValueError):
            create_student(**fields)

    def test_demo_data_is_valid(self):
        self.assertEqual(len(students), 10)
        self.assertEqual(full_name(students[2]), "Ірина Бондар")

    def test_generated_data_is_reproducible_and_unique(self):
        first = generate_students(1_000, seed=7)
        self.assertEqual(first, generate_students(1_000, seed=7))
        self.assertNotEqual(first, generate_students(1_000, seed=8))
        self.assertEqual(len(create_student_index(first)), 1_000)
        self.assertTrue(all(0 <= s["average_grade"] <= 100 for s in first))


if __name__ == "__main__":
    unittest.main()
