#!/usr/bin/env python3
"""Generate itemized discrepancies log and claim-by-claim paper audit for CachePIM Verification."""

from pathlib import Path
import pandas as pd


def generate_discrepancies_csv(out_dirs: list[Path]):
    discrepancies = [
        {
            "Discrepancy_ID": "DISC-01",
            "Category": "Workload & Trace Provenance",
            "Title": "Table VI Synthetic Preset Provenance Misattribution",
            "Paper_Location": "Section V-B, Table VI",
            "Original_Claim_or_Behavior": "Table VI presented results as native dynamic memory traces collected via Valgrind Lackey on PrIM benchmarks.",
            "Verified_Finding": "Table VI numbers (VA: 316.76 / 15.12 / 20.95x; GEMV: 57.65 / 14.35 / 4.02x; SEL: 133.77 / 10.00 / 13.38x; BS: 88.56 / 15.68 / 5.65x) were generated from 64 KiB synthetic presets, NOT native Lackey traces. Native traces have 60,000 accesses, 97.7-99.8% hit rate, and 24.4x-31.6x speedup.",
            "Severity": "Critical",
            "Root_Cause": "Synthetic preset benchmark script output was mistakenly copied into Table VI under the native trace label during manuscript assembly.",
            "Status": "Confirmed & Proven",
            "Resolution": "Provide clear dual reporting in Table VI: distinctly tabulate Native Lackey Traces vs Synthetic Presets in results/verification/corrected/table_vi_real_vs_synthetic.csv."
        },
        {
            "Discrepancy_ID": "DISC-02",
            "Category": "Architectural Cost Modeling",
            "Title": "Row-Buffer Locality Inactive in Baseline Table IV",
            "Paper_Location": "Section IV-C, Section V-A, Table IV",
            "Original_Claim_or_Behavior": "Text states DRAM row-buffer factor eta_row is 0.90 for STREAM, 0.60 for REUSE, and 0.25 for RANDOM.",
            "Verified_Finding": "Table IV reported identical PIM time (21.825 us) across REUSE, RANDOM, and MIXED_PHASE because row_buffer_locality_enabled defaulted to False in config.py.",
            "Severity": "Major",
            "Root_Cause": "PIMConfig.row_buffer_locality_enabled was False by default; getattr returned False and forced eta_row = 1.0.",
            "Status": "Confirmed & Fixed",
            "Resolution": "Config wired to enable row-buffer locality when requested. Table IV regenerated under both Flat PIM (21.825 us) and Row-Buffer PIM (STREAM 7.78 us, REUSE 7.82 us, RANDOM 9.61 us)."
        },
        {
            "Discrepancy_ID": "DISC-03",
            "Category": "Policy Algorithm Formulation",
            "Title": "Eq. (8) Unphysical CPU Credit & Over-crediting",
            "Paper_Location": "Section IV-D, Eq. (8)",
            "Original_Claim_or_Behavior": "Eq. (8) subtracted temporal credit: delta_t = N_hits * t_hit * 0.5 * (C / W) when W <= C.",
            "Verified_Finding": "When W <= C/2, C/W >= 2.0, so the credit exceeded 100% of the total hit service time, making CPU appear artificially free and causing 40-70 false-CPU missed offloads.",
            "Severity": "Major",
            "Root_Cause": "Unclamped formulation lacked dimensional ceiling and upper bound on cache hit latency credit.",
            "Status": "Confirmed & Fixed",
            "Resolution": "Clamped temporal credit physically to min(hits * t_hit, hits * t_hit * 0.25 * fit_ratio) and tuned on dev seeds 42-46."
        },
        {
            "Discrepancy_ID": "DISC-04",
            "Category": "Policy Evaluation & Regret Claims",
            "Title": "Cost-Based Policy Strictly Outperforms Reuse-Aware Policy",
            "Paper_Location": "Abstract, Section V-C, Table V",
            "Original_Claim_or_Behavior": "Abstract claimed Dynamic Footprint Estimator policy reduces decision regret and achieves superior performance.",
            "Verified_Finding": "Cost-based policy strictly outperforms Reuse-aware policy: Cost-based achieves 96.0% accuracy, 4.0% bad offload rate, 0.671 us regret, and 0 missed offloads, whereas Reuse-aware achieves 82-88% accuracy, 18.68 us regret, and 40-70 missed offloads.",
            "Severity": "Critical",
            "Root_Cause": "Heuristic credit distortion impairs analytical cost comparisons. Direct analytical cost comparison naturally captures cache residency without heuristic penalties.",
            "Status": "Confirmed & Documented (Honest Negative Result)",
            "Resolution": "Acknowledge as a key scientific finding: recommend Cost-based policy as gold standard; document why heuristic hit-credit adjustments fail to beat direct analytical cost comparison."
        },
        {
            "Discrepancy_ID": "DISC-05",
            "Category": "Manuscript Presentation",
            "Title": "Table V Caption Swapped Accuracy Figures",
            "Paper_Location": "Section V-C, Table V Caption",
            "Original_Claim_or_Behavior": "Caption under Table V swapped the 96% and 85% figures between Cost-based and Reuse-aware.",
            "Verified_Finding": "Table V body reported Cost-based 96% and Reuse-aware 85%, but the caption text incorrectly attributed 96% to Reuse-aware.",
            "Severity": "Moderate",
            "Root_Cause": "Editorial transposition during manuscript revision.",
            "Status": "Confirmed & Corrected",
            "Resolution": "Corrected Table V caption in final report to accurately reflect that Cost-based achieved 96.0% and Reuse-aware achieved 88.0% (clamped) / 82.0% (uncorrected)."
        },
        {
            "Discrepancy_ID": "DISC-06",
            "Category": "Experimental Sweeps & Claims",
            "Title": "Abstract Crossover Latency & Sweep Range Discrepancy",
            "Paper_Location": "Abstract, Section V-D",
            "Original_Claim_or_Behavior": "Abstract claimed '1.45x CPU advantage at 1-4 GB/s' and '2.45x at >16 GB/s'.",
            "Verified_Finding": "The paper contains no sweep above 16 GB/s. At 1 GB/s, REUSE showed ~4.3x CPU advantage, and 2.45x was actually the static published UPMEM VA speedup point in Table VII.",
            "Severity": "Moderate",
            "Root_Cause": "Conflation of sweep endpoint values and single-kernel validation speedups in executive text.",
            "Status": "Confirmed & Documented",
            "Resolution": "Replace with exact sweep endpoints: 'CPU achieves up to 4.3x advantage under constrained 1.0 GB/s link, while PIM delivers up to 2.38x-2.45x speedup under high bandwidth (16 GB/s).'"
        },
        {
            "Discrepancy_ID": "DISC-07",
            "Category": "Provenance & Configuration",
            "Title": "Configuration SHA-256 Hash Stagnation",
            "Paper_Location": "Section IV, Section V",
            "Original_Claim_or_Behavior": "Config hash reported in paper as ac915cd97def15fd.",
            "Verified_Finding": "Hash ac915cd97def15fd corresponds to the frozen Oct 13 snapshot. The current codebase produces fff7e9ba223ae65a because ways, overlap_factor, row_buffer_locality_enabled, and use_footprint_estimator were added to dataclasses.",
            "Severity": "Minor",
            "Root_Cause": "Configuration dataclasses expanded without recomputing and updating the printed hash in the manuscript text.",
            "Status": "Confirmed & Resolved",
            "Resolution": "Explicitly document the configuration hash lineage: ac915cd97def15fd (v1.0 baseline) and fff7e9ba223ae65a (v1.1 verified extended)."
        },
        {
            "Discrepancy_ID": "DISC-08",
            "Category": "Validation & Calibration",
            "Title": "Hardware Calibration Limited to 4 In-Sample Kernels",
            "Paper_Location": "Section IV-B, Table VII",
            "Original_Claim_or_Behavior": "Table VII reported hardware calibration with MAPE = 3.57% across VA, SEL, GEMV, BS.",
            "Verified_Finding": "Arithmetic was verified exact (2.86%, 3.37%, 2.94%, 5.13%), but VA error was printed as 2.8% instead of rounding to 2.9%, and validation lacked leave-one-out cross validation and independent held-out kernels.",
            "Severity": "Moderate",
            "Root_Cause": "Limited validation reporting without cross-validation fold details.",
            "Status": "Confirmed & Augmented",
            "Resolution": "Generated 4-fold leave-one-out cross-validation (train MAPE 3.06-3.81%, test error 2.86-5.13%) and evaluated 4 independent held-out kernels (RED, HST, SpMV, BFS) in results/verification/calibration_results.csv."
        },
        {
            "Discrepancy_ID": "DISC-09",
            "Category": "Benchmark Suite Completeness",
            "Title": "Omission of PrIM Presets Favoring CPU (RED, HST, SpMV, BFS)",
            "Paper_Location": "Section III, Section V-B",
            "Original_Claim_or_Behavior": "Paper restricted evaluation to 4 kernels (VA, GEMV, BS, SEL) stating only these 4 were in the frontend.",
            "Verified_Finding": "Code contained 8 presets. The 4 omitted kernels (HST, SpMV, BFS, RED) actually favor the CPU under realistic links (1 GB/s) and row-buffer misses (e.g. HST speedup 0.36x = CPU 2.78x faster).",
            "Severity": "Major",
            "Root_Cause": "Pruning of workloads for frontend simplicity inadvertently biased paper towards PIM-friendly kernels.",
            "Status": "Confirmed & Evaluated",
            "Resolution": "Evaluated all 4 omitted kernels under baseline and calibrated configurations in results/verification/corrected/dropped_presets_evaluation.csv."
        },
        {
            "Discrepancy_ID": "DISC-10",
            "Category": "Cache Modeling",
            "Title": "Set Associativity Insensitivity for In-Cache Footprints",
            "Paper_Location": "Section IV-C (M6)",
            "Original_Claim_or_Behavior": "Paper claimed N-way set associativity captured conflict misses across all evaluations.",
            "Verified_Finding": "For W <= 32 KiB on a 32 KiB cache, uniform indexing across cache sets causes 0 conflict misses, so hit rates are identical across FA, 16-way, 8-way, and 4-way. Conflict misses only appear at W >= 64 KiB, where they flip exactly 19 of 500 decisions (3.8%).",
            "Severity": "Moderate",
            "Root_Cause": "Synthetic sequential addresses map uniformly across sets; conflict misses only occur when lines exceed set capacity.",
            "Status": "Confirmed & Clarified",
            "Resolution": "Documented exact geometry mechanics and generated associativity sensitivity sweep across 16-128 KiB in results/verification/corrected/associativity_sweep.csv."
        },
        {
            "Discrepancy_ID": "DISC-11",
            "Category": "Statistical Methodology",
            "Title": "Multi-Seed Sweep Analytical Determinism (Zero Variance)",
            "Paper_Location": "Section V-E, Fig 8 / Sweeps",
            "Original_Claim_or_Behavior": "Manuscript discussed multi-seed variability across master seeds 47-51 for bank count and skew sweeps.",
            "Verified_Finding": "CachePIM's analytical equations for bank count and bank skew are strictly deterministic functions of operation count and descriptor parameters, yielding mathematical zero variance across seeds for identical inputs.",
            "Severity": "Minor",
            "Root_Cause": "Analytical cost formulas evaluate deterministically; random seed only affects address generation, not bank division arithmetic.",
            "Status": "Confirmed & Documented",
            "Resolution": "Documented zero variance across seeds 47-51 in results/verification/corrected/multiseed_bank_count_sweep.csv and multiseed_bank_skew_sweep.csv."
        },
        {
            "Discrepancy_ID": "DISC-12",
            "Category": "Compiler Integration",
            "Title": "Compiler Prototype Scope Misclassification",
            "Paper_Location": "Section IV-E",
            "Original_Claim_or_Behavior": "Section IV-E described compiler-driven offloading, polyhedral analysis, and loop transformation.",
            "Verified_Finding": "Codebase contains an analytical loop descriptor demo script (compiler_demo.py), not an actual LLVM IR, Polly, or MLIR compiler lowering pipeline.",
            "Severity": "Moderate",
            "Root_Cause": "Conceptual compiler architecture described as an implemented subsystem rather than an analytical loop-descriptor prototype.",
            "Status": "Confirmed & Clarified",
            "Resolution": "Reframe Section IV-E as an 'Analytical Loop-Descriptor Prototype' and provide exact demonstration in results/verification/corrected/compiler_demo.csv."
        },
        {
            "Discrepancy_ID": "DISC-13",
            "Category": "Trace Instrumentation",
            "Title": "Valgrind Lackey Trace Pure Memory Access Stream",
            "Paper_Location": "Section III, Section V-B",
            "Original_Claim_or_Behavior": "Traces described as comprehensive application execution profiles.",
            "Verified_Finding": "All 4 trace files contain exactly 60,000 data memory references (L/S/M records) with zero instruction fetch (I) records, representing pure memory stream sampling without CPU instruction overhead.",
            "Severity": "Minor",
            "Root_Cause": "Valgrind Lackey invoked with default memory-access tracing flags omitting instruction records.",
            "Status": "Confirmed & Documented",
            "Resolution": "Explicitly document Lackey trace composition in results/verification/trace_manifest.csv and manuscript methodology."
        },
        {
            "Discrepancy_ID": "DISC-14",
            "Category": "Architectural Scope",
            "Title": "Single-Level LLC Modeling vs Multi-Level Text Claims",
            "Paper_Location": "Section IV-D, Section VI-C",
            "Original_Claim_or_Behavior": "Eq. (8) text mentioned L1/L2 hits while Section VI-C acknowledged single-level LLC.",
            "Verified_Finding": "Simulator models a single-level LLC cache. There is no multi-level L1/L2/L3 cache hierarchy or hardware prefetcher in the simulation engine.",
            "Severity": "Minor",
            "Root_Cause": "Descriptive terminology in Eq. (8) motivation conflated conceptual L1/L2 hits with modeled LLC hits.",
            "Status": "Confirmed & Corrected",
            "Resolution": "Standardize all text to describe the model strictly as a single-level LLC cache with 2.0 ns hit latency."
        },
        {
            "Discrepancy_ID": "DISC-15",
            "Category": "Scholarly References",
            "Title": "Reference Metadata and DOI Inaccuracies",
            "Paper_Location": "References Section ([10], [11], [12])",
            "Original_Claim_or_Behavior": "References [10], [11], [12] cited with specific DOIs, journal volumes, and page ranges.",
            "Verified_Finding": "Ref [10] (Lee et al.) cites IEEE Trans. Computers with forward-dated / non-standard metadata; Ref [11] (Zhang et al., CAL) has unverifiable DOI format; Ref [12] (Yang et al., ISCA) has unconfirmed conference pagination.",
            "Severity": "Moderate",
            "Root_Cause": "Hallucinated or placeholder citation strings inserted during prior LLM editing passes.",
            "Status": "Confirmed & Flagged",
            "Resolution": "Flag citations as UNVERIFIED / PLACEHOLDER in paper claim audit and provide corrected verified reference entries."
        }
    ]

    df = pd.DataFrame(discrepancies)
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        out_csv = od / "discrepancies.csv"
        df.to_csv(out_csv, index=False)
        print(f"Wrote discrepancies to {out_csv}")


def generate_paper_claim_audit_csv(out_dirs: list[Path]):
    claims = [
        {
            "Claim_ID": "CLM-01",
            "Paper_Version": "Revised MD & Original PDF",
            "Section": "Abstract / Introduction",
            "Text_Excerpt": "CachePIM provides transparent, high-throughput analytical simulation evaluating thousands of configurations in seconds.",
            "Claim_Category": "Performance / Throughput",
            "Evidence_Source": "results/verification/corrected/runtime_benchmark.json",
            "Verified_Finding": "Simulator executes 1,000 complete evaluations (cache simulate + CPU + PIM + policy) in ~4.8 seconds (208 evals/sec). Pure analytical evaluations exceed 15,000 evals/sec.",
            "Status": "SUPPORTED",
            "Required_Correction": "None; claim is mathematically and empirically validated."
        },
        {
            "Claim_ID": "CLM-02",
            "Paper_Version": "Revised MD & Original PDF",
            "Section": "Abstract",
            "Text_Excerpt": "1.45x CPU advantage under PCIe-constrained transfer regimes (1-4 GB/s) and 2.45x PIM advantage at >16 GB/s.",
            "Claim_Category": "Crossover Latency",
            "Evidence_Source": "results/verification/corrected/table_v_balanced_grid.csv & overlap_alpha_sweep.csv",
            "Verified_Finding": "At 1 GB/s, CPU achieves up to 4.3x advantage for REUSE. The paper contains no sweep >16 GB/s; 2.45x was the static published UPMEM VA point in Table VII.",
            "Status": "CONTRADICTED",
            "Required_Correction": "Correct abstract to: 'CPU achieves up to 4.3x advantage under constrained 1.0 GB/s link, while PIM delivers up to 2.38x-2.45x speedup under high bandwidth (16 GB/s).'"
        },
        {
            "Claim_ID": "CLM-03",
            "Paper_Version": "Revised MD",
            "Section": "Abstract / Section V-C",
            "Text_Excerpt": "Dynamic Working-Set Footprint Estimator policy reduces decision regret and achieves up to 96% accuracy.",
            "Claim_Category": "Policy Evaluation",
            "Evidence_Source": "results/verification/corrected/table_v_balanced_grid.csv",
            "Verified_Finding": "Cost-based policy achieves 96.0% accuracy and 0.671 us regret. Reuse-aware achieves 82.0% (uncorrected) / 88.0% (clamped) and 18.68 us regret with 40-70 missed offloads.",
            "Status": "CONTRADICTED",
            "Required_Correction": "Reframe honestly: Cost-based policy is the gold standard (96.0% accuracy, 0.671 us regret); footprint credit heuristic at best achieves 88.0% and suffers 40 missed offloads."
        },
        {
            "Claim_ID": "CLM-04",
            "Paper_Version": "Revised MD & Original PDF",
            "Section": "Section IV-C, Table I",
            "Text_Excerpt": "DRAM row-buffer locality factor eta_row is 0.90 for STREAM, 0.60 for REUSE, and 0.25 for RANDOM.",
            "Claim_Category": "PIM Modeling",
            "Evidence_Source": "cachepim/pim_model.py & results/verification/corrected/table_iv_baseline_comparison.csv",
            "Verified_Finding": "Model formulas support eta_row, but default config had row_buffer_locality_enabled=False, causing Table IV to report flat PIM (21.825 us) across patterns.",
            "Status": "PARTIALLY_SUPPORTED",
            "Required_Correction": "Explicitly report Table IV under both Flat PIM (21.825 us @ 64 KiB) and Row-Buffer PIM (STREAM 7.78 us, REUSE 7.82 us, RANDOM 9.61 us @ 32 KiB)."
        },
        {
            "Claim_ID": "CLM-05",
            "Paper_Version": "Revised MD",
            "Section": "Section IV-C (M6)",
            "Text_Excerpt": "N-way set-associative cache model captures conflict misses across all benchmark configurations.",
            "Claim_Category": "Cache Modeling",
            "Evidence_Source": "results/verification/corrected/associativity_sweep.csv",
            "Verified_Finding": "Set-associative model is implemented, but for W <= 32 KiB on 32 KiB cache, uniform indexing causes 0 conflict misses. Conflict misses only occur at W >= 64 KiB (flipping 19 of 500 decisions).",
            "Status": "PARTIALLY_SUPPORTED",
            "Required_Correction": "Clarify that conflict misses occur specifically when working set exceeds cache capacity (W >= 64 KiB), where 4-way hit rates drop by 0.5-1.6% compared to fully associative."
        },
        {
            "Claim_ID": "CLM-06",
            "Paper_Version": "Revised MD",
            "Section": "Section IV-C (M8)",
            "Text_Excerpt": "Pipelined host transfer and bank execution model captures double-buffering overlap alpha in [0, 1].",
            "Claim_Category": "Concurrency Modeling",
            "Evidence_Source": "results/verification/corrected/overlap_alpha_sweep.csv",
            "Verified_Finding": "Implemented equation max(T_xfer, T_exec) + (1-alpha)*min(T_xfer, T_exec) reduces latency by up to 29.8% at alpha=1.0.",
            "Status": "SUPPORTED",
            "Required_Correction": "None; verified with complete sensitivity sweep."
        },
        {
            "Claim_ID": "CLM-07",
            "Paper_Version": "Revised MD",
            "Section": "Section V-B, Table VI",
            "Text_Excerpt": "Table VI reports results on native PrIM dynamic memory traces collected via Valgrind Lackey.",
            "Claim_Category": "Trace Provenance",
            "Evidence_Source": "results/verification/table_vi_provenance.csv & table_vi_real_vs_synthetic.csv",
            "Verified_Finding": "Table VI numbers match 64 KiB synthetic presets exactly (VA 316.76 us, GEMV 57.65 us, BS 88.56 us, SEL 133.77 us). Real Lackey traces yield 97.7-99.8% hit rate and 24.4x-31.6x speedup.",
            "Status": "CONTRADICTED",
            "Required_Correction": "Disclose provenance honestly: provide separate dual tables for Native Lackey Traces and Synthetic Presets."
        },
        {
            "Claim_ID": "CLM-08",
            "Paper_Version": "Revised MD",
            "Section": "Section V-B, Table VII",
            "Text_Excerpt": "CachePIM predictions match physical UPMEM PrIM measurements with overall MAPE = 3.57%.",
            "Claim_Category": "Hardware Validation",
            "Evidence_Source": "results/verification/calibration_results.csv",
            "Verified_Finding": "Arithmetic verified exact (VA 2.86%, SEL 3.37%, GEMV 2.94%, BS 5.13%, MAPE 3.57%). VA error rounded to 2.8% instead of 2.9%. Cross-validation confirmed 4-fold test MAPE = 3.57%.",
            "Status": "SUPPORTED",
            "Required_Correction": "Round VA error to 2.9% and include leave-one-out cross validation table and independent held-out kernels (RED, HST, SpMV, BFS)."
        },
        {
            "Claim_ID": "CLM-09",
            "Paper_Version": "Revised MD",
            "Section": "Section III / Section V-B",
            "Text_Excerpt": "PrIM evaluation restricted to VA, GEMV, BS, SEL because other kernels were not supported.",
            "Claim_Category": "Workload Selection",
            "Evidence_Source": "results/verification/corrected/dropped_presets_evaluation.csv",
            "Verified_Finding": "Code contained 8 presets. The 4 omitted kernels (RED, HST, SpMV, BFS) actually favor CPU under realistic links and row-buffer misses (HST speedup 0.36x = CPU 2.78x faster).",
            "Status": "CONTRADICTED",
            "Required_Correction": "Document all 8 presets and report that CPU wins on 3 of the 4 omitted kernels under calibrated parameters."
        },
        {
            "Claim_ID": "CLM-09b",
            "Paper_Version": "Original PDF & Revised MD",
            "Section": "Section V-D, Fig 8",
            "Text_Excerpt": "Multi-seed sensitivity analysis evaluates variability across seeds 47-51 for bank count and skew sweeps.",
            "Claim_Category": "Statistical Methodology",
            "Evidence_Source": "results/verification/corrected/multiseed_bank_count_sweep.csv",
            "Verified_Finding": "Analytical cost formulas for bank count and skew evaluate deterministically; latency variance across seeds 47-51 is mathematically zero.",
            "Status": "CONTRADICTED",
            "Required_Correction": "Clarify that analytical PIM equations are strictly deterministic; seed variation only affects address patterns, not bank load partitioning."
        },
        {
            "Claim_ID": "CLM-10",
            "Paper_Version": "Revised MD",
            "Section": "Section IV-E",
            "Text_Excerpt": "Polyhedral compiler pass analyzes loop nests and lowers kernels directly to PIM binaries.",
            "Claim_Category": "Compiler Integration",
            "Evidence_Source": "results/verification/corrected/compiler_demo.csv",
            "Verified_Finding": "Codebase contains an analytical loop descriptor model (compiler_demo.py), not an LLVM IR or Polly compilation pass.",
            "Status": "CONTRADICTED",
            "Required_Correction": "Reframe Section IV-E as an 'Analytical Loop-Descriptor Prototype' rather than a functional LLVM IR compiler pass."
        },
        {
            "Claim_ID": "CLM-11",
            "Paper_Version": "Revised MD & Original PDF",
            "Section": "Section IV-A",
            "Text_Excerpt": "Configuration hash ac915cd97def15fd uniquely identifies the simulator configuration state.",
            "Claim_Category": "Reproducibility / Hashing",
            "Evidence_Source": "cachepim/config.py & results/manifest.json",
            "Verified_Finding": "ac915cd97def15fd was generated by v1.0 baseline config. The current v1.1 config hash is fff7e9ba223ae65a due to added parameters.",
            "Status": "PARTIALLY_SUPPORTED",
            "Required_Correction": "Report both hashes with their corresponding version numbers and dataclass schemas."
        },
        {
            "Claim_ID": "CLM-12",
            "Paper_Version": "Revised MD & Original PDF",
            "Section": "References",
            "Text_Excerpt": "References [10], [11], [12] provide published citations for PIM compilers and architectures.",
            "Claim_Category": "Scholarly Citations",
            "Evidence_Source": "Manuscript bibliography audit",
            "Verified_Finding": "Ref [10] (Lee et al.) has invalid forward volume date; Ref [11] (Zhang et al.) has non-resolving DOI; Ref [12] (Yang et al.) has unverified conference page numbers.",
            "Status": "UNVERIFIED",
            "Required_Correction": "Replace with verified peer-reviewed publications and valid DOIs."
        }
    ]

    df = pd.DataFrame(claims)
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        out_csv = od / "paper_claim_audit.csv"
        df.to_csv(out_csv, index=False)
        print(f"Wrote paper claim audit to {out_csv}")


if __name__ == "__main__":
    project_dir = Path("CDv2AV/CachePIM-Analyser-corrected").resolve()
    out_dirs = [
        Path("results/verification").resolve(),
        (project_dir / "results" / "verification").resolve()
    ]
    generate_discrepancies_csv(out_dirs)
    generate_paper_claim_audit_csv(out_dirs)

