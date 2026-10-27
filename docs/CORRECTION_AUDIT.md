# CachePIM Correction Audit

**Audited artifact version:** `1.1.0-lambda-0`  
**Result classification:** analytical estimates from the simulator on deterministic synthetic traces; not physical-hardware measurements.  
**Automated tests:** `python -m pytest -q` — 24 passed in the verified run.

## Corrections implemented

1. **Output isolation.** Tuning, held-out evaluation, individual sweeps, summaries, and configuration snapshots use distinct output names/directories. The full suite writes to a chosen result directory. The original uploaded output is preserved as `results_original_snapshot/` and is not used as the current result source.
2. **Master-seed statistics.** Trace-level outcomes are averaged within each master seed before the across-seed mean, sample standard deviation, and confidence interval are calculated. Paired policy comparisons use the same master-seed aggregation unit.
3. **PIM workload footprints.** Vector operations now declare two input arrays and an output array; reduction declares its input and scalar result; filter declares input and a conservative full-output footprint. PIM output movement is charged when the descriptor has positive output bytes.
4. **Internal PIM memory service.** Effective PIM internal bandwidth now contributes to the time equation as a separate term; the model explicitly treats internal memory service and arithmetic service serially.
5. **Bank imbalance.** The configured skew factor affects deterministic operation distribution across banks. Total operations remain conserved, and the computed imbalance is reported.
6. **Reuse parameter evaluation.** `lambda` is selected using development master seeds 42–46 and then frozen for held-out master seeds 47–51. The reuse threshold gates whether the reuse penalty applies. The current selected value is `lambda = 0.0`, so the reuse-aware policy collapses to the cost-only decision rule under the current model.
7. **Configured sweep dimensions.** Sweep definitions are loaded from YAML configuration. A PIM bank-count sweep is implemented as a distinct stage. Raw files contain configuration hashes and relevant dimensions.
8. **Plot provenance.** The joint crossover heatmap reads its values from the saved `joint_crossover_sweep_raw.csv`. The nine plot outputs are generated from saved CSV artifacts. Figure titles were removed from inside the charts so captions can be provided by the paper.
9. **Tests.** Regression tests cover cache correctness, transfer accounting, bank skew, policy threshold behavior, output isolation, aggregation, determinism, and basic end-to-end behavior.

## Verified held-out study

- Development master seeds: 42–46.
- Held-out master seeds: 47–51.
- Held-out: 5 traces per workload type per master seed; four workload patterns and five working-set cases yield 100 distinct trace cases and 600 policy/trace rows.
- Policies: CPU-cache, CPU-no-cache, PIM-always, Cost-based, Reuse-aware, Oracle.
- Tuning selects `lambda = 0.0` by minimum mean normalized regret on development master-seed means, with time and then lower lambda as tie-breaks.
- Under the configured assumed parameters, Cost-based, PIM-always, Reuse-aware, and Oracle all select PIM on the 100 held-out cases and have identical modeled latency with zero modeled regret. This does not demonstrate that reuse-awareness improves policy quality.
- Overall held-out mean latency across five master-seed means: CPU-cache 132.215 ± 0.159 μs; CPU-no-cache 633.938 ± 0.000 μs; each PIM-selecting policy 22.190 ± 0.000 μs. Ratio of the two means is about 5.96× under the current model and workload mix.
- Sensitivity sweeps for transfer bandwidth, joint cache-capacity/transfer bandwidth, cache capacity/working-set size, bank count, bank skew, and reuse penalty use a single controlled development seed in this version. Treat them as descriptive sweeps; do not use them for population-level claims or multi-seed significance.

## Known limitations and unresolved research issues

1. **Assumed timing values.** Defaults are model inputs, not calibrated to a named CPU, DRAM-PIM system, or commercial interconnect. The reported times are not hardware timings.
2. **Simplified cache.** One fully associative LRU LLC is modeled. The simulator does not include out-of-order execution, MSHRs, prefetching, cache-coherence protocols, or detailed multi-level caches.
3. **Sequential accounting.** PIM internal-memory service and compute are added serially. There is no latency overlap model; the system is not cycle accurate.
4. **Synthetic workload traces.** The four access-pattern generators do not constitute a trace from a real application or physical system.
5. **Crossover interpretation.** The main default settings strongly favor PIM, so default held-out policy comparisons alone do not establish broad crossovers. Crossover observations arise in explicit transfer/capacity sensitivity sweeps.
6. **Heuristic contribution.** The currently tuned reuse penalty is zero, providing no improvement over cost-based selection in this model. A positive nonzero reuse penalty is not supported by current development results. Do not claim an improvement; revise the algorithm or research question only after additional defensible experiments.
7. **Sensitivity-seed coverage.** The parameter sweeps are currently one-seed studies. Increase seed coverage before using them to support strong claims across workload variability.
8. **External validation.** This pass runs model-level tests and controlled experiments but does not perform hardware validation or prove calibrated agreement with an external simulator. That remains future work.
9. **Public repository status.** Corrections are local to the supplied ZIP/artifact and have not been pushed to GitHub. Any manuscript/repo citation should identify the exact artifact version or commit used for the final submission.

## Reproduction

```bash
python -m pytest -q
python -m cachepim.experiments --config config/experiment.yaml --output-dir results_reproduction
python -c "from cachepim.plots import generate_all_plots; generate_all_plots('results_reproduction')"
```

Do not rerun into an existing directory if prior artifacts must be preserved.
