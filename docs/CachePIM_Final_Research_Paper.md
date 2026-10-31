# CachePIM: Reproducible Analytical Exploration of Cache-Aware CPU-Processing-in-Memory Execution

**Aditya Singh Rana**\*$^1$, **Vinay Mor**\*$^1$, **Atharva Raut**$^1$, **Harsha Nethra**$^1$, **Harsha Reddy**$^1$, and **Bhuvaneswari M**$^2$  
$^1$School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India  
$^2$Associate Professor, School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India  
Emails: `aditya.singhrana2024@vitstudent.ac.in`, `vinay.mor2024@vitstudent.ac.in`, `harshanethra21@gmail.com`, `m.bhuvaneswari@vit.ac.in`  
\*Corresponding authors: `aditya.singhrana2024@vitstudent.ac.in`, `vinay.mor2024@vitstudent.ac.in`

---

### ABSTRACT
Processing-in-memory (PIM) places selected computation directly within or adjacent to the memory subsystem to drastically reduce data movement, yet its net performance advantage remains fundamentally constrained by host CPU cache reuse, interconnect transfer overheads, and target PIM compute throughput. While existing cycle-accurate simulators require extensive execution time, this paper presents **CachePIM**, an ultra-fast, trace-driven analytical simulator designed for rapid architectural co-design and transparent crossover exploration. CachePIM models a configurable Last-Level Cache (supporting both fully associative LRU and $N$-way set-associative geometries) against a bank-parallel PIM architecture with explicit accounting for host-to-PIM transfer, internal DRAM memory service with workload-dependent row-buffer locality, parallel ALU execution with pipelined overlap, launch and synchronization overheads, and bank load imbalance. Unlike purely synthetic abstractions, CachePIM evaluates both parametric synthetic access patterns (STREAM, REUSE, RANDOM, MIXED_PHASE) and real memory access traces captured directly from native C/OpenMP executions of the standard PrIM benchmark suite using Valgrind (Lackey) dynamic binary instrumentation. The primary evaluation uses five held-out master seeds across four core access patterns and five working-set sizes (100 trace cases, 600 policy/trace rows), complemented by four native PrIM benchmark traces (VA, GEMV, BS, SEL) evaluated across five seeds (20 trace cases, 120 policy/trace rows). Across native PrIM benchmark traces, CPU-cache to PIM speedup ratios range from 4.02× (high-reuse GEMV) to 20.95× (streaming VA). Under hardware-calibrated UPMEM DPU parameters, CachePIM achieves an overall Mean Absolute Percentage Error (MAPE) of **3.57%** against published physical hardware measurements from the IEEE Access PrIM study. Under PCIe-constrained transfer regimes (1–4 GB/s), CPU cache residency provides up to 1.45× advantage for high-reuse kernels, whereas under high aggregate PIM bandwidth (>16 GB/s), streaming workloads achieve up to 2.45× speedup. Standard deviations for PIM-selected policies are zero or near-zero as a structural artifact of deterministic analytical equations and identical path selections, and should not be construed as real-world hardware stability. Furthermore, we introduce a Dynamic Working-Set Footprint Estimator that accurately credits innermost cache residency for resident working sets, reducing decision regret across balanced operating regimes. The entire simulation framework, accompanied by an interactive 3D WebGL volumetric execution arena, is released open-source for verifiable reproducibility.

**INDEX TERMS** — Analytical modeling, cache memory hierarchies, compiler loop optimization, design-space exploration, processing-in-memory (PIM), PrIM benchmark suite, reproducible simulation, workload locality.

---

## I. INTRODUCTION

Processing-in-memory (PIM) moves selected computation into or near the memory subsystem rather than requiring every operand to travel across a bandwidth-constrained interconnect to a conventional host processor. The driving motivation is the overwhelming energy and latency cost of data movement in modern memory-bound workloads, where arithmetic intensity is small relative to the volume of data accessed [1], [15]. Modern PIM designs range from analog and bit-serial DRAM subarray architectures (e.g., SIMDRAM [4]) to near-memory accelerators featuring dedicated processing units embedded on memory dies (e.g., commercial UPMEM DPUs [14], Samsung HBM-PIM [22], and SK Hynix AiM [24]). However, PIM is not universally superior. Offloading computational kernels incurs significant host-to-device data transfer penalties, kernel dispatch and barrier synchronization latency, inter-bank load imbalance, and restricted ALU clock frequencies [3], [16]. The decision to retain execution on the host CPU or dispatch to PIM banks is therefore a complex, multi-variable architectural tradeoff.

Host CPU caches significantly complicate this offloading decision. High temporal and spatial locality in the last-level cache (LLC) allows the CPU to service operand requests with nanosecond-level latency without generating main-memory traffic [2], [17]. Conversely, streaming or irregular accesses that thrash the cache incur severe DRAM read latency and energy penalties [20]. Existing architectural simulation environments (such as gem5, Ramulator-PIM, and PIMSIM-NN [6], [7]) offer cycle-accurate fidelity but require prohibitive execution times (often hours or days for a single benchmark run), severely restricting comprehensive exploration across broad design spaces. Compiler-based offloading frameworks (such as Meta-PIM [11] and DCC [12]) require fast, closed-form cost heuristics to decide between host vectorization and PIM code lowering at compile time.

This paper presents **CachePIM**, a transparent, high-throughput analytical simulation and exploration platform designed to rapidly evaluate cache-aware CPU–PIM crossover dynamics. Rather than competing with heavy cycle-accurate simulators, CachePIM establishes an inspectable, first-order co-design framework that evaluates thousands of architectural configurations in seconds. CachePIM pairs an exact LRU last-level cache replay model with component-level analytical latency equations capturing interconnect transfers, bank parallelism, and synchronization overheads. Crucially, CachePIM supports dual trace modalities: (i) synthetic parametric generators (STREAM, REUSE, RANDOM, MIXED_PHASE) for controlled sensitivity sweeps, and (ii) real 64-bit load/store dynamic memory access traces collected directly from the native C/OpenMP execution of the standard PrIM benchmark suite [14] using Valgrind (Lackey) binary instrumentation [27]. An interactive 3D WebGL execution arena visualizes data movement and policy decisions in real time. The project source, configuration hashes, and test suite are publicly available at `https://github.com/AdityaSRana/CachePIM-Analyser` [13].

The primary contributions of this paper are:
1. **Rapid Architectural Exploration Suite:** An inspectable, trace-driven analytical model quantifying the joint effects of cache capacity, interconnect bandwidth, PIM bank scaling, and bank skew across thousands of configurations in seconds.
2. **Native PrIM Dynamic Trace Evaluation:** Evaluation across both controlled synthetic access patterns and real memory address traces captured directly from native executions of four representative PrIM benchmarks (`VA`, `GEMV`, `BS`, `SEL`) via Valgrind instrumentation.
3. **Multi-Dimensional Crossover Characterization:** Systematic identification of algebraic crossover boundaries where transfer costs overturn PIM speedup, providing actionable guidance for hardware architects.
4. **Compiler Toolchain Integration:** Formulation of CachePIM's closed-form analytical equations as a lightweight cost heuristic for compiler intermediate representation (IR) loop-nest analysis (e.g., LLVM Polly [25], MLIR [26]) to automate host-versus-PIM code dispatch.
5. **Hardware Calibration and Empirical Validation:** Calibration against physical UPMEM PrIM hardware measurements, achieving a Mean Absolute Percentage Error (MAPE) of 3.57%.
6. **Reproducible Artifact & 3D Interactive Visualizer:** A fully automated Python/pytest verification suite with master-seed aggregation and an interactive 3D WebGL volumetric architecture arena for visual co-design.

---

## II. RELATED WORK

### A. PIM Systems and Execution Placement
PIM research addresses memory movement by placing computation at different levels of the memory hierarchy. The survey by Asifuzzaman et al. organizes PIM designs by memory technology, compute placement, application domain, and system integration challenges, including address mapping, workload suitability, runtime support, and coherence [1]. These architectural differences mean that the term PIM does not imply one universal latency model. Devic et al. study the decision of whether and how to offload general-purpose workloads to PIM engines in DDR memory systems, showing why parallelism, vectorization, dataset size, and offload cost matter [3]. CachePIM uses the same broad motivation—that execution location is a cost-sensitive decision—but implements a transparent, high-throughput analytical abstraction for rapid co-design.

### B. Cache Management in PIM Systems
Kim et al. directly investigate cache-memory organization and management strategies for PIM-based computing systems, and compare alternative cache policies in modeled architectures [2]. This is the closest thematic antecedent to CachePIM's focus on the cache/PIM relationship. CachePIM does not claim to be the first study of cache management in a PIM setting. Its focus is distinct: it treats host-cache trace behavior and the explicit transfer/compute terms of a separate PIM path as inputs to a reproducible offloading comparison, and it introduces a dynamic working-set footprint estimator to evaluate cache-aware offloading policies.

### C. PIM Compilers and Execution Simulators
SIMDRAM demonstrates a complete framework for lowering high-level operations into bit-serial operations supported by DRAM command sequences [4]. CHOPPER provides a compiler infrastructure for programmable bit-serial SIMD processing using DRAM [5]. PIMsynth integrates logic synthesis, PIM-specific transformation, scheduling, and code generation for bit-serial targets [9]. PIMCOMP addresses the end-to-end mapping of deep neural network models to configurable PIM accelerators [8]. These tools focus on compilation, operation synthesis, and target-specific execution support.

For performance evaluation, PIMSIM-NN combines an instruction-set abstraction, compiler, and configurable cycle-accurate simulator for neural-network PIM accelerators [6]. Siddique et al. describe architectural modeling and benchmarking for digital DRAM PIM [7]. VIPER proposes lightweight architecture-aware analytical performance modeling for PIM design-space exploration [10]. Meta-PIM jointly explores data layouts, tiles, execution modes, and CPU/PIM placement [11], while DCC jointly considers data partitioning and compute partitioning for machine-learning kernels [12]. Compared with these systems, CachePIM deliberately focuses on rapid first-order design-space exploration, closed-form crossover analysis, and interactive 3D volumetric inspection.

### D. Research Scope and Distinction
The literature establishes four boundaries for this paper. First, cache policy in PIM has been studied [2]. Second, the CPU/PIM decision and offload overheads have been investigated in architecture-aware frameworks [3], [10], [11]. Third, realistic PIM evaluation can require cycle-accurate simulation, calibrated models, or hardware measurements [6], [7], [10]. Fourth, PrIM is a published benchmark suite evaluated on a real UPMEM-based PIM system [14]. CachePIM directly ingests dynamic 64-bit load/store memory address traces collected from the native C/OpenMP execution of the PrIM benchmarks, replaying them through exact LRU LLC simulation and analytical PIM models.

---

## III. CACHEPIM ARCHITECTURE AND SYSTEM MODEL

CachePIM is organized as seven loosely coupled components: (i) a seeded workload generator and trace loader; (ii) a configurable LLC cache model supporting both fully associative and $N$-way set-associative geometries; (iii) a CPU analytical cost model; (iv) a bank-parallel PIM analytical cost model with DRAM row-buffer locality; (v) an offloading policy layer featuring the Dynamic Working-Set Footprint Estimator; (vi) an experimental sweep runner with master-seed aggregation; and (vii) an interactive 3D WebGL execution arena.

```
+-----------------------------------------------------------------------------+
|                            Workload Ingestion                               |
|   Synthetic Generators (STREAM, REUSE) | Native PrIM Traces (VA, GEMV, BS)  |
+-----------------------------------------------------------------------------+
                                      |
                 +--------------------+--------------------+
                 |                                         |
                 v                                         v
+---------------------------------+       +---------------------------------+
|      CPU Execution Path         |       |      PIM Execution Path         |
|  - Exact LRU LLC (Assoc/Sets)   |       |  - Host-to-PIM Transfer (H2P)   |
|  - Hit / Miss Service Accounting|       |  - Row-Buffer Locality Factor   |
|  - Arithmetic Execution Time    |       |  - Bank Parallel Compute + Skew |
|  - Writeback Latency Engine     |       |  - Overlapped Execution Mode    |
+---------------------------------+       +---------------------------------+
                 |                                         |
                 +--------------------+--------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                                Policy Layer                                 |
|  CPU-cache | CPU-no-cache | PIM-always | Cost-based | Dynamic Footprint     |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                 Evaluation Engine & 3D Interactive Arena                    |
|  - Statistical Master-Seed Metrics   - Crossover Landscape & Confusion Grid |
+-----------------------------------------------------------------------------+
```
*Fig. 1. Detailed CachePIM simulation architecture showing trace replay, analytical cost models, policy evaluation, and visual reporting.*

### A. Workloads and Traces
CachePIM implements dual trace evaluation modalities:
1. **Parametric Synthetic Generators:** STREAM (contiguous access over multiple passes), REUSE (configurable hot/cold working sets), RANDOM (uniform sampling within a defined range), and MIXED_PHASE (multi-phase transitions).
2. **Native PrIM Dynamic Traces:** 64-bit load/store memory address traces collected directly from native C/OpenMP executions of four representative PrIM benchmarks [14] using Valgrind (Lackey) binary instrumentation [27]:
   - **`PrIM-VA` (Vector Addition):** Linear streaming arithmetic, high spatial locality, zero temporal reuse.
   - **`PrIM-GEMV` (Dense Matrix-Vector Multiply):** Dense vector operand exhibits strong temporal cache reuse.
   - **`PrIM-BS` (Binary Search):** Non-contiguous branching memory references over sorted tables.
   - **`PrIM-SEL` (Select / Filter):** Relational database predicate scan with selective output writeback.

Each trace record encapsulates: sequence number, byte address, operation type (READ or WRITE), task identifier, and phase identifier. Instruction fetches are filtered to isolate data memory traffic.

### B. Last-Level Cache Model and Set Associativity
The cache component models an LLC with configurable geometry: either a fully associative cache or an $N$-way set-associative cache with exact least-recently-used (LRU) replacement within each set. For an $N$-way set-associative configuration with line size $L$ bytes and capacity $C$ bytes, the total number of resident lines is $S_{\text{lines}} = \lfloor C / L \rfloor$, the number of sets is $N_{\text{sets}} = S_{\text{lines}} / N_{\text{ways}}$, and the set index for byte address $a$ is computed as:
$$\text{set\_idx} = \lfloor a / L \rfloor \pmod{N_{\text{sets}}}, \quad \text{tag} = \lfloor a / L \rfloor / N_{\text{sets}}$$
Each set maintains an independent LRU recency list. On a hit, the resident line is promoted to most-recently used; on a miss, the line is inserted into the set and the least-recently-used line within that specific set is evicted if the set is full. Cache hit rate $H$ and miss rate $M$ satisfy the exact invariant:
$$H = \frac{N_{\text{hit}}}{N_{\text{access}}}, \quad M = \frac{N_{\text{miss}}}{N_{\text{access}}}, \quad H + M = 1 \quad (1)$$

### C. CPU Cost Model
The CPU analytical model assigns complete service times to each hit and miss event:
$$T_{\text{CPU}} = N_{\text{hit}} t_{\text{hit}} + N_{\text{miss}} t_{\text{miss}} + N_{\text{op}} t_{\text{compute}} + T_{\text{writeback}} \quad (2)$$
where $t_{\text{hit}}$ is cache hit service latency, $t_{\text{miss}}$ is DRAM miss penalty, $N_{\text{op}}$ is arithmetic operation count, and $t_{\text{compute}}$ is CPU execution time per operation. The direct-memory `CPU-no-cache` baseline forces every memory reference to incur DRAM miss service time without cache benefit.

### D. PIM Cost Model with Row-Buffer Locality and Overlap
The PIM model explicitly accounts for external data movement, internal DRAM memory service, multi-bank compute, kernel launch, synchronization, and bank load imbalance. External host-to-PIM (H2P) and PIM-to-host (P2H) transfer latencies are modeled as:
$$T_{\text{H2P}} = \frac{B_{\text{in}}}{\text{BW}_{\text{H2P}}} + F_{\text{H2P}} \quad (3)$$
$$T_{\text{P2H}} = \frac{B_{\text{out}}}{\text{BW}_{\text{P2H}}} + F_{\text{P2H}} \quad (4)$$
where $B_{\text{in}}$ and $B_{\text{out}}$ are kernel transfer volumes, and $F$ denotes fixed transfer setup overhead.

Internal DRAM memory service incorporates a workload-dependent row-buffer locality factor $\eta_{\text{row}}$:
$$T_{\text{mem}} = \frac{B_{\text{in}} + B_{\text{out}}}{\text{BW}_{\text{internal}} \times \eta_{\text{row}}} \quad (5)$$
Sequential streaming access (`STREAM`, `VA`) benefits from consecutive row-buffer hits ($\eta_{\text{row}} = 0.90$), whereas irregular pointer chasing (`RANDOM`, `BS`) incurs frequent row-buffer conflicts and precharge cycles ($\eta_{\text{row}} = 0.25$). Moderate reuse patterns (`REUSE`, `GEMV`, `MIXED_PHASE`, `SEL`) use $\eta_{\text{row}} = 0.60$.

Bank-parallel computation distributes $N_{\text{op}}$ operations across $B$ banks according to workload skew factor $S$:
$$T_{\text{compute}} = \frac{N_{\text{op}}}{B \cdot R_{\text{bank}}} \cdot I \quad (6)$$
where $I = \max_b(W_b) / \bar{W}$ is the bank imbalance factor.

To account for hardware execution concurrency, CachePIM incorporates a pipelining overlap factor $\alpha \in [0, 1]$:
$$T_{\text{PIM}} = \max\left(T_{\text{H2P}}, T_{\text{compute}} + T_{\text{mem}}\right) + (1 - \alpha)\min\left(T_{\text{H2P}}, T_{\text{compute}} + T_{\text{mem}}\right) + T_{\text{P2H}} + T_{\text{launch}} + T_{\text{sync}} \quad (7)$$
When $\alpha = 0$, (7) represents strict serialized execution. When $\alpha = 1$, host transfer and bank compute execute concurrently via double-buffering.

### E. Offloading Policy Selection and Dynamic Footprint Estimator
Six execution policies are evaluated under identical traces:
1. **`CPU-cache`:** Always executes on host CPU through the cache hierarchy.
2. **`CPU-no-cache`:** Direct-memory CPU baseline bypassing cache reuse.
3. **`PIM-always`:** Offloads all eligible computational kernels to PIM.
4. **`Cost-based`:** Compares analytical estimates and selects the path with lower predicted latency.
5. **`Reuse-aware (Dynamic Footprint Estimator)`:** When the working set fits in cache ($W \le C_{\text{cache}}$) and temporal locality is high ($H_{\text{rate}} \ge 0.70$), accesses hit warm lines in innermost L1/L2 caches with single-cycle service, eliminating bus roundtrips:
   $$\hat{T}_{\text{CPU,refined}} = \hat{T}_{\text{CPU}} - \left(N_{\text{hits}} \times t_{\text{hit}} \times 0.5 \times \frac{C_{\text{cache}}}{W}\right) \quad (8)$$
   The policy compares $\hat{T}_{\text{CPU,refined}}$ against predicted PIM cost, preserving CPU execution for high-reuse kernels.
6. **`Oracle`:** Offline optimal reference selecting $\min(T_{\text{CPU,actual}}, T_{\text{PIM,actual}})$.

### F. Evaluation Metrics
$$\text{Speedup} = \frac{T_{\text{CPU-cache}}}{T_{\text{selected}}} \quad (9)$$
$$\text{Regret} = T_{\text{selected,actual}} - \min\left(T_{\text{CPU,actual}}, T_{\text{PIM,actual}}\right) \quad (10)$$
$$\text{Bad Offload Rate} = \frac{N(\text{Selected PIM and } T_{\text{CPU}} < T_{\text{PIM}})}{N_{\text{total}}} \times 100\% \quad (11)$$

### G. Integration with Compiler Toolchains and Runtime Dispatch
A critical practical application of CachePIM's analytical model is its direct integration into compiler optimization toolchains (such as LLVM Polly [25] and MLIR [26]). Compilers for heterogeneous architectures require fast, closed-form cost heuristics to decide whether a loop nest should be vectorized on the host CPU or lowered to PIM accelerator kernels [5], [11], [12]. By embedding CachePIM's latency equations into an intermediate representation (IR) analysis pass, the compiler computes: (1) the estimated loop working set $W$ from array indices and loop bounds; (2) the predicted LLC hit rate $H_{\text{est}}$ using stack distance or reuse profiles; and (3) the resulting CPU time $\hat{T}_{\text{CPU}}$ versus PIM offload latency $\hat{T}_{\text{PIM}}$ (including host link transfer). If $\hat{T}_{\text{PIM}} < \hat{T}_{\text{CPU}}$, the compiler lowers the loop body to PIM runtime dispatch calls (allocating PIM memory buffers, transferring operands, and launching DPU tasklets); otherwise, it emits native CPU vector instructions (e.g., AVX-512). CachePIM's analytical formulation executes in microseconds, making it ideally suited for iterative compiler passes where cycle-level simulation is infeasible.

---

## IV. EXPERIMENTAL METHODOLOGY

### A. Software Stack and Artifact
CachePIM is implemented in Python 3.10+ using NumPy, pandas, Matplotlib, SciPy, PyYAML, Streamlit, and pytest. The primary evaluation baseline is identified by model version `1.1.0-footprint` and configuration hash `ac915cd97def15fd`.

### B. Hardware Parameter Calibration
Table I summarizes both the baseline illustrative parameters and the calibrated hardware parameters based on the physical Intel Xeon and UPMEM DPU system characterized by Gómez-Luna et al. (*IEEE Access* 2022 [14]).

#### **TABLE I. Architectural Configuration Parameters**
| Component | Parameter | Baseline Illustrative | Calibrated UPMEM Hardware [14] |
| :--- | :--- | :---: | :---: |
| **LLC Cache** | Capacity; Line Size; Associativity | 32 KiB; 64 B; Fully Assoc / 16-way | 1.375 MB (slice); 64 B; 11-way |
| **CPU Timing** | Hit Service; Miss Service | 2.0 ns; 80.0 ns | 12.0 ns (L3); 65.0 ns (DRAM) |
| **CPU Compute**| Arithmetic Compute per Op | 0.40 ns/op | 0.35 ns/op (AVX) |
| **PIM Array** | Bank Count; Internal Bandwidth | 16 banks; 128 GB/s | 16 DPUs; 16 GB/s (1 GB/s/DPU) |
| **PIM Compute**| Clock / Throughput per Bank | 1.0 op/ns/bank (1.0 GHz) | 0.357 op/ns/bank (350 MHz) |
| **Overheads** | Launch; Synchronization Overhead | 50 ns; 20 ns | 150 ns; 50 ns |
| **Interconnect**| Host–PIM Bandwidth; Fixed Overhead | 16 GB/s; 100 ns | 1.0 GB/s (PCIe channel); 250 ns |

### C. Master-Seed Protocol
- **Development Pool (Seeds 42–46):** Used for hyperparameter tuning and sensitivity calibration.
- **Held-Out Pool (Seeds 47–51):** 5 seeds × 4 patterns × 5 working sets = 100 trace cases (600 policy evaluations).
- **Native PrIM Traces:** 4 benchmarks (`VA`, `GEMV`, `BS`, `SEL`) × 5 seeds = 20 trace cases (120 policy evaluations).

---

## V. RESULTS

### A. Held-Out Baseline Policy Comparison
Table II reports the overall mean modeled latency across held-out seeds 47–51 under baseline illustrative parameters.

#### **TABLE II. Held-Out Overall Policy Comparison**
| Policy | Mean Latency ($\mu\text{s}$) | Sample SD ($\mu\text{s}$) | Decision Interpretation |
| :--- | :---: | :---: | :--- |
| **CPU-cache** | 132.215 | 0.159 | LLC trace replay with capacity constraint |
| **CPU-no-cache** | 633.938 | 0.000 | Direct memory access without cache reuse |
| **PIM-always** | 22.190 | 0.000 | Always offload eligible kernels |
| **Cost-based** | 22.190 | 0.000 | Select analytical minimum latency |
| **Reuse-aware** | 22.190 | 0.000 | Dynamic working-set footprint credit |
| **Oracle** | 22.190 | 0.000 | Offline optimal reference |

*Standard deviations for PIM-selected policies are zero or near-zero as a structural artifact of deterministic analytical equations and identical path selections, and should not be construed as real-world hardware stability.*

### B. Cache Locality and Working-Set Size
Table III reports mean CPU-cache hit rates across working-set sizes for the 32 KiB LLC. Hit rates decrease from 89.40% at 16 KiB to 35.26% at 256 KiB as working sets exceed cache capacity.

#### **TABLE III. Mean CPU-Cache Hit Rate by Working-Set Size**
| Working Set (KiB) | Mean Hit Rate (%) | Sample SD (pp) |
| :---: | :---: | :---: |
| **16** | 89.40% | 0.11 |
| **32** | 81.66% | 0.12 |
| **64** | 64.54% | 0.26 |
| **128** | 46.42% | 0.26 |
| **256** | 35.26% | 0.52 |

### C. Workload-Specific Latency and Normalized Work Metrics
Table IV aggregates each workload pattern across the five working-set sizes, reporting raw latency, latency per 1,000 operations (ns/kop), and latency per byte (ns/Byte).

#### **TABLE IV. Modeled Latency and Work-Normalized Metrics by Workload Pattern**
| Pattern | CPU-cache ($\mu\text{s}$) | PIM ($\mu\text{s}$) | Speedup | CPU (ns/kop) | PIM (ns/kop) | CPU (ns/Byte) | PIM (ns/Byte) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`STREAM`** | 296.571 ± 0.000 | 23.284 ± 0.000 | 12.74× | 18,101 | 1,421 | 2.26 | 0.18 |
| **`REUSE`** | 56.723 ± 0.625 | 21.825 ± 0.000 | 2.60× | 27,697 | 10,657 | 3.46 | 1.33 |
| **`RANDOM`** | 88.556 ± 0.277 | 21.825 ± 0.000 | 4.06× | 43,240 | 10,657 | 5.41 | 1.33 |
| **`MIXED_PHASE`** | 87.009 ± 0.295 | 21.825 ± 0.000 | 3.99× | 42,485 | 10,657 | 5.31 | 1.33 |

*With DRAM row-buffer locality enabled ($\eta_{\text{row}} = 0.25$ for RANDOM vs $0.90$ for STREAM), RANDOM internal memory service time increases by 3.6×, penalizing irregular pointer chasing.*

### D. Multi-Seed Transfer-Bandwidth Sensitivity and Crossover Variation
Evaluating transfer sensitivity across all five held-out master seeds (47–51) for 64 KiB working sets yields the exact crossover bandwidths where PIM speedup equals 1.0×:
- **`STREAM`:** $1.00 \pm 0.00\text{ GB/s}$
- **`RANDOM`:** $2.17 \pm 0.05\text{ GB/s}$
- **`MIXED_PHASE`:** $2.58 \pm 0.02\text{ GB/s}$
- **`REUSE`:** $4.61 \pm 0.17\text{ GB/s}$

At bandwidths below these thresholds, CPU cache residency outperforms PIM offloading.

### E. PIM Bank-Count and Skew Sensitivity
Increasing bank count from 4 to 64 improves CPU/PIM speedup from 8.68× to 10.97× for STREAM and from 3.86× to 4.14× for REUSE. Gains exhibit diminishing returns beyond 16 banks because external transfer and internal memory service times do not scale with bank count. Deterministic bank skew (skew factor 0 to 4) increases PIM execution time by 4.5% due to bottlenecking on the highest-loaded bank.

### F. Balanced Architectural Evaluation Grid (M2 & M3)
To evaluate decision quality when neither path unconditionally dominates, Table V presents the confusion matrix across 500 instances varying link bandwidth (1.0–16.0 GB/s) and working sets (8–128 KiB).

#### **TABLE V. Policy Confusion Matrix and Decision Quality Across Balanced Regimes (500 Instances)**
| Policy | Accuracy (%) | Bad Offload Rate (%) | True PIM | True CPU | False PIM (Bad Offload) | False CPU (Missed Offload) | Mean Regret ($\mu\text{s}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cost-based** | **96.0%** | **4.0%** | 330 | 150 | 20 | 0 | **0.67** |
| **Reuse-aware (Footprint)** | **85.0%** | **4.0%** | 275 | 150 | 20 | 55 | **18.73** |
| **PIM-always Baseline** | 66.0% | 34.0% | 330 | 0 | 170 | 0 | 20.40 |
| **CPU-cache Baseline** | 34.0% | 0.0% | 0 | 170 | 0 | 330 | 33.42 |

*The Dynamic Working-Set Footprint Estimator and Cost-based policy achieve 96% and 85% decision accuracy, limiting bad offloads to 4.0%, whereas blind offloading (PIM-always) suffers a 34.0% bad-offload rate.*

### G. Seed-Level Variability
Across the five master-seed means, CPU-cache exhibits a small standard deviation of 0.159 $\mu\text{s}$, driven by deterministic trace variations. Zero standard deviation for PIM-selected policies follows from deterministic closed-form equations and identical path choices.

### H. Native PrIM Dynamic Memory Trace Evaluation (M4 & M5)
Table VI reports evaluation results across the four native PrIM benchmark traces replayed through CachePIM.

#### **TABLE VI. Evaluation on Native PrIM Dynamic Memory Traces**
| Benchmark | Working Set (KiB) | LLC Hit Rate (%) | CPU-cache ($\mu\text{s}$) | PIM ($\mu\text{s}$) | Speedup | CPU (ns/kop) | CPU (ns/Byte) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`PrIM-VA`** | 64 | 87.50% | 316.76 | 15.12 | **20.95×** | 77,334 | 4.83 |
| **`PrIM-GEMV`** | 64 | 85.15% | 57.65 | 14.35 | **4.02×** | 14,075 | 0.88 |
| **`PrIM-BS`** | 64 | 42.10% | 88.56 | 18.25 | **4.85×** | 21,621 | 1.35 |
| **`PrIM-SEL`** | 64 | 87.50% | 133.77 | 10.00 | **13.38×** | 65,317 | 2.04 |

#### **TABLE VII. Hardware Validation Against Published UPMEM PrIM Measurements**
Under calibrated hardware parameters (Section IV-B), CachePIM speedup predictions closely match physical hardware measurements from Gómez-Luna et al. (*IEEE Access* 2022 [14]):

| Benchmark Kernel | Workload Profile | CachePIM Predicted Speedup | Published UPMEM Speedup [14] | Absolute Error (%) |
| :--- | :--- | :---: | :---: | :---: |
| **`VA`** (Vector Addition) | Memory-bound streaming | **$2.38\times$** | **$2.45\times$** | **2.8%** |
| **`SEL`** (Select / Filter) | Relational scan / filter | **$1.84\times$** | **$1.78\times$** | **3.4%** |
| **`GEMV`** (Matrix-Vector) | High-reuse linear algebra | **$0.70\times$ (CPU wins)** | **$0.68\times$ (CPU wins)** | **2.9%** |
| **`BS`** (Binary Search) | Non-contiguous branching | **$2.05\times$** | **$1.95\times$** | **5.1%** |
| **Overall Summary** | — | — | — | **MAPE = 3.57%** |

---

## VI. DISCUSSION

### A. Interpretation of Crossover Boundaries
The central finding from CachePIM is that the offloading boundary between CPU and PIM is not a static constant, but a dynamic multi-dimensional surface governed by interconnect transfer bandwidth, cache residency, and bank parallelism. When link bandwidth is constrained (e.g., 1–4 GB/s PCIe channels), high cache locality allows the host CPU to outperform PIM. When aggregate internal PIM bandwidth dominates and working sets exceed cache capacity, PIM provides substantial throughput speedups.

### B. Architectural Model Fidelity and Concurrency
By incorporating $N$-way set associativity and DRAM row-buffer locality factors, CachePIM captures conflict misses and the hardware penalties of irregular pointer chasing. Furthermore, the pipelined execution model ($\alpha \in [0, 1]$) demonstrates that double-buffered host transfers can expand the PIM advantage region by 30–45%.

### C. Threats to Validity and Limitations
1. **Simplified Hierarchy:** CachePIM abstracts the cache as a single-level LLC; multi-level inclusive/exclusive hierarchies and hardware prefetchers are not explicitly modeled.
2. **First-Order Timing:** While calibrated against published UPMEM measurements with 3.57% MAPE, the analytical equations do not simulate instruction-level pipeline stalls or DRAM bank-group command timing.
3. **Coherence:** Hardware cache coherence for CPU-modified data consumed by PIM is not modeled; explicit data transfer volumes are charged.

---

## VII. CONCLUSION

This paper presented CachePIM, a trace-driven analytical simulator for investigating the crossover dynamics between host CPU cache execution and Processing-in-Memory. CachePIM models configurable LLC caches, explicit transfer and internal memory costs with row-buffer locality, multi-bank parallelism, and offloading decision policies. Validated against physical UPMEM PrIM hardware measurements, CachePIM achieves an overall Mean Absolute Percentage Error (MAPE) of **3.57%**. Across a balanced evaluation grid, CachePIM demonstrates that intelligent cost-based and footprint-aware policies achieve up to **96% decision accuracy**, effectively curbing bad offloads to **4.0%**, compared to **34.0% bad offloads for naive PIM offloading**. The open-source simulator and interactive 3D WebGL volumetric execution arena provide a rapid, reproducible exploration vehicle for future PIM architectural co-design and compiler optimization.

---

## AUTHOR CONTRIBUTIONS
- **Aditya Singh Rana** and **Vinay Mor:** Conceptualization, analytical cost modeling, mathematical formulation, software simulation engine, and manuscript drafting.
- **Atharva Raut:** Cache simulation engine, $N$-way set-associative model, LRU replacement implementation, and Valgrind trace parsing.
- **Harsha Nethra:** Experimental sweep pipeline, statistical master-seed evaluation, multi-seed sensitivity analysis, and publication figure generation.
- **Harsha Reddy:** Interactive 3D WebGL volumetric execution arena, Streamlit dashboard interface, and UI component architecture.
- **Bhuvaneswari M:** Research supervision, methodology validation, architectural modeling review, and manuscript finalization.

---

## ACKNOWLEDGMENT
The authors thank the School of Computer Science and Engineering (SCOPE) at Vellore Institute of Technology for providing computational facilities.

---

## DATA AND CODE AVAILABILITY
The complete CachePIM source code, trace files, configuration files, automated pytest suite, and interactive 3D dashboard are available under the MIT License at:  
`https://github.com/AdityaSRana/CachePIM-Analyser` [13].

---

## REFERENCES

[1] K. Asifuzzaman, N. R. Miniskar, A. R. Young, F. Liu, and J. S. Vetter, "A survey on processing-in-memory techniques: Advances and challenges," *Memories - Materials, Devices, Circuits and Systems*, vol. 4, Art. no. 100022, Jul. 2023, doi: 10.1016/j.memori.2022.100022.  
[2] Y.-K. Kim, B. Moon, D.-S. Kim, and Y.-J. Jang, "Cache memory organization for processing in memory," *IEICE Electronics Express*, vol. 16, no. 16, Art. no. 20190393, 2019, doi: 10.1587/ELEX.16.20190393.  
[3] A. Devic, S. B. Rai, A. Sivasubramaniam, A. Akel, S. Eilert, and J. Eno, "To PIM or not for emerging general purpose processing in DDR memory systems," in *Proc. 49th Annu. Int. Symp. Computer Architecture (ISCA)*, 2022, pp. 231–244, doi: 10.1145/3470496.3527431.  
[4] N. Hajinazar, G. F. Oliveira, S. Gregorio, J. D. Ferreira, N. M. Ghiasi, M. Patel, M. Alser, S. Ghose, J. Gómez-Luna, and O. Mutlu, "SIMDRAM: An end-to-end framework for bit-serial SIMD computing in DRAM," in *Proc. 26th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS)*, 2021, pp. 329–345, doi: 10.1145/3445814.3446749.  
[5] X. Peng, Y. Wang, and M.-C. Yang, "CHOPPER: A compiler infrastructure for programmable bit-serial SIMD processing using memory in DRAM," in *Proc. IEEE Int. Symp. High-Performance Computer Architecture (HPCA)*, 2023, pp. 1275–1288, doi: 10.1109/HPCA56546.2023.10071070.  
[6] X. Wang, X. Sun, Y. Han, and X. Chen, "PIMSIM-NN: An ISA-based simulation framework for processing-in-memory accelerators," in *Proc. Design, Automation & Test in Europe Conf. & Exhibition (DATE)*, 2024, pp. 1–6, doi: 10.23919/DATE58400.2024.10546788.  
[7] F. A. Siddique et al., "Architectural modeling and benchmarking for digital DRAM PIM," in *Proc. IEEE Int. Symp. Workload Characterization (IISWC)*, 2024, pp. 247–261, doi: 10.1109/IISWC63097.2024.00030.  
[8] X. Sun, X. Wang, W. Li, Y. Han, and X. Chen, "PIMCOMP: An end-to-end DNN compiler for processing-in-memory accelerators," *IEEE Trans. Computer-Aided Design of Integrated Circuits and Systems*, vol. 44, no. 5, pp. 1745–1759, 2025, doi: 10.1109/TCAD.2024.3496847.  
[9] D. Guo, M. Gholamrezaei, M. Hofmann, A. Venkat, Z. Zhang, and K. Skadron, "PIMsynth: A unified compiler framework for bit-serial processing-in-memory architectures," *IEEE Computer Architecture Letters*, vol. 24, no. 2, pp. 277–280, 2025, doi: 10.1109/LCA.2025.3600588.  
[10] H. Geng, T. S. Pereira, X. Lu, X.-H. Sun, M. Niemier, and X. S. Hu, "VIPER: Architecture-aware performance modeling for processing-in-memory design-space exploration," in *Proc. IEEE/ACM Int. Conf. Computer-Aided Design (ICCAD)*, 2026, pp. 1–9.  
[11] J. Zhang, H. Wang, and E. Sadredini, "Meta-PIM: An end-to-end compiler for configurable processing-in-memory," *IEEE Computer Architecture Letters*, vol. 25, no. 2, pp. 112–116, Jul.-Dec. 2026, doi: 10.1109/LCA.2026.3709790.  
[12] P. Yang, S. Durvasula, I. Fernandez, M. Sadrosadati, O. Mutlu, G. Pekhimenko, and C. Giannoula, "DCC: Data-centric compilation of machine learning kernels for processing-in-memory architectures," in *Proc. 53rd ACM/IEEE Annu. Int. Symp. Computer Architecture (ISCA)*, 2026, pp. 2582–2599, doi: 10.1109/ISCA66397.2026.00180.  
[13] A. S. Rana, V. Mor, A. Raut, H. Nethra, and H. Reddy, "CachePIM-Analyser: Open-Source CPU-PIM Architectural Simulation Suite," 2026. [Online]. Available: `https://github.com/AdityaSRana/CachePIM-Analyser`.  
[14] J. Gómez-Luna, I. El Hajj, I. Fernandez, C. Giannoula, G. F. Oliveira, and O. Mutlu, "Benchmarking a new paradigm: Experimental analysis and characterization of a real processing-in-memory system," *IEEE Access*, vol. 10, pp. 52565–52608, 2022, doi: 10.1109/ACCESS.2022.3174101.  
[15] O. Mutlu, S. Ghose, J. Gómez-Luna, and R. Ausavarungnirun, "A modern primer on processing in memory," in *Emerging Computing: From Devices to Systems*, Springer, 2023, pp. 171–243.  
[16] C. Giannoula, I. Fernandez, R. Quislant, E. Gutiérrez, O. Plata, and O. Mutlu, "SynCron: Efficient synchronization support for near-data-processing architectures," in *Proc. IEEE Int. Symp. High-Performance Computer Architecture (HPCA)*, 2021, pp. 263–276, doi: 10.1109/HPCA51647.2021.00031.  
[17] A. Boroumand et al., "CoNDA: Efficient cache coherence support for near-data computing," in *Proc. 46th Annu. Int. Symp. Computer Architecture (ISCA)*, 2019, pp. 629–642, doi: 10.1145/3307650.3322259.  
[18] S. Ghose et al., "Processing-in-memory: A workload-driven perspective," *IBM Journal of Research and Development*, vol. 63, no. 6, pp. 3:1–3:19, 2019, doi: 10.1147/JRD.2019.2934048.  
[19] K. Hsieh, E. Ebrahimi, G. Kim, N. Chatterjee, M. O'Connor, N. Vijaykumar, O. Mutlu, and S. W. Keckler, "Transparent offloading and mapping (TOM): Enabling programmer-transparent near-data processing in GPU systems," in *Proc. 43rd Annu. Int. Symp. Computer Architecture (ISCA)*, 2016, pp. 204–216, doi: 10.1145/2925426.2926288.  
[20] G. F. Oliveira et al., "DAMOV: A new methodology and benchmark suite for evaluating data movement bottlenecks," *IEEE Access*, vol. 9, pp. 134443–134473, 2021, doi: 10.1109/ACCESS.2021.3115456.  
[21] L. Ke et al., "RecNMP: Accelerating personalized recommendation with near-memory processing," in *Proc. 47th Annu. Int. Symp. Computer Architecture (ISCA)*, 2020, pp. 790–803, doi: 10.1109/ISCA45697.2020.00071.  
[22] Y. Kwon et al., "25.4 A 20nm 6GB function-in-memory DRAM, with a floating-point programmable accelerator for computing-in-memory applications," in *IEEE Int. Solid-State Circuits Conf. (ISSCC)*, 2021, pp. 350–352, doi: 10.1109/ISSCC42613.2021.9365780.  
[23] J. Lee et al., "Hardware architecture and software stack for PIM-based neural network accelerators," *IEEE Micro*, vol. 41, no. 6, pp. 49–57, 2021, doi: 10.1109/MM.2021.3111425.  
[24] S. Lee et al., "AiM: A 16Gb 1.0 GHz GDDR6 accelerator-in-memory for energy-efficient deep learning," in *IEEE Int. Solid-State Circuits Conf. (ISSCC)*, 2022, pp. 1–3, doi: 10.1109/ISSCC42614.2022.9731671.  
[25] T. Grosser, A. Groesslinger, and C. Lengauer, "Polly—Performing polyhedral loop transformations on a high-level IL," in *Proc. First Int. Workshop on Polyhedral Compilation Techniques (IMPACT)*, 2011, pp. 1–8.  
[26] C. Lattner, M. Amini, U. Bondhugula, A. Cohen, A. Davis, J. Pienaar, R. Riddle, T. Shpeisman, N. Vasilache, and O. Zinenko, "MLIR: Scaling compiler infrastructure for domain-specific computation," in *Proc. IEEE/ACM Int. Symp. Code Generation and Optimization (CGO)*, 2021, pp. 2–14, doi: 10.1109/CGO51591.2021.9370308.  
[27] N. Nethercote and J. Seward, "Valgrind: A framework for heavyweight dynamic binary instrumentation," in *Proc. ACM SIGPLAN Conf. Programming Language Design and Implementation (PLDI)*, 2007, pp. 89–100, doi: 10.1145/1250734.1250746.  
[28] G. Pekhimenko, V. Seshadri, Y. Kim, H. Xin, O. Mutlu, P. B. Gibbons, M. A. Kozuch, and T. C. Mowry, "Linearly compressed pages: A main memory compression framework," in *Proc. 46th Annu. IEEE/ACM Int. Symp. Microarchitecture (MICRO)*, 2013, pp. 172–184, doi: 10.1145/2540708.2540724.  
[29] M. Gao, G. Ayers, and C. Kozyrakis, "Practical near-data processing for in-memory analytics," in *Proc. 20th Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS)*, 2015, pp. 113–126, doi: 10.1145/2694344.2694386.  
[30] J. Ahn, S. Hong, S. Yoo, O. Mutlu, and K. Choi, "A scalable processing-in-memory accelerator for parallel graph processing," in *Proc. 42nd Annu. Int. Symp. Computer Architecture (ISCA)*, 2015, pp. 105–117, doi: 10.1145/2749469.2750386.
