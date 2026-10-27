"""Seed-aware statistical analysis and paper-table utilities for CachePIM."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats

from cachepim.metrics import calculate_seed_aggregates, paired_policy_comparison


def analyze_baseline_results(raw_csv_path: str = "results/raw/baseline_comparison_raw.csv") -> Dict[str, Any]:
    """Summarize policies with master seeds as the inferential unit.

    Descriptive policy estimates are averaged within each master seed before
    calculating across-seed means and standard deviations. Paired comparisons
    use the same master-seed unit rather than treating every trace as an
    independent replicate.
    """
    path = Path(raw_csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw results file not found at {raw_csv_path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Raw results file contains no rows: {raw_csv_path}")

    seed_col = "master_seed" if "master_seed" in df.columns else "seed"
    seed_means = df.groupby([seed_col, "policy_name"], dropna=False).agg(
        selected_model_ns=("selected_model_ns", "mean"),
        regret_ns=("regret_ns", "mean"),
        normalized_regret=("normalized_regret", "mean"),
        bad_offload=("bad_offload", "mean"),
    ).reset_index()

    summary: Dict[str, Dict[str, float]] = {}
    for policy, group in seed_means.groupby("policy_name"):
        summary[str(policy)] = {}
        for metric in ["selected_model_ns", "regret_ns", "normalized_regret", "bad_offload"]:
            vals = group[metric].to_numpy(dtype=float)
            summary[str(policy)][f"{metric}_mean"] = float(np.mean(vals))
            summary[str(policy)][f"{metric}_sample_std"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            summary[str(policy)][f"{metric}_master_seed_n"] = int(len(vals))

    paired_test = paired_policy_comparison(df, "Reuse-aware", "Cost-based", metric="selected_model_ns")
    bad_offload_rates = {
        str(policy): float(group["bad_offload"].mean())
        for policy, group in seed_means.groupby("policy_name")
    }
    return {
        "num_run_rows": int(len(df)),
        "independent_master_seeds": int(df[seed_col].nunique()),
        "experimental_unit": seed_col,
        "policy_summary_across_master_seed_means": summary,
        "paired_comparison_reuse_vs_cost": paired_test,
        "bad_offload_rate_mean_across_master_seeds": bad_offload_rates,
        "note": "Analytical simulation on synthetic traces; statistics summarize this model and workload generator.",
    }


def format_paper_table(summary_csv_path: str = "results/summary/baseline_comparison_summary.csv") -> pd.DataFrame:
    """Return a tidy per-workload policy/metric table from a saved summary CSV."""
    path = Path(summary_csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Summary results file not found at {summary_csv_path}")
    df = pd.read_csv(path)
    required = {"workload_type", "policy_name", "metric_name", "mean"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Summary file missing columns: {sorted(missing)}")
    return df.pivot_table(index=["workload_type", "policy_name"], columns="metric_name", values="mean")
