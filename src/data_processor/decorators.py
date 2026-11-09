from collections import Counter, deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

HISTORY_SIZE = 5

operation_history: deque[str] = deque(maxlen=HISTORY_SIZE)
operation_counts: Counter[str] = Counter()


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"[час] {func.__name__}: {elapsed:.6f} с")
        return result

    return wrapper


def track_operation(
    label: str,
    *,
    history: deque[str] | None = None,
    counts: Counter[str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    target_history = operation_history if history is None else history
    target_counts = operation_counts if counts is None else counts

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            target_history.append(label)
            target_counts[label] += 1
            return result

        return wrapper

    return decorator
