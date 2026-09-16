from typing import cast
import random
import json
import time

from constants import WORDS_DIR, WORDS_FILE, WORDS_MODE_LEN, REFILL_THRESHOLD
from state import TestState


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
