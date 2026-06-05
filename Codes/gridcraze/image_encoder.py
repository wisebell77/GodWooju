from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
import re

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class BoardGeometry:
    x0: int
    y0: int
    x1: int
    y1: int
    cell_size: int
    rows: int
    cols: int

    def as_dict(self) -> dict[str, int]:
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "cell_size": self.cell_size,
            "rows": self.rows,
            "cols": self.cols,
        }


def parse_image_name(path: str | Path) -> tuple[str, int | None]:
    stem = Path(path).stem
    if "_" not in stem:
        return stem, None
    stage_id, suffix = stem.rsplit("_", 1)
    return stage_id, int(suffix) if suffix.isdigit() else None


def load_rgb(path: str | Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def load_rgb_bytes(data: bytes) -> np.ndarray:
    return np.array(Image.open(BytesIO(data)).convert("RGB"))


def corner_background(image: np.ndarray, sample: int = 24) -> np.ndarray:
    blocks = [
        image[:sample, :sample],
        image[:sample, -sample:],
        image[-sample:, :sample],
        image[-sample:, -sample:],
    ]
    pixels = np.concatenate([block.reshape(-1, 3) for block in blocks], axis=0)
    return np.median(pixels, axis=0)


def longest_true_segment(flags: np.ndarray) -> tuple[int, int]:
    best_start = 0
    best_end = 0
    start: int | None = None
    for idx, flag in enumerate(flags.tolist() + [False]):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            if idx - start > best_end - best_start:
                best_start, best_end = start, idx
            start = None
    if best_end <= best_start:
        raise ValueError("could not find a board segment")
    return best_start, best_end


def estimate_geometry(
    image: np.ndarray,
    rows: int | None = None,
    cols: int | None = None,
    cell_size: int | None = None,
) -> tuple[BoardGeometry, np.ndarray]:
    background = corner_background(image)
    diff = np.linalg.norm(image.astype(int) - background.astype(int), axis=2)
    foreground = diff > 35

    h, w = image.shape[:2]
    row_threshold = max(350, int(w * 0.30))
    col_threshold = max(350, int(h * 0.30))
    y0, y1 = longest_true_segment(foreground.sum(axis=1) > row_threshold)
    x0, x1 = longest_true_segment(foreground.sum(axis=0) > col_threshold)

    board_w = x1 - x0
    board_h = y1 - y0

    if rows and cols:
        inferred_cell_w = board_w / cols
        inferred_cell_h = board_h / rows
        inferred_cell = int(round((inferred_cell_w + inferred_cell_h) / 2))
        if abs(inferred_cell_w - inferred_cell_h) > 2:
            raise ValueError("rows/cols do not describe square cells")
        return BoardGeometry(x0, y0, x1, y1, cell_size or inferred_cell, rows, cols), background

    if cell_size:
        cols = int(round(board_w / cell_size))
        rows = int(round(board_h / cell_size))
        return BoardGeometry(x0, y0, x1, y1, cell_size, rows, cols), background

    candidates: list[tuple[int, int, int, float]] = []
    for size in range(35, 141):
        candidate_cols = int(round(board_w / size))
        candidate_rows = int(round(board_h / size))
        if not (8 <= candidate_cols <= 20 and 8 <= candidate_rows <= 24):
            continue
        width_error = abs(board_w - candidate_cols * size)
        height_error = abs(board_h - candidate_rows * size)
        if width_error <= 2 and height_error <= 2:
            candidates.append((size, candidate_rows, candidate_cols, width_error + height_error))

    if not candidates:
        for size in range(35, 141):
            candidate_cols = int(round(board_w / size))
            candidate_rows = int(round(board_h / size))
            if 8 <= candidate_cols <= 20 and 8 <= candidate_rows <= 24:
                score = abs(board_w / size - candidate_cols) + abs(board_h / size - candidate_rows)
                candidates.append((size, candidate_rows, candidate_cols, score))

    if not candidates:
        raise ValueError(f"could not infer cell size from board {board_w}x{board_h}")

    size, rows, cols, _ = max(candidates, key=lambda item: item[0])
    return BoardGeometry(x0, y0, x0 + cols * size, y0 + rows * size, size, rows, cols), background


def digit_features(cell: np.ndarray) -> tuple[float, float, float, float, float, float] | None:
    arr = cell.astype(int)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    white = (r > 165) & (g > 165) & (b > 145) & ((r + g + b) > 500)
    ys, xs = np.where(white)
    if len(xs) == 0:
        return None

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    glyph = white[y0:y1, x0:x1]
    height, width = glyph.shape
    if height == 0 or width == 0:
        return None

    top = float(glyph[: height // 3, :].mean())
    middle = float(glyph[height // 3 : 2 * height // 3, :].mean())
    bottom = float(glyph[2 * height // 3 :, :].mean())
    left = float(glyph[:, : width // 3].mean())
    ratio = width / height
    area = float(glyph.mean())
    return ratio, area, top, middle, bottom, left


def classify_rebound_digit(cell: np.ndarray) -> int:
    features = digit_features(cell)
    if features is None:
        return 1
    ratio, _area, top, middle, bottom, left = features
    if ratio < 0.60:
        return 1
    if ratio > 0.88:
        return 4
    if middle < 0.42 and bottom > 0.68:
        return 2
    if middle > 0.52 and left > 0.48:
        return 5
    if bottom - top > 0.05 and middle < 0.45:
        return 2
    return 3


def classify_cell(cell: np.ndarray, background: np.ndarray) -> str:
    arr = cell.astype(int)
    h, w = arr.shape[:2]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    center = arr[int(0.30 * h) : int(0.70 * h), int(0.30 * w) : int(0.70 * w)]

    red = (r > 140) & (g < 120) & (b < 120) & (r > g + 35)
    center_red = (
        (center[:, :, 0] > 140)
        & (center[:, :, 1] < 120)
        & (center[:, :, 2] < 120)
        & (center[:, :, 0] > center[:, :, 1] + 35)
    )
    blue = (b > 110) & (g > 70) & (r < 80) & (b > r + 50)

    if blue.mean() > 0.30:
        return f"R{classify_rebound_digit(cell)}"
    if center_red.mean() > 0.40:
        return "P"
    if red.mean() > 0.10:
        return "G"

    center_distance = np.linalg.norm(center.mean(axis=(0, 1)) - background)
    if center_distance < 28:
        return "#"

    margin = max(4, int(min(h, w) * 0.14))
    ring = np.ones((h, w), dtype=bool)
    ring[margin : h - margin, margin : w - margin] = False
    luminance = arr.mean(axis=2)
    center_luminance = float(center.mean())
    ring_dark = ring & (luminance < center_luminance - 35) & (luminance > 60)
    if ring_dark.mean() > 0.035:
        return "S"

    return "."


def encode_array(
    image: np.ndarray,
    stage_id: str,
    optimal_moves: int | None,
    source_image: str | None = None,
    rows: int | None = None,
    cols: int | None = None,
    cell_size: int | None = None,
) -> dict[str, Any]:
    geometry, background = estimate_geometry(image, rows=rows, cols=cols, cell_size=cell_size)
    grid: list[list[str]] = []
    for row in range(geometry.rows):
        values: list[str] = []
        for col in range(geometry.cols):
            y0 = geometry.y0 + row * geometry.cell_size
            x0 = geometry.x0 + col * geometry.cell_size
            cell = image[y0 : y0 + geometry.cell_size, x0 : x0 + geometry.cell_size]
            values.append(classify_cell(cell, background))
        grid.append(values)

    stage = {
        "id": stage_id,
        "rows": geometry.rows,
        "cols": geometry.cols,
        "optimal_moves": optimal_moves,
        "source_image": source_image,
        "grid": grid,
        "metadata": {
            "encoder": "color-geometry-v1",
            "geometry": geometry.as_dict(),
            "background_rgb": [round(float(x), 2) for x in background.tolist()],
        },
    }
    validate_encoded_stage(stage)
    return stage


def encode_image(
    path: str | Path,
    rows: int | None = None,
    cols: int | None = None,
    cell_size: int | None = None,
) -> dict[str, Any]:
    stage_id, optimal_moves = parse_image_name(path)
    return encode_array(
        load_rgb(path),
        stage_id=stage_id,
        optimal_moves=optimal_moves,
        source_image=str(Path(path)),
        rows=rows,
        cols=cols,
        cell_size=cell_size,
    )


def encode_image_bytes(
    data: bytes,
    filename: str = "uploaded_stage.jpg",
    rows: int | None = None,
    cols: int | None = None,
    cell_size: int | None = None,
) -> dict[str, Any]:
    stage_id, optimal_moves = parse_image_name(filename)
    if not re.search(r"\w", stage_id):
        stage_id = "uploaded_stage"
    return encode_array(
        load_rgb_bytes(data),
        stage_id=stage_id,
        optimal_moves=optimal_moves,
        source_image=filename,
        rows=rows,
        cols=cols,
        cell_size=cell_size,
    )


def validate_encoded_stage(stage: dict[str, Any]) -> None:
    flat = [cell for row in stage["grid"] for cell in row]
    players = flat.count("P")
    goals = flat.count("G")
    if players != 1 or goals != 1:
        raise ValueError(f"encoded stage must have one P and one G, got P={players}, G={goals}")
    for token in flat:
        if token in {".", "#", "P", "G", "S"}:
            continue
        if token.startswith("R") and token[1:].isdigit():
            continue
        raise ValueError(f"unknown cell token: {token}")
