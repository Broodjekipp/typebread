from dataclasses import dataclass, field
from blessed import Terminal
from blessed.keyboard import Keystroke
import plotille
import random
import shutil
import json
import time

term = Terminal()

SPACE_CHAR = "•"
WORDS_DIR = "words"
WORDS_FILE = "english.json"
SMOOTHING_WINDOW = 10
WORDS_MODE_LEN = 15
TIME_MODE_LEN = 10
REFILL_THRESHOLD = 50


@dataclass
class Layout:
    terminal_size: tuple[int, int] = field(default_factory=shutil.get_terminal_size)
    keybind_tip_coords: tuple[int, int] = (0, 0)
    test_settings_coords: tuple[int, int] = (2, 2)
    result_stats_coords: tuple[int, int] = (1, 1)
    result_graph_coords: tuple[int, int] = (1, 5)

    progress_coords: tuple[int, int] = field(init=False)
    target_coords: tuple[int, int] = field(init=False)
    target_width: int = field(init=False)
    result_graph_width: int = field(init=False)
    result_graph_height: int = field(init=False)

    def __post_init__(self):
        cols, lines = self.terminal_size
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
    key_wpms: list[float] = field(default_factory=list)
    prev_key_start_time: float = 0


def print_keybind_tips(keybinds: list[str], coords: tuple[int, int]) -> None:
    print_aligned(keybinds, coords)


def print_text(target: str, typed: str, coords: tuple[int, int], width: int) -> int:
    wrapped = wrap_chars(target, width)[0]
    cursor_xy = get_cursor_xy(len(typed), wrapped)

    wrapped, made_errors = colorize_text(wrapped, typed)

    print_aligned(
        wrapped,
        coords,
    )

    print(
        term.move_xy(
            cursor_xy[0] + coords[0],
            cursor_xy[1] + coords[1],
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
        colorized_line: list[str] = []

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

    lines: list[str] = []
    current: list[list[str]] = []
    line_len: int = 0

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

    print(term.move_xy(*layout.progress_coords), end="")
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
    key_wpms: list[float],
    coords: tuple[int, int],
    width: int,
    height: int,
    smoothing_window: int,
) -> None:
    if not key_wpms:  # No keypresses in the test
        print_aligned("(no data - AFK detected)", coords)
        return

    smooth_key_wpms = smoothe_graph(key_wpms, smoothing_window)

    fig = plotille.Figure()
    fig.width = width
    fig.height = height
    fig.set_x_limits(min_=0)
    fig.set_y_limits(min_=0)
    fig.origin = False
    fig.plot(list(range(0, len(smooth_key_wpms))), smooth_key_wpms)

    print_aligned(format_results_graph(fig.show()), coords)


def print_aligned(
    text: str | list[str], coords: tuple[int, int], is_input: bool = False
) -> None:
    if type(text) == str:
        text = text.split("\n")
    for l in range(len(text)):
        print(term.move_xy(coords[0], coords[1] + l), end="")
        print(text[l])
    if is_input:
        _ = input()
    return


def format_results_graph(graph: str) -> str:
    graph_lines: list[str] = graph.split("\n")
    _ = graph_lines.pop(0)  # Remove top line
    _ = graph_lines.pop(-1)  # Remove bottom line
    max_digit_count = 0
    float_digit_count = 0
    int_digit_count = 0
    for l in range(len(graph_lines[:-1])):
        split_line = graph_lines[l].split("|")
        number = split_line[0]
        try:
            int_digit_count = len(str(round(float(number))))
        except ValueError:
            int_digit_count = len(number)

        float_digit_count = len(number)
        if int_digit_count > max_digit_count:
            max_digit_count = int_digit_count  # Get highest whole digit count
        graph_lines[l] = (
            f"{str(round(float(number))).ljust(max_digit_count)} |{split_line[1]}"  # Remove all spaces before the comma and add padding
        )
    graph_lines[-1] = "-" * (
        len(graph_lines[-1]) - float_digit_count + int_digit_count - 8
    )
    graph_lines.insert(0, "(wpm)")  # Add y label
    return "\n".join(graph_lines)


def check_finished(
    made_error: int,
    target: str,
    typed: str,
    test_type: str,
    elapsed_time: float,
    time_mode_len: int,
) -> bool:
    if test_type == "words":
        if not made_error and target == typed:
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
            data: dict[str, list[str]] = json.load(file)
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


def smoothe_graph(graph: list[float], smoothness: int) -> list[float]:
    smooth_graph: list[float] = []
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


def render_results_frame(
    layout: Layout,
    state: TestState,
    smoothing_window: int,
    elapsed_time: float,
    wpm: float,
    accuracy: float,
):
    print(term.clear())

    print_results_stats(elapsed_time, wpm, accuracy, layout.result_stats_coords)
    print_results_graph(
        state.key_wpms,
        layout.result_graph_coords,
        layout.result_graph_width,
        layout.result_graph_height,
        smoothing_window,
    )


def handle_key(state: TestState, key: Keystroke, test_type: str) -> None:
    key_start_time = time.time()

    if not state.started:
        state.start_time = key_start_time
        state.started = True

    if key.is_sequence:
        if key.name == "KEY_BACKSPACE" and state.typed_text:
            state.typed_text = state.typed_text[:-1]
            if state.key_wpms:
                _ = state.key_wpms.pop()
        return

    if not key.isprintable():
        return

    state.typed_text += str(key)

    if (
        test_type == "time"
        and len(state.target_text) - len(state.typed_text) < REFILL_THRESHOLD
    ):
        state.target_text += " " + get_target_text(WORDS_MODE_LEN)

    if state.prev_key_start_time:
        state.key_wpms.append(
            compute_wpm(1, key_start_time - state.prev_key_start_time)
        )

    idx = len(state.typed_text) - 1
    if idx < len(state.target_text) and state.typed_text[-1] == state.target_text[idx]:
        state.correct_keys += 1
    else:
        state.incorrect_keys += 1

    state.prev_key_start_time = key_start_time


def test(test_type: str) -> None:
    layout = Layout()

    with term.cbreak():
        print(term.clear)
        print("\x1b[6 q", end="", flush=True)  # set bar cursor

        try:
            state = TestState(target_text=get_target_text(WORDS_MODE_LEN))

            finished = False
            first_frame = True
            made_errors = 0
            elapsed_time = 0
            prev_elapsed_time = 0
            wpm = 0
            accuracy = 0

            while not finished:
                key = term.inkey(timeout=0.05)
                if key:
                    handle_key(state, key, test_type)

                elapsed_time = time.time() - state.start_time if state.started else 0
                wpm = compute_wpm(len(state.typed_text), elapsed_time)
                accuracy = compute_accuracy(state.correct_keys, state.incorrect_keys)

                print(term.clear(), end="")

                if key or first_frame or int(elapsed_time) != int(prev_elapsed_time):
                    print_progress(
                        accuracy, elapsed_time, wpm, test_type, TIME_MODE_LEN, layout
                    )
                    made_errors = print_text(
                        state.target_text,
                        state.typed_text,
                        layout.target_coords,
                        layout.target_width,
                    )
                    first_frame = False

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

        except KeyboardInterrupt:
            pass
        finally:
            print("\x1b[0 q", end="", flush=True)  # reset cursor


def start_test(coords: tuple[int, int]) -> None:
    print_aligned("", coords)


test("time")
