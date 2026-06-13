from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import statistics
import tracemalloc
from collections import defaultdict, deque
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable

from PIL import Image, ImageDraw, ImageFont

from .image_encoder import encode_image
from .model import Position, StageProblem
from .solver import DIRECTIONS, SearchResult, bfs, ids, reconstruct_path, slide


ALGORITHM_COLORS = {
    "BFS": "#2563eb",
    "DFS": "#0891b2",
    "IDS": "#dc2626",
    "BFS(bound)": "#16a34a",
    "IDS(bound)": "#f97316",
    "DLS(bound)": "#7c3aed",
}

ALGORITHM_ORDER = {
    "BFS": 0,
    "DFS": 1,
    "IDS": 2,
    "BFS(bound)": 3,
    "IDS(bound)": 4,
    "DLS(bound)": 5,
}


def collect_images(path: str | Path) -> list[Path]:
    root = Path(path)
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    if root.is_file():
        return [root]
    return [p for p in sorted(root.rglob("*")) if p.suffix.lower() in extensions]


def move_bin(value: int | None, width: int) -> str:
    if value is None:
        return "unknown"
    start = ((value - 1) // width) * width + 1
    end = start + width - 1
    return f"{start}-{end}"


def bin_start(label: str) -> int:
    if label == "unknown":
        return 10**9
    return int(label.split("-", 1)[0])


def category_sort_key(value: Any) -> tuple[int, Any]:
    if value is None or value == "":
        return (1, 10**9)
    if isinstance(value, int):
        return (0, value)
    text = str(value)
    if text == "unknown":
        return (1, 10**9)
    if "-" in text:
        return (0, int(text.split("-", 1)[0]))
    if text.isdigit():
        return (0, int(text))
    return (2, text)


def category_numeric(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if text == "unknown":
        return None
    if "-" in text:
        return int(text.split("-", 1)[0])
    if text.isdigit():
        return int(text)
    return None


def algorithm_sort_key(value: str) -> tuple[int, str]:
    return (ALGORITHM_ORDER.get(value, 99), value)


def bfs_depth_bound(problem: StageProblem, max_depth: int) -> SearchResult:
    started = perf_counter()
    queue: deque[tuple[Position, int]] = deque([(problem.start, 0)])
    parent: dict[Position, tuple[Position | None, str | None]] = {
        problem.start: (None, None)
    }
    expanded = 0
    generated = 0

    while queue:
        state, depth = queue.popleft()
        expanded += 1
        if problem.is_goal(state):
            elapsed = (perf_counter() - started) * 1000
            return SearchResult(
                algorithm="BFS(bound)",
                solved=True,
                moves=reconstruct_path(parent, state),
                expanded_states=expanded,
                generated_states=generated,
                visited_states=len(parent),
                runtime_ms=elapsed,
                final_state=state,
                depth_limit=max_depth,
            )
        if depth >= max_depth:
            continue

        for action in DIRECTIONS:
            nxt = slide(problem, state, action)
            if nxt == state:
                continue
            generated += 1
            if nxt not in parent:
                parent[nxt] = (state, action)
                queue.append((nxt, depth + 1))

    elapsed = (perf_counter() - started) * 1000
    return SearchResult(
        algorithm="BFS(bound)",
        solved=False,
        moves=[],
        expanded_states=expanded,
        generated_states=generated,
        visited_states=len(parent),
        runtime_ms=elapsed,
        depth_limit=max_depth,
    )


def dfs_search(problem: StageProblem) -> SearchResult:
    started = perf_counter()
    stack: list[Position] = [problem.start]
    parent: dict[Position, tuple[Position | None, str | None]] = {
        problem.start: (None, None)
    }
    expanded = 0
    generated = 0

    while stack:
        state = stack.pop()
        expanded += 1
        if problem.is_goal(state):
            elapsed = (perf_counter() - started) * 1000
            return SearchResult(
                algorithm="DFS",
                solved=True,
                moves=reconstruct_path(parent, state),
                expanded_states=expanded,
                generated_states=generated,
                visited_states=len(parent),
                runtime_ms=elapsed,
                final_state=state,
            )

        for action in DIRECTIONS:
            nxt = slide(problem, state, action)
            if nxt == state:
                continue
            generated += 1
            if nxt not in parent:
                parent[nxt] = (state, action)
                stack.append(nxt)

    elapsed = (perf_counter() - started) * 1000
    return SearchResult(
        algorithm="DFS",
        solved=False,
        moves=[],
        expanded_states=expanded,
        generated_states=generated,
        visited_states=len(parent),
        runtime_ms=elapsed,
    )


def depth_limited_dfs(problem: StageProblem, max_depth: int) -> SearchResult:
    started = perf_counter()
    expanded = 0
    generated = 0
    visited: set[Position] = set()
    best_remaining: dict[Position, int] = {}
    path: list[str] = []
    final_state: Position | None = None
    found_path: list[str] | None = None

    def dfs(state: Position, remaining: int) -> bool:
        nonlocal expanded, generated, final_state, found_path
        expanded += 1
        visited.add(state)
        if problem.is_goal(state):
            final_state = state
            found_path = path[:]
            return True
        if remaining == 0:
            return False

        previous = best_remaining.get(state)
        if previous is not None and previous >= remaining:
            return False
        best_remaining[state] = remaining

        for action in DIRECTIONS:
            nxt = slide(problem, state, action)
            if nxt == state:
                continue
            generated += 1
            path.append(action)
            if dfs(nxt, remaining - 1):
                return True
            path.pop()
        return False

    solved = dfs(problem.start, max_depth)
    elapsed = (perf_counter() - started) * 1000
    return SearchResult(
        algorithm="DLS(bound)",
        solved=solved,
        moves=found_path or [],
        expanded_states=expanded,
        generated_states=generated,
        visited_states=len(visited),
        runtime_ms=elapsed,
        final_state=final_state,
        depth_limit=max_depth,
    )


def run_measured(func: Callable[[], SearchResult]) -> tuple[SearchResult, float, float]:
    gc.collect()
    tracemalloc.start()
    wall_started = perf_counter()
    try:
        result = func()
        wall_runtime_ms = (perf_counter() - wall_started) * 1000
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, wall_runtime_ms, peak / 1024


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.fmean(values) if values else float("nan")


def median(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.median(values) if values else float("nan")


def percentile(values: Iterable[float], pct: float) -> float:
    values = sorted(values)
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    index = (len(values) - 1) * pct
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[lower]
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(
    rows: list[dict[str, Any]],
    group_fields: list[str],
    extra_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)

    output: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items(), key=lambda pair: pair[0]):
        summary = {field: value for field, value in zip(group_fields, key)}
        stage_ids = {item["stage_id"] for item in items}
        runtimes = [float(item["runtime_ms"]) for item in items]
        memories = [float(item["peak_memory_kib"]) for item in items]
        expanded = [float(item["expanded_states"]) for item in items]
        visited = [float(item["visited_states"]) for item in items]
        summary.update(
            {
                "stage_count": len(stage_ids),
                "trial_count": len(items),
                "solved_count": sum(1 for item in items if item["solved"]),
                "matched_count": sum(1 for item in items if item["matched_optimal"]),
                "mean_runtime_ms": round(mean(runtimes), 6),
                "median_runtime_ms": round(median(runtimes), 6),
                "p95_runtime_ms": round(percentile(runtimes, 0.95), 6),
                "mean_peak_memory_kib": round(mean(memories), 6),
                "median_peak_memory_kib": round(median(memories), 6),
                "p95_peak_memory_kib": round(percentile(memories, 0.95), 6),
                "mean_expanded_states": round(mean(expanded), 6),
                "mean_visited_states": round(mean(visited), 6),
            }
        )
        if extra_fields:
            for field in extra_fields:
                values = {item[field] for item in items}
                summary[field] = next(iter(values)) if len(values) == 1 else ""
        output.append(summary)
    return output


def best_row(rows: list[dict[str, Any]], phase: str, metric: str) -> dict[str, Any]:
    candidates = [row for row in rows if row["phase"] == phase]
    return min(candidates, key=lambda row: float(row[metric]))


def best_full_match_row(rows: list[dict[str, Any]], phase: str, metric: str) -> dict[str, Any]:
    candidates = [
        row
        for row in rows
        if row["phase"] == phase and int(row["matched_count"]) == int(row["trial_count"])
    ]
    return min(candidates, key=lambda row: float(row[metric]))


def read_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill="#111827") -> None:
    draw.text(xy, text, font=font, fill=fill)


def draw_bar_chart(
    rows: list[dict[str, Any]],
    value_field: str,
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    width, height = 1100, 640
    margin_left, margin_right = 110, 50
    margin_top, margin_bottom = 90, 120
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = read_font(28)
    label_font = read_font(16)
    small_font = read_font(13)

    values = [float(row[value_field]) for row in rows]
    max_value = max(values) if values else 1
    max_value = max(max_value * 1.15, 1)
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    baseline_y = margin_top + chart_h

    draw_text(draw, (margin_left, 28), title, title_font)
    draw_text(draw, (margin_left, margin_top - 28), ylabel, label_font, "#4b5563")
    draw.line((margin_left, margin_top, margin_left, baseline_y), fill="#374151", width=2)
    draw.line((margin_left, baseline_y, margin_left + chart_w, baseline_y), fill="#374151", width=2)

    for idx in range(5):
        y_value = max_value * idx / 4
        y = baseline_y - int((y_value / max_value) * chart_h)
        draw.line((margin_left - 6, y, margin_left + chart_w, y), fill="#e5e7eb", width=1)
        draw_text(draw, (16, y - 8), f"{y_value:.1f}", small_font, "#6b7280")

    count = len(rows)
    slot = chart_w / max(count, 1)
    bar_w = min(90, slot * 0.62)
    for i, row in enumerate(rows):
        value = float(row[value_field])
        x_center = margin_left + slot * (i + 0.5)
        x0 = int(x_center - bar_w / 2)
        x1 = int(x_center + bar_w / 2)
        y0 = baseline_y - int((value / max_value) * chart_h)
        color = ALGORITHM_COLORS.get(row["algorithm"], "#2563eb")
        draw.rectangle((x0, y0, x1, baseline_y), fill=color)
        draw_text(draw, (x0, y0 - 22), f"{value:.2f}", small_font, "#111827")
        label = str(row["algorithm"])
        draw_text(draw, (x0 - 8, baseline_y + 14), label, label_font, "#111827")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def draw_line_chart(
    rows: list[dict[str, Any]],
    bin_field: str,
    value_field: str,
    title: str,
    ylabel: str,
    path: Path,
    stage_counts: dict[Any, int] | None = None,
) -> None:
    width, height = 1200, 680
    margin_left, margin_right = 110, 240
    margin_top, margin_bottom = 90, 112
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = read_font(28)
    label_font = read_font(16)
    small_font = read_font(13)

    bins = sorted({row[bin_field] for row in rows}, key=category_sort_key)
    algorithms = sorted({row["algorithm"] for row in rows}, key=algorithm_sort_key)
    values = [float(row[value_field]) for row in rows]
    max_value = max(values) if values else 1
    max_value = max(max_value * 1.15, 1)
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    baseline_y = margin_top + chart_h

    draw_text(draw, (margin_left, 28), title, title_font)
    draw_text(draw, (margin_left, margin_top - 28), ylabel, label_font, "#4b5563")
    draw.line((margin_left, margin_top, margin_left, baseline_y), fill="#374151", width=2)
    draw.line((margin_left, baseline_y, margin_left + chart_w, baseline_y), fill="#374151", width=2)

    for idx in range(5):
        y_value = max_value * idx / 4
        y = baseline_y - int((y_value / max_value) * chart_h)
        draw.line((margin_left - 6, y, margin_left + chart_w, y), fill="#e5e7eb", width=1)
        draw_text(draw, (16, y - 8), f"{y_value:.1f}", small_font, "#6b7280")

    def point(bin_label: str, value: float) -> tuple[int, int]:
        if len(bins) == 1:
            x = margin_left + chart_w // 2
        else:
            x = margin_left + int((bins.index(bin_label) / (len(bins) - 1)) * chart_w)
        y = baseline_y - int((value / max_value) * chart_h)
        return x, y

    row_map = {(row[bin_field], row["algorithm"]): row for row in rows}
    for algorithm in algorithms:
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        points: list[tuple[int, int]] = []
        for bin_label in bins:
            row = row_map.get((bin_label, algorithm))
            if row is None:
                continue
            points.append(point(bin_label, float(row[value_field])))
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)

    for bin_label in bins:
        x, _ = point(bin_label, 0)
        draw.line((x, baseline_y, x, baseline_y + 6), fill="#374151", width=2)
        label = str(bin_label)
        draw_text(draw, (x - 10 * len(label) // 2, baseline_y + 16), label, label_font, "#111827")
        if stage_counts and bin_label in stage_counts:
            count_label = f"n={stage_counts[bin_label]}"
            draw_text(draw, (x - 4 * len(count_label), baseline_y + 40), count_label, small_font, "#6b7280")

    legend_x = width - margin_right + 35
    legend_y = margin_top + 20
    for idx, algorithm in enumerate(algorithms):
        y = legend_y + idx * 30
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        draw.rectangle((legend_x, y + 4, legend_x + 18, y + 18), fill=color)
        draw_text(draw, (legend_x + 28, y), algorithm, label_font, "#111827")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def draw_grouped_bar_chart(
    rows: list[dict[str, Any]],
    category_field: str,
    value_field: str,
    title: str,
    ylabel: str,
    path: Path,
    stage_counts: dict[Any, int] | None = None,
) -> None:
    categories = sorted({row[category_field] for row in rows}, key=category_sort_key)
    algorithms = sorted({row["algorithm"] for row in rows}, key=algorithm_sort_key)
    width = max(1320, 250 + len(categories) * 82)
    height = 720
    margin_left, margin_right = 110, 235
    margin_top, margin_bottom = 90, 120
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = read_font(28)
    label_font = read_font(16)
    small_font = read_font(13)

    values = [float(row[value_field]) for row in rows]
    max_value = max(values) if values else 1
    max_value = max(max_value * 1.15, 1)
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    baseline_y = margin_top + chart_h

    draw_text(draw, (margin_left, 28), title, title_font)
    draw_text(draw, (margin_left, margin_top - 28), ylabel, label_font, "#4b5563")
    draw.line((margin_left, margin_top, margin_left, baseline_y), fill="#374151", width=2)
    draw.line((margin_left, baseline_y, margin_left + chart_w, baseline_y), fill="#374151", width=2)

    for idx in range(5):
        y_value = max_value * idx / 4
        y = baseline_y - int((y_value / max_value) * chart_h)
        draw.line((margin_left - 6, y, margin_left + chart_w, y), fill="#e5e7eb", width=1)
        draw_text(draw, (16, y - 8), f"{y_value:.1f}", small_font, "#6b7280")

    row_map = {(row[category_field], row["algorithm"]): row for row in rows}
    slot = chart_w / max(len(categories), 1)
    group_w = slot * 0.72
    bar_w = max(8, min(22, group_w / max(len(algorithms), 1) - 3))

    for category_index, category in enumerate(categories):
        group_center = margin_left + slot * (category_index + 0.5)
        start_x = group_center - ((len(algorithms) - 1) * (bar_w + 3)) / 2
        for algorithm_index, algorithm in enumerate(algorithms):
            row = row_map.get((category, algorithm))
            if row is None:
                continue
            value = float(row[value_field])
            x0 = int(start_x + algorithm_index * (bar_w + 3))
            x1 = int(x0 + bar_w)
            y0 = baseline_y - int((value / max_value) * chart_h)
            color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
            draw.rectangle((x0, y0, x1, baseline_y), fill=color)

        label = str(category)
        draw_text(draw, (int(group_center - 5 * len(label)), baseline_y + 16), label, label_font, "#111827")
        if stage_counts and category in stage_counts:
            count_label = f"n={stage_counts[category]}"
            draw_text(draw, (int(group_center - 4 * len(count_label)), baseline_y + 40), count_label, small_font, "#6b7280")

    legend_x = width - margin_right + 35
    legend_y = margin_top + 20
    for idx, algorithm in enumerate(algorithms):
        y = legend_y + idx * 30
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        draw.rectangle((legend_x, y + 4, legend_x + 18, y + 18), fill=color)
        draw_text(draw, (legend_x + 28, y), algorithm, label_font, "#111827")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def compute_marginal_rate_rows(
    rows: list[dict[str, Any]],
    category_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["phase"], row["algorithm"])].append(row)

    output: list[dict[str, Any]] = []
    for (phase, algorithm), items in sorted(
        grouped.items(), key=lambda pair: (pair[0][0], algorithm_sort_key(pair[0][1]))
    ):
        ordered = sorted(items, key=lambda row: category_sort_key(row[category_field]))
        for left, right in zip(ordered, ordered[1:]):
            left_x = category_numeric(left[category_field])
            right_x = category_numeric(right[category_field])
            if left_x is None or right_x is None or right_x == left_x:
                continue
            step = right_x - left_x
            runtime_from = float(left["mean_runtime_ms"])
            runtime_to = float(right["mean_runtime_ms"])
            memory_from = float(left["mean_peak_memory_kib"])
            memory_to = float(right["mean_peak_memory_kib"])
            output.append(
                {
                    "phase": phase,
                    "algorithm": algorithm,
                    "from_category": left[category_field],
                    "to_category": right[category_field],
                    "transition": f"{left[category_field]}->{right[category_field]}",
                    "from_x": left_x,
                    "to_x": right_x,
                    "j": step,
                    "mean_runtime_ms_from": round(runtime_from, 6),
                    "mean_runtime_ms_to": round(runtime_to, 6),
                    "mean_runtime_ms_delta": round(runtime_to - runtime_from, 6),
                    "mean_runtime_ms_mr": round((runtime_to - runtime_from) / step, 6),
                    "mean_peak_memory_kib_from": round(memory_from, 6),
                    "mean_peak_memory_kib_to": round(memory_to, 6),
                    "mean_peak_memory_kib_delta": round(memory_to - memory_from, 6),
                    "mean_peak_memory_kib_mr": round((memory_to - memory_from) / step, 6),
                }
            )
    return output


def value_axis_bounds(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    min_value = min(values)
    max_value = max(values)
    if min_value >= 0:
        return 0.0, max(max_value * 1.15, 1.0)
    if max_value <= 0:
        return min(min_value * 1.15, -1.0), 0.0
    padding = (max_value - min_value) * 0.12
    return min_value - padding, max_value + padding


def scale_y(value: float, min_value: float, max_value: float, chart_h: int, top: int) -> int:
    if max_value == min_value:
        return top + chart_h // 2
    return top + chart_h - int(((value - min_value) / (max_value - min_value)) * chart_h)


def mr_transitions(rows: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(
        {
            (int(row["from_x"]), int(row["to_x"]), str(row["transition"]))
            for row in rows
        }
    )
    return [label for _start, _end, label in ordered]


def draw_mr_line_chart(
    rows: list[dict[str, Any]],
    value_field: str,
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    width, height = 1420, 720
    margin_left, margin_right = 120, 240
    margin_top, margin_bottom = 90, 145
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = read_font(28)
    label_font = read_font(16)
    small_font = read_font(13)

    transitions = mr_transitions(rows)
    algorithms = sorted({row["algorithm"] for row in rows}, key=algorithm_sort_key)
    values = [float(row[value_field]) for row in rows]
    min_value, max_value = value_axis_bounds(values)
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    baseline_y = scale_y(0.0, min_value, max_value, chart_h, margin_top)

    draw_text(draw, (margin_left, 28), title, title_font)
    draw_text(draw, (margin_left, margin_top - 28), ylabel, label_font, "#4b5563")
    draw.line((margin_left, margin_top, margin_left, margin_top + chart_h), fill="#374151", width=2)
    draw.line((margin_left, baseline_y, margin_left + chart_w, baseline_y), fill="#374151", width=2)

    for idx in range(5):
        y_value = min_value + (max_value - min_value) * idx / 4
        y = scale_y(y_value, min_value, max_value, chart_h, margin_top)
        draw.line((margin_left - 6, y, margin_left + chart_w, y), fill="#e5e7eb", width=1)
        draw_text(draw, (12, y - 8), f"{y_value:.2f}", small_font, "#6b7280")

    def point(label: str, value: float) -> tuple[int, int]:
        if len(transitions) == 1:
            x = margin_left + chart_w // 2
        else:
            x = margin_left + int((transitions.index(label) / (len(transitions) - 1)) * chart_w)
        y = scale_y(value, min_value, max_value, chart_h, margin_top)
        return x, y

    row_map = {(row["transition"], row["algorithm"]): row for row in rows}
    for algorithm in algorithms:
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        points: list[tuple[int, int]] = []
        for transition in transitions:
            row = row_map.get((transition, algorithm))
            if row is None:
                continue
            points.append(point(transition, float(row[value_field])))
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)

    for transition in transitions:
        x, _ = point(transition, 0.0)
        draw.line((x, baseline_y, x, baseline_y + 6), fill="#374151", width=2)
        label = transition.replace("->", "\n")
        parts = label.split("\n")
        for idx, part in enumerate(parts):
            draw_text(draw, (x - 5 * len(part), margin_top + chart_h + 18 + idx * 18), part, small_font, "#111827")

    legend_x = width - margin_right + 35
    legend_y = margin_top + 20
    for idx, algorithm in enumerate(algorithms):
        y = legend_y + idx * 30
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        draw.rectangle((legend_x, y + 4, legend_x + 18, y + 18), fill=color)
        draw_text(draw, (legend_x + 28, y), algorithm, label_font, "#111827")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def draw_mr_grouped_bar_chart(
    rows: list[dict[str, Any]],
    value_field: str,
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    transitions = mr_transitions(rows)
    algorithms = sorted({row["algorithm"] for row in rows}, key=algorithm_sort_key)
    width = max(1420, 310 + len(transitions) * 88)
    height = 740
    margin_left, margin_right = 120, 240
    margin_top, margin_bottom = 90, 145
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = read_font(28)
    label_font = read_font(16)
    small_font = read_font(13)

    values = [float(row[value_field]) for row in rows]
    min_value, max_value = value_axis_bounds(values)
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    zero_y = scale_y(0.0, min_value, max_value, chart_h, margin_top)

    draw_text(draw, (margin_left, 28), title, title_font)
    draw_text(draw, (margin_left, margin_top - 28), ylabel, label_font, "#4b5563")
    draw.line((margin_left, margin_top, margin_left, margin_top + chart_h), fill="#374151", width=2)
    draw.line((margin_left, zero_y, margin_left + chart_w, zero_y), fill="#374151", width=2)

    for idx in range(5):
        y_value = min_value + (max_value - min_value) * idx / 4
        y = scale_y(y_value, min_value, max_value, chart_h, margin_top)
        draw.line((margin_left - 6, y, margin_left + chart_w, y), fill="#e5e7eb", width=1)
        draw_text(draw, (12, y - 8), f"{y_value:.2f}", small_font, "#6b7280")

    row_map = {(row["transition"], row["algorithm"]): row for row in rows}
    slot = chart_w / max(len(transitions), 1)
    group_w = slot * 0.72
    bar_w = max(8, min(22, group_w / max(len(algorithms), 1) - 3))

    for transition_index, transition in enumerate(transitions):
        group_center = margin_left + slot * (transition_index + 0.5)
        start_x = group_center - ((len(algorithms) - 1) * (bar_w + 3)) / 2
        for algorithm_index, algorithm in enumerate(algorithms):
            row = row_map.get((transition, algorithm))
            if row is None:
                continue
            value = float(row[value_field])
            x0 = int(start_x + algorithm_index * (bar_w + 3))
            x1 = int(x0 + bar_w)
            y_value = scale_y(value, min_value, max_value, chart_h, margin_top)
            color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
            draw.rectangle((x0, min(y_value, zero_y), x1, max(y_value, zero_y)), fill=color)

        label_parts = transition.replace("->", "\n").split("\n")
        for idx, part in enumerate(label_parts):
            draw_text(draw, (int(group_center - 5 * len(part)), margin_top + chart_h + 18 + idx * 18), part, small_font, "#111827")

    legend_x = width - margin_right + 35
    legend_y = margin_top + 20
    for idx, algorithm in enumerate(algorithms):
        y = legend_y + idx * 30
        color = ALGORITHM_COLORS.get(algorithm, "#2563eb")
        draw.rectangle((legend_x, y + 4, legend_x + 18, y + 18), fill=color)
        draw_text(draw, (legend_x + 28, y), algorithm, label_font, "#111827")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def write_report(
    path: Path,
    total_stages: int,
    trials: int,
    overall_summary: list[dict[str, Any]],
    winners: dict[str, dict[str, Any]],
    plot_paths: list[Path],
) -> None:
    lines = [
        "# GridCraze Benchmark Report",
        "",
        f"- Stages: {total_stages}",
        f"- Trials per stage/algorithm: {trials}",
        "- Runtime: algorithm execution only, measured in milliseconds",
        "- Peak memory: Python `tracemalloc` peak allocation during the algorithm call",
        "",
        "## Winners",
        "",
        f"- Least memory, standard search: {winners['standard_least_memory']['algorithm']}",
        f"- Fastest, standard search: {winners['standard_fastest']['algorithm']}",
        f"- Least memory, standard search with full optimal match: {winners['standard_optimal_least_memory']['algorithm']}",
        f"- Fastest, standard search with full optimal match: {winners['standard_optimal_fastest']['algorithm']}",
        f"- Least memory, optimal-bound search: {winners['bound_least_memory']['algorithm']}",
        f"- Fastest, optimal-bound search: {winners['bound_fastest']['algorithm']}",
        "",
        "Note: DFS is included as a non-optimal baseline. It can be fast and memory-light,",
        "but it does not guarantee a minimum-move solution. Check the `Matched` column before",
        "using it as an optimal solver.",
        "",
        "## Overall Summary",
        "",
        "| Phase | Algorithm | Mean Time (ms) | Mean Peak Memory (KiB) | Mean Expanded | Solved | Matched |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in overall_summary:
        lines.append(
            "| {phase} | {algorithm} | {time:.4f} | {memory:.2f} | {expanded:.2f} | {solved} | {matched} |".format(
                phase=row["phase"],
                algorithm=row["algorithm"],
                time=float(row["mean_runtime_ms"]),
                memory=float(row["mean_peak_memory_kib"]),
                expanded=float(row["mean_expanded_states"]),
                solved=row["solved_count"],
                matched=row["matched_count"],
            )
        )

    lines.extend(["", "## Graphs", ""])
    for plot in plot_paths:
        lines.append(f"- `{plot.as_posix()}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def count_rows_for_field(
    stage_records: list[dict[str, Any]],
    category_field: str,
) -> tuple[list[dict[str, Any]], dict[Any, int]]:
    counts: dict[Any, int] = defaultdict(int)
    for record in stage_records:
        counts[record[category_field]] += 1
    rows = [
        {category_field: category, "stage_count": counts[category]}
        for category in sorted(counts, key=category_sort_key)
    ]
    return rows, counts


def write_analysis_folder(
    base_dir: Path,
    folder_name: str,
    summary_rows: list[dict[str, Any]],
    summary_fields: list[str],
    count_rows: list[dict[str, Any]],
    count_fields: list[str],
    category_field: str,
    category_title: str,
    stage_counts: dict[Any, int],
    plot_paths: list[Path],
) -> None:
    analysis_dir = base_dir / folder_name
    plot_dir = analysis_dir / "plots"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    write_csv(analysis_dir / "counts.csv", count_rows, count_fields)
    write_csv(analysis_dir / "summary.csv", summary_rows, summary_fields)

    mr_rows = compute_marginal_rate_rows(summary_rows, category_field)
    mr_fields = [
        "phase",
        "algorithm",
        "from_category",
        "to_category",
        "transition",
        "from_x",
        "to_x",
        "j",
        "mean_runtime_ms_from",
        "mean_runtime_ms_to",
        "mean_runtime_ms_delta",
        "mean_runtime_ms_mr",
        "mean_peak_memory_kib_from",
        "mean_peak_memory_kib_to",
        "mean_peak_memory_kib_delta",
        "mean_peak_memory_kib_mr",
    ]
    write_csv(analysis_dir / "marginal_rate_summary.csv", mr_rows, mr_fields)

    for phase in ["standard", "optimal_bound"]:
        phase_rows = [row for row in summary_rows if row["phase"] == phase]
        phase_mr_rows = [row for row in mr_rows if row["phase"] == phase]
        for metric, ylabel, suffix, title_metric in [
            ("mean_runtime_ms", "Mean runtime (ms)", "runtime", "Runtime"),
            ("mean_peak_memory_kib", "Mean peak memory (KiB)", "memory", "Memory"),
        ]:
            line_path = plot_dir / f"value_{phase}_{suffix}_line.png"
            draw_line_chart(
                phase_rows,
                category_field,
                metric,
                f"{category_title}: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                line_path,
                stage_counts=stage_counts,
            )
            plot_paths.append(line_path)

            bar_path = plot_dir / f"value_{phase}_{suffix}_grouped_bar.png"
            draw_grouped_bar_chart(
                phase_rows,
                category_field,
                metric,
                f"{category_title}: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                bar_path,
                stage_counts=stage_counts,
            )
            plot_paths.append(bar_path)

        for metric, ylabel, suffix, title_metric in [
            ("mean_runtime_ms_mr", "Marginal runtime rate (ms/move)", "runtime", "Runtime"),
            ("mean_peak_memory_kib_mr", "Marginal memory rate (KiB/move)", "memory", "Memory"),
        ]:
            line_path = plot_dir / f"mr_{phase}_{suffix}_line.png"
            draw_mr_line_chart(
                phase_mr_rows,
                metric,
                f"MR {category_title}: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                line_path,
            )
            plot_paths.append(line_path)

            bar_path = plot_dir / f"mr_{phase}_{suffix}_grouped_bar.png"
            draw_mr_grouped_bar_chart(
                phase_mr_rows,
                metric,
                f"MR {category_title}: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                bar_path,
            )
            plot_paths.append(bar_path)


def run_benchmark(args: argparse.Namespace) -> None:
    image_paths = collect_images(args.images)
    if not image_paths:
        raise SystemExit(f"no images found under {args.images}")

    out_dir = Path(args.out)
    plot_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    stage_records: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []

    for image_path in image_paths:
        stage = encode_image(image_path)
        problem = StageProblem.from_dict(stage)
        optimal = problem.optimal_moves
        stage_records.append(
            {
                "stage_id": problem.stage_id,
                "image_path": str(image_path),
                "difficulty_group": image_path.parent.name,
                "rows": problem.rows,
                "cols": problem.cols,
                "optimal_moves": optimal,
                "range5": move_bin(optimal, 5),
                "range10": move_bin(optimal, 10),
            }
        )

        standard_algorithms: list[tuple[str, Callable[[], SearchResult]]] = [
            ("BFS", lambda p=problem: bfs(p)),
            ("DFS", lambda p=problem: dfs_search(p)),
            ("IDS", lambda p=problem: ids(p, max_depth=p.rows * p.cols)),
        ]
        if optimal is None:
            bound_algorithms: list[tuple[str, Callable[[], SearchResult]]] = []
        else:
            bound_algorithms = [
                ("BFS(bound)", lambda p=problem, d=optimal: bfs_depth_bound(p, d)),
                ("IDS(bound)", lambda p=problem, d=optimal: ids(p, max_depth=d)),
                ("DLS(bound)", lambda p=problem, d=optimal: depth_limited_dfs(p, d)),
            ]

        for phase, algorithms in [
            ("standard", standard_algorithms),
            ("optimal_bound", bound_algorithms),
        ]:
            for algorithm_name, func in algorithms:
                for trial in range(1, args.trials + 1):
                    result, wall_runtime_ms, peak_memory_kib = run_measured(func)
                    matched = (
                        optimal is not None
                        and result.move_count is not None
                        and result.move_count == optimal
                    )
                    raw_rows.append(
                        {
                            "stage_id": problem.stage_id,
                            "image_path": str(image_path),
                            "difficulty_group": image_path.parent.name,
                            "rows": problem.rows,
                            "cols": problem.cols,
                            "optimal_moves": optimal,
                            "range5": move_bin(optimal, 5),
                            "range10": move_bin(optimal, 10),
                            "phase": phase,
                            "algorithm": algorithm_name,
                            "trial": trial,
                            "solved": result.solved,
                            "move_count": result.move_count,
                            "matched_optimal": matched,
                            "runtime_ms": round(result.runtime_ms, 6),
                            "wall_runtime_ms": round(wall_runtime_ms, 6),
                            "peak_memory_kib": round(peak_memory_kib, 6),
                            "expanded_states": result.expanded_states,
                            "generated_states": result.generated_states,
                            "visited_states": result.visited_states,
                            "depth_limit": result.depth_limit,
                            "sequence": " ".join(result.moves),
                        }
                    )

    raw_fields = [
        "stage_id",
        "image_path",
        "difficulty_group",
        "rows",
        "cols",
        "optimal_moves",
        "range5",
        "range10",
        "phase",
        "algorithm",
        "trial",
        "solved",
        "move_count",
        "matched_optimal",
        "runtime_ms",
        "wall_runtime_ms",
        "peak_memory_kib",
        "expanded_states",
        "generated_states",
        "visited_states",
        "depth_limit",
        "sequence",
    ]
    write_csv(out_dir / "raw_results.csv", raw_rows, raw_fields)

    stage_summary = summarize(
        raw_rows,
        ["stage_id", "phase", "algorithm"],
        extra_fields=["optimal_moves", "range5", "range10", "difficulty_group"],
    )
    stage_fields = [
        "stage_id",
        "phase",
        "algorithm",
        "difficulty_group",
        "optimal_moves",
        "range5",
        "range10",
        "stage_count",
        "trial_count",
        "solved_count",
        "matched_count",
        "mean_runtime_ms",
        "median_runtime_ms",
        "p95_runtime_ms",
        "mean_peak_memory_kib",
        "median_peak_memory_kib",
        "p95_peak_memory_kib",
        "mean_expanded_states",
        "mean_visited_states",
    ]
    write_csv(out_dir / "stage_summary.csv", stage_summary, stage_fields)

    overall_summary = summarize(raw_rows, ["phase", "algorithm"])
    overall_fields = [
        "phase",
        "algorithm",
        "stage_count",
        "trial_count",
        "solved_count",
        "matched_count",
        "mean_runtime_ms",
        "median_runtime_ms",
        "p95_runtime_ms",
        "mean_peak_memory_kib",
        "median_peak_memory_kib",
        "p95_peak_memory_kib",
        "mean_expanded_states",
        "mean_visited_states",
    ]
    write_csv(out_dir / "overall_summary.csv", overall_summary, overall_fields)

    optimal_length_counts: dict[Any, int] = defaultdict(int)
    for record in stage_records:
        optimal_length_counts[record["optimal_moves"]] += 1
    optimal_length_count_rows = [
        {"optimal_moves": optimal, "stage_count": optimal_length_counts[optimal]}
        for optimal in sorted(optimal_length_counts, key=category_sort_key)
    ]
    write_csv(
        out_dir / "optimal_length_counts.csv",
        optimal_length_count_rows,
        ["optimal_moves", "stage_count"],
    )

    optimal_length_summary = summarize(raw_rows, ["phase", "optimal_moves", "algorithm"])
    optimal_length_fields = [
        "phase",
        "optimal_moves",
        "algorithm",
        "stage_count",
        "trial_count",
        "solved_count",
        "matched_count",
        "mean_runtime_ms",
        "median_runtime_ms",
        "p95_runtime_ms",
        "mean_peak_memory_kib",
        "median_peak_memory_kib",
        "p95_peak_memory_kib",
        "mean_expanded_states",
        "mean_visited_states",
    ]
    write_csv(
        out_dir / "optimal_length_summary.csv",
        optimal_length_summary,
        optimal_length_fields,
    )

    range_summaries: dict[str, list[dict[str, Any]]] = {}
    range_summary_fields = [
        "phase",
        "algorithm",
        "stage_count",
        "trial_count",
        "solved_count",
        "matched_count",
        "mean_runtime_ms",
        "median_runtime_ms",
        "p95_runtime_ms",
        "mean_peak_memory_kib",
        "median_peak_memory_kib",
        "p95_peak_memory_kib",
        "mean_expanded_states",
        "mean_visited_states",
    ]
    for width, field in [(5, "range5"), (10, "range10")]:
        summary = summarize(raw_rows, ["phase", field, "algorithm"])
        range_summaries[str(width)] = summary
        write_csv(
            out_dir / f"range_summary_{width}.csv",
            summary,
            ["phase", field] + range_summary_fields[1:],
        )

    winners = {
        "standard_least_memory": best_row(overall_summary, "standard", "mean_peak_memory_kib"),
        "standard_fastest": best_row(overall_summary, "standard", "mean_runtime_ms"),
        "standard_optimal_least_memory": best_full_match_row(
            overall_summary, "standard", "mean_peak_memory_kib"
        ),
        "standard_optimal_fastest": best_full_match_row(
            overall_summary, "standard", "mean_runtime_ms"
        ),
        "bound_least_memory": best_row(overall_summary, "optimal_bound", "mean_peak_memory_kib"),
        "bound_fastest": best_row(overall_summary, "optimal_bound", "mean_runtime_ms"),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "total_stages": len(stage_records),
                "trials": args.trials,
                "winners": winners,
                "overall_summary": overall_summary,
                "optimal_length_counts": optimal_length_count_rows,
                "optimal_length_summary": optimal_length_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    plot_paths: list[Path] = []
    for phase in ["standard", "optimal_bound"]:
        phase_rows = [row for row in overall_summary if row["phase"] == phase]
        for metric, ylabel, suffix, title_metric in [
            ("mean_runtime_ms", "Mean runtime (ms)", "runtime", "Runtime"),
            ("mean_peak_memory_kib", "Mean peak memory (KiB)", "memory", "Memory"),
        ]:
            path = plot_dir / f"overall_{phase}_{suffix}.png"
            draw_bar_chart(
                phase_rows,
                metric,
                f"Overall {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                path,
            )
            plot_paths.append(path)

    for width, field in [(5, "range5"), (10, "range10")]:
        for phase in ["standard", "optimal_bound"]:
            rows = [row for row in range_summaries[str(width)] if row["phase"] == phase]
            for metric, ylabel, suffix, title_metric in [
                ("mean_runtime_ms", "Mean runtime (ms)", "runtime", "Runtime"),
                ("mean_peak_memory_kib", "Mean peak memory (KiB)", "memory", "Memory"),
            ]:
                path = plot_dir / f"range{width}_{phase}_{suffix}.png"
                draw_line_chart(
                    rows,
                    field,
                    metric,
                    f"{width}-Move Bins: {phase.replace('_', ' ').title()} {title_metric}",
                    ylabel,
                    path,
                )
                plot_paths.append(path)

    for phase in ["standard", "optimal_bound"]:
        rows = [row for row in optimal_length_summary if row["phase"] == phase]
        for metric, ylabel, suffix, title_metric in [
            ("mean_runtime_ms", "Mean runtime (ms)", "runtime", "Runtime"),
            ("mean_peak_memory_kib", "Mean peak memory (KiB)", "memory", "Memory"),
        ]:
            line_path = plot_dir / f"optimal_length_{phase}_{suffix}_line.png"
            draw_line_chart(
                rows,
                "optimal_moves",
                metric,
                f"Optimal Length: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                line_path,
                stage_counts=dict(optimal_length_counts),
            )
            plot_paths.append(line_path)

            bar_path = plot_dir / f"optimal_length_{phase}_{suffix}_grouped_bar.png"
            draw_grouped_bar_chart(
                rows,
                "optimal_moves",
                metric,
                f"Optimal Length: {phase.replace('_', ' ').title()} {title_metric}",
                ylabel,
                bar_path,
                stage_counts=dict(optimal_length_counts),
            )
            plot_paths.append(bar_path)

    write_analysis_folder(
        out_dir,
        "exact_optimal_length",
        optimal_length_summary,
        optimal_length_fields,
        optimal_length_count_rows,
        ["optimal_moves", "stage_count"],
        "optimal_moves",
        "Exact Optimal Length",
        dict(optimal_length_counts),
        plot_paths,
    )

    range5_count_rows, range5_counts = count_rows_for_field(stage_records, "range5")
    write_analysis_folder(
        out_dir,
        "range_5",
        range_summaries["5"],
        ["phase", "range5"] + range_summary_fields[1:],
        range5_count_rows,
        ["range5", "stage_count"],
        "range5",
        "5-Move Range",
        range5_counts,
        plot_paths,
    )

    range10_count_rows, range10_counts = count_rows_for_field(stage_records, "range10")
    write_analysis_folder(
        out_dir,
        "range_10",
        range_summaries["10"],
        ["phase", "range10"] + range_summary_fields[1:],
        range10_count_rows,
        ["range10", "stage_count"],
        "range10",
        "10-Move Range",
        range10_counts,
        plot_paths,
    )

    write_csv(
        out_dir / "stage_inventory.csv",
        stage_records,
        [
            "stage_id",
            "image_path",
            "difficulty_group",
            "rows",
            "cols",
            "optimal_moves",
            "range5",
            "range10",
        ],
    )
    write_report(
        out_dir / "report.md",
        len(stage_records),
        args.trials,
        overall_summary,
        winners,
        plot_paths,
    )

    print(json.dumps({"out": str(out_dir), "total_stages": len(stage_records), "trials": args.trials}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gridcraze-benchmark")
    parser.add_argument("--images", default="../Images", help="image file or directory")
    parser.add_argument("--out", default="results/benchmark", help="output directory")
    parser.add_argument("--trials", type=int, default=5, help="runs per stage/algorithm")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.trials < 1:
        raise SystemExit("--trials must be at least 1")
    run_benchmark(args)


if __name__ == "__main__":
    main()
