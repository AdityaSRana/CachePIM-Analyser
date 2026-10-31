"""Phase A.2: Conclusive Table VI Provenance Audit."""

import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.trace_loader import load_trace
from cachepim.workloads import PRIM_PRESETS, WorkloadGenerator

out_evidence = PROJECT_ROOT / "results" / "verification" / "evidence"
out_dir = PROJECT_ROOT / "results" / "verification"
out_evidence.mkdir(parents=True, exist_ok=True)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

cfg = CachePIMConfig()
sim = Simulator(cfg)
gen = WorkloadGenerator(line_size_bytes=64)

trace_info_map = {
    "PrIM-VA": PROJECT_ROOT / "data" / "traces" / "stream_va.txt",
    "PrIM-GEMV": PROJECT_ROOT / "data" / "traces" / "reuse_gemv.txt",
    "PrIM-BS": PROJECT_ROOT / "data" / "traces" / "random_bs.txt",
    "PrIM-SEL": PROJECT_ROOT / "data" / "traces" / "mixed_sel.txt",
}

audit_records = []
detailed_evidence = {}

# Historical values reported in Original PDF (Table VII) and Revised MD (Table VI)
historical_table_vi = {
    "PrIM-VA": {"cpu_cache_us": 316.76, "pim_us": 15.12, "speedup": 20.95, "hit_rate": 87.50, "ops": 4096},
    "PrIM-GEMV": {"cpu_cache_us": 57.65, "pim_us": 14.35, "speedup": 4.02, "hit_rate": 85.15, "ops": 4096},
    "PrIM-BS": {"cpu_cache_us": 88.56, "pim_us": 21.83, "speedup": 4.06, "hit_rate": 75.59, "ops": 2048},  # In original Table IV RANDOM mean was 88.56
    "PrIM-SEL": {"cpu_cache_us": 133.77, "pim_us": 10.00, "speedup": 13.38, "hit_rate": 87.50, "ops": 2048},
}

for name, path in trace_info_map.items():
    file_sha = sha256_file(path)
    file_bytes = path.stat().st_size
    
    # Line count and opcode breakdown in file
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]
    file_line_count = len(lines)
    
    op_counts_raw = {"L": 0, "S": 0, "M": 0, "I": 0, "OTHER": 0}
    raw_addrs = []
    for l in lines:
        parts = l.split()
        if parts:
            op = parts[0]
            if op in op_counts_raw:
                op_counts_raw[op] += 1
            else:
                op_counts_raw["OTHER"] += 1
            if len(parts) >= 2 and op in ("L", "S", "M"):
                addr_hex = parts[1].split(",")[0]
                try:
                    raw_addrs.append(int(addr_hex, 16))
                except ValueError:
                    pass
                    
    min_addr_hex = hex(min(raw_addrs)) if raw_addrs else "N/A"
    max_addr_hex = hex(max(raw_addrs)) if raw_addrs else "N/A"
    
    # 1. Parse via load_trace
    records_real, desc_real = load_trace(str(path), line_size_bytes=64)
    res_real = sim.run_all_policies_on_trace(records_real, desc_real)
    rm_real = {r.policy_name: r for r in res_real}
    
    cpu_real_us = rm_real["CPU-cache"].selected_model_ns / 1000.0
    pim_real_us = rm_real["PIM-always"].selected_model_ns / 1000.0
    hit_rate_real = rm_real["CPU-cache"].cache_hit_rate * 100.0
    sp_real = cpu_real_us / pim_real_us if pim_real_us > 0 else 0.0
    
    # 2. Generate via generate_preset
    records_synth, desc_synth = gen.generate_preset(name, seed=42)
    res_synth = sim.run_all_policies_on_trace(records_synth, desc_synth)
    rm_synth = {r.policy_name: r for r in res_synth}
    
    cpu_synth_us = rm_synth["CPU-cache"].selected_model_ns / 1000.0
    pim_synth_us = rm_synth["PIM-always"].selected_model_ns / 1000.0
    hit_rate_synth = rm_synth["CPU-cache"].cache_hit_rate * 100.0
    sp_synth = cpu_synth_us / pim_synth_us if pim_synth_us > 0 else 0.0
    
    hist = historical_table_vi[name]
    
    # Comparison verdict
    # Check if historical matches synthetic preset
    pim_match = abs(hist["pim_us"] - pim_synth_us) < 0.05
    hit_match = abs(hist["hit_rate"] - hit_rate_synth) < 1.0
    if pim_match and hit_match:
        provenance_verdict = "MATCHES_SYNTHETIC_PRESET"
    else:
        provenance_verdict = "DISCREPANT_OR_HYBRID"
        
    audit_records.append({
        "Kernel": name,
        "Trace_File": path.name,
        "File_SHA256": file_sha[:16],
        "File_Lines": file_line_count,
        "Parsed_Accesses_Real": len(records_real),
        "Unique_64B_Lines_Real": len(set(r.address // 64 for r in records_real)),
        "WS_Bytes_Real": desc_real.working_set_bytes,
        "HitRate_Real_Pct": round(hit_rate_real, 2),
        "CPU_Real_us": round(cpu_real_us, 2),
        "PIM_Real_us": round(pim_real_us, 2),
        "Speedup_Real": round(sp_real, 2),
        "Historical_CPU_us": hist["cpu_cache_us"],
        "Historical_PIM_us": hist["pim_us"],
        "Historical_Speedup": hist["speedup"],
        "Historical_HitRate_Pct": hist["hit_rate"],
        "Synth_CPU_us": round(cpu_synth_us, 2),
        "Synth_PIM_us": round(pim_synth_us, 2),
        "Synth_Speedup": round(sp_synth, 2),
        "Synth_HitRate_Pct": round(hit_rate_synth, 2),
        "Verdict": provenance_verdict,
    })
    
    detailed_evidence[name] = {
        "file_path": str(path.relative_to(PROJECT_ROOT)),
        "file_sha256": file_sha,
        "file_bytes": file_bytes,
        "raw_opcode_counts": op_counts_raw,
        "min_address": min_addr_hex,
        "max_address": max_addr_hex,
        "real_trace_metrics": {
            "parsed_records": len(records_real),
            "reads": sum(1 for r in records_real if r.operation == "READ"),
            "writes": sum(1 for r in records_real if r.operation == "WRITE"),
            "unique_lines": len(set(r.address // 64 for r in records_real)),
            "working_set_bytes": desc_real.working_set_bytes,
            "operation_count": desc_real.operation_count,
            "cache_hits": rm_real["CPU-cache"].cache_hits,
            "cache_misses": rm_real["CPU-cache"].cache_misses,
            "hit_rate": rm_real["CPU-cache"].cache_hit_rate,
            "cpu_latency_ns": rm_real["CPU-cache"].selected_model_ns,
            "pim_latency_ns": rm_real["PIM-always"].selected_model_ns,
        },
        "synthetic_preset_metrics": {
            "preset_config": PRIM_PRESETS[name],
            "records": len(records_synth),
            "unique_lines": len(set(r.address // 64 for r in records_synth)),
            "working_set_bytes": desc_synth.working_set_bytes,
            "operation_count": desc_synth.operation_count,
            "cache_hits": rm_synth["CPU-cache"].cache_hits,
            "cache_misses": rm_synth["CPU-cache"].cache_misses,
            "hit_rate": rm_synth["CPU-cache"].cache_hit_rate,
            "cpu_latency_ns": rm_synth["CPU-cache"].selected_model_ns,
            "pim_latency_ns": rm_synth["PIM-always"].selected_model_ns,
        },
    }

df_audit = pd.DataFrame(audit_records)
df_audit.to_csv(out_dir / "table_vi_provenance.csv", index=False)
df_audit.to_csv(out_evidence / "table_vi_provenance.csv", index=False)

# Also mirror to root results/verification
root_out = WORKSPACE_ROOT / "results" / "verification"
root_out.mkdir(parents=True, exist_ok=True)
df_audit.to_csv(root_out / "table_vi_provenance.csv", index=False)

with open(out_evidence / "table_vi_detailed_audit.json", "w") as f:
    json.dump(detailed_evidence, f, indent=2)

print("Table VI provenance audit complete. Output written to table_vi_provenance.csv.")

