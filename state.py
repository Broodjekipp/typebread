from dataclasses import dataclass, field
import shutil


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
