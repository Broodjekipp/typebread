import termios
import select
import sys
import tty


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


def move_cursor(x: int, y: int, flush: bool = False) -> None:
    print(f"\033[{y};{x}H", end="", flush=flush)


def clear_terminal():
    print(chr(27) + "[2J")


def print_aligned(
    text: str | list[str], coords: tuple[int, int], is_input: bool = False
) -> None:
    if isinstance(text, str):
        text = text.split("\n")
    for l in range(len(text)):
        move_cursor(coords[0], coords[1] + l)
        print(text[l])
    if is_input:
        _ = input()
    return
