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

Notes
-----

The image encoder is color and geometry based. For the provided screenshots,
this is more reliable than calling a text-oriented OCR or multimodal API:
the game has a fixed grid, stable colors, and large numeric rebound blocks.

The encoder assumes screenshots use the same visual style as the provided
samples. If the game theme, colors, rotation, or crop changes significantly,
the image may need manual checking or encoder tuning.
