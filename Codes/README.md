GridCraze Solver
================

This project converts GridCraze stage screenshots into symbolic boards and
solves them with state-space search.

The implementation follows the idea report:

- screenshots are converted into a symbolic JSON board
- board cells use `P`, `G`, `#`, `S`, `.`, and `Rn`
- BFS is the main optimal solver because every slide costs 1 move
- IDS is included as a comparison baseline
- the web UI uploads a screenshot, extracts the board, prints the answer
  sequence, and compares BFS/IDS runtime, peak memory, and explored states

Project Structure
-----------------

```text
Codes/
  gridcraze/
    image_encoder.py   # screenshot -> symbolic board
    solver.py          # slide transition rules, BFS, IDS
    cli.py             # command-line encoder/evaluator
    web_app.py         # local upload UI
  data/stages/         # encoded sample stages
  tests/               # regression tests for sample stages
  requirements.txt
```

Setup
-----

Run commands from the `Codes` folder.

```powershell
cd Project\Codes
pip install -r requirements.txt
```

The code requires Python 3.10+ and uses only `numpy` and `Pillow` as external
packages.

Image Filename Rule
-------------------

For best UI output, name screenshots like this:

```text
Stage.Name_OptimalMoveCount.jpg
```

Example:

```text
Normal.2.B_6.jpg
```

The UI reads `Normal.2.B` as the stage id and `6` as the game-provided optimal
move count. If the filename has no `_number` suffix, the solver still runs, but
the game optimal comparison is shown as unavailable.

Important: the UI does not look up an existing JSON file. It converts the
uploaded image bytes directly into a board every time.

Command-Line Usage
------------------

Convert all screenshots in `../Images`:

```powershell
python -m gridcraze.cli encode-dir ..\Images --out data\stages
```

Solve one encoded stage with BFS:

```powershell
python -m gridcraze.cli solve data\stages\Normal.2.B.json --algorithm bfs
```

Compare BFS and IDS on all encoded stages:

```powershell
python -m gridcraze.cli evaluate data\stages --algorithm both
```

Web UI
------

Start the local UI:

```powershell
python -m gridcraze.web_app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

Upload a GridCraze screenshot. The result page shows:

- optimal move sequence, e.g. `R D R U L U`
- game optimal move count if available from the filename
- BFS vs IDS comparison table
- runtime in milliseconds
- peak memory in KiB, measured with Python `tracemalloc`
- expanded and visited state counts

Tests
-----

Run the regression tests:

```powershell
python -m unittest discover -s tests
```

The included tests verify that BFS matches the game optimal move count for the
provided sample stages and that IDS finds the same optimal depth.

Benchmark
---------

Run the full benchmark from the `Codes` folder:

```powershell
python -m gridcraze.benchmark --images ..\Images --out results\benchmark --trials 5
```

The benchmark reads all screenshots under `Images`, encodes each image, and
measures BFS/DFS/IDS performance. DFS is included as a non-optimal baseline, so
check the matched-optimal count before interpreting it as a solver. The
benchmark also includes optimal-bound variants:

- `BFS(bound)`: BFS with a depth cutoff equal to the known optimal move count
- `IDS(bound)`: IDS capped at the known optimal move count
- `DLS(bound)`: depth-limited DFS capped at the known optimal move count

Generated outputs:

- `results/benchmark/raw_results.csv`
- `results/benchmark/stage_summary.csv`
- `results/benchmark/overall_summary.csv`
- `results/benchmark/optimal_length_counts.csv`
- `results/benchmark/optimal_length_summary.csv`
- `results/benchmark/range_summary_5.csv`
- `results/benchmark/range_summary_10.csv`
- `results/benchmark/summary.json`
- `results/benchmark/report.md`
- `results/benchmark/plots/*.png`, including exact optimal-length line and
  grouped-bar charts
- `results/benchmark/exact_optimal_length/`
- `results/benchmark/range_5/`
- `results/benchmark/range_10/`

The separated analysis folders contain:

- `counts.csv`
- `summary.csv`
- `marginal_rate_summary.csv`
- `plots/value_*.png`
- `plots/mr_*.png`

The marginal-rate charts use adjacent observed x-axis categories only. If the
next observed category is `j` moves away, the marginal rate is calculated as
`(next_value - current_value) / j`.

Notes
-----

The image encoder is color and geometry based. For the provided screenshots,
this is more reliable than calling a text-oriented OCR or multimodal API:
the game has a fixed grid, stable colors, and large numeric rebound blocks.

The encoder assumes screenshots use the same visual style as the provided
samples. If the game theme, colors, rotation, or crop changes significantly,
the image may need manual checking or encoder tuning.
