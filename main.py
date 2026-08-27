"""
FEATURES TO ADD:
 - Save previous test results in a .json
 - Track progress in that .json
 - Keybinds for next test/profile/scrolling
 - Misspelled words shouldn't count toward the WPM

PROPOSED CODE REFACTORS:

BUGS:
 - Cursor y position is +1 when on the last character of a test

MINOR BUGS/EDGE CASES:
 - Currenty whole frame is redrawn every 0.1s, only draw on keypress or
 elapsed_time tick region
 - wrap_chars() can inject a spurious leading space into the wrapped output
 whenever a single word is longer than TARGET_WIDTH (rare since TARGET_WIDTH
 is half the terminal width)
"""

from dataclasses import dataclass, field
from blessed import Terminal
import plotille
import textwrap
import numbers
import random
import shutil
import json
import time
import math
import os
import re

term = Terminal()
terminal_size = shutil.get_terminal_size()

SPACE_CHAR = "•"
WORDS_FILE = "english.json"
SMOOTHING_WINDOW = 10
TARGET_LENGTH = 20

KEYBIND_TIP_COORDS = (0, 0)
PROGRESS_COORDS = (int(terminal_size.columns / 4), int(terminal_size.lines / 6))
TARGET_COORDS = (int(terminal_size.columns / 4), int(terminal_size.lines / 6) + 1)
TARGET_WIDTH = int(terminal_size.columns / 2)
RESULT_STATS_COORDS = (1, 1)
RESULT_GRAPH_COORDS = (1, 5)
RESULT_GRAPH_WIDTH = int(terminal_size.columns / 1.2 - 2)
RESULT_GRAPH_HEIGHT = int(terminal_size.lines / 3)


def print_keybind_tips(
    keybinds: list[str], KEYBIND_TIP_COORDS: tuple[int, int]
) -> None:
    print(term.move_xy(*KEYBIND_TIP_COORDS))


def print_text(
    target: str, typed: str, TARGET_COORDS: tuple[int, int], TARGET_WIDTH: int
) -> int:
    wrapped = wrap_chars(target, TARGET_WIDTH)[0]
    cursor_xy = get_cursor_xy(len(typed), wrapped)

    wrapped, made_errors = colorize_text(wrapped, typed)

    print_aligned(
        wrapped,
        TARGET_COORDS,
    )

    print(
        term.move_xy(
            cursor_xy[0] + TARGET_COORDS[0],
            cursor_xy[1] + TARGET_COORDS[1],
        ),
        end="",
        flush=True,
    )

    return made_errors


def colorize_text(target_split: list[str], typed: str) -> tuple[str, int]:
    typed_index = 0
    made_errors = 0
    colorized_lines: list[str] = []

    for target_line in target_split:
        colorized_line = []

        for target_char in target_line:
            if typed_index < len(typed):
                typed_char = typed[typed_index]

                if typed_char == target_char:
                    colorized_line.append(
                        term.green(SPACE_CHAR if target_char == " " else target_char)
                    )
                else:
                    colorized_line.append(
                        term.red(SPACE_CHAR if target_char == " " else target_char)
                    )
                    made_errors += 1

                typed_index += 1
            else:
                colorized_line.append(SPACE_CHAR if target_char == " " else target_char)

        colorized_lines.append("".join(colorized_line))

    return "\n".join(colorized_lines), made_errors


def get_cursor_xy(char_count: int, wrapped: list[str]) -> tuple[int, int]:
    line_count = 0
    row_count = 0

    for line in wrapped:
        stripped_line = term.strip_seqs(line)
        row_count = 0

        for _ in stripped_line:
            if char_count == 0:
                return row_count, line_count
            row_count += 1
            char_count -= 1

        line_count += 1

    return row_count, line_count


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

    lines = []
    current = []
    line_len = 0

    for word in words:
        word_str = "".join(word)
        word_len = term.length(word_str)
        add_len = word_len if line_len == 0 else word_len + 1
        if line_len + add_len > width:
            if current:
                lines.append(" ".join("".join(w) for w in current) + " ")
            current = [word]
            line_len = word_len
        else:
            current.append(word)
            line_len += add_len

    lines.append(" ".join("".join(w) for w in current))
    return lines, (len(lines[-1]), len(lines))


def print_progress(
    accuracy: float, elapsed: float, wpm: float, PROGRESS_COORDS: tuple[int, int]
) -> None:
    print(term.move_xy(*PROGRESS_COORDS), end="")
    print(f"{int(elapsed)} {int(wpm)} {int(accuracy * 100)}% {" "*20}", end="")


def print_results_stats(elapsed_time: float, wpm: float, accuracy: float) -> None:
    print_aligned(
        f"""Time: {elapsed_time:.2f}s
WPM:  {int(wpm)}
Acc:  {int(accuracy * 100)}%""",
        RESULT_STATS_COORDS,
    )


def print_results_graph(
    key_wpms: list[float],
    terminal_size: os.terminal_size,
    RESULT_GRAPH_COORDS: tuple[int, int],
    RESULT_GRAPH_WIDTH: int,
    RESULT_GRAPH_HEIGHT: int,
) -> None:
    smooth_key_wpms = smoothe_graph(key_wpms, SMOOTHING_WINDOW)

    fig = plotille.Figure()
    fig.width = RESULT_GRAPH_WIDTH
    fig.height = RESULT_GRAPH_HEIGHT
    fig.set_x_limits(min_=0)
    fig.set_y_limits(min_=0)
    fig.origin = False
    fig.plot(list(range(0, len(smooth_key_wpms))), smooth_key_wpms)

    print_aligned(format_results_graph(fig.show()), RESULT_GRAPH_COORDS)


def print_aligned(text: str, coords: tuple[int, int]) -> None:
    split_text = text.split("\n")
    for l in range(len(split_text)):
        print(term.move_xy(coords[0], coords[1] + l), end="")
        print(split_text[l])


def format_results_graph(graph: str) -> str:
    graph_lines: list[str] = graph.split("\n")
    graph_lines.pop(0)
    graph_lines.pop(-1)
    max_digit_count = 0
    float_digit_count = 0
    int_digit_count = 0
    for l in range(len(graph_lines[:-1])):
        split_line = graph_lines[l].split("|")
        number = split_line[0]
        int_digit_count = len(str(round(float(number))))
        float_digit_count = len(number)
        if int_digit_count > max_digit_count:
            max_digit_count = int_digit_count
        graph_lines[l] = (
            f"{str(round(float(number))).ljust(max_digit_count)} |{split_line[1]}"
        )
    graph_lines[-1] = "-" * (
        len(graph_lines[-1]) - float_digit_count + int_digit_count - 8
    )
    graph_lines.insert(0, "(wpm)")
    return "\n".join(graph_lines)


def check_finished(made_error: int, target: str, typed: str) -> bool:
    if not made_error and target == typed:
        return True
    if len(typed) == len(target) + 1:
        return True
    return False


def get_target_text(word_count: int) -> str:
    with open(WORDS_FILE, "r") as file:
        data: dict[str, list[str]] = json.load(file)
    return " ".join(random.sample(data["words"], k=word_count)).lower()


def smoothe_graph(graph: list[float], smoothness: int) -> list[float]:
    smooth_graph = []
    for i in range(len(graph)):
        avg_range = graph[
            max(0, i - smoothness // 2) : min(len(graph), i + smoothness // 2)
        ]
        new_item = sum(avg_range) / len(avg_range)
        smooth_graph.append(new_item)
    return smooth_graph


def compute_wpm(chars: int, elapsed: float) -> float:
    if elapsed and chars:
        return chars / 5 / (elapsed / 60)
    return 0


def compute_accuracy(correct_chars: int, incorrect_chars: int) -> float:
    if correct_chars or incorrect_chars:
        return correct_chars / (correct_chars + incorrect_chars)
    return 0


def test() -> None:
    with term.cbreak():
        print(term.clear)
        print("\x1b[6 q", end="", flush=True)  # set bar cursor

        try:
            typed_text = ""
            target_text = get_target_text(TARGET_LENGTH)

            started = False
            finished = False
            start = 0

            correct_keys = 0
            incorrect_keys = 0

            elapsed_time = 0
            wpm = 0
            accuracy = 0
            key_wpms: list[float] = []
            key_start_time = 0
            prev_key_start_time = 0

            while not finished:
                key = term.inkey(timeout=0.1)
                if key:
                    key_start_time = time.time()
                    if not started:
                        start = time.time()
                        started = True
                    if key.is_sequence:
                        if key.name == "KEY_BACKSPACE":
                            if typed_text:
                                typed_text = typed_text[:-1]
                                if key_wpms:
                                    key_wpms.pop()
                        continue

                    if not key.isprintable():
                        continue

                    typed_text += str(key)

                    if prev_key_start_time:
                        key_wpms.append(
                            compute_wpm(1, key_start_time - prev_key_start_time)
                        )
                    prev_key_start_time = key_start_time
                    idx = len(typed_text) - 1
                    if idx < len(target_text) and typed_text[-1] == target_text[idx]:
                        correct_keys += 1
                        prev_key_start_time = key_start_time
                    else:
                        incorrect_keys += 1

                elapsed_time = time.time() - start if started else 0

                wpm = compute_wpm(len(typed_text), elapsed_time)
                accuracy = compute_accuracy(correct_keys, incorrect_keys)

                print(term.clear(), end="")
                print_progress(accuracy, elapsed_time, wpm, PROGRESS_COORDS)
                made_errors = print_text(
                    target_text, typed_text, TARGET_COORDS, TARGET_WIDTH
                )

                finished = check_finished(made_errors, target_text, typed_text)

            print(term.clear())
            print_results_stats(elapsed_time, wpm, accuracy)
            print_results_graph(
                key_wpms,
                terminal_size,
                RESULT_GRAPH_COORDS,
                RESULT_GRAPH_WIDTH,
                RESULT_GRAPH_HEIGHT,
            )

        finally:
            print("\x1b[0 q", end="", flush=True)  # reset cursor


test()
