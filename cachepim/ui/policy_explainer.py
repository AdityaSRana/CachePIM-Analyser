"""Policy Comparison and Analytical Mechanics Explainer.

Presents a faculty-ready evaluation of all six offloading policies:
1. CPU-cache
2. CPU-no-cache
3. PIM-always
4. Cost-based
5. Reuse-aware (including lambda-penalty and lambda=0 finding)
6. Oracle (offline theoretical non-deployable reference)

Includes human-readable explanations free of raw code or formula syntax.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cachepim.types import SimulationResult
from cachepim.ui.theme import clean_html


def humanize_decision_reason(reason: str) -> str:
    """Convert raw internal enum codes to clean, human-readable explanations."""
    mapping = {
        "REUSE_AWARE_PRESERVED_CPU_DUE_TO_REUSE": "Retained on Host CPU (High temporal cache reuse detected)",
        "COST_PIM_LOWER": "Offloaded to PIM Accelerator (Estimated PIM latency is lower)",
        "COST_CPU_LOWER": "Retained on Host CPU (Estimated CPU latency is lower)",
        "ALWAYS_CPU_CACHE": "Executed on Host CPU through Cache Hierarchy (Policy default)",
        "DIRECT_MEMORY_BASELINE": "Executed directly through DRAM without cache reuse (Baseline)",
        "ALWAYS_PIM": "Offloaded to PIM Accelerator (Policy default)",
        "ORACLE_PIM_OPTIMAL": "PIM offload selected as the optimal minimum-latency path",
        "ORACLE_CPU_OPTIMAL": "Host CPU selected as the optimal minimum-latency path",
        "UNSUPPORTED_BY_PIM": "Retained on Host CPU (Kernel unsupported by PIM hardware)",
    }
    return mapping.get(reason, reason.replace("_", " ").title())


def render_policy_comparison_section(
    results: list[SimulationResult],
    active_policy_name: str,
    reuse_penalty_weight: float,
) -> None:
    """Render comprehensive policy comparison table, metric cards, and architectural explanations."""
    st.subheader("Six-Policy Architectural Evaluation")
    st.markdown(
        "Evaluate offloading decisions, modeled execution times, and decision regret across all six policies. "
        "Each policy evaluates the exact same workload trace under identical memory constraints."
    )

    res_dict = {r.policy_name: r for r in results}
    cpu_res = res_dict["CPU-cache"]
    oracle_res = res_dict["Oracle"]
    target_res = res_dict.get(active_policy_name, res_dict["Reuse-aware"])

    # Build Comparison Table with Clean Labels (no raw codes or symbols)
    rows = []
    for r in results:
        is_active = r.policy_name == active_policy_name
        speedup_val = cpu_res.selected_model_ns / r.selected_model_ns if r.selected_model_ns > 0 else 1.0
        rows.append({
            "Policy": f"{'* ' if is_active else ''}{r.policy_name}",
            "Path": r.selected_path,
            "Latency (μs)": round(r.selected_model_ns / 1000.0, 2),
            "Speedup": f"{speedup_val:.2f}x",
            "Cache Hit Rate": f"{r.cache_hit_rate * 100.0:.1f}%",
            "Regret (μs)": round(r.regret_ns / 1000.0, 2),
            "Bad Offload": "Yes" if r.bad_offload == 1 else "No",
            "Decision Reason": humanize_decision_reason(r.decision_reason),
        })

    df_display = pd.DataFrame(rows)
    st.dataframe(df_display, use_container_width=True)

    # Scientific Findings Note (Human-readable, no raw math code or emojis)
    if reuse_penalty_weight == 0.0:
        st.info(
            "**Architectural Insight (Reuse Penalty Weight = 0.0):** Under the current configuration, "
            "the **Reuse-aware** policy operates identically to the **Cost-based** policy. "
            "This directly reflects the empirical finding from development tuning: positive penalty weights "
            "did not reduce regret under default interconnect assumptions, confirming that a penalty does not outperform pure cost-based selection."
        )
    else:
        st.warning(
            f"**Active Reuse Penalty (Weight = {reuse_penalty_weight:.2f}):** A penalty is applied against offloading, "
            "calculated from the configured penalty weight, cache hit ratio, and host link transfer duration. "
            "This encourages the system to retain workloads on the CPU when they exhibit high cache hit rates and reusable working sets."
        )

    # Architectural Policy Rationale (Clear natural language cards without code blocks)
    st.markdown("### Architectural Policy Rationale")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            clean_html("""
            <div class="cachepim-card cachepim-card-cyan">
                <h4 style="color: #91B8D8; margin-bottom: 8px;">1. CPU-cache (Baseline)</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Executes entirely on the Host CPU through an exact fully-associative Last-Level Cache (LLC) with LRU replacement.
                    Execution time accounts for cache hit service time, main memory miss latency, and arithmetic instruction execution.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Best for:</strong> Compact working sets that fit inside LLC with intense temporal reuse.
                </div>
            </div>

            <div class="cachepim-card">
                <h4 style="color: #A8B3C2; margin-bottom: 8px;">2. CPU-no-cache (Direct-Memory Baseline)</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Direct-memory baseline where every memory reference incurs full DRAM access latency without cache reuse.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Purpose:</strong> Isolates the maximum performance benefit contributed by the cache hierarchy.
                </div>
            </div>

            <div class="cachepim-card">
                <h4 style="color: #8FB7A5; margin-bottom: 8px;">3. PIM-always (Static Offload)</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Unconditionally offloads all supported kernels to PIM memory banks, falling back to CPU only if the kernel type is unsupported.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Risk:</strong> Can cause severe latency penalties when transfer overhead exceeds PIM computation savings.
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            clean_html(f"""
            <div class="cachepim-card cachepim-card-amber">
                <h4 style="color: #D5AD72; margin-bottom: 8px;">4. Cost-based Policy</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Compares profile-level estimated CPU latency against estimated PIM latency and offloads only when PIM provides a latency advantage.
                    Uses transparent metadata estimates of compulsory and capacity misses without oracle knowledge.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Trade-off:</strong> Highly effective for streaming and random patterns; agnostic to cache line reuse history.
                </div>
            </div>

            <div class="cachepim-card">
                <h4 style="color: #8FB7A5; margin-bottom: 8px;">5. Reuse-aware Candidate Policy</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Extends Cost-based selection by charging a dimensionally consistent reuse penalty against offloading when working sets exhibit high reuse.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Active Penalty Weight:</strong> {reuse_penalty_weight:.2f} (Development tuning identified weight 0.0 as optimal).
                </div>
            </div>

            <div class="cachepim-card">
                <h4 style="color: #E2E8F0; margin-bottom: 8px;">6. Oracle (Theoretical Upper Bound)</h4>
                <p style="font-size: 0.84rem; color: #A8B3C2; line-height: 1.5;">
                    Selects the true minimum-latency path using post-simulation actual costs.
                </p>
                <div style="font-size: 0.78rem; color: #E2E8F0; margin-top: 6px;">
                    <strong>Non-Deployable:</strong> Evaluated strictly as a theoretical upper bound with zero regret.
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
