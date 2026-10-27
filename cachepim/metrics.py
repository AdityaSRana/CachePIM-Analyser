"""Statistical aggregation for reproducible CachePIM experiments.

When a ``master_seed`` column is available, traces are first averaged within
master seed and workload. Inferential summaries therefore do not pretend that
multiple traces from the same master-seed realization are independent seeds.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats


def calculate_seed_aggregates(
    df: pd.DataFrame,
    metrics: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Aggregate traces within master seed and configuration, then summarize seeds.

    Sweep dimensions remain separate in summaries; multiple cache capacities,
    bandwidths, working-set sizes, skew values, or policy penalties are never
    collapsed into one average. The master seed is the replication unit.
    """
    base_columns = [
        "metric_name", "policy_name", "workload_type", "configuration_group",
        "number_of_master_seeds", "mean", "sample_std", "median",
        "confidence_interval_low", "confidence_interval_high", "ci_method",
    ]
    if df.empty:
        return pd.DataFrame(columns=base_columns)

    if metrics is None:
        metrics = ["selected_model_ns", "cache_hit_rate", "regret_ns", "normalized_regret", "bad_offload"]
    else:
        metrics = list(metrics)

    data = df.copy()
    if "speedup" not in data.columns:
        cpu_rows = data[data["policy_name"] == "CPU-cache"]
        match_cols = ["trace_id"]
        if "config_hash" in data.columns:
            match_cols.append("config_hash")
        cpu_baselines = cpu_rows.set_index(match_cols)["selected_model_ns"]
        data["_speedup_key"] = list(map(tuple, data[match_cols].astype(str).to_numpy()))
        cpu_map = {
            tuple(map(str, key if isinstance(key, tuple) else (key,))): val
            for key, val in cpu_baselines.items()
        }
        data["_cpu_cache_baseline_ns"] = data["_speedup_key"].map(cpu_map)
        data["speedup"] = np.where(
            data["selected_model_ns"] > 0,
            data["_cpu_cache_baseline_ns"] / data["selected_model_ns"],
            np.nan,
        )
        if "speedup" not in metrics:
            metrics.append("speedup")

    seed_col = "master_seed" if "master_seed" in data.columns else "seed"

    # Preserve known sweep dimensions that exist in this result table. Prefer
    # working_set_kb when available to avoid duplicating it with working_set_bytes.
    config_candidates = [
        "cache_capacity_kb",
        "transfer_bandwidth_gb_s",
        "bank_skew_factor",
        "lambda_weight",
        "bank_count",
        "line_size_bytes",
    ]
    config_cols = [c for c in config_candidates if c in data.columns]
    if "working_set_kb" in data.columns:
        config_cols.append("working_set_kb")
    elif "working_set_bytes" in data.columns:
        config_cols.append("working_set_bytes")

    available_metrics = [m for m in metrics if m in data.columns]
    group_seed_cols = ["policy_name", "workload_type", *config_cols, seed_col]
    seed_level = data.groupby(group_seed_cols, dropna=False)[available_metrics].mean().reset_index()

    summary_group_cols = ["policy_name", "workload_type", *config_cols]
    rows: List[Dict[str, Any]] = []
    for group_key, group in seed_level.groupby(summary_group_cols, dropna=False, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        group_values = dict(zip(summary_group_cols, group_key))
        config_label = "; ".join(f"{c}={group_values[c]}" for c in config_cols) or "default"
        for metric in available_metrics:
            vals = group[metric].dropna().to_numpy(dtype=float)
            n = len(vals)
            if n == 0:
                continue
            mean = float(np.mean(vals))
            std = float(np.std(vals, ddof=1)) if n > 1 else 0.0
            median = float(np.median(vals))
            ci_low = ci_high = mean
            ci_method = "not_estimable_n_lt_2"
            if n > 1:
                sem = std / np.sqrt(n)
                if std <= 1e-12:
                    ci_low = ci_high = mean
                    ci_method = "degenerate_zero_variance_t_interval"
                else:
                    crit = float(stats.t.ppf(0.975, df=n - 1))
                    ci_low = float(mean - crit * sem)
                    ci_high = float(mean + crit * sem)
                    ci_method = "students_t_95_over_master_seed_means"
            row = {
                "metric_name": metric,
                "policy_name": group_values["policy_name"],
                "workload_type": group_values["workload_type"],
                "configuration_group": config_label,
                "number_of_master_seeds": n,
                "mean": mean,
                "sample_std": std,
                "median": median,
                "confidence_interval_low": ci_low,
                "confidence_interval_high": ci_high,
                "ci_method": ci_method,
            }
            for col in config_cols:
                row[col] = group_values[col]
            rows.append(row)
    out = pd.DataFrame(rows)
    preferred = base_columns + config_cols
    return out[[c for c in preferred if c in out.columns]]


def paired_policy_comparison(
    df: pd.DataFrame,
    test_policy: str = "Reuse-aware",
    baseline_policy: str = "Cost-based",
    metric: str = "selected_model_ns",
    workload_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare paired policies at the master-seed level.

    Positive mean difference means ``test_policy`` has a lower value than
    ``baseline_policy``. For latency/regret, lower is better.
    """
    data = df.copy()
    if workload_type is not None:
        data = data[data["workload_type"] == workload_type]
    missing = {"policy_name", metric} - set(data.columns)
    if missing:
        return {"error": f"Missing required columns: {sorted(missing)}"}
    if "master_seed" in data.columns:
        unit_col = "master_seed"
    elif "seed" in data.columns:
        unit_col = "seed"
    else:
        return {"error": "Input data must contain master_seed or seed"}

    eligible = data[data["policy_name"].isin([test_policy, baseline_policy])]
    seed_means = eligible.groupby([unit_col, "policy_name"], dropna=False)[metric].mean().reset_index()
    pivot = seed_means.pivot(index=unit_col, columns="policy_name", values=metric).dropna()
    if test_policy not in pivot.columns or baseline_policy not in pivot.columns:
        return {"error": f"Policies {test_policy} or {baseline_policy} not present in paired data"}

    diff = (pivot[baseline_policy] - pivot[test_policy]).to_numpy(dtype=float)
    n = len(diff)
    mean_diff = float(np.mean(diff)) if n else 0.0
    std_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    p_value = None
    t_stat = None
    ci_low = ci_high = mean_diff
    ci_method = "not_estimable_n_lt_2"
    if n > 1:
        if std_diff <= 1e-12:
            p_value = 1.0 if abs(mean_diff) <= 1e-12 else 0.0
            # The statistic is mathematically unbounded for a nonzero constant
            # difference; store null rather than non-finite JSON Infinity.
            t_stat = 0.0 if abs(mean_diff) <= 1e-12 else None
            ci_method = "degenerate_zero_variance"
        else:
            t_stat_raw, p_val_raw = stats.ttest_1samp(diff, 0.0)
            t_stat = float(t_stat_raw)
            p_value = float(p_val_raw)
            sem = std_diff / np.sqrt(n)
            crit = float(stats.t.ppf(0.975, df=n - 1))
            ci_low = float(mean_diff - crit * sem)
            ci_high = float(mean_diff + crit * sem)
            ci_method = "paired_student_t_95_over_master_seed_means"

    return {
        "test_policy": test_policy,
        "baseline_policy": baseline_policy,
        "metric": metric,
        "workload_type": workload_type or "ALL",
        "experimental_unit": unit_col,
        "num_pairs": int(n),
        "mean_difference_baseline_minus_test": mean_diff,
        "sample_std_difference": std_diff,
        "confidence_interval_low": ci_low,
        "confidence_interval_high": ci_high,
        "ci_method": ci_method,
        "t_statistic": t_stat,
        "p_value": p_value,
        "test_policy_faster_pct": float(np.mean(diff > 0) * 100.0) if n else 0.0,
    }
