# CachePIM: A Statistical Simulator for Cache-Aware CPU–Processing-in-Memory Execution

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Testing](https://img.shields.io/badge/pytest-passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CachePIM is a reproducible, trace-driven analytical research simulator designed to investigate the architectural conditions under which computational workloads should execute on a host CPU through a capacity-limited cache versus offloading to Processing-in-Memory (PIM).

---

## 1. Research Question

> **"How do cache capacity, workload reuse, and host-to-PIM transfer overhead jointly influence the performance crossover between CPU execution and Processing-in-Memory (PIM), and can a lightweight reuse-aware policy improve offloading decisions over conventional cost-based selection?"**

CachePIM evaluates this question experimentally using deterministic trace generation, an exact LRU last-level cache model, component-level analytical latency models, and an offline oracle reference.

---

## 2. Repository Structure

```
prototype/
├── cachepim/                     # Core simulation package
│   ├── __init__.py               # Package metadata and version
│   ├── config.py                 # Configuration dataclasses, validation, and provenance
│   ├── types.py                  # Dataclasses and enums for traces, costs, and results
│   ├── workloads.py              # Trace generators (STREAM, REUSE, RANDOM, MIXED_PHASE)
│   ├── cache_model.py            # Fully associative LRU cache model
│   ├── cpu_model.py              # Analytical CPU execution cost model
│   ├── pim_model.py              # Analytical PIM bank parallelism & transfer model
│   ├── policies.py               # Six offloading policies (CPU, PIM, Cost, Reuse, Oracle)
│   ├── simulator.py              # Unified simulation engine
│   ├── metrics.py                # Statistical aggregations, seed summaries & CI
│   ├── experiments.py            # Standalone experimental sweep runner
│   ├── analysis.py               # Statistical hypothesis testing and paired t-tests
│   ├── plots.py                  # Publication-ready Matplotlib figure generation
│   └── run.py                    # Single-run CLI entry point
├── config/
│   ├── default.yaml              # Default architectural parameters
│   └── experiment.yaml           # Parameter sweep ranges and experimental settings
├── tests/
│   ├── test_cache_model.py       # Hand-verified LRU trace and capacity tests
│   ├── test_cost_models.py       # CPU and PIM cost accounting tests
│   ├── test_policies.py          # Policy fallback, regret invariants, and consistency
│   └── test_reproducibility.py   # Seed determinism, config hashing, and UI/CLI parity
├── results/
│   ├── raw/                      # Final held-out data and sensitivity sweeps
│   ├── summary/                  # Master-seed summaries and held-out analysis
│   ├── figures/                  # Nine figures generated from saved CSV outputs
│   ├── configs/                  # Configuration snapshots for each experiment
│   ├── tuning/                   # Per-lambda development runs and selection scores
│   ├── held_out/                 # Frozen-policy held-out evaluation outputs
│   └── manifest.json             # Reproducibility run manifest
├── docs/                         # Research paper, benchmark citations, and correction audit
│   ├── CachePIM_Complete_Research_Paper.pdf
│   ├── CORRECTION_AND_RESULTS_REPORT.md
│   ├── CORRECTION_AUDIT.md
│   └── PRIM_BENCHMARK_CITATIONS.md
├── app.py                        # Interactive Streamlit dashboard
├── python.bat                    # Windows wrapper for Python environment
├── streamlit.bat                 # Windows wrapper for Streamlit dashboard
├── run_dashboard.bat             # One-click Windows dashboard launcher
├── setup.bat                     # One-click Windows environment setup script
├── run_dashboard.sh              # One-click macOS / Linux dashboard launcher
├── setup.sh                      # One-click macOS / Linux environment setup script
├── pyproject.toml                # Modern Python packaging configuration (PEP 517/518)
├── setup.py                      # Fallback setup configuration
├── .gitattributes                # Enforces cross-platform line endings and binary safety
├── requirements.txt              # Standard Python package dependencies
└── README.md                     # Documentation and reproduction guide
```

---

## 3. Installation and Setup (All Devices)

CachePIM is 100% cross-platform and runs on **Windows, macOS (Apple Silicon M1-M4 & Intel), and Linux**.

### Quick Setup

#### Windows
Double-click `setup.bat` or run in Command Prompt / PowerShell:
```bat
.\setup.bat
```

#### macOS & Linux
Run the setup shell script in Terminal:
```bash
chmod +x setup.sh run_dashboard.sh
./setup.sh
```

#### Manual Cross-Platform Setup (Any OS)
```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# or on Windows:
# .venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Install CachePIM in editable development mode
pip install -e .
```

---

## 4. Execution Commands

### A. Launch the Interactive Dashboard (Recommended)

- **Windows**: Double-click `run_dashboard.bat` (or run `.\run_dashboard.bat` in terminal).
- **macOS / Linux**: Run `./run_dashboard.sh` in terminal.
- **Manual (Any OS)**:
  ```bash
  python -m streamlit run app.py
  ```
The dashboard will open automatically in your browser at `http://localhost:8505`.

### B. Run an Individual Simulation via CLI
Simulate a specific workload pattern under a deterministic seed:
```bash
python -m cachepim.run --config config/default.yaml --workload STREAM --seed 42
```
Optional arguments:
- `--working-set-kb <int>`: Working set in KiB (default: 32).
- `--access-count <int>`: Number of memory accesses (default: 2048).
- `--output <path>`: Optional path to save CSV results.

### C. Run the Full Experimental Suite
Run the reproducible experimental pipeline. The reuse penalty is selected using development seeds only; the selected value is then frozen for held-out evaluation. Crossover, transfer-bandwidth, joint cache/transfer, bank-count, bank-imbalance, and reuse-weight ablation sweeps use explicitly configured grids. Each stage writes to separate artifact paths, and saved outputs include configuration hashes:
```bash
python -m cachepim.experiments --config config/experiment.yaml --output-dir results
```
For a new run, use a new output directory (for example `results_run2`) to preserve previous results.

### D. Generate Publication Figures
Generate all 9 publication figures from saved CSV outputs. The joint crossover heatmap is read from `joint_crossover_sweep_raw.csv`; the plotter does not execute a hidden simulation or hardcode heatmap values:
```bash
python -c "from cachepim.plots import generate_all_plots; generate_all_plots('results')"
```

### E. Run the Correctness Test Suite
Use module invocation so the current repository is reliably available on the import path:
```bash
python -m pytest -v tests/
```

---

## 5. Architectural Models & Mathematical Formulation

### A. CPU Cache & Execution Model
- **Cache Mapping**: Line ID $L = \lfloor \text{address} / \text{line\_size\_bytes} \rfloor$.
- **LRU Eviction**: Maintained via an exact recency map. When resident lines reach capacity $N_{\text{lines}} = \text{capacity\_bytes} / \text{line\_size\_bytes}$, the least recently used line is evicted.
- **CPU Latency Equation**:
  $$T_{\text{CPU}} = N_{\text{hit}} \times t_{\text{hit}} + N_{\text{miss}} \times t_{\text{miss}} + N_{\text{ops}} \times t_{\text{compute}} + T_{\text{writeback}}$$
  where:
  - $t_{\text{miss}}$ is the complete service time for a cache miss (replaces, rather than adds to, hit latency).
  - $T_{\text{writeback}} = N_{\text{dirty\_evictions}} \times t_{\text{miss}}$ (zero for clean/read-only inputs).

- **CPU-no-cache Baseline**:
  $$T_{\text{CPU-no-cache}} = N_{\text{accesses}} \times t_{\text{miss}} + N_{\text{ops}} \times t_{\text{compute}}$$

### B. Processing-in-Memory (PIM) Model
- **PIM Latency Equation**:
  $$T_{\text{PIM}} = T_{\text{H2P}} + T_{\text{internal-memory}} + T_{\text{compute\_PIM}} + T_{\text{P2H}} + T_{\text{launch}} + T_{\text{sync}} + T_{\text{imbalance}}$$
  where:
  - $T_{\text{H2P}} = \frac{\text{PIM input bytes}}{\text{BW}_{\text{H2P}}} + t_{\text{fixed\_H2P}}$ when input bytes are positive.
  - $T_{\text{P2H}} = \frac{\text{PIM output bytes}}{\text{BW}_{\text{P2H}}} + t_{\text{fixed\_P2H}}$ when output bytes are positive.
  - $T_{\text{internal-memory}} = (\text{PIM input bytes} + \text{PIM output bytes})/\text{BW}_{\text{PIM-internal}}$.
  - $T_{\text{compute\_base}} = \frac{N_{\text{ops}}}{B \times \text{OPS\_per\_ns\_per\_bank}}$ (across $B$ banks).
  - The initial model adds internal-memory service and arithmetic service serially; this is a simplifying assumption, not an overlap or cycle-accurate model.
  - Bank load distribution: Operations assigned deterministically across banks $b \in [0, B-1]$ yielding per-bank work $W_b$.
  - $\text{imbalance\_factor} = \frac{\max_b(W_b)}{\text{mean}_b(W_b)}$
  - $T_{\text{imbalance}} = T_{\text{compute\_base}} \times (\text{imbalance\_factor} - 1.0)$
  - Total compute time $T_{\text{compute\_base}} + T_{\text{imbalance}} = \frac{\max_b(W_b)}{\text{OPS\_per\_ns\_per\_bank}}$ (accounts for bottleneck bank without double counting parallelism).

### C. Execution Policies
1. **CPU-cache**: Always execute via modeled CPU cache.
2. **CPU-no-cache**: Direct-memory access baseline.
3. **PIM-always**: Always offload supported kernels to PIM; falls back to CPU if unsupported with reason `UNSUPPORTED_BY_PIM`.
4. **Cost-based**: Estimates $T_{\text{CPU}}$ and $T_{\text{PIM}}$ using policy-visible parameters. Offloads to PIM if $T_{\text{PIM\_est}} < T_{\text{CPU\_est}}$.
5. **Reuse-aware** (Proposed candidate): Incorporates a dimensionally consistent reuse-preservation cost in nanoseconds:
   $$T_{\text{PIM\_adjusted}} = T_{\text{PIM\_est}} + \lambda \times R_{\text{cost}}$$
   $$R_{\text{cost}} = \left(\frac{\text{effective\_reusable\_bytes}}{\text{cache\_capacity\_bytes}}\right) \times \text{estimated\_CPU\_reuse\_benefit\_ns}$$
   where $\text{estimated\_CPU\_reuse\_benefit\_ns} = N_{\text{hits\_est}} \times (t_{\text{miss}} - t_{\text{hit}})$.
   Offloads to PIM only if $T_{\text{PIM\_adjusted}} < T_{\text{CPU\_est}}$.
6. **Oracle**: Optimal offline baseline selecting $\min(T_{\text{CPU\_actual}}, T_{\text{PIM\_actual}})$.

---

## 6. Architectural Parameters & Provenance

All timing and bandwidth values in the default configuration are **illustrative assumptions**, not a calibration of one specific CPU, PIM device, or interconnect. They are exposed in configuration files so the crossover analysis can sweep them. The value 1 byte/ns is numerically equivalent to 1 decimal GB/s. Do not describe simulated times or energy proxies as physical measurements.

| Parameter | Default | Unit | Status |
| :--- | ---: | :--- | :--- |
| `cache.capacity_bytes` | 32,768 | bytes | Assumed baseline; swept |
| `cache.line_size_bytes` | 64 | bytes | Assumed representative line size |
| `cpu.hit_service_ns` | 2.0 | ns/access | Assumed timing input |
| `cpu.miss_service_ns` | 80.0 | ns/miss | Assumed complete miss-service time |
| `cpu.compute_ns_per_op` | 0.4 | ns/op | Assumed compute-service time |
| `pim.bank_count` | 16 | banks | Generic analytical target |
| `pim.effective_bandwidth_bytes_per_ns` | 128.0 | bytes/ns | Assumed aggregate internal bandwidth; now explicitly used in the internal-memory term |
| `pim.compute_ops_per_ns_per_bank` | 1.0 | ops/ns/bank | Assumed PIM throughput |
| `pim.launch_overhead_ns` | 50.0 | ns | Assumed fixed overhead |
| `pim.sync_overhead_ns` | 20.0 | ns | Assumed fixed overhead |
| `transfer.host_to_pim_bandwidth_bytes_per_ns` | 16.0 | bytes/ns | Assumed transfer bandwidth |
| `transfer.pim_to_host_bandwidth_bytes_per_ns` | 16.0 | bytes/ns | Assumed transfer bandwidth |
| Transfer fixed overheads | 100.0 each | ns | Assumed fixed overheads |
| `policy.reuse_threshold` | 0.5 | estimated-hit fraction | Assumed gate: apply reuse penalty only at or above this hit fraction |
| `policy.reuse_penalty_weight` | 1.0 initial | dimensionless | Initial value only; the runner tunes candidate values on development seeds and records the selection |

The code's `get_parameter_provenance()` catalogue deliberately labels generic timing assumptions as `assumed`. The CPU compute cost is specified directly in ns/op; the implementation does not use a separate CPU clock-frequency parameter. The grid definitions are loaded from the top-level `sweeps` section of the YAML config rather than silently ignoring configured sweep ranges. Citations in the literature review motivate the modeled concepts; they do not imply that these numeric defaults were measured or calibrated from the cited architectures.

---

## 7. Model Scope & Known Limitations

1. **Analytical vs. Cycle-Accurate**: CachePIM uses transparent analytical timing equations rather than cycle-by-cycle microarchitectural simulation (e.g., gem5).
2. **Cache Hierarchy**: Evaluates a single-level LLC. Multi-level L1/L2 caches, prefetchers, out-of-order instruction scheduling, and memory-level parallelism (MSHRs) are abstracted.
3. **Synthetic Traces**: Memory addresses are generated from parameterized statistical patterns rather than hardware/OS traces.
4. **Kernel transfer footprint**: Kernel-level PIM input/output bytes are explicit and separate from trace read/write bytes. The default vector-operation model transfers two input arrays and one output array; reduction emits one scalar; filtering uses a conservative full-output bound. These are analytical workload assumptions, not reconstructed instruction streams.
5. **Data coherence**: The current execution alternatives are modeled independently with clean inputs; hardware cache-coherence protocols, dirty-line interaction across CPU and PIM execution, and physical writeback timing are not comprehensively modeled.
6. **Internal memory service**: Internal PIM memory service and arithmetic service are added serially. The model does not hide latency/bandwidth overlap or claim cycle accuracy.
7. **Bank skew**: A nonnegative synthetic skew factor controls deterministic work distribution. It characterizes sensitivity in the model; it is not inferred from a real bank-address mapping unless a future trace-driven mapping extension is added.
8. **Statistical scope**: Confidence intervals and paired comparisons summarize the synthetic workload generator. They do not establish performance on real workloads or hardware.

## 8. Corrected Experimental Results (Model-Derived, Not Hardware Measurements)

The repository has been corrected and the experiment suite rerun using CachePIM model version `1.1.0-lambda-0`. The authoritative outputs for this run are under `results/`; `results_original_snapshot/` is a preserved copy of the originally uploaded results and must not be used as the corrected result set.

### Main held-out evaluation

The held-out evaluation uses master seeds 47–51, five traces per workload and seed, four workload patterns, five working-set sizes, and six policy rows per trace. This yields **100 distinct held-out trace cases and 600 policy-trace rows**. Development seeds 42–46 are used for reuse-penalty selection; held-out seeds are not used to tune the parameter.

Across master-seed means, the overall modeled mean execution time is:

| Policy | Mean modeled latency (µs) | Sample SD across five master-seed means (µs) |
| :--- | ---: | ---: |
| CPU-cache | 132.215 | 0.159 |
| CPU-no-cache | 633.938 | 0.000 |
| PIM-always | 22.190 | 0.000 |
| Cost-based | 22.190 | 0.000 |
| Reuse-aware | 22.190 | 0.000 |
| Oracle | 22.190 | 0.000 |

The ratio of mean CPU-cache latency to mean PIM latency is approximately **5.96×** for this exact synthetic workload mix and assumed default configuration. This is an analytical-model comparison, not a measured speedup on hardware. Zero standard deviation for the PIM-selecting policies occurs because the current model gives the same deterministic modeled time across the held-out configurations; it must not be interpreted as evidence of zero real-world variability.

All four PIM-selecting strategies choose PIM for all 100 held-out trace cases. Cost-based and oracle therefore tie with zero modeled regret in the current configuration. Development-set tuning selects `lambda = 0.0`; the reuse-aware candidate consequently reduces to cost-only selection and **does not demonstrate an improvement** in this evaluation. Positive reuse-penalty values increase modeled regret on the development sweep. This negative result is retained rather than presented as an algorithmic gain.

### Per-workload latency

The following values average the five working-set cases within each master seed and then summarize the five held-out master-seed means. All times are modeled microseconds, reported as mean ± sample standard deviation.

| Workload | CPU-cache (µs) | CPU-no-cache (µs) | PIM / cost / reuse / oracle (µs) |
| :--- | ---: | ---: | ---: |
| MIXED_PHASE | 87.009 ± 0.295 | 164.659 ± 0.000 | 21.825 ± 0.000 |
| RANDOM | 88.556 ± 0.277 | 164.659 ± 0.000 | 21.825 ± 0.000 |
| REUSE | 56.723 ± 0.625 | 164.659 ± 0.000 | 21.825 ± 0.000 |
| STREAM | 296.571 ± 0.000 | 2041.774 ± 0.000 | 23.284 ± 0.000 |

These results are conditional on the model's trace generators and parameter values. STREAM traces have a different access count from other patterns (because the generator traverses the configured working set in two passes); interpret the latency values with that workload definition in mind.

### Sensitivity studies

For the 64-KiB working-set transfer-bandwidth sweep, modeled speedup is defined as CPU-cache time divided by PIM-always time. At 0.5 GB/s, PIM is slower than CPU-cache for STREAM (0.503×), RANDOM (0.243×), and REUSE (0.117×). At 8 GB/s, the modeled speedups increase to 7.264×, 3.616×, and 1.751× respectively. At 4 GB/s, REUSE remains slightly CPU-favorable (0.908×). These controlled crossover results demonstrate that the chosen transfer assumptions and workload pattern alter the modeled execution crossover.

Increasing the modeled number of PIM banks from 4 to 64 improves modeled speedup but with diminishing returns under the current parameters. For example, STREAM increases from 8.675× to 10.973× and REUSE from 3.856× to 4.137× in the bank-count sweep. The bank-skew sweep also increases the modeled imbalance factor from 1.0 to approximately 1.66 at skew factor 4.0, but the resulting latency change remains small in this configuration because modeled transfer costs dominate much of PIM execution time.

The transfer, crossover, joint cache/transfer, bank-count, bank-skew, and penalty sweeps are one-seed controlled sensitivity experiments. They are descriptive parameter studies, **not multi-seed statistical estimates**. Their raw rows include the chosen seed and configuration metadata.

### How to reproduce the results

From the repository root, use a fresh output directory to avoid mixing a new run with prior artifacts:

```bash
python -m pytest -q
python -m cachepim.experiments --config config/experiment.yaml --output-dir results_reproduction
```

To regenerate plots from saved data without rerunning the simulation:

```bash
python -c "from cachepim.plots import generate_all_plots; generate_all_plots('results_reproduction')"
```

The checked-in `results/manifest.json` records model version, seeds, the selected reuse penalty, and result classification. All numbers above are simulated analytical estimates over synthetic traces. No physical CPU/PIM performance or energy was measured.

## 9. Correction Audit and Reproducibility Notes

The corrected version addresses result-path collisions between tuning and held-out data, master-seed aggregation, missing PIM output bytes for supported kernels, PIM internal-memory service accounting, deterministic bank-skew modeling, and configuration-driven sweeps. The heatmap is rendered from the saved joint-sweep CSV rather than silently running a hidden sweep inside the plotting routine. The corrected automated suite contains **24 passing tests** in the verified run. See `docs/CORRECTION_AUDIT.md` for the change list and known caveats.

The local corrected source and results are not automatically pushed to the public GitHub repository. The files in the accompanying corrected-source archive represent the audited artifact. Publish them to GitHub only after reviewing the changes and confirming the final manuscript and artifact version.
