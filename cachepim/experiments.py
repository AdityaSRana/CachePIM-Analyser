"""Reproducible experiment runner for CachePIM.

Development data are used to select reuse-penalty lambda. Held-out seeds are
then evaluated using that frozen value. Every stage has its own output path so
one experiment cannot silently overwrite another stage's data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from cachepim.config import CachePIMConfig
from cachepim.metrics import calculate_seed_aggregates, paired_policy_comparison
from cachepim.simulator import Simulator
from cachepim.workloads import WorkloadGenerator


class ExperimentRunner:
    """Runs policy comparisons, sensitivity sweeps, and held-out evaluation."""

    def __init__(self, config: CachePIMConfig, output_dir: str = "results"):
        config.validate()
        self.config = config
        self.output_dir = Path(output_dir)
        self.raw_dir = self.output_dir / "raw"
        self.summary_dir = self.output_dir / "summary"
        self.figures_dir = self.output_dir / "figures"
        self.config_dir = self.output_dir / "configs"
        for path in (self.raw_dir, self.summary_dir, self.figures_dir, self.config_dir):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _float_slug(value: float) -> str:
        return f"{value:g}".replace("-", "m").replace(".", "p")

    def _save_config(self, stem: str, config: Optional[CachePIMConfig] = None) -> None:
        (config or self.config).to_yaml(self.config_dir / f"{stem}.yaml")

    def _save_df(self, df: pd.DataFrame, output_stem: str, config: Optional[CachePIMConfig] = None) -> None:
        """Persist raw and master-seed summary output under a unique experiment name."""
        raw_path = self.raw_dir / f"{output_stem}_raw.csv"
        summary_path = self.summary_dir / f"{output_stem}_summary.csv"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(raw_path, index=False)
        calculate_seed_aggregates(df).to_csv(summary_path, index=False)
        self._save_config(output_stem, config)

    def run_baseline_comparison(
        self,
        seeds: Optional[List[int]] = None,
        traces_per_seed: Optional[int] = None,
        patterns: Optional[List[str]] = None,
        output_stem: str = "baseline_comparison",
    ) -> pd.DataFrame:
        """Evaluate all policies on identical traces; preserve per-stage outputs."""
        seeds = list(self.config.experiment.master_seeds if seeds is None else seeds)
        traces_per_seed = int(self.config.experiment.traces_per_seed if traces_per_seed is None else traces_per_seed)
        patterns = list(self.config.experiment.default_workload_patterns if patterns is None else patterns)
        if traces_per_seed <= 0:
            raise ValueError("traces_per_seed must be positive")

        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        sim = Simulator(self.config)
        all_results: List[Dict[str, Any]] = []
        run_count = 0
        ws_sizes = [16384, 32768, 65536, 131072, 262144]

        for master_seed in seeds:
            for pattern in patterns:
                for trace_idx in range(traces_per_seed):
                    run_count += 1
                    trace_seed = master_seed * 1000 + trace_idx
                    trace_id = f"{output_stem}_{pattern}_ms{master_seed}_t{trace_idx}"
                    ws_bytes = ws_sizes[trace_idx % len(ws_sizes)]
                    trace, desc = gen.generate(
                        pattern=pattern,
                        seed=trace_seed,
                        working_set_bytes=ws_bytes,
                        access_count=2048,
                    )
                    for result in sim.run_all_policies_on_trace(
                        trace=trace,
                        descriptor=desc,
                        run_id=f"{output_stem}_run_{run_count}",
                        trace_id=trace_id,
                    ):
                        row = result.to_dict()
                        row["master_seed"] = master_seed
                        row["trace_index"] = trace_idx
                        row["working_set_bytes"] = ws_bytes
                        row["config_hash"] = self.config.get_hash()
                        all_results.append(row)

        df = pd.DataFrame(all_results)
        self._save_df(df, output_stem)
        return df

    def run_crossover_sweep(
        self,
        working_set_sizes_kb: Optional[List[int]] = None,
        cache_capacities_kb: Optional[List[int]] = None,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """Sweep cache capacity against working-set size using development seed only."""
        working_set_sizes_kb = working_set_sizes_kb or self.config.sweeps.working_set_sizes_kb
        cache_capacities_kb = cache_capacities_kb or self.config.sweeps.cache_capacities_kb
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)

        for cap_kb in cache_capacities_kb:
            cfg = CachePIMConfig.from_dict(self.config.to_dict())
            cfg.cache.capacity_bytes = cap_kb * 1024
            sim = Simulator(cfg)
            for ws_kb in working_set_sizes_kb:
                for pattern in ["STREAM", "REUSE"]:
                    trace, desc = gen.generate(pattern=pattern, seed=seed, working_set_bytes=ws_kb * 1024, access_count=2048)
                    trace_id = f"crossover_c{cap_kb}_w{ws_kb}_{pattern}_s{seed}"
                    for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                        row = result.to_dict()
                        row.update(master_seed=seed, cache_capacity_kb=cap_kb, working_set_kb=ws_kb)
                        rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "crossover_sweep")
        return df

    def run_transfer_sensitivity(
        self,
        bandwidths_gb_s: Optional[List[float]] = None,
        working_set_kb: int = 64,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """Sweep host/PIM transfer bandwidth; 1 byte/ns is 1 decimal GB/s."""
        bandwidths_gb_s = bandwidths_gb_s or self.config.sweeps.transfer_bandwidths_gb_s
        working_set_kb = self.config.sweeps.transfer_sensitivity_working_set_kb if working_set_kb == 64 else working_set_kb
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        for bw in bandwidths_gb_s:
            cfg = CachePIMConfig.from_dict(self.config.to_dict())
            cfg.transfer.host_to_pim_bandwidth_bytes_per_ns = float(bw)
            cfg.transfer.pim_to_host_bandwidth_bytes_per_ns = float(bw)
            sim = Simulator(cfg)
            for pattern in ["STREAM", "REUSE", "RANDOM"]:
                trace, desc = gen.generate(pattern=pattern, seed=seed, working_set_bytes=working_set_kb * 1024, access_count=2048)
                trace_id = f"transfer_bw{bw:g}_{pattern}_s{seed}"
                for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                    row = result.to_dict()
                    row.update(master_seed=seed, transfer_bandwidth_gb_s=float(bw), working_set_kb=working_set_kb)
                    row["config_hash"] = cfg.get_hash()
                    rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "transfer_sensitivity")
        return df

    def run_joint_crossover_sweep(
        self,
        cache_capacities_kb: Optional[List[int]] = None,
        bandwidths_gb_s: Optional[List[float]] = None,
        working_set_kb: int = 64,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """Run the actual joint parameter sweep used by the crossover heatmap."""
        cache_capacities_kb = cache_capacities_kb or self.config.sweeps.cache_capacities_kb
        bandwidths_gb_s = bandwidths_gb_s or self.config.sweeps.transfer_bandwidths_gb_s
        working_set_kb = self.config.sweeps.crossover_working_set_kb if working_set_kb == 64 else working_set_kb
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        # One deterministic trace is reused for every configuration in this sweep.
        trace, desc = gen.generate(pattern="STREAM", seed=seed, working_set_bytes=working_set_kb * 1024, access_count=2048)
        for cap_kb in cache_capacities_kb:
            for bw in bandwidths_gb_s:
                cfg = CachePIMConfig.from_dict(self.config.to_dict())
                cfg.cache.capacity_bytes = int(cap_kb) * 1024
                cfg.transfer.host_to_pim_bandwidth_bytes_per_ns = float(bw)
                cfg.transfer.pim_to_host_bandwidth_bytes_per_ns = float(bw)
                sim = Simulator(cfg)
                trace_id = f"joint_c{cap_kb}_bw{bw:g}_w{working_set_kb}_s{seed}"
                for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                    row = result.to_dict()
                    row.update(master_seed=seed, cache_capacity_kb=int(cap_kb), transfer_bandwidth_gb_s=float(bw), working_set_kb=working_set_kb)
                    row["config_hash"] = cfg.get_hash()
                    rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "joint_crossover_sweep")
        return df

    def run_bank_imbalance_sweep(
        self,
        skew_values: Optional[List[float]] = None,
        working_set_kb: int = 64,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """Evaluate bank imbalance as an explicit synthetic workload parameter."""
        skew_values = skew_values or self.config.sweeps.bank_skew_values
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        for skew in skew_values:
            for pattern in ["STREAM", "REUSE", "RANDOM"]:
                trace, desc = gen.generate(
                    pattern=pattern, seed=seed, working_set_bytes=working_set_kb * 1024,
                    access_count=2048, bank_skew_factor=float(skew),
                )
                trace_id = f"bank_skew{skew:g}_{pattern}_w{working_set_kb}_s{seed}"
                sim = Simulator(self.config)
                for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                    row = result.to_dict()
                    row.update(master_seed=seed, bank_skew_factor=float(skew), working_set_kb=working_set_kb)
                    row["config_hash"] = self.config.get_hash()
                    rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "bank_imbalance_sweep")
        return df

    def run_bank_count_sweep(
        self,
        bank_counts: Optional[List[int]] = None,
        working_set_sizes_kb: Optional[List[int]] = None,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """Sweep configured PIM bank counts with the same traces across configs."""
        bank_counts = bank_counts or self.config.sweeps.pim_bank_counts
        working_set_sizes_kb = working_set_sizes_kb or [16, 32, 64, 128]
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        for bank_count in bank_counts:
            cfg = CachePIMConfig.from_dict(self.config.to_dict())
            cfg.pim.bank_count = int(bank_count)
            sim = Simulator(cfg)
            for pattern in ["STREAM", "REUSE", "RANDOM", "MIXED_PHASE"]:
                for ws_kb in working_set_sizes_kb:
                    trace, desc = gen.generate(
                        pattern=pattern,
                        seed=seed,
                        working_set_bytes=int(ws_kb) * 1024,
                        access_count=2048,
                    )
                    trace_id = f"bank_count{bank_count}_{pattern}_ws{ws_kb}_s{seed}"
                    for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                        row = result.to_dict()
                        row.update(master_seed=seed, bank_count=int(bank_count), working_set_kb=int(ws_kb))
                        # Config hash describes actual configuration for this sweep point.
                        row["config_hash"] = cfg.get_hash()
                        rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "bank_count_sweep")
        return df

    def run_ablation_sweep(self, lambda_weights: Optional[List[float]] = None, seed: Optional[int] = None) -> pd.DataFrame:
        """Evaluate reuse-policy penalty weights on development traces."""
        lambda_weights = lambda_weights or self.config.sweeps.reuse_penalty_weights
        seed = self.config.experiment.dev_seeds[0] if seed is None else seed
        rows: List[Dict[str, Any]] = []
        gen = WorkloadGenerator(line_size_bytes=self.config.cache.line_size_bytes)
        for lam in lambda_weights:
            cfg = CachePIMConfig.from_dict(self.config.to_dict())
            cfg.policy.reuse_penalty_weight = float(lam)
            sim = Simulator(cfg)
            for pattern in ["REUSE", "STREAM", "MIXED_PHASE"]:
                for ws_kb in [16, 32, 64, 128]:
                    trace, desc = gen.generate(pattern=pattern, seed=seed, working_set_bytes=ws_kb * 1024, access_count=2048)
                    trace_id = f"ablation_lam{lam:g}_{pattern}_ws{ws_kb}k_s{seed}"
                    for result in sim.run_all_policies_on_trace(trace, desc, trace_id=trace_id):
                        row = result.to_dict()
                        row.update(master_seed=seed, lambda_weight=float(lam), working_set_kb=ws_kb)
                        row["config_hash"] = cfg.get_hash()
                        rows.append(row)
        df = pd.DataFrame(rows)
        self._save_df(df, "ablation_sweep")
        return df

    def run_held_out_evaluation(self) -> Dict[str, Any]:
        """Tune lambda on development seeds, freeze it, and evaluate held-out seeds.

        The development candidates and test results are stored in separate folders.
        Held-out traces are not used in parameter selection.
        """
        dev_seeds = list(self.config.experiment.dev_seeds)
        test_seeds = list(self.config.experiment.held_out_seeds)
        overlap = set(dev_seeds) & set(test_seeds)
        if overlap:
            raise ValueError(f"Development/test seed leakage detected: {sorted(overlap)}")
        candidates = list(self.config.experiment.reuse_penalty_candidates)
        traces_for_tuning = self.config.experiment.tuning_traces_per_seed
        score_rows: List[Dict[str, Any]] = []
        best_key = None
        best_lambda = None
        best_dev_df = None

        print(f"Tuning reuse penalty on development seeds {dev_seeds}; held-out seeds remain untouched.")
        for lam in candidates:
            tuned_candidate = CachePIMConfig.from_dict(self.config.to_dict())
            tuned_candidate.policy.reuse_penalty_weight = float(lam)
            label = f"lambda_{self._float_slug(float(lam))}"
            candidate_runner = ExperimentRunner(tuned_candidate, self.output_dir / "tuning" / label)
            df_dev = candidate_runner.run_baseline_comparison(
                seeds=dev_seeds,
                traces_per_seed=traces_for_tuning,
                output_stem="development_comparison",
            )
            reuse_rows = df_dev[df_dev["policy_name"] == "Reuse-aware"]
            per_master = reuse_rows.groupby("master_seed").agg(
                mean_normalized_regret=("normalized_regret", "mean"),
                mean_regret_ns=("regret_ns", "mean"),
                mean_selected_ns=("selected_model_ns", "mean"),
            )
            score = {
                "lambda_weight": float(lam),
                "mean_normalized_regret": float(per_master["mean_normalized_regret"].mean()),
                "mean_regret_ns": float(per_master["mean_regret_ns"].mean()),
                "mean_selected_model_ns": float(per_master["mean_selected_ns"].mean()),
                "development_master_seeds": len(per_master),
                "development_traces_per_seed": traces_for_tuning,
                "selection_objective": "minimize mean normalized regret; tie-break mean modeled time; then lower lambda",
            }
            score_rows.append(score)
            key = (score["mean_normalized_regret"], score["mean_selected_model_ns"], float(lam))
            if best_key is None or key < best_key:
                best_key = key
                best_lambda = float(lam)
                best_dev_df = df_dev.copy()

        if best_lambda is None or best_dev_df is None:
            raise RuntimeError("No reuse-penalty candidate completed successfully")

        scores = pd.DataFrame(score_rows).sort_values(
            ["mean_normalized_regret", "mean_selected_model_ns", "lambda_weight"], ascending=True
        )
        tune_dir = self.output_dir / "tuning"
        tune_dir.mkdir(parents=True, exist_ok=True)
        scores.to_csv(tune_dir / "tuning_scores.csv", index=False)

        self.config.policy.reuse_penalty_weight = best_lambda
        self.config.version = f"{self.config.version}-lambda-{self._float_slug(best_lambda)}"
        self._save_config("frozen_test_config")

        dev_comparison = paired_policy_comparison(best_dev_df, "Reuse-aware", "Cost-based")
        tuned_test_runner = ExperimentRunner(self.config, self.output_dir / "held_out")
        df_test = tuned_test_runner.run_baseline_comparison(
            seeds=test_seeds,
            traces_per_seed=self.config.experiment.traces_per_seed,
            output_stem="held_out_test",
        )

        # Publish the final held-out evaluation at conventional root result paths.
        # The original uploaded results are archived separately before full suite.
        shutil.copy2(self.output_dir / "held_out" / "raw" / "held_out_test_raw.csv", self.raw_dir / "baseline_comparison_raw.csv")
        calculate_seed_aggregates(df_test).to_csv(self.summary_dir / "baseline_comparison_summary.csv", index=False)

        test_comparison = paired_policy_comparison(df_test, "Reuse-aware", "Cost-based")
        per_workload_test = {
            pattern: paired_policy_comparison(df_test, "Reuse-aware", "Cost-based", workload_type=pattern)
            for pattern in self.config.experiment.default_workload_patterns
        }
        eval_summary = {
            "selected_lambda": best_lambda,
            "selection_objective": "minimum mean normalized regret on development master-seed means; tie-break lower modeled time; then lower lambda",
            "dev_seeds": dev_seeds,
            "held_out_seeds": test_seeds,
            "tuning_traces_per_seed": traces_for_tuning,
            "held_out_traces_per_seed": self.config.experiment.traces_per_seed,
            "tuning_candidates": score_rows,
            "dev_comparison_reuse_aware_vs_cost_based": dev_comparison,
            "test_comparison_reuse_aware_vs_cost_based": test_comparison,
            "test_comparison_by_workload": per_workload_test,
            "result_classification": "analytical simulation estimates on synthetic traces; not hardware measurements",
        }
        with open(self.summary_dir / "held_out_evaluation.json", "w", encoding="utf-8") as f:
            json.dump(eval_summary, f, indent=2, allow_nan=False)
        with open(tune_dir / "selection.json", "w", encoding="utf-8") as f:
            json.dump({"selected_lambda": best_lambda, "scores": score_rows}, f, indent=2, allow_nan=False)
        return eval_summary

    def run_full_suite(self) -> None:
        """Run all experiments without using held-out seeds for parameter tuning."""
        print("[1/8] Tuning reuse-aware policy on development seeds and evaluating held-out seeds...")
        held_out_summary = self.run_held_out_evaluation()
        print(f"Selected lambda={held_out_summary['selected_lambda']} using development seeds only.")

        print("[2/8] Running CPU/PIM crossover sweep on development seed...")
        self.run_crossover_sweep()
        print("[3/8] Running transfer bandwidth sensitivity sweep on development seed...")
        self.run_transfer_sensitivity()
        print("[4/8] Running joint cache-capacity / transfer-bandwidth sweep...")
        self.run_joint_crossover_sweep()
        print("[5/8] Running bank-count sensitivity sweep...")
        self.run_bank_count_sweep()
        print("[6/8] Running bank-imbalance sensitivity sweep...")
        self.run_bank_imbalance_sweep()
        print("[7/8] Running reuse-penalty ablation sweep on development seed...")
        self.run_ablation_sweep()

        print("[8/8] Generating publication figures from saved experiment CSVs...")
        from cachepim.plots import generate_all_plots
        generate_all_plots(results_dir=str(self.output_dir))

        manifest = {
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "config_hash_after_tuning": self.config.get_hash(),
            "model_version": self.config.version,
            "development_seeds": self.config.experiment.dev_seeds,
            "held_out_seeds": self.config.experiment.held_out_seeds,
            "traces_per_seed_final_test": self.config.experiment.traces_per_seed,
            "tuning_traces_per_seed": self.config.experiment.tuning_traces_per_seed,
            "selected_lambda": held_out_summary["selected_lambda"],
            "sweep_configuration": self.config.to_dict().get("sweeps", {}),
            "result_classification": "analytical simulation estimates on synthetic traces; not hardware measurements",
            "raw_dir": str(self.raw_dir),
            "summary_dir": str(self.summary_dir),
            "figures_dir": str(self.figures_dir),
        }
        with open(self.output_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, allow_nan=False)
        print(f"Experimental suite completed. Results saved under {self.output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CachePIM: Reproducible batch experiment runner")
    parser.add_argument("--config", type=str, default="config/experiment.yaml", help="Path to experiment config YAML")
    parser.add_argument("--output-dir", type=str, default="results", help="Directory to save experiment outputs")
    args = parser.parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {args.config}")
    config = CachePIMConfig.from_yaml(cfg_path)
    ExperimentRunner(config, output_dir=args.output_dir).run_full_suite()


if __name__ == "__main__":
    main()
