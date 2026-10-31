# CachePIM Reproduction Commands Guide

This document provides exact, end-to-end command lines to execute and reproduce every verified table, figure, sweep, parameter manifest, and audit finding from scratch.

---

## 1. Environment Setup

All commands assume a local Windows environment with Python 3.13. No external internet or GitHub access is required.

```powershell
# Navigate to the project directory
cd C:\Users\harsh\Desktop\CD_final_5\CDv2AV\CachePIM-Analyser-corrected

# Activate the local virtual environment
.\.venv\Scripts\Activate.ps1

# Verify installed packages and interpreter
python -c "import cachepim, pandas, numpy, pytest, streamlit; print('Environment verified. CachePIM v' + cachepim.__version__)"
```

---

## 2. Regression Testing

Run the full pytest suite to verify that all architectural models, replacement policies, cost estimators, and invariants pass:

```powershell
# Run the complete test suite (39 tests)
python -m pytest tests -v
```

---

## 3. End-to-End Verification Pipeline

Execute the following standalone verification scripts to regenerate all deliverables into `results/verification/`:

### A. Pre-Audit File Inventory & Project Identity
Records file hashes (SHA-256), git commit, and interpreter metadata:
```powershell
python scripts/verification/audit_phase_a_identity.py
# Outputs:
# - results/verification/evidence/pre_audit_file_inventory.csv
# - results/verification/evidence/project_identity_and_environment.json
```

### B. Table VI Provenance Audit
Audits native Lackey memory traces against the historical 64 KiB synthetic presets to reproduce Table VI numbers:
```powershell
python scripts/verification/audit_phase_a_table_vi_provenance.py
# Outputs:
# - results/verification/table_vi_provenance.csv
# - results/verification/evidence/table_vi_detailed_audit.json
```

### C. Parameter Manifest & Trace Manifest
Extracts all architectural/policy parameters, sources, units, calibration status, and parses all 4 Valgrind Lackey memory trace files:
```powershell
python scripts/verification/generate_parameter_and_trace_manifests.py
# Outputs:
# - results/verification/parameter_manifest.json
# - results/verification/trace_manifest.csv
```

### D. Hardware Calibration & Cross-Validation
Calibrates against physical UPMEM PrIM hardware (Gómez-Luna et al., *IEEE Access* 2022), runs 4-fold leave-one-out cross validation, and evaluates held-out kernels (RED, HST, SpMV, BFS):
```powershell
python scripts/verification/generate_calibration_results.py
# Outputs:
# - results/verification/calibration_results.csv
```

### E. Balanced Grid Policy Simulation (Table V)
Simulates all 1,000 grid instances (dev seeds 42–46, held-out seeds 47–51, 4 patterns, 5 working sets, 5 bandwidths) across all 6 policies:
```powershell
python scripts/verification/generate_policy_decisions_and_grid.py
# Outputs:
# - results/verification/policy_decisions.csv (complete 7,000 policy decisions)
# - results/verification/corrected/table_v_balanced_grid.csv (held-out confusion matrix)
```

### F. Regenerated Experiments & Sensitivity Sweeps
Generates Table IV under baseline flat PIM and row-buffer PIM, Table VI real vs. synthetic comparison, dropped preset evaluations, overlap factor sweep, associativity sweep, multi-seed determinism sweeps, runtime profiling, and compiler loop demo:
```powershell
python scripts/verification/generate_corrected_experiments.py
# Outputs:
# - results/verification/corrected/table_iv_baseline_comparison.csv
# - results/verification/corrected/table_iv_original_paper_64kb_ws.csv
# - results/verification/corrected/table_vi_real_vs_synthetic.csv
# - results/verification/corrected/dropped_presets_evaluation.csv
# - results/verification/corrected/overlap_alpha_sweep.csv
# - results/verification/corrected/associativity_sweep.csv
# - results/verification/corrected/multiseed_bank_count_sweep.csv
# - results/verification/corrected/multiseed_bank_skew_sweep.csv
# - results/verification/corrected/runtime_benchmark.json
# - results/verification/corrected/compiler_demo.csv
```

### G. Discrepancy Log & Paper Claim Audit
Compiles itemized discrepancy logs and audit results across all 13 core paper claims:
```powershell
python scripts/verification/generate_discrepancies_and_claim_audit.py
# Outputs:
# - results/verification/discrepancies.csv
# - results/verification/paper_claim_audit.csv
```

---

## 4. One-Click Full Reproduction Script

To run the entire verification suite in a single command:

```powershell
python -c "
import subprocess, sys

scripts = [
    'scripts/verification/audit_phase_a_identity.py',
    'scripts/verification/audit_phase_a_table_vi_provenance.py',
    'scripts/verification/generate_parameter_and_trace_manifests.py',
    'scripts/verification/generate_calibration_results.py',
    'scripts/verification/generate_policy_decisions_and_grid.py',
    'scripts/verification/generate_corrected_experiments.py',
    'scripts/verification/generate_discrepancies_and_claim_audit.py'
]

for s in scripts:
    print(f'=== Running {s} ===')
    res = subprocess.run([sys.executable, s], capture_output=True, text=True)
    if res.returncode != 0:
        print(f'FAILED: {s}\n{res.stderr}')
        sys.exit(1)
    else:
        print(res.stdout.strip())
print('\n>>> All verification deliverables generated successfully!')
"
```

---

## 5. Interactive UI Dashboard

To launch the CachePIM Streamlit dashboard with the 3D WebGL execution arena:

```powershell
# Using the pre-configured batch script
.\run_dashboard.bat

# Or directly via streamlit
streamlit run app.py
```

