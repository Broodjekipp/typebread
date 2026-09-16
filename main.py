import time

from typing_logic import (
    get_target_text,
    compute_correct_wpm,
    compute_accuracy,
    check_finished,
    handle_key,
)
from render import print_text, print_progress, print_results_stats, print_results_graph
from terminal import get_key, clear_terminal, print_aligned
from storage import save_results
from constants import (
    PROGRESS_FILE,
    SMOOTHING_WINDOW,
    WORDS_MODE_LEN,
    TIME_MODE_LEN,
    REFILL_THRESHOLD,
)
from state import Layout, TestState


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
