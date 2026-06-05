from __future__ import annotations

from pathlib import Path
import unittest

from gridcraze.model import StageProblem
from gridcraze.solver import bfs, ids


ROOT = Path(__file__).resolve().parents[1]
STAGES = ROOT / "data" / "stages"


class SampleStageTests(unittest.TestCase):
    def test_bfs_matches_game_optimal_moves(self) -> None:
        for stage_file in sorted(STAGES.glob("*.json")):
            with self.subTest(stage=stage_file.name):
                problem = StageProblem.from_json(stage_file)
                result = bfs(problem)
                self.assertTrue(result.solved)
                self.assertEqual(problem.optimal_moves, result.move_count)

    def test_ids_matches_bfs_move_count(self) -> None:
        for stage_file in sorted(STAGES.glob("*.json")):
            with self.subTest(stage=stage_file.name):
                problem = StageProblem.from_json(stage_file)
                bfs_result = bfs(problem)
                ids_result = ids(problem, max_depth=bfs_result.move_count)
                self.assertTrue(ids_result.solved)
                self.assertEqual(bfs_result.move_count, ids_result.move_count)


if __name__ == "__main__":
    unittest.main()
