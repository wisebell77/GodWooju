from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import perf_counter

from .model import Position, StageProblem


DIRECTIONS: dict[str, Position] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    solved: bool
    moves: list[str]
    expanded_states: int
    generated_states: int
    visited_states: int
    runtime_ms: float
    final_state: Position | None = None
    depth_limit: int | None = None

    @property
    def move_count(self) -> int | None:
        return len(self.moves) if self.solved else None


def rebound_distance(tile: str) -> int | None:
    if len(tile) >= 2 and tile[0] == "R" and tile[1:].isdigit():
        return int(tile[1:])
    return None


def slide(problem: StageProblem, state: Position, action: str) -> Position:
    """Apply one GridCraze slide action and return the final player position."""
    if action not in DIRECTIONS:
        raise ValueError(f"unknown action: {action}")

    direction = DIRECTIONS[action]
    pos = state
    forced_steps: int | None = None
    forced_taken = 0
    interaction_limit = max(16, problem.rows * problem.cols * 4)
    interactions = 0

    while True:
        if forced_steps is not None and forced_taken >= forced_steps:
            return pos

        dr, dc = direction
        nxt = (pos[0] + dr, pos[1] + dc)
        tile = problem.tile_at(nxt)

        if tile == "#":
            return pos
        if tile == "G":
            return nxt
        if tile == "S":
            return nxt

        distance = rebound_distance(tile)
        if distance is not None:
            interactions += 1
            if interactions > interaction_limit:
                return pos
            direction = (-dr, -dc)
            forced_steps = distance
            forced_taken = 0
            continue

        pos = nxt
        if forced_steps is not None:
            forced_taken += 1


def reconstruct_path(
    parent: dict[Position, tuple[Position | None, str | None]], goal: Position
) -> list[str]:
    moves: list[str] = []
    cur = goal
    while True:
        prev, move = parent[cur]
        if prev is None:
            break
        moves.append(move or "")
        cur = prev
    moves.reverse()
    return moves


def bfs(problem: StageProblem) -> SearchResult:
    started = perf_counter()
    queue: deque[Position] = deque([problem.start])
    parent: dict[Position, tuple[Position | None, str | None]] = {
        problem.start: (None, None)
    }
    expanded = 0
    generated = 0

    while queue:
        state = queue.popleft()
        expanded += 1
        if problem.is_goal(state):
            elapsed = (perf_counter() - started) * 1000
            return SearchResult(
                algorithm="bfs",
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
                queue.append(nxt)

    elapsed = (perf_counter() - started) * 1000
    return SearchResult(
        algorithm="bfs",
        solved=False,
        moves=[],
        expanded_states=expanded,
        generated_states=generated,
        visited_states=len(parent),
        runtime_ms=elapsed,
    )


def ids(problem: StageProblem, max_depth: int | None = None) -> SearchResult:
    if max_depth is None:
        max_depth = problem.optimal_moves or (problem.rows * problem.cols)

    started = perf_counter()
    total_expanded = 0
    total_generated = 0
    last_seen = 1

    for depth_limit in range(max_depth + 1):
        best_depth: dict[Position, int] = {}
        path: list[str] = []
        found: list[str] | None = None
        final_state: Position | None = None
        expanded = 0
        generated = 0

        def dfs(state: Position, depth: int) -> bool:
            nonlocal expanded, generated, found, final_state
            expanded += 1
            if problem.is_goal(state):
                found = path[:]
                final_state = state
                return True
            if depth == depth_limit:
                return False

            previous_best = best_depth.get(state)
            if previous_best is not None and previous_best <= depth:
                return False
            best_depth[state] = depth

            for action in DIRECTIONS:
                nxt = slide(problem, state, action)
                if nxt == state:
                    continue
                generated += 1
                path.append(action)
                if dfs(nxt, depth + 1):
                    return True
                path.pop()
            return False

        if dfs(problem.start, 0):
            elapsed = (perf_counter() - started) * 1000
            return SearchResult(
                algorithm="ids",
                solved=True,
                moves=found or [],
                expanded_states=total_expanded + expanded,
                generated_states=total_generated + generated,
                visited_states=len(best_depth),
                runtime_ms=elapsed,
                final_state=final_state,
                depth_limit=depth_limit,
            )

        total_expanded += expanded
        total_generated += generated
        last_seen = max(last_seen, len(best_depth))

    elapsed = (perf_counter() - started) * 1000
    return SearchResult(
        algorithm="ids",
        solved=False,
        moves=[],
        expanded_states=total_expanded,
        generated_states=total_generated,
        visited_states=last_seen,
        runtime_ms=elapsed,
        depth_limit=max_depth,
    )
