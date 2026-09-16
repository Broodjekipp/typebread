from dataclasses import dataclass, field
from typing import cast
import termios
import random
import shutil
import select
import json
import time
import sys
import tty

from graph import make_data_graph, format_results_graph

SPACE_CHAR = "•"
WORDS_DIR = "words"
WORDS_FILE = "english.json"
PROGRESS_FILE = "progress.json"
SMOOTHING_WINDOW = 10
WORDS_MODE_LEN = 20
TIME_MODE_LEN = 15
REFILL_THRESHOLD = 100


@dataclass
class Layout:
    terminal_size: tuple[int, int] = field(default_factory=shutil.get_terminal_size)
    keybind_tip_coords: tuple[int, int] = (0, 0)
    test_settings_coords: tuple[int, int] = (2, 2)
    result_stats_coords: tuple[int, int] = (1, 1)
    result_graph_coords: tuple[int, int] = (1, 5)
    target_height: int = 4
    target_upper_cursor_padding: int = 1

    profile_coords: tuple[int, int] = field(init=False)
    profile_width: int = field(init=False)
    progress_coords: tuple[int, int] = field(init=False)
    target_coords: tuple[int, int] = field(init=False)
    target_width: int = field(init=False)
    result_graph_width: int = field(init=False)
    result_graph_height: int = field(init=False)

    def __post_init__(self):
        cols, lines = self.terminal_size
        self.profile_coords = (cols // 10, lines // 10)
        self.profile_width = cols // 10 * 8
        self.progress_coords = (cols // 4, lines // 5)
        self.target_coords = (cols // 4, lines // 5 + 1)
        self.target_width = cols // 2
        self.result_graph_width = int(cols / 1.2 - 2)
        self.result_graph_height = lines // 3


@dataclass
class TestState:
    target_text: str
    typed_text: str = ""
    started: bool = False
    start_time: float = 0
    correct_keys: int = 0
    incorrect_keys: int = 0
    wpm_samples: list[float] = field(default_factory=list)


def print_keybind_tips(keybinds: list[str], coords: tuple[int, int]) -> None:
    print_aligned(keybinds, coords)


def print_text(
    target: str,
    typed: str,
    coords: tuple[int, int],
    width: int,
    target_height: int,
    upper_pad: int,
) -> int:
    wrapped = wrap_chars(target, width)[0]
    cursor_xy = get_cursor_xy(len(typed), wrapped)

    wrapped, made_errors = colorize_text(wrapped, typed)

    wrapped, cursor_xy = text_scroll(
        wrapped.split("\n"),
        target_height,
        cursor_xy,
        upper_pad,
    )
    print_aligned(
        wrapped,
        coords,
    )

    move_cursor(
        cursor_xy[0] + coords[0],
        cursor_xy[1] + coords[1],
        flush=True
    )

    return made_errors


def colorize_text(target_split: list[str], typed: str) -> tuple[str, int]:
    typed_index = 0
    made_errors = 0
    colorized_lines: list[str] = []

    for target_line in target_split:
        colorized_line: list[str] = []

        for target_char in target_line:
            if typed_index < len(typed):
                typed_char = typed[typed_index]

                if typed_char == target_char:
                    colorized_line.append(
                        f"\033[32m{SPACE_CHAR if target_char == " " else target_char}"
                    )
                else:
                    colorized_line.append(
                        f"\033[31m{SPACE_CHAR if target_char == " " else target_char}"
                    )
                    made_errors += 1

                typed_index += 1
            else:
                colorized_line.append(
                    f"\033[39m{SPACE_CHAR if target_char == " " else target_char}"
                )

        colorized_lines.append("".join(colorized_line))

    return "\n".join(colorized_lines), made_errors


def get_cursor_xy(char_count: int, wrapped: list[str]) -> tuple[int, int]:
    line_count = 0
    row_count = 0

    for line in wrapped:
        row_count = 0

        for _ in line:
            if char_count == 0:
                return row_count, line_count
            row_count += 1
            char_count -= 1

        line_count += 1

    return row_count, line_count - 1


def wrap_chars(text: str, width: int) -> tuple[list[str], tuple[int, int]]:
    chars = list(text)

    words: list[list[str]] = [[]]
    word_count = 0

    for char in chars:
        if char == " ":
            word_count += 1
            words.append([])
            continue
        words[word_count].append(char)

    lines: list[str] = []
    current_line_words: list[list[str]] = []
    line_len: int = 0

    for word in words:
        word_str = "".join(word)
        word_len = len(word_str)
        add_len = word_len if line_len == 0 else word_len + 1
        if line_len + add_len > width:
            if current_line_words:
                lines.append(" ".join("".join(w) for w in current_line_words) + " ")
            current_line_words = [word]
            line_len = word_len
        else:
            current_line_words.append(word)
            line_len += add_len

    lines.append(" ".join("".join(w) for w in current_line_words))
    return lines, (len(lines[-1]), len(lines))


def text_scroll(
    text: list[str],
    target_height: int,
    cursor_xy: tuple[int, int],
    upper_pad: int,
) -> tuple[list[str], tuple[int, int]]:
    if len(text) <= target_height:
        return text, cursor_xy

    top_line = max(0, cursor_xy[1] - upper_pad)
    line_window = text[top_line : top_line + target_height]

    new_cursor_y = cursor_xy[1] - top_line

    return line_window, (cursor_xy[0], new_cursor_y)


def move_cursor(x: int, y: int, flush: bool = False) -> None:
    print(f"\033[{y};{x}H", end="", flush=flush)


def clear_terminal():
    print(chr(27) + "[2J")


def print_progress(
    accuracy: float,
    elapsed_time: float,
    wpm: float,
    test_type: str,
    time_mode_len: int,
    layout: Layout,
) -> None:
    if test_type == "time":
        time_to_print = time_mode_len - elapsed_time
    else:
        time_to_print = elapsed_time

    move_cursor(*layout.progress_coords)
    print(f"{int(time_to_print)} {int(wpm)} {int(accuracy * 100)}%", end="")


def print_results_stats(
    elapsed_time: float, wpm: float, accuracy: float, coords: tuple[int, int]
) -> None:
    print_aligned(
        f"""Time: {elapsed_time:.2f}s
WPM:  {int(wpm)}
Acc:  {int(accuracy * 100)}%""",
        coords,
    )


def print_results_graph(
    data: list[float],
    coords: tuple[int, int],
    width: int,
    height: int,
    smoothing_window: int,
) -> None:
    print_aligned(
        format_results_graph(
            make_data_graph(data, width, height, smoothing_window), width
        ),
        coords,
    )


def print_aligned(
    text: str | list[str], coords: tuple[int, int], is_input: bool = False
) -> None:
    if type(text) == str:
        text = text.split("\n")
    for l in range(len(text)):
        move_cursor(coords[0], coords[1] + l)
        print(text[l])
    if is_input:
        _ = input()
    return


""" Layout overview:
Tests Started: 1327 
Total length typed: 5:34:75
Records:
    15s:  79
    30s:  66
    60s:  43
    120s: - 

[INSERT GIANT GRAPH OF TEST RESULTS]

"""


def get_stats_from_progress_file() -> tuple[float, float, str, float]:
    raise NotImplementedError


def check_finished(
    made_errors: int,
    target: str,
    typed: str,
    test_type: str,
    elapsed_time: float,
    time_mode_len: int,
) -> bool:

    if test_type == "words":
        if not made_errors and target == typed:
            return True
        if len(typed) == len(target) + 1:
            return True
        return False
    elif test_type == "time":
        if elapsed_time >= time_mode_len:
            return True
        return False
    return False


def get_target_text(word_count: int) -> str:
    try:
        with open(f"{WORDS_DIR}/{WORDS_FILE}", "r") as file:
            data = cast(dict[str, list[str]], json.load(file))
    except FileNotFoundError:
        raise SystemExit(f"Word list not found: {WORDS_FILE}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {WORDS_FILE}: {e}")

    words = data.get("words")
    if not words:
        raise SystemExit(f"No 'words' key (or empty list) in {WORDS_FILE}")
    if word_count > len(words):
        word_count = len(words)

    return " ".join(random.sample(words, k=word_count)).lower()


def categorize_chars(target: str, typed: str) -> tuple[list[int], list[int], list[int]]:
    correct_chars: list[int] = []
    incorrect_chars: list[int] = []
    untyped_chars: list[int] = []

    for typed_idx in range(len(target)):
        if typed_idx < len(typed):
            typed_char = typed[typed_idx]
            target_char = target[typed_idx]

            if typed_char == target_char:
                correct_chars.append(typed_idx)
            else:
                incorrect_chars.append(typed_idx)

        else:
            untyped_chars.append(typed_idx)

    return correct_chars, incorrect_chars, untyped_chars


def remove_incorrect_words(text: str, incorrect_chars: list[int]) -> str:
    incorrect_set = set(incorrect_chars)
    words = text.split(" ")

    kept_words: list[str] = []
    offset = 0

    for word in words:
        word_range = range(offset, offset + len(word))
        if not any(idx in incorrect_set for idx in word_range):
            kept_words.append(word)
        offset += len(word) + 1

    return " ".join(kept_words)


def compute_correct_wpm(target: str, typed: str, elapsed: float) -> float:
    _, incorrect_chars, untyped_chars = categorize_chars(target, typed)
    correct_words = remove_incorrect_words(target, incorrect_chars + untyped_chars)
    return compute_wpm(len(correct_words), elapsed)


def compute_wpm(chars: int, elapsed: float) -> float:
    if elapsed and chars:
        return chars / 5 / (elapsed / 60)
    return 0


def compute_accuracy(correct_chars: int, incorrect_chars: int) -> float:
    if correct_chars or incorrect_chars:
        return correct_chars / (correct_chars + incorrect_chars)
    return 0


def render_results_frame(
    layout: Layout,
    state: TestState,
    smoothing_window: int,
    elapsed_time: float,
    wpm: float,
    accuracy: float,
):
    clear_terminal()

    print_results_stats(elapsed_time, wpm, accuracy, layout.result_stats_coords)
    print_results_graph(
        state.wpm_samples,
        layout.result_graph_coords,
        layout.result_graph_width,
        layout.result_graph_height,
        smoothing_window,
    )


def handle_key(state: TestState, key: str, test_type: str) -> None:
    key_start_time = time.time()

    if not state.started:
        state.start_time = key_start_time
        state.started = True

    if key in ('\x7f', '\x08') and state.typed_text:
        state.typed_text = state.typed_text[:-1]
        return

    if not key.isprintable():
        return

    state.typed_text += str(key)

    if (
        test_type == "time"
        and len(state.target_text) - len(state.typed_text) < REFILL_THRESHOLD
    ):
        state.target_text += " " + get_target_text(WORDS_MODE_LEN)

    idx = len(state.typed_text) - 1
    if idx < len(state.target_text) and state.typed_text[-1] == state.target_text[idx]:
        state.correct_keys += 1
    else:
        state.incorrect_keys += 1


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


def get_key(timeout: float | None = None) -> str | None:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        _ = tty.setraw(fd)
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        ch: str = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def test(test_type: str) -> None:
    layout = Layout()

    clear_terminal()
    print("\x1b[6 q", end="", flush=True)  # set bar cursor

    try:
        state = TestState(
            target_text=get_target_text(
                REFILL_THRESHOLD if test_type == "time" else WORDS_MODE_LEN
            )
        )

        finished = False
        made_errors = 0
        elapsed_time = 0
        prev_elapsed_time = 0
        wpm = 0
        accuracy = 0
        clear_terminal()
        print_progress(accuracy, elapsed_time, wpm, test_type, TIME_MODE_LEN, layout)
        made_errors = print_text(
            state.target_text,
            state.typed_text,
            layout.target_coords,
            layout.target_width,
            layout.target_height,
            layout.target_upper_cursor_padding,
        )

        while not finished:
            key = get_key(timeout=0.1)
            if key:
                handle_key(state, key, test_type)

            elapsed_time = time.time() - state.start_time if state.started else 0

            wpm = compute_correct_wpm(
                state.target_text, state.typed_text, elapsed_time
            )
            accuracy = compute_accuracy(state.correct_keys, state.incorrect_keys)

            if key or int(elapsed_time) != int(prev_elapsed_time):
                clear_terminal()
                print_progress(
                    accuracy, elapsed_time, wpm, test_type, TIME_MODE_LEN, layout
                )
                made_errors = print_text(
                    state.target_text,
                    state.typed_text,
                    layout.target_coords,
                    layout.target_width,
                    layout.target_height,
                    layout.target_upper_cursor_padding,
                )

            if int(elapsed_time) != int(prev_elapsed_time):
                state.wpm_samples.append(wpm)

            prev_elapsed_time = elapsed_time

            finished = check_finished(
                made_errors,
                state.target_text,
                state.typed_text,
                test_type,
                elapsed_time,
                TIME_MODE_LEN,
            )

        render_results_frame(
            layout, state, SMOOTHING_WINDOW, elapsed_time, wpm, accuracy
        )
        test_len = WORDS_MODE_LEN if test_type == "words" else TIME_MODE_LEN
        save_results(PROGRESS_FILE, time.time(), accuracy, wpm, test_type, test_len)

    except KeyboardInterrupt:
        pass
    finally:
        print("\x1b[0 q", end="", flush=True)  # reset cursor


def start_test(coords: tuple[int, int]) -> None:
    print_aligned("", coords)


test("time")
