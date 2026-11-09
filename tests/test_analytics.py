import contextlib
import io
import json
import tempfile
import unittest
from collections import Counter, deque
from pathlib import Path

from data_processor.analytics import (
    GradeStats,
    build_summary,
    calculate_average,
    calculate_stats,
    export_summary,
    find_best_student,
    stats_by_group,
)
from data_processor.benchmark import run_benchmark
from data_processor.data import students
from data_processor.decorators import measure_time, track_operation


class AggregationTests(unittest.TestCase):
    def test_average(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertAlmostEqual(calculate_average(students), 80.05, places=2)
            self.assertEqual(calculate_average([]), 0.0)

    def test_best_student(self):
        self.assertEqual(find_best_student(students)["id"], 3)
        self.assertIsNone(find_best_student([]))

    def test_calculate_stats_with_args(self):
        self.assertEqual(calculate_stats(10, 20, 30, 40), GradeStats(4, 25.0, 10, 40))
        self.assertEqual(calculate_stats(77.5), GradeStats(1, 77.5, 77.5, 77.5))
        self.assertEqual(calculate_stats().size, 0)

    def test_stats_by_group(self):
        per_group = stats_by_group(students)
        self.assertEqual(sorted(per_group), ["PI-21", "PI-22", "PI-23"])
        self.assertEqual(per_group["PI-21"], GradeStats(4, 83.7, 70.6, 91.5))
        self.assertEqual(per_group["PI-22"].average, 80.43)
        self.assertEqual(per_group["PI-23"].minimum, 58.9)
        self.assertEqual(sum(stats.size for stats in per_group.values()), len(students))


class SummaryTests(unittest.TestCase):
    def test_summary_options(self):
        summary = build_summary(students, top=2, min_grade=90)
        self.assertEqual(summary["top_students"], [3, 9])
        self.assertEqual(summary["students_above_min"], 3)
        self.assertEqual(summary["students_by_group"]["PI-22"], 3)
        self.assertEqual(summary["best_student"], "Ірина Бондар")

    def test_summary_defaults(self):
        summary = build_summary(students)
        self.assertEqual(len(summary["top_students"]), 3)
        self.assertEqual(summary["min_grade"], 85.0)

    def test_summary_of_empty_data(self):
        summary = build_summary([])
        self.assertIsNone(summary["best_student"])
        self.assertEqual(summary["statistics"]["size"], 0)

    def test_unknown_option_rejected(self):
        with self.assertRaises(TypeError):
            build_summary(students, colour="red")

    def test_export_round_trip(self):
        summary = build_summary(students)
        with tempfile.TemporaryDirectory() as folder:
            path = export_summary(summary, Path(folder) / "out" / "summary.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), summary)


class DecoratorTests(unittest.TestCase):
    def test_measure_time_keeps_result_and_name(self):
        @measure_time
        def add(a, b):
            return a + b

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(add(2, 3), 5)
        self.assertEqual(add.__name__, "add")
        self.assertIn("add:", buffer.getvalue())

    def test_track_operation_history_is_bounded(self):
        history = deque(maxlen=2)
        counts = Counter()

        @track_operation("op", history=history, counts=counts)
        def identity(value):
            return value

        for value in range(3):
            self.assertEqual(identity(value), value)
        self.assertEqual(list(history), ["op", "op"])
        self.assertEqual(counts["op"], 3)
        self.assertEqual(identity.__name__, "identity")


class BenchmarkTests(unittest.TestCase):
    def test_small_benchmark_runs(self):
        (row,) = run_benchmark(sizes=[200], lookups=20)
        self.assertEqual(row.size, 200)
        self.assertGreater(row.list_search, row.dict_search)


if __name__ == "__main__":
    unittest.main()
