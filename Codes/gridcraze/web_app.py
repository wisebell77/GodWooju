from __future__ import annotations

import argparse
import gc
import html
import sys
import tracemalloc
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

warnings.filterwarnings("ignore", category=DeprecationWarning, module="cgi")
import cgi

from .image_encoder import encode_image_bytes
from .model import StageProblem
from .solver import bfs, ids


CELL_CLASSES = {
    ".": "empty",
    "#": "wall",
    "P": "player",
    "G": "goal",
    "S": "stop",
}


def page(content: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GridCraze Solver</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #202833;
      --muted: #64717f;
      --line: #d9dee5;
      --paper: #f7f8fa;
      --panel: #ffffff;
      --wall: #304052;
      --empty-a: #d4d4d2;
      --empty-b: #c4c6c8;
      --blue: #057aa4;
      --red: #c65047;
      --stop: #65727e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 28px;
      align-items: start;
    }}
    h1 {{ margin: 0 0 18px; font-size: 28px; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    form, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    label {{ display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }}
    input[type=file] {{ width: 100%; margin-bottom: 14px; }}
    button {{
      width: 100%;
      height: 40px;
      border: 0;
      border-radius: 6px;
      background: var(--ink);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }}
    .status {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-height: 64px;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 5px; font-size: 20px; }}
    .answer {{
      margin: 16px 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcfd;
    }}
    .answer span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }}
    .answer strong {{
      display: block;
      font-size: 30px;
      letter-spacing: 0;
      word-break: break-word;
    }}
    .comparison {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 14px;
    }}
    .comparison th,
    .comparison td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: right;
      white-space: nowrap;
    }}
    .comparison th:first-child,
    .comparison td:first-child {{
      text-align: left;
    }}
    .comparison th {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .board-wrap {{ overflow: auto; }}
    table.board {{ border-collapse: collapse; background: var(--wall); }}
    .board td {{
      width: 34px;
      height: 34px;
      min-width: 34px;
      text-align: center;
      vertical-align: middle;
      font-weight: 800;
      color: #ece8dd;
      border: 1px solid rgba(255, 255, 255, 0.05);
      position: relative;
    }}
    .empty {{ background: var(--empty-a); color: transparent; }}
    .empty.alt {{ background: var(--empty-b); }}
    .wall {{ background: var(--wall); color: transparent; }}
    .rebound {{ background: var(--blue); }}
    .goal {{ background: var(--red); color: transparent; }}
    .player {{ background: var(--empty-a); color: transparent; box-shadow: inset 0 0 0 5px var(--red); }}
    .stop {{ background: var(--empty-a); color: transparent; box-shadow: inset 0 0 0 5px var(--stop); }}
    pre {{
      white-space: pre-wrap;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fbfcfd;
      overflow: auto;
    }}
    .error {{ border-color: #d96b63; color: #9f312b; }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; padding: 18px; }}
      .status {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .comparison th,
      .comparison td {{ padding: 8px 6px; font-size: 12px; }}
    }}
  </style>
</head>
<body>
<main>
  <div>
    <h1>GridCraze Solver</h1>
    <form method="post" action="/solve" enctype="multipart/form-data">
      <label for="stage">Stage screenshot</label>
      <input id="stage" name="stage" type="file" accept="image/*" required>
      <button type="submit">Solve</button>
    </form>
  </div>
  {content}
</main>
</body>
</html>""".encode("utf-8")


def render_board(problem: StageProblem) -> str:
    grid = problem.to_dict(include_player=True)["grid"]
    rows: list[str] = []
    for r, row in enumerate(grid):
        cells: list[str] = []
        for c, token in enumerate(row):
            cls = CELL_CLASSES.get(token, "rebound")
            if token == "." and (r + c) % 2:
                cls += " alt"
            text = html.escape(token[1:] if token.startswith("R") else token)
            cells.append(f'<td class="{cls}">{text}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return '<div class="board-wrap"><table class="board">' + "".join(rows) + "</table></div>"


def run_with_peak_memory(solver_func):
    gc.collect()
    tracemalloc.start()
    try:
        result = solver_func()
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak / 1024


def format_moves(moves: list[str]) -> str:
    return " ".join(moves) if moves else "-"


def render_comparison_rows(rows: list[tuple[str, object, float]]) -> str:
    html_rows: list[str] = []
    for name, result, peak_kib in rows:
        move_count = result.move_count if result.move_count is not None else "-"
        html_rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{html.escape(str(move_count))}</td>"
            f"<td>{html.escape(format_moves(result.moves))}</td>"
            f"<td>{result.runtime_ms:.3f}</td>"
            f"<td>{peak_kib:.1f}</td>"
            f"<td>{result.expanded_states}</td>"
            f"<td>{result.visited_states}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def render_solution(stage: dict) -> str:
    problem = StageProblem.from_dict(stage)
    bfs_result, bfs_memory = run_with_peak_memory(lambda: bfs(problem))
    ids_result, ids_memory = run_with_peak_memory(
        lambda: ids(problem, max_depth=bfs_result.move_count or None)
    )
    match = "-"
    if problem.optimal_moves is not None and bfs_result.move_count is not None:
        match = "yes" if problem.optimal_moves == bfs_result.move_count else "no"
    answer = format_moves(bfs_result.moves) if bfs_result.solved else "No solution"

    metrics = [
        ("Stage", problem.stage_id),
        ("BFS moves", str(bfs_result.move_count) if bfs_result.solved else "-"),
        ("Game optimal", str(problem.optimal_moves) if problem.optimal_moves is not None else "-"),
        ("Match", match),
    ]
    metric_html = "".join(
        f'<div class="metric"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in metrics
    )
    comparison_rows = render_comparison_rows(
        [("BFS", bfs_result, bfs_memory), ("IDS", ids_result, ids_memory)]
    )
    return f"""
<section>
  <div class="status">{metric_html}</div>
  <div class="answer">
    <span>Optimal move sequence</span>
    <strong>{html.escape(answer)}</strong>
  </div>
  {render_board(problem)}
  <h2>Algorithm Comparison</h2>
  <table class="comparison">
    <thead>
      <tr>
        <th>Algorithm</th>
        <th>Moves</th>
        <th>Sequence</th>
        <th>Time (ms)</th>
        <th>Peak Memory (KiB)</th>
        <th>Expanded</th>
        <th>Visited</th>
      </tr>
    </thead>
    <tbody>{comparison_rows}</tbody>
  </table>
</section>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "GridCrazeHTTP/1.0"

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/":
            self.send_error(404)
            return
        self.respond(page("<section><h2>Ready</h2><pre>Upload a stage screenshot.</pre></section>"))

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/solve":
            self.send_error(404)
            return
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )
            item = form["stage"]
            filename = item.filename or "uploaded_stage.jpg"
            data = item.file.read()
            stage = encode_image_bytes(data, filename=filename)
            self.respond(page(render_solution(stage)))
        except Exception as exc:
            message = html.escape(str(exc))
            self.respond(page(f'<section class="error"><h2>Error</h2><pre>{message}</pre></section>'), status=400)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(fmt % args + "\n")

    def respond(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
