import argparse
import csv
import random
import timeit
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple

from data_processor.data import generate_students
from data_processor.processors import create_student_index, find_student_linear

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)


class BenchmarkRow(NamedTuple):
    size: int
    list_search: float
    dict_search: float
    list_in: float
    set_in: float
    index_build: float


def time_per_call(search: Callable[[int], object], targets: list[int], repeat: int = 5) -> float:
    def run() -> None:
        for student_id in targets:
            search(student_id)

    timer = timeit.Timer(run)
    loops, _ = timer.autorange()
    best = min(timer.repeat(repeat=repeat, number=loops))
    return best / (loops * len(targets))


def measure_size(size: int, lookups: int, seed: int) -> BenchmarkRow:
    students = generate_students(size, seed)
    ids = [student["id"] for student in students]
    targets = random.Random(seed).sample(ids, k=min(lookups, size))
    index = create_student_index(students)
    id_set = set(ids)

    build = min(timeit.repeat(lambda: create_student_index(students), number=1, repeat=5))
    return BenchmarkRow(
        size=size,
        list_search=time_per_call(
            lambda student_id: find_student_linear(students, student_id), targets
        ),
        dict_search=time_per_call(index.get, targets),
        list_in=time_per_call(ids.__contains__, targets),
        set_in=time_per_call(id_set.__contains__, targets),
        index_build=build,
    )


def run_benchmark(
    sizes: Sequence[int] = SIZES,
    lookups: int = 200,
    seed: int = 1,
) -> list[BenchmarkRow]:
    return [measure_size(size, lookups, seed) for size in sizes]


def print_table(rows: list[BenchmarkRow]) -> None:
    header = (
        f"{'Записів':>8} | {'list, мкс':>10} | {'dict, мкс':>9} | {'разів':>7} | "
        f"{'in list':>9} | {'in set':>7} | {'індекс, мс':>10}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row.size:>8} | {row.list_search * 1e6:>10.2f} | {row.dict_search * 1e6:>9.3f} | "
            f"{row.list_search / row.dict_search:>7.0f} | {row.list_in * 1e6:>9.2f} | "
            f"{row.set_in * 1e6:>7.3f} | {row.index_build * 1e3:>10.3f}"
        )


def save_csv(rows: list[BenchmarkRow], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(BenchmarkRow._fields)
        writer.writerows(rows)
    return path


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark: list vs dict/set")
    parser.add_argument("--sizes", type=int, nargs="+", default=list(SIZES))
    parser.add_argument("--lookups", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--csv", type=Path, default=Path("results") / "benchmark.csv")
    args = parser.parse_args(argv)

    rows = run_benchmark(args.sizes, args.lookups, args.seed)
    print_table(rows)
    print(f"\nРезультати збережено: {save_csv(rows, args.csv)}")


if __name__ == "__main__":
    main()
