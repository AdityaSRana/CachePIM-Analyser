# CachePIM Verification & Defect Repair Fix Log

This document records all confirmed defects, root-cause investigations, source-code modifications, and experiment pipeline corrections executed during the independent verification of **CachePIM**.

All changes were implemented cleanly and verified against the complete unit test suite (39/39 passing tests). Pre-audit source tree state is immutably archived at `backup_pre_audit_20261028_2105/`.

---

## 1. Summary of Identified Defects and Applied Fixes

| Fix ID | Target Component | Description / Root Cause | Applied Correction | Impact on Results | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FIX-01** | `cachepim/policies.py` | **Eq. (8) Unphysical Hit-Credit Overcharge**: Credit formula $\Delta t = N_{\text{hits}} \cdot t_{\text{hit}} \cdot 0.5 \cdot (C/W)$ over-credited CPU when $W \le C/2$ ($C/W \ge 2.0$), subtracting up to $200\%$ of hit latency and causing 70 false-CPU missed offloads on the balanced grid. | Clamped credit physically: $\Delta t = \min(N_{\text{hits}} \cdot t_{\text{hit}}, N_{\text{hits}} \cdot t_{\text{hit}} \cdot 0.25 \cdot \text{fit\_ratio})$ and tuned credit multiplier to $0.25$ on dev seeds 42–46. | Reduced false-CPU missed offloads from 70 to 40 on held-out seeds 47–51. Accuracy improved from 82.0% to 88.0%. | Verified; 39/39 tests pass. Confirmed Cost-based policy (96.0% accuracy, 0.671 $\mu$s regret, 0 missed offloads) remains superior. |
| **FIX-02** | `cachepim/config.py` | **Parameter Provenance Catalog Incompleteness**: `get_parameter_provenance()` omitted fields added during revisions (`cache.ways`, `pim.overlap_factor`, `pim.row_buffer_locality_enabled`, `policy.use_footprint_estimator`). | Appended explicit parameter descriptors with unit, provenance classification (`literature-derived` / `assumed`), hardware calibration flag, and literature references. | Enables complete automated parameter audits and manifest generation (`parameter_manifest.json`). | Verified; complete audit manifest generated. |
| **FIX-03** | `cachepim/pim_model.py` / Baseline Experiment Pipeline | **Row-Buffer Locality Inactive in Baseline Table IV**: Baseline PIM latency in Table IV was flat ($21.825\ \mu\text{s}$) because `row_buffer_locality_enabled` was `False` by default in `config.py`. | Created dual regeneration in `results/verification/corrected/table_iv_baseline_comparison.csv` documenting both Flat PIM ($21.825\ \mu\text{s}$) and Row-Buffer PIM ($\eta_{\text{row}} \in \{0.90, 0.60, 0.25\}$). | Resolves Claude review item 2: STREAM = $7.78\ \mu\text{s}$, REUSE = $7.82\ \mu\text{s}$, RANDOM = $9.61\ \mu\text{s}$. | Verified; exact provenance reproduced. |
| **FIX-04** | Experiment Pipeline (`table_vi_real_vs_synthetic.py`) | **Table VI Provenance Misattribution**: Table VI in the paper reported synthetic preset numbers ($64\ \text{KiB}$ WS) under the label of native Valgrind Lackey memory traces. | Built explicit provenance reconstruction script separating Native Lackey Traces ($60,000$ records, $97.7\%\text{--}99.8\%$ hit rate, $24.4\times\text{--}31.6\times$ speedup) from Synthetic Presets ($64\ \text{KiB}$, $20.95\times, 4.02\times, 5.65\times, 13.38\times$). | Full scientific transparency established in `table_vi_real_vs_synthetic.csv` and `table_vi_provenance.csv`. | Verified; matches paper numbers to 2 decimal places. |
| **FIX-05** | Policy Evaluation Pipeline (`generate_policy_decisions_and_grid.py`) | **Table V Inversion & Evaluation Metric Clarity**: Table V caption swapped 96% and 85% accuracy between Cost-based and Reuse-aware. Full confusion matrix was missing. | Simulated all 1,000 grid instances (500 dev, 500 held-out) across all 6 policies. Generated full confusion matrix: True Offload, Bad Offload, True CPU, Missed Offload. | Corrected held-out accuracy: Cost-based = 96.0% ($0.671\ \mu\text{s}$ regret), Reuse-aware tuned = 88.0% ($18.68\ \mu\text{s}$ regret), Reuse-aware uncorrected = 82.0% ($18.87\ \mu\text{s}$ regret). | Verified; saved to `results/verification/corrected/table_v_balanced_grid.csv`. |
| **FIX-06** | Hardware Calibration & Validation Pipeline | **Limited Calibration Scope & In-Sample Bias**: Table VII only had 4 in-sample data points (VA, GEMV, BS, SEL) without independent held-out validation or leave-one-out cross-validation. | Implemented 4-fold leave-one-out cross-validation (train MAPE 3.06%–3.81%, test error 2.86%–5.13%) and evaluated 4 omitted held-out kernels (RED, HST, SpMV, BFS). | Proves that under calibrated link bandwidth ($1.0\ \text{GB/s}$) and row-buffer penalty, CPU outperforms PIM on 3 of the 4 omitted kernels (HST speedup $0.36\times$, SpMV $0.91\times$, BFS $0.91\times$). | Verified; saved to `results/verification/calibration_results.csv`. |
| **FIX-07** | Cache Associativity Verification (`generate_corrected_experiments.py`) | **Associativity Invariant Documentation**: Clarified why $W \le 32\ \text{KiB}$ produces identical hit rates across geometries, while conflict misses appear at $W \ge 64\ \text{KiB}$. | Evaluated Fully Associative, 16-way, 8-way, and 4-way geometries across $16, 32, 64, 128\ \text{KiB}$. Documented the exact 19 boundary decisions that flip. | Generated `results/verification/corrected/associativity_sweep.csv`. | Verified; confirmed 3.8% decision shift near crossover. |
| **FIX-08** | Concurrency Overlap Model (`generate_corrected_experiments.py`) | **Pipelined Transfer Verification**: Verified implementation of $T_{\text{pipelined}} = \max(T_{\text{xfer}}, T_{\text{exec}}) + (1-\alpha)\min(T_{\text{xfer}}, T_{\text{exec}})$. | Generated complete sensitivity sweep across $\alpha \in \{0.0, 0.25, 0.5, 0.75, 1.0\}$. | Quantified latency reduction up to $29.8\%$ at $\alpha=1.0$; saved to `overlap_alpha_sweep.csv`. | Verified; matches analytical model. |
| **FIX-09** | Statistical Sweeps Verification (`generate_corrected_experiments.py`) | **Multi-Seed Variance Clarification**: Fig 8 / sweeps implied empirical seed variance for analytical bank division equations. | Documented that CachePIM's analytical equations evaluate deterministically, producing mathematical zero variance across master seeds 47–51. | Saved exact sweep data to `multiseed_bank_count_sweep.csv` and `multiseed_bank_skew_sweep.csv`. | Verified; variance is $0.000000\ \mu\text{s}^2$. |
| **FIX-10** | Benchmark & Runtime Engine | **Execution Throughput & Latency Profiling**: Quantified simulator speed to substantiate "thousands of evaluations in seconds" claim. | Measured end-to-end evaluation throughput with warmups over 1,000 iterations. | Recorded $208.3\ \text{evals/sec}$ for full trace cache simulation and $>15,000\ \text{evals/sec}$ for pure analytical evaluations; saved to `runtime_benchmark.json`. | Verified; 1,000 runs complete in $4.80\ \text{seconds}$. |

---

## 2. Detailed Source Code Diffs

### A. Fix FIX-01: `cachepim/policies.py`
```diff
--- a/cachepim/policies.py
+++ b/cachepim/policies.py
@@ -373,7 +373,11 @@ class ReuseAwarePolicy(BasePolicy):
         if use_footprint and is_resident and (hit_fraction >= config.policy.reuse_threshold or reusability >= 0.4):
             # When working set fits in cache with high temporal locality, repeated hits
-            # benefit from innermost cache residency without bus arbitration
-            temporal_credit = hits_est * (config.cpu.hit_service_ns * 0.5 * fit_ratio)
+            # benefit from innermost cache residency without bus arbitration.
+            # Clamped physically to never exceed total hit service time (M2 repair).
+            # Tuned credit multiplier is 0.25 based on dev seeds 42-46.
+            raw_credit = hits_est * (config.cpu.hit_service_ns * 0.25 * fit_ratio)
+            temporal_credit = min(hits_est * config.cpu.hit_service_ns, raw_credit)
             refined_cpu_est = max(0.0, cpu_est - temporal_credit)
             pim_adjusted = pim_est
         else:
```

### B. Fix FIX-02: `cachepim/config.py`
```diff
--- a/cachepim/config.py
+++ b/cachepim/config.py
@@ -375,4 +375,32 @@ def get_parameter_provenance() -> Dict[str, ParameterProvenance]:
             reference="config/experiment.yaml reuse_penalty_candidates"
         ),
+        "policy.use_footprint_estimator": ParameterProvenance(
+            value=True,
+            unit="boolean",
+            provenance="assumed",
+            description="Dynamic Working-Set Footprint Estimator gating cache temporal residency (M2).",
+            reference="Spec Sec 5.2"
+        ),
+        "cache.ways": ParameterProvenance(
+            value=None,
+            unit="ways",
+            provenance="assumed",
+            description="Set associativity (None/0 = fully associative; >0 = N-way set associative).",
+            reference="Spec Sec 5.1 (M6)"
+        ),
+        "pim.overlap_factor": ParameterProvenance(
+            value=0.0,
+            unit="dimensionless factor [0, 1]",
+            provenance="assumed",
+            description="PIM transfer/compute overlap pipelining factor (0 = serial, 1 = fully overlapped).",
+            reference="Spec Sec 6.3 (M8)"
+        ),
+        "pim.row_buffer_locality_enabled": ParameterProvenance(
+            value=False,
+            unit="boolean",
+            provenance="literature-derived",
+            description="Enables DRAM row-buffer locality factor eta_row (0.90 stream, 0.60 reuse, 0.25 random).",
+            reference="SAFARI PrIM benchmark paper (Gomez-Luna et al., IEEE Access 2022) (M7)"
+        ),
     }
```

---

## 3. Regression Test Verification
Following all modifications, pytest was executed from the project root:
```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\harsh\Desktop\CD_final_5\CDv2AV\CachePIM-Analyser-corrected
configfile: pyproject.toml
collected 39 items

tests\test_cache_model.py .....                                          [ 12%]
tests\test_cost_models.py .......                                        [ 30%]
tests\test_metrics_experiments.py ......                                 [ 46%]
tests\test_policies.py ......                                            [ 61%]
tests\test_prim_presets.py ...                                           [ 69%]
tests\test_reproducibility.py ....                                       [ 79%]
tests\test_trace_loader.py ....                                          [ 89%]
tests\test_ui_components.py ....                                         [100%]

============================= 39 passed in 14.35s =============================
```
100% of unit tests pass with zero regressions.

