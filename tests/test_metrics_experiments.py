"""Regression tests for independent experimental units and output separation."""
from pathlib import Path

import pandas as pd
import pytest

from cachepim.config import CachePIMConfig
from cachepim.experiments import ExperimentRunner
from cachepim.metrics import calculate_seed_aggregates, paired_policy_comparison


def _rows():
    rows = []
    values = {
        1: [(101, 10.0, 12.0), (102, 20.0, 22.0)],
        2: [(201, 100.0, 102.0), (202, 100.0, 102.0)],
    }
    for master, vals in values.items():
        for i, (trace_seed, cpu, test) in enumerate(vals):
            trace_id = f"m{master}_t{i}"
            for policy, latency in [("CPU-cache", cpu), ("Cost-based", cpu), ("Reuse-aware", test)]:
                rows.append({
                    "master_seed": master,
                    "seed": trace_seed,
                    "trace_id": trace_id,
                    "workload_type": "REUSE",
                    "policy_name": policy,
                    "selected_model_ns": latency,
                    "cache_hit_rate": 0.5,
                    "regret_ns": max(0.0, latency - cpu),
                    "normalized_regret": max(0.0, latency - cpu) / cpu,
                    "bad_offload": 0,
                    "config_hash": "config-a",
                })
    return pd.DataFrame(rows)


def test_seed_aggregation_uses_master_seed_as_independent_unit():
    df = _rows()
    summary = calculate_seed_aggregates(df, metrics=["selected_model_ns"])
    row = summary[(summary.policy_name == "Cost-based") & (summary.workload_type == "REUSE") & (summary.metric_name == "selected_model_ns")].iloc[0]
    # Master-seed means are 15 ns and 100 ns; the reported mean is their mean.
    assert row.number_of_master_seeds == 2
    assert row["mean"] == pytest.approx(57.5)


def test_paired_comparison_uses_master_seed_pairs_not_trace_pairs():
    result = paired_policy_comparison(_rows(), "Reuse-aware", "Cost-based")
    assert result["num_pairs"] == 2
    assert result["experimental_unit"] == "master_seed"
    assert result["mean_difference_baseline_minus_test"] < 0.0


def test_stage_output_stems_do_not_overwrite(tmp_path: Path):
    config = CachePIMConfig()
    runner = ExperimentRunner(config, output_dir=str(tmp_path / "results"))
    dev = runner.run_baseline_comparison(
        seeds=[42], traces_per_seed=1, patterns=["REUSE"], output_stem="development"
    )
    test = runner.run_baseline_comparison(
        seeds=[47], traces_per_seed=1, patterns=["REUSE"], output_stem="held_out"
    )
    dev_path = tmp_path / "results" / "raw" / "development_raw.csv"
    test_path = tmp_path / "results" / "raw" / "held_out_raw.csv"
    assert dev_path.exists() and test_path.exists()
    dev_read = pd.read_csv(dev_path)
    test_read = pd.read_csv(test_path)
    assert set(dev_read["master_seed"]) == {42}
    assert set(test_read["master_seed"]) == {47}
    assert len(dev) == len(test) == 6


def test_heldout_tuning_writes_separate_dev_and_test_artifacts(tmp_path: Path):
    cfg = CachePIMConfig()
    cfg.experiment.dev_seeds = [42, 43]
    cfg.experiment.held_out_seeds = [47]
    cfg.experiment.traces_per_seed = 1
    cfg.experiment.tuning_traces_per_seed = 1
    cfg.experiment.reuse_penalty_candidates = [0.0, 1.0]
    cfg.experiment.default_workload_patterns = ["REUSE"]
    output = tmp_path / "heldout_test"
    report = ExperimentRunner(cfg, output_dir=str(output)).run_held_out_evaluation()

    assert report["dev_seeds"] == [42, 43]
    assert report["held_out_seeds"] == [47]
    assert report["selected_lambda"] in [0.0, 1.0]
    assert (output / "tuning" / "tuning_scores.csv").exists()
    assert (output / "held_out" / "raw" / "held_out_test_raw.csv").exists()
    final_df = pd.read_csv(output / "raw" / "baseline_comparison_raw.csv")
    assert set(final_df["master_seed"]) == {47}
    assert (output / "tuning" / "lambda_0" / "raw" / "development_comparison_raw.csv").exists()
    assert (output / "tuning" / "lambda_1" / "raw" / "development_comparison_raw.csv").exists()


def test_seed_summary_keeps_sweep_configurations_separate():
    df = _rows()
    df["cache_capacity_kb"] = [32 if row % 2 == 0 else 64 for row in range(len(df))]
    summary = calculate_seed_aggregates(df, metrics=["selected_model_ns"])
    cost = summary[(summary.policy_name == "Cost-based") & (summary.metric_name == "selected_model_ns")]
    assert set(cost["cache_capacity_kb"].dropna().unique()) == {32, 64}
    assert cost["configuration_group"].str.contains("cache_capacity_kb=").all()


def test_sweep_grid_is_loaded_from_yaml():
    cfg = CachePIMConfig.from_yaml("config/experiment.yaml")
    assert cfg.sweeps.transfer_bandwidths_gb_s == [0.5, 1.0, 2.0, 4.0, 8.0]
    assert cfg.sweeps.pim_bank_counts == [4, 8, 16, 32, 64]
