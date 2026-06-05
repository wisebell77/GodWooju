GridCraze Solver
================

This repository contains a GridCraze screenshot encoder and optimal solver.

The solver converts a GridCraze stage screenshot into a symbolic board, then
computes the minimum-move solution with BFS. IDS is also included for comparison
of runtime, memory usage, and explored states.

Repository Structure
--------------------

```text
Project/
  Codes/    # Python source code, CLI, web UI, tests, encoded sample stages
  Images/   # sample GridCraze screenshots
```

Quick Start
-----------

Run all commands from the `Codes` folder.

```powershell
cd Codes
pip install -r requirements.txt
```

Start the local upload UI:

```powershell
python -m gridcraze.web_app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

Upload a GridCraze screenshot. The UI will:

- convert the screenshot into a symbolic board
- show the optimal move sequence, e.g. `R D R U L U`
- compare BFS and IDS by runtime, peak memory, and explored states

Image Filename Rule
-------------------

For best output, name screenshots like this:

```text
Stage.Name_OptimalMoveCount.jpg
```

Example:

```text
Normal.2.B_6.jpg
```

The `_6` suffix is used as the game-provided optimal move count for comparison.
The board itself is still extracted from the uploaded image pixels.

Command-Line Usage
------------------

Convert all sample screenshots:

```powershell
python -m gridcraze.cli encode-dir ..\Images --out data\stages
```

Evaluate BFS and IDS:

```powershell
python -m gridcraze.cli evaluate data\stages --algorithm both
```

Run tests:

```powershell
python -m unittest discover -s tests
```

More Details
------------

See `Codes/README.md` for the detailed implementation notes and CLI examples.
