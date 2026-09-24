def smooth_data(data: list[float | int], smoothing_window: int) -> list[float | int]:
    smooth_graph: list[float] = []
    for i in range(len(data)):
        avg_range = data[
            max(0, i - smoothing_window // 2) : min(
                len(data), i + smoothing_window // 2 + 1
            )
        ]
        new_item = sum(avg_range) / len(avg_range)
        smooth_graph.append(new_item)
    return smooth_graph


def interpolate_data(data: list[float | int], target_length: int) -> list[float]:
    if target_length <= 1:
        raise ValueError("target_length must be greater than 1")

    interp_data: list[float] = []
    for i in range(target_length):
        pos = i * (len(data) - 1) / (target_length - 1)
        lo = int(pos)
        hi = min(lo + 1, len(data) - 1)
        frac = pos - lo
        interp_data.append(data[lo] + (data[hi] - data[lo]) * frac)

    return interp_data


def scale_data_height(data: list[float | int], target_height: int) -> list[int]:
    data_max = max(data)
    scale_factor: float = target_height / data_max if data_max else 0
    return [int(x * scale_factor) for x in data]


def make_braille_graph(data: list[int], width: int) -> str:
    if not data:
        return ""

    double_braille_chars: list[list[str]] = [
        ["⠉", "⠑", "⠡"],  # Upper dot
        ["⠊", "⠒", "⠢"],  # Middle dot
        ["⠌", "⠔", "⠤"],  # Bottom dot
    ]
    single_braille_chars: list[list[str]] = [["⠁", "⠂", "⠄"], ["⠈", "⠐", "⠠"]]

    num_rows = max(data) // 3 + 1
    graph_list: list[str] = ["" for _ in range(num_rows)]

    i = 0
    col = 0
    n = len(data)
    while i < n:
        if i + 1 >= n:
            height = data[i] // 3
            char = single_braille_chars[0][data[i] % 3]
            graph_list[height] = graph_list[height].ljust(col) + char
            i += 1
        else:
            h1, h2 = data[i] // 3, data[i + 1] // 3
            if h1 == h2:
                char = double_braille_chars[data[i] % 3][data[i + 1] % 3]
                graph_list[h1] = graph_list[h1].ljust(col) + char
            else:
                c1 = single_braille_chars[0][data[i] % 3]
                c2 = single_braille_chars[1][data[i + 1] % 3]
                graph_list[h1] = graph_list[h1].ljust(col) + c1
                graph_list[h2] = graph_list[h2].ljust(col) + c2
            i += 2
        col += 1

    for r in range(len(graph_list)):
        graph_list[r] = graph_list[r].ljust(width)

    graph_list.reverse()
    return "\n".join(graph_list)


def format_results_graph(graph: str, width: int) -> str:
    graph_list = graph.split("\n")
    graph_list = ["|" + i + "|" for i in graph_list]
    graph_list.insert(0, f"+{"-" * width}+")
    graph_list.append(f"+{"-" * width}+")
    return "\n".join(graph_list)


def make_data_graph(
    data: list[float | int], width: int, height: int, smoothing_window: int
) -> str:
    if not data:
        return "(no data - AFK detected)"
    # Braille characters are 2x3
    graph_width_points = width * 2
    graph_height_points = height * 3

    data = smooth_data(data, smoothing_window)
    data = interpolate_data(data, graph_width_points)
    data_int = scale_data_height(data, graph_height_points)
    return make_braille_graph(data_int, width)
