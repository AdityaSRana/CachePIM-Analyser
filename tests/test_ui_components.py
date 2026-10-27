"""Tests for CachePIM UI components and visualization modules."""

from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.ui.arena_3d import render_execution_arena_html
from cachepim.ui.cache_visualizer import render_cache_capacity_visualizer
from cachepim.ui.charts import (
    plot_bank_distribution,
    plot_cache_event_donut,
    plot_component_breakdown,
    plot_hit_miss_vs_workingset,
    plot_performance_vs_bank_count,
    plot_policy_comparison,
    plot_speedup_vs_bandwidth,
)
from cachepim.workloads import WorkloadGenerator


def test_arena_3d_html_generation():
    """Verify that the 3D execution arena generates valid HTML containing data and Three.js components."""
    html = render_execution_arena_html(
        workload_type="STREAM",
        working_set_kb=32,
        capacity_kb=32,
        line_size_bytes=64,
        bank_count=16,
        link_bw_gb_s=16.0,
        cache_hit_rate=0.938,
        cache_miss_rate=0.062,
        cache_hits=1920,
        cache_misses=128,
        selected_path="PIM",
        policy_name="Cost-based",
        decision_reason="COST_PIM_LOWER",
        cpu_latency_us=59.6,
        pim_latency_us=7.7,
        speedup=7.74,
        h2p_time_us=1.2,
        bank_compute_time_us=3.4,
        p2h_time_us=0.8,
        bank_imbalance=1.05,
        per_bank_work=[128] * 16,
    )

    assert "<!DOCTYPE html>" in html
    assert "CPU vs PIM Execution Arena" in html
    assert "three.min.js" in html
    assert "OrbitControls.js" in html
    assert "DATA" in html
    assert "7.74" in html
    assert "fallback-canvas" in html


def test_ui_charts_generation():
    """Verify that all Plotly charts generate without error and contain valid data."""
    cfg = CachePIMConfig()
    sim = Simulator(cfg)
    gen = WorkloadGenerator(line_size_bytes=cfg.cache.line_size_bytes)
    trace, desc = gen.generate(pattern="STREAM", seed=42, working_set_bytes=32768)

    results = sim.run_all_policies_on_trace(trace, desc)
    pim_breakdown = sim.pim_model.evaluate(desc)
    cpu_breakdown = sim.cpu_model.evaluate(sim.cache_model.get_stats(), desc.operation_count)

    # 1. Component breakdown
    fig_comp = plot_component_breakdown(cpu_breakdown, pim_breakdown)
    assert fig_comp is not None
    assert len(fig_comp.data) > 0

    # 2. Donut
    fig_donut = plot_cache_event_donut(100, 20, 0.833)
    assert fig_donut is not None

    # 3. Policy comparison
    fig_pol = plot_policy_comparison(results, "Reuse-aware")
    assert fig_pol is not None
    assert len(fig_pol.data) == 1

    # 4. Speedup vs bandwidth
    fig_bw = plot_speedup_vs_bandwidth(trace, desc, cfg)
    assert fig_bw is not None

    # 5. Performance vs bank count
    fig_banks = plot_performance_vs_bank_count(trace, desc, cfg)
    assert fig_banks is not None

    # 6. Bank distribution
    fig_dist = plot_bank_distribution(pim_breakdown.per_bank_work, pim_breakdown.bank_imbalance_factor)
    assert fig_dist is not None

    # 7. Locality vs working set
    fig_loc = plot_hit_miss_vs_workingset(gen, sim, "STREAM", 42, 32)
    assert fig_loc is not None


def test_3d_policy_layer_graph():
    """Verify that the 3D Policy Layer graph renders valid Scatter3d and Surface figures."""
    from cachepim.ui.charts import plot_3d_policy_layer
    from cachepim.ui.policy_explainer import humanize_decision_reason

    cfg = CachePIMConfig()
    sim = Simulator(cfg)
    gen = WorkloadGenerator(line_size_bytes=cfg.cache.line_size_bytes)

    # Test Ribbon style (Scatter3d)
    fig_ribbon = plot_3d_policy_layer(gen, sim, "STREAM", 42, cfg, metric="latency", style="ribbon")
    assert fig_ribbon is not None
    assert len(fig_ribbon.data) == 6  # 6 policies

    # Test Surface style (Surface)
    fig_surface = plot_3d_policy_layer(gen, sim, "STREAM", 42, cfg, metric="speedup", style="surface")
    assert fig_surface is not None
    assert len(fig_surface.data) == 1

    # Test Crossover Landscape style
    from cachepim.ui.charts import plot_3d_crossover_landscape
    fig_crossover = plot_3d_crossover_landscape(gen, sim, "STREAM", 42, cfg, current_ws_kb=32, current_link_bw_gb_s=16.0, current_speedup=2.5)
    assert fig_crossover is not None
    assert len(fig_crossover.data) == 3  # Surface + Break-even Plane + Active Beacon

    # Test humanize_decision_reason
    assert "Retained on Host CPU" in humanize_decision_reason("REUSE_AWARE_PRESERVED_CPU_DUE_TO_REUSE")
    assert "Offloaded to PIM" in humanize_decision_reason("COST_PIM_LOWER")


def test_clean_html_prevents_code_blocks():
    """Verify that clean_html strips leading indentation and blank lines to avoid markdown code blocks."""
    from cachepim.ui.theme import clean_html

    sample_html = """
        <div class="hero-container">
            <div class="hero-title">Title</div>

            <div class="disclaimer-banner">
                <span>Notice</span>
            </div>
        </div>
    """
    cleaned = clean_html(sample_html)
    for line in cleaned.splitlines():
        assert not line.startswith("    "), f"Line still has 4 leading spaces: {line}"
        assert line.strip() == line, f"Line has unstripped whitespace: {line}"
    assert len(cleaned.splitlines()) == 6
