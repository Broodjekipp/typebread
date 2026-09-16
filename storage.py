from typing import cast
import json


def save_results(
    path: str, timestamp: float, acc: float, wpm: float, test_type: str, test_len: int
) -> None:
    file_data = open_json(path)
    test_data = {
        "acc": acc,
        "wpm": wpm,
        "mode": f"{test_type} {test_len}",
        "datetime": timestamp,
        "time": test_len,
    }
    next_id = max((int(k) for k in file_data), default=-1) + 1
    file_data[next_id] = test_data
    write_json(path, file_data)


def open_json(path: str) -> dict[int, dict[str, int | float | str]]:
    try:
        with open(path) as f:
            raw = cast(dict[str, dict[str, int | float | str]], json.load(f))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise SyntaxError("Progress file is wrong or corrupted.")

    return {int(k): v for k, v in raw.items()}


def write_json(path: str, data: dict[int, dict[str, int | float | str]]) -> None:
    with open(path, "w") as f:
        json.dump(data, f)


def get_stats_from_progress_file() -> tuple[float, float, str, float]:
    raise NotImplementedError
