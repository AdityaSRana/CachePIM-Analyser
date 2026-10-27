# CachePIM Correction and Results Report

**Artifact version:** `1.1.0-lambda-0`  
**Status:** Corrected local repository and regenerated analytical simulation artifacts. These changes have **not** been pushed to the public GitHub repository.  
**Scope:** Software-only analytical simulation using deterministic synthetic workloads. No physical CPU/PIM hardware was measured, and timings are not calibrated hardware latency.

## Corrections completed

1. Separated experiment outputs so development tuning, held-out evaluation, and sensitivity sweeps do not overwrite one another.
2. Aggregated metrics within each master seed before computing across-seed means and sample standard deviations. Paired comparisons use master-seed means.
3. Corrected explicit PIM input/output footprints for vector operations, reduction, and filter; output transfer is charged when the output footprint is nonzero.
4. Connected the configured internal PIM-memory bandwidth to the analytical latency calculation.
5. Connected synthetic skew to deterministic bank-work distribution and reported imbalance.
6. Added explicit development-only selection of the reuse penalty, frozen evaluation on held-out seeds, and made the reuse threshold active in the policy.
7. Made sweep grids configuration-driven and added a PIM bank-count sweep.
8. Changed crossover heatmap generation to read saved experiment CSVs rather than silently rerun a second simulation.
9. Added regression tests and updated documentation / provenance.

## Verification

- Test command: `python -m pytest -q`
- Result: **24 passed**
- Full experimental runner: exited successfully (exit code 0).
- Held-out master seeds: 47–51 (five seeds).
- Development master seeds: 42–46 (five seeds).
- Held-out traces: five traces for each combination of four workload patterns and five working-set sizes, yielding **100 trace cases** and **600 policy/trace rows** across six policies.
- Lambda selected from development data: **0.0**.

## Main held-out results

Mean modeled latency is calculated by first averaging traces within each master seed, then reporting the mean and sample standard deviation across the five held-out master-seed means.

| Policy | Mean modeled latency (µs) | Sample SD (µs) |
|---|---:|---:|
| CPU-cache | 132.215 | 0.159 |
| CPU-no-cache | 633.938 | 0.000 |
| PIM-always | 22.190 | 0.000 |
| Cost-based | 22.190 | 0.000 |
| Reuse-aware | 22.190 | 0.000 |
| Oracle | 22.190 | 0.000 |

The ratio of overall mean CPU-cache time to PIM-selecting policy time is approximately **5.96×** under the current configuration and workload mix. It is a ratio of analytical model outputs, not a hardware speedup claim. The zero SD for PIM-path strategies reflects deterministic cost equations and the fact that those strategies all choose the same PIM path in this configuration; it must not be interpreted as hardware performance stability.

### Mean latency by workload pattern

| Workload | CPU-cache mean ± SD (µs) | PIM mean ± SD (µs) | Ratio of means |
|---|---:|---:|---:|
| MIXED_PHASE | 87.009 ± 0.295 | 21.825 ± 0.000 | 3.99× |
| RANDOM | 88.556 ± 0.277 | 21.825 ± 0.000 | 4.06× |
| REUSE | 56.723 ± 0.625 | 21.825 ± 0.000 | 2.60× |
| STREAM | 296.571 ± 0.000 | 23.284 ± 0.000 | 12.74× |

Average CPU-cache hit rates by workload under the held-out setup were approximately 48.61% for MIXED_PHASE, 47.64% for RANDOM, 67.57% for REUSE, and 90.00% for STREAM. The high streaming hit rate in this model is compatible with spatial locality (multiple accesses within an already fetched line) and should not be interpreted as evidence of temporal reuse.

## Important negative finding

The development-only selection chooses reuse penalty `λ = 0`. Positive weights increase normalized regret in the development sweep. Therefore, the reuse-aware policy collapses to the cost-based rule under these default assumptions, and it does **not** demonstrate an improvement over cost-based selection in the held-out evaluation. The paper must not claim otherwise.

The default parameters strongly favor PIM. The crossover region is visible in explicit transfer-bandwidth/capacity sensitivity sweeps. Most sensitivity sweeps currently use a single fixed development seed and are therefore **descriptive only**. They do not support population-level or multi-seed inferential claims.

## Known limitations and what remains

- Default timing and bandwidth values are illustrative assumptions, not calibrated to a named CPU, memory system, interconnect, or PIM device.
- The cache model is a fully associative, single-level LRU last-level cache abstraction; it excludes detailed multi-level hierarchy, prefetching, out-of-order execution, MSHRs, and coherence protocols.
- The PIM timing model adds internal-memory service and computation serially and is not cycle-accurate.
- Workloads are synthetic traces, not traces collected from real applications or hardware.
- The reuse-aware candidate did not improve performance under the current model; a stronger research contribution would require revising the hypothesis only after defensible new experiments.
- Crossover, bank-count, bank-skew, and other sensitivity sweeps need multiple seeds before making strong claims about variability.
- The corrected local artifact has not yet been pushed to GitHub. The manuscript's public release/commit identifier needs updating after the corrected repository is published.
- The manuscript still needs confirmation of which author is the corresponding author.

## Reproduction

From the repository root:

```bash
python -m pytest -q
python -m cachepim.experiments --config config/experiment.yaml --output-dir results_reproduction
python -c "from cachepim.plots import generate_all_plots; generate_all_plots('results_reproduction')"
```

Run the reproduction command into a fresh output directory to preserve existing results. Raw CSVs, summaries, configuration snapshots, figures (PNG and PDF), the manifest, the original-result snapshot, and a more detailed correction audit are included in the source archive.
