from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json


Grid = list[list[str]]
Position = tuple[int, int]


@dataclass(frozen=True)
class StageProblem:
    stage_id: str
    rows: int
    cols: int
    grid: Grid
    start: Position
    goal: Position
    optimal_moves: int | None = None
    source_image: str | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageProblem":
        rows = int(data["rows"])
        cols = int(data["cols"])
        grid = [[str(cell) for cell in row] for row in data["grid"]]
        if len(grid) != rows or any(len(row) != cols for row in grid):
            raise ValueError("grid shape does not match rows/cols")

        starts: list[Position] = []
        goals: list[Position] = []
        static_grid: Grid = []
        for r, row in enumerate(grid):
            static_row: list[str] = []
            for c, token in enumerate(row):
                if token == "P":
                    starts.append((r, c))
                    static_row.append(".")
                elif token == "G":
                    goals.append((r, c))
                    static_row.append("G")
                else:
                    static_row.append(token)
            static_grid.append(static_row)

        if len(starts) != 1:
            raise ValueError(f"expected exactly one P cell, found {len(starts)}")
        if len(goals) != 1:
            raise ValueError(f"expected exactly one G cell, found {len(goals)}")

        return cls(
            stage_id=str(data.get("id", "unnamed_stage")),
            rows=rows,
            cols=cols,
            grid=static_grid,
            start=starts[0],
            goal=goals[0],
            optimal_moves=data.get("optimal_moves"),
            source_image=data.get("source_image"),
            metadata=data.get("metadata"),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "StageProblem":
        with Path(path).open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def tile_at(self, pos: Position) -> str:
        r, c = pos
        if r < 0 or c < 0 or r >= self.rows or c >= self.cols:
            return "#"
        return self.grid[r][c]

    def is_goal(self, pos: Position) -> bool:
        return pos == self.goal

    def to_dict(self, include_player: bool = True) -> dict[str, Any]:
        grid = [row[:] for row in self.grid]
        if include_player:
            sr, sc = self.start
            grid[sr][sc] = "P"
        return {
            "id": self.stage_id,
            "rows": self.rows,
            "cols": self.cols,
            "optimal_moves": self.optimal_moves,
            "source_image": self.source_image,
            "grid": grid,
            "metadata": self.metadata or {},
        }


def dump_stage(data: dict[str, Any], path: str | Path, pretty: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def iter_stage_files(path: str | Path) -> Iterable[Path]:
    path = Path(path)
    if path.is_file():
        yield path
        return
    yield from sorted(path.glob("*.json"))
