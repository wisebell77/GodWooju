from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from .image_encoder import encode_image
from .model import StageProblem, dump_stage, iter_stage_files
from .solver import SearchResult, bfs, ids


def solve_with(problem: StageProblem, algorithm: str) -> SearchResult:
    if algorithm == "bfs":
        return bfs(problem)
    if algorithm == "ids":
        return ids(problem)
    raise ValueError(f"unknown algorithm: {algorithm}")


def render_grid(problem: StageProblem) -> str:
    data = problem.to_dict(include_player=True)["grid"]
    width = max(len(cell) for row in data for cell in row)
    return "\n".join(" ".join(cell.rjust(width) for cell in row) for row in data)


def print_result(stage_id: str, optimal: int | None, result: SearchResult) -> None:
    match = ""
    if optimal is not None and result.solved:
        match = "yes" if optimal == result.move_count else "no"
    print(
        "\t".join(
            [
                stage_id,
                result.algorithm,
                str(optimal) if optimal is not None else "-",
                str(result.move_count) if result.move_count is not None else "-",
                match or "-",
                " ".join(result.moves) if result.moves else "-",
                str(result.expanded_states),
                str(result.generated_states),
                f"{result.runtime_ms:.3f}",
            ]
        )
    )


def command_encode_image(args: argparse.Namespace) -> None:
    stage = encode_image(args.image, rows=args.rows, cols=args.cols, cell_size=args.cell_size)
    out = Path(args.out)
    if out.suffix.lower() != ".json":
        out.mkdir(parents=True, exist_ok=True)
        out = out / f"{stage['id']}.json"
    dump_stage(stage, out, pretty=not args.compact)
    print(out)


def command_encode_dir(args: argparse.Namespace) -> None:
    image_dir = Path(args.image_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = [path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in extensions]
    for image in images:
        stage = encode_image(image, rows=args.rows, cols=args.cols, cell_size=args.cell_size)
        out = out_dir / f"{stage['id']}.json"
        dump_stage(stage, out, pretty=not args.compact)
        print(out)


def command_solve(args: argparse.Namespace) -> None:
    problem = StageProblem.from_json(args.stage)
    if args.show_grid:
        print(render_grid(problem))
    result = solve_with(problem, args.algorithm)
    print("stage\talgorithm\toptimal\tsolver\tmatch\tmoves\texpanded\tgenerated\truntime_ms")
    print_result(problem.stage_id, problem.optimal_moves, result)


def command_evaluate(args: argparse.Namespace) -> None:
    algorithms: Iterable[str]
    algorithms = ["bfs", "ids"] if args.algorithm == "both" else [args.algorithm]
    print("stage\talgorithm\toptimal\tsolver\tmatch\tmoves\texpanded\tgenerated\truntime_ms")
    for stage_file in iter_stage_files(args.stages):
        problem = StageProblem.from_json(stage_file)
        for algorithm in algorithms:
            print_result(problem.stage_id, problem.optimal_moves, solve_with(problem, algorithm))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gridcraze")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_one = subparsers.add_parser("encode-image")
    encode_one.add_argument("image")
    encode_one.add_argument("--out", required=True)
    encode_one.add_argument("--rows", type=int)
    encode_one.add_argument("--cols", type=int)
    encode_one.add_argument("--cell-size", type=int)
    encode_one.add_argument("--compact", action="store_true")
    encode_one.set_defaults(func=command_encode_image)

    encode_dir = subparsers.add_parser("encode-dir")
    encode_dir.add_argument("image_dir")
    encode_dir.add_argument("--out", required=True)
    encode_dir.add_argument("--rows", type=int)
    encode_dir.add_argument("--cols", type=int)
    encode_dir.add_argument("--cell-size", type=int)
    encode_dir.add_argument("--compact", action="store_true")
    encode_dir.set_defaults(func=command_encode_dir)

    solve_parser = subparsers.add_parser("solve")
    solve_parser.add_argument("stage")
    solve_parser.add_argument("--algorithm", choices=["bfs", "ids"], default="bfs")
    solve_parser.add_argument("--show-grid", action="store_true")
    solve_parser.set_defaults(func=command_solve)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("stages")
    evaluate.add_argument("--algorithm", choices=["bfs", "ids", "both"], default="bfs")
    evaluate.set_defaults(func=command_evaluate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
