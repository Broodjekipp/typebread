from graph import make_data_graph, format_results_graph
from constants import SPACE_CHAR
from state import Layout
from terminal import print_aligned, move_cursor


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

    move_cursor(cursor_xy[0] + coords[0], cursor_xy[1] + coords[1], flush=True)

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
            # The width and height should get minus the horizontal chars added by format_results_graph()
            make_data_graph(data, width - 5, height - 2, smoothing_window),
            int(max(data)),
        ),
        coords,
    )
