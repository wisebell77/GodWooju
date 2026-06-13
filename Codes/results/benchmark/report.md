# GridCraze Benchmark Report

- Stages: 320
- Trials per stage/algorithm: 5
- Runtime: algorithm execution only, measured in milliseconds
- Peak memory: Python `tracemalloc` peak allocation during the algorithm call

## Winners

- Least memory, standard search: DFS
- Fastest, standard search: DFS
- Least memory, standard search with full optimal match: IDS
- Fastest, standard search with full optimal match: BFS
- Least memory, optimal-bound search: IDS(bound)
- Fastest, optimal-bound search: BFS(bound)

Note: DFS is included as a non-optimal baseline. It can be fast and memory-light,
but it does not guarantee a minimum-move solution. Check the `Matched` column before
using it as an optimal solver.

## Overall Summary

| Phase | Algorithm | Mean Time (ms) | Mean Peak Memory (KiB) | Mean Expanded | Solved | Matched |
|---|---:|---:|---:|---:|---:|---:|
| optimal_bound | BFS(bound) | 1.3526 | 9.42 | 48.92 | 1600 | 1600 |
| optimal_bound | DLS(bound) | 4.5981 | 10.40 | 394.24 | 1600 | 1600 |
| optimal_bound | IDS(bound) | 36.5239 | 7.63 | 3035.62 | 1600 | 1600 |
| standard | BFS | 1.4199 | 9.35 | 48.92 | 1600 | 1600 |
| standard | DFS | 1.0365 | 7.36 | 33.84 | 1600 | 470 |
| standard | IDS | 36.9766 | 7.63 | 3035.62 | 1600 | 1600 |

## Graphs

- `results/benchmark/plots/overall_standard_runtime.png`
- `results/benchmark/plots/overall_standard_memory.png`
- `results/benchmark/plots/overall_optimal_bound_runtime.png`
- `results/benchmark/plots/overall_optimal_bound_memory.png`
- `results/benchmark/plots/range5_standard_runtime.png`
- `results/benchmark/plots/range5_standard_memory.png`
- `results/benchmark/plots/range5_optimal_bound_runtime.png`
- `results/benchmark/plots/range5_optimal_bound_memory.png`
- `results/benchmark/plots/range10_standard_runtime.png`
- `results/benchmark/plots/range10_standard_memory.png`
- `results/benchmark/plots/range10_optimal_bound_runtime.png`
- `results/benchmark/plots/range10_optimal_bound_memory.png`
- `results/benchmark/plots/optimal_length_standard_runtime_line.png`
- `results/benchmark/plots/optimal_length_standard_runtime_grouped_bar.png`
- `results/benchmark/plots/optimal_length_standard_memory_line.png`
- `results/benchmark/plots/optimal_length_standard_memory_grouped_bar.png`
- `results/benchmark/plots/optimal_length_optimal_bound_runtime_line.png`
- `results/benchmark/plots/optimal_length_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/plots/optimal_length_optimal_bound_memory_line.png`
- `results/benchmark/plots/optimal_length_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/value_standard_runtime_line.png`
- `results/benchmark/exact_optimal_length/plots/value_standard_runtime_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/value_standard_memory_line.png`
- `results/benchmark/exact_optimal_length/plots/value_standard_memory_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/mr_standard_runtime_line.png`
- `results/benchmark/exact_optimal_length/plots/mr_standard_runtime_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/mr_standard_memory_line.png`
- `results/benchmark/exact_optimal_length/plots/mr_standard_memory_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/value_optimal_bound_runtime_line.png`
- `results/benchmark/exact_optimal_length/plots/value_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/value_optimal_bound_memory_line.png`
- `results/benchmark/exact_optimal_length/plots/value_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/mr_optimal_bound_runtime_line.png`
- `results/benchmark/exact_optimal_length/plots/mr_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/exact_optimal_length/plots/mr_optimal_bound_memory_line.png`
- `results/benchmark/exact_optimal_length/plots/mr_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/range_5/plots/value_standard_runtime_line.png`
- `results/benchmark/range_5/plots/value_standard_runtime_grouped_bar.png`
- `results/benchmark/range_5/plots/value_standard_memory_line.png`
- `results/benchmark/range_5/plots/value_standard_memory_grouped_bar.png`
- `results/benchmark/range_5/plots/mr_standard_runtime_line.png`
- `results/benchmark/range_5/plots/mr_standard_runtime_grouped_bar.png`
- `results/benchmark/range_5/plots/mr_standard_memory_line.png`
- `results/benchmark/range_5/plots/mr_standard_memory_grouped_bar.png`
- `results/benchmark/range_5/plots/value_optimal_bound_runtime_line.png`
- `results/benchmark/range_5/plots/value_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/range_5/plots/value_optimal_bound_memory_line.png`
- `results/benchmark/range_5/plots/value_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/range_5/plots/mr_optimal_bound_runtime_line.png`
- `results/benchmark/range_5/plots/mr_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/range_5/plots/mr_optimal_bound_memory_line.png`
- `results/benchmark/range_5/plots/mr_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/range_10/plots/value_standard_runtime_line.png`
- `results/benchmark/range_10/plots/value_standard_runtime_grouped_bar.png`
- `results/benchmark/range_10/plots/value_standard_memory_line.png`
- `results/benchmark/range_10/plots/value_standard_memory_grouped_bar.png`
- `results/benchmark/range_10/plots/mr_standard_runtime_line.png`
- `results/benchmark/range_10/plots/mr_standard_runtime_grouped_bar.png`
- `results/benchmark/range_10/plots/mr_standard_memory_line.png`
- `results/benchmark/range_10/plots/mr_standard_memory_grouped_bar.png`
- `results/benchmark/range_10/plots/value_optimal_bound_runtime_line.png`
- `results/benchmark/range_10/plots/value_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/range_10/plots/value_optimal_bound_memory_line.png`
- `results/benchmark/range_10/plots/value_optimal_bound_memory_grouped_bar.png`
- `results/benchmark/range_10/plots/mr_optimal_bound_runtime_line.png`
- `results/benchmark/range_10/plots/mr_optimal_bound_runtime_grouped_bar.png`
- `results/benchmark/range_10/plots/mr_optimal_bound_memory_line.png`
- `results/benchmark/range_10/plots/mr_optimal_bound_memory_grouped_bar.png`
