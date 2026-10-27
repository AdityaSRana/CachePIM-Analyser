"""CLI entry point for running individual CachePIM simulations.

Usage:
    python -m cachepim.run --config config/default.yaml --workload STREAM --seed 42
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.trace_loader import load_trace
from cachepim.workloads import PRIM_PRESETS, WorkloadGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="CachePIM: Single Workload Simulation CLI")
    parser.add_argument("--config", type=str, default="config/default.yaml", help="Path to config YAML")
    parser.add_argument(
        "--trace-file",
        type=str,
        default=None,
        help="Path to real memory trace file (e.g. Valgrind lackey or generic trace)",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        choices=list(PRIM_PRESETS.keys()),
        help="Optional PrIM benchmark preset (e.g., PrIM-VA, PrIM-GEMV, PrIM-SpMV)",
    )
    parser.add_argument(
        "--workload",
        type=str,
        default="STREAM",
        choices=["STREAM", "REUSE", "RANDOM", "MIXED_PHASE"],
        help="Workload memory pattern (used when --preset and --trace-file are not specified)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--working-set-kb", type=int, default=32, help="Working-set size in KiB")
    parser.add_argument("--access-count", type=int, default=2048, help="Number of trace accesses")
    parser.add_argument("--output", type=str, default=None, help="Optional output CSV path")
    args = parser.parse_args()

    # Load configuration
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Error: Config file not found at {args.config}", file=sys.stderr)
        sys.exit(1)

    config = CachePIMConfig.from_yaml(cfg_path)
    config.validate()

    # Generate or load workload
    if args.trace_file:
        trace, descriptor = load_trace(
            source=args.trace_file,
            max_records=args.access_count if args.access_count > 0 else None,
            line_size_bytes=config.cache.line_size_bytes,
            workload_name=Path(args.trace_file).stem,
        )
        workload_label = f"Real Trace: {Path(args.trace_file).name}"
    elif args.preset:
        gen = WorkloadGenerator(line_size_bytes=config.cache.line_size_bytes)
        trace, descriptor = gen.generate_preset(args.preset, seed=args.seed)
        workload_label = args.preset
    else:
        gen = WorkloadGenerator(line_size_bytes=config.cache.line_size_bytes)
        working_set_bytes = args.working_set_kb * 1024
        trace, descriptor = gen.generate(
            pattern=args.workload,
            seed=args.seed,
            working_set_bytes=working_set_bytes,
            access_count=args.access_count,
        )
        workload_label = f"{args.workload} ({args.working_set_kb} KiB)"

    # Run simulator for all 6 policies
    sim = Simulator(config)
    results = sim.run_all_policies_on_trace(trace, descriptor)

    # Format table for display
    rows = [r.to_dict() for r in results]
    df = pd.DataFrame(rows)

    print("\n" + "=" * 80)
    print(f"CachePIM Simulation Results (Workload: {workload_label}, Seed: {args.seed})")
    print("=" * 80)

    display_cols = [
        "policy_name",
        "selected_path",
        "decision_reason",
        "selected_model_ns",
        "cache_hit_rate",
        "regret_ns",
        "bad_offload",
    ]
    formatted_df = df[display_cols].copy()
    formatted_df["selected_model_us"] = formatted_df["selected_model_ns"] / 1000.0
    formatted_df["cache_hit_%"] = (formatted_df["cache_hit_rate"] * 100).round(1)
    formatted_df["regret_us"] = formatted_df["regret_ns"] / 1000.0

    print(formatted_df[[
        "policy_name",
        "selected_path",
        "selected_model_us",
        "cache_hit_%",
        "regret_us",
        "bad_offload",
        "decision_reason",
    ]].to_string(index=False))
    print("=" * 80)
    print(f"Config Hash: {config.get_hash()} | Model Version: {config.version}\n")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
