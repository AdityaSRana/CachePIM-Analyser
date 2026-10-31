#!/usr/bin/env python3
"""Generate Policy Decisions CSV and Table V Balanced Grid for CachePIM Verification."""

from pathlib import Path
import pandas as pd

from cachepim.cache_model import CacheModel
from cachepim.config import CacheConfig, CachePIMConfig
from cachepim.cpu_model import CPUModel
from cachepim.pim_model import PIMModel
from cachepim.policies import (
    CostBasedPolicy,
    CPUCachePolicy,
    CPUNoCachePolicy,
    OraclePolicy,
    PIMAlwaysPolicy,
    ReuseAwarePolicy,
)
from cachepim.workloads import WorkloadGenerator


def run_grid_simulation(project_dir: Path, out_dirs: list[Path]):
    cfg = CachePIMConfig()
    gen = WorkloadGenerator(cfg.cache.line_size_bytes)
    cpu_model = CPUModel(cfg.cpu)

    seeds = list(range(42, 52))  # 42..46 dev, 47..51 held-out
    patterns = ["STREAM", "REUSE", "RANDOM", "MIXED_PHASE"]
    ws_sizes_kib = [8, 16, 32, 64, 128]
    bandwidths = [1.0, 2.0, 4.0, 8.0, 16.0]

    # Pre-simulate trace and actual execution latencies for each grid combination
    grid_data = {}
    for seed in seeds:
        for pat in patterns:
            for ws_kib in ws_sizes_kib:
                ws_bytes = ws_kib * 1024
                trace, desc = gen.generate(
                    pattern=pat,
                    seed=seed,
                    working_set_bytes=ws_bytes,
                    access_count=2048,
                    passes=2 if pat == "STREAM" else 1,
                )

                cache = CacheModel(cfg.cache)
                stats = cache.run(trace)
                cpu_eval = cpu_model.evaluate(stats, desc.operation_count)
                cpu_actual_ns = cpu_eval.total_cpu_time_ns

                for bw in bandwidths:
                    local_cfg = CachePIMConfig()
                    local_cfg.transfer.host_to_pim_bandwidth_bytes_per_ns = bw
                    local_cfg.transfer.pim_to_host_bandwidth_bytes_per_ns = bw
                    local_cfg.pim.row_buffer_locality_enabled = True

                    pim_model = PIMModel(local_cfg.pim, local_cfg.transfer)
                    pim_eval = pim_model.evaluate(desc)
                    pim_actual_ns = pim_eval.total_pim_time_ns

                    grid_data[(seed, pat, ws_kib, bw)] = {
                        "desc": desc,
                        "cpu_actual_ns": cpu_actual_ns,
                        "pim_actual_ns": pim_actual_ns,
                        "local_cfg": local_cfg,
                    }

    # Evaluate policies
    policies = {
        "CPU-cache": CPUCachePolicy(),
        "CPU-no-cache": CPUNoCachePolicy(),
        "PIM-always": PIMAlwaysPolicy(),
        "Cost-based": CostBasedPolicy(),
        "Reuse-aware (Tuned/Clamped)": ReuseAwarePolicy(),
        "Oracle": OraclePolicy(),
    }

    # Also evaluate uncorrected Reuse-aware policy for scientific transparency
    class UncorrectedReuseAwarePolicy(ReuseAwarePolicy):
        def decide(self, descriptor, config, actual_cpu_ns=None, actual_pim_ns=None):
            from cachepim.policies import estimate_cache_hits_and_misses
            from cachepim.types import CacheStats, ExecutionPath, PolicyDecision
            hits_est, misses_est = estimate_cache_hits_and_misses(
                descriptor, config.cache.capacity_bytes, config.cache.line_size_bytes
            )
            stats = CacheStats(
                accesses=descriptor.trace_length or descriptor.operation_count,
                hits=hits_est,
                misses=misses_est,
                dirty_evictions=0,
            )
            cpu_cost = CPUModel(config.cpu).evaluate(stats, descriptor.operation_count)
            cpu_est = cpu_cost.total_cpu_time_ns
            pim_model = PIMModel(config.pim, config.transfer)
            pim_cost = pim_model.evaluate(descriptor)
            pim_est = pim_cost.total_pim_time_ns if pim_cost else float("inf")

            accesses = max(1, int(descriptor.trace_length or descriptor.operation_count))
            hit_fraction = hits_est / accesses
            is_resident = descriptor.working_set_bytes <= config.cache.capacity_bytes
            reusability = max(0.0, float(descriptor.reusable_bytes or 0)) / max(1, descriptor.working_set_bytes)
            fit_ratio = config.cache.capacity_bytes / max(1, descriptor.working_set_bytes)

            if is_resident and (hit_fraction >= config.policy.reuse_threshold or reusability >= 0.4):
                # Uncorrected Eq 8 formula: over-credits when W <= C
                temporal_credit = hits_est * (config.cpu.hit_service_ns * 0.5 * fit_ratio)
                refined_cpu_est = max(0.0, cpu_est - temporal_credit)
                pim_adjusted = pim_est
            else:
                refined_cpu_est = cpu_est
                lam = config.policy.reuse_penalty_weight
                r_cost = self.calculate_reuse_cost(descriptor, config, hits_est)
                pim_adjusted = pim_est + (lam * r_cost)

            selected = ExecutionPath.PIM.value if pim_adjusted < refined_cpu_est else ExecutionPath.CPU.value
            return PolicyDecision(
                policy_name=self.name,
                selected_path=selected,
                decision_reason="UNCORRECTED_EQ8",
                cpu_estimated_ns=refined_cpu_est,
                pim_estimated_ns=pim_est,
                policy_overhead_ns=0.0,
            )

    policies["Reuse-aware (Uncorrected Eq8)"] = UncorrectedReuseAwarePolicy()

    all_rows = []
    instance_id = 0

    for (seed, pat, ws_kib, bw), item in grid_data.items():
        instance_id += 1
        desc = item["desc"]
        cpu_act_ns = item["cpu_actual_ns"]
        pim_act_ns = item["pim_actual_ns"]
        local_cfg = item["local_cfg"]
        dataset_split = "Dev" if seed <= 46 else "Held-Out"

        # Oracle choice
        oracle_path = "PIM" if pim_act_ns < cpu_act_ns else "CPU"
        oracle_latency_us = min(cpu_act_ns, pim_act_ns) / 1000.0

        for pol_name, pol_obj in policies.items():
            if pol_name == "Oracle":
                dec = pol_obj.decide(desc, local_cfg, actual_cpu_ns=cpu_act_ns, actual_pim_ns=pim_act_ns)
            else:
                dec = pol_obj.decide(desc, local_cfg)

            sel_path = dec.selected_path
            sel_latency_us = (pim_act_ns if sel_path == "PIM" else cpu_act_ns) / 1000.0
            regret_us = max(0.0, sel_latency_us - oracle_latency_us)

            # Confusion matrix outcome
            if oracle_path == "PIM":
                outcome = "True Offload" if sel_path == "PIM" else "Missed Offload (False CPU)"
            else:
                outcome = "Bad Offload (False Offload)" if sel_path == "PIM" else "True CPU"

            all_rows.append({
                "Instance_ID": instance_id,
                "Dataset_Split": dataset_split,
                "Seed": seed,
                "Workload_Pattern": pat,
                "Working_Set_KiB": ws_kib,
                "Transfer_BW_GB_s": bw,
                "Policy_Name": pol_name,
                "Selected_Path": sel_path,
                "Oracle_Path": oracle_path,
                "Outcome": outcome,
                "Is_Correct": sel_path == oracle_path,
                "Selected_Latency_us": round(sel_latency_us, 4),
                "Oracle_Latency_us": round(oracle_latency_us, 4),
                "Regret_us": round(regret_us, 4),
                "CPU_Actual_us": round(cpu_act_ns / 1000.0, 4),
                "PIM_Actual_us": round(pim_act_ns / 1000.0, 4),
                "CPU_Estimated_us": round(dec.cpu_estimated_ns / 1000.0, 4),
                "PIM_Estimated_us": round(dec.pim_estimated_ns / 1000.0, 4),
            })

    df = pd.DataFrame(all_rows)
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        out_csv = od / "policy_decisions.csv"
        df.to_csv(out_csv, index=False)
        print(f"Wrote policy decisions to {out_csv}")

    # Generate Table V summary for Held-Out Set (500 instances)
    held_out_df = df[df["Dataset_Split"] == "Held-Out"]
    summary_rows = []

    for pol_name in [
        "CPU-cache",
        "CPU-no-cache",
        "PIM-always",
        "Cost-based",
        "Reuse-aware (Tuned/Clamped)",
        "Reuse-aware (Uncorrected Eq8)",
        "Oracle",
    ]:
        sub = held_out_df[held_out_df["Policy_Name"] == pol_name]
        total_n = len(sub)
        true_offloads = len(sub[sub["Outcome"] == "True Offload"])
        bad_offloads = len(sub[sub["Outcome"] == "Bad Offload (False Offload)"])
        true_cpus = len(sub[sub["Outcome"] == "True CPU"])
        missed_offloads = len(sub[sub["Outcome"] == "Missed Offload (False CPU)"])
        correct_n = len(sub[sub["Is_Correct"]])

        acc_pct = round(100.0 * correct_n / total_n, 2)
        bad_offload_pct = round(100.0 * bad_offloads / total_n, 2)
        missed_offload_pct = round(100.0 * missed_offloads / total_n, 2)
        mean_regret = round(sub["Regret_us"].mean(), 4)
        max_regret = round(sub["Regret_us"].max(), 4)

        summary_rows.append({
            "Policy": pol_name,
            "Total_Decisions": total_n,
            "True_Offloads": true_offloads,
            "Bad_Offloads": bad_offloads,
            "True_CPUs": true_cpus,
            "Missed_Offloads": missed_offloads,
            "Decision_Accuracy_Pct": acc_pct,
            "Bad_Offload_Rate_Pct": bad_offload_pct,
            "Missed_Offload_Rate_Pct": missed_offload_pct,
            "Mean_Regret_us": mean_regret,
            "Max_Regret_us": max_regret,
        })

    summary_df = pd.DataFrame(summary_rows)
    for od in out_dirs:
        corr_dir = od / "corrected" if od.name != "corrected" else od
        corr_dir.mkdir(parents=True, exist_ok=True)
        summary_csv = corr_dir / "table_v_balanced_grid.csv"
        summary_df.to_csv(summary_csv, index=False)
        print(f"Wrote Table V balanced grid summary to {summary_csv}")


if __name__ == "__main__":
    project_dir = Path("CDv2AV/CachePIM-Analyser-corrected").resolve()
    out_dirs = [
        Path("results/verification").resolve(),
        (project_dir / "results" / "verification").resolve(),
    ]
    run_grid_simulation(project_dir, out_dirs)
