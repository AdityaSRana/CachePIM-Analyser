"""Phase A.1: Project Identity, Environment, Hashes, and Baseline Inventory."""

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent

out_evidence = PROJECT_ROOT / "results" / "verification" / "evidence"
out_evidence.mkdir(parents=True, exist_ok=True)

print(f"Project Root: {PROJECT_ROOT}")
print(f"Workspace Root: {WORKSPACE_ROOT}")

# 1. Environment and System Info
env_info = {
    "project_root": str(PROJECT_ROOT),
    "workspace_root": str(WORKSPACE_ROOT),
    "os_system": platform.system(),
    "os_release": platform.release(),
    "os_version": platform.version(),
    "architecture": platform.machine(),
    "processor": platform.processor(),
    "python_executable": sys.executable,
    "python_version": sys.version,
}

# Dependency versions
try:
    import numpy, pandas, matplotlib, scipy, streamlit, plotly, pytest, yaml
    env_info["dependencies"] = {
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "matplotlib": matplotlib.__version__,
        "scipy": scipy.__version__,
        "streamlit": streamlit.__version__,
        "plotly": plotly.__version__,
        "pytest": pytest.__version__,
        "pyyaml": yaml.__version__,
    }
except Exception as e:
    env_info["dependencies_error"] = str(e)

# Git status check (purely local, no network)
try:
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    env_info["git_status"] = git_status.stdout.strip()
    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    env_info["git_head"] = git_head.stdout.strip()
except Exception as e:
    env_info["git_error"] = str(e)

# 2. File Inventory & SHA-256 Hashes
def get_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

files_to_hash = []

# Scan cachepim source files
for f in sorted((PROJECT_ROOT / "cachepim").rglob("*.py")):
    files_to_hash.append(("cachepim_source", f.relative_to(PROJECT_ROOT), f))

# Config files
for f in sorted((PROJECT_ROOT / "config").rglob("*.yaml")):
    files_to_hash.append(("config", f.relative_to(PROJECT_ROOT), f))

# Trace files
for f in sorted((PROJECT_ROOT / "data" / "traces").rglob("*.txt")):
    files_to_hash.append(("trace_data", f.relative_to(PROJECT_ROOT), f))

# Result manifests and summary CSVs
if (PROJECT_ROOT / "results" / "manifest.json").exists():
    files_to_hash.append(("result_manifest", Path("results/manifest.json"), PROJECT_ROOT / "results" / "manifest.json"))

for f in sorted((PROJECT_ROOT / "results" / "summary").rglob("*.csv")):
    files_to_hash.append(("result_summary", f.relative_to(PROJECT_ROOT), f))

# Paper files
for p in [WORKSPACE_ROOT / "CachePIM_Final_Research_Paper.md", WORKSPACE_ROOT / "CachePIM_Final_Submission_CD.pdf"]:
    if p.exists():
        files_to_hash.append(("paper", p.relative_to(WORKSPACE_ROOT), p))

# Previous verification report
prev_rep = PROJECT_ROOT / "results" / "verification" / "report.md"
if prev_rep.exists():
    files_to_hash.append(("previous_verification_report", Path("results/verification/report.md"), prev_rep))

inventory = []
for cat, rel_path, abs_path in files_to_hash:
    sz = abs_path.stat().st_size
    sha = get_sha256(abs_path)
    inventory.append({
        "category": cat,
        "relative_path": str(rel_path).replace("\\", "/"),
        "size_bytes": sz,
        "sha256": sha,
    })

df_inventory = pd.DataFrame(inventory)
df_inventory.to_csv(out_evidence / "pre_audit_file_inventory.csv", index=False)

# 3. Model Version and Config Hash Inspection
sys.path.insert(0, str(PROJECT_ROOT))
from cachepim.config import CachePIMConfig

cfg = CachePIMConfig()
env_info["model_version"] = cfg.version
env_info["model_version_source"] = "cachepim/config.py:CachePIMConfig.version"
env_info["config_hash"] = cfg.get_hash()

# Check what fields are included in to_dict() vs omitted from get_hash()
cfg_dict = cfg.to_dict()
env_info["config_dict_keys"] = list(cfg_dict.keys())
env_info["config_to_dict_full"] = cfg_dict

with open(out_evidence / "project_identity_and_environment.json", "w") as f:
    json.dump(env_info, f, indent=2)

print("Pre-audit file inventory and project identity recorded successfully.")
print(f"Total files hashed: {len(inventory)}")
print(f"Config Hash: {cfg.get_hash()}")

