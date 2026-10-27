"""Advanced Data Visualizations for CachePIM.

Provides publication-grade interactive Plotly figures:
1. CPU vs PIM component-level latency breakdown
2. Cache hit/miss donut with locality stats
3. Six execution policies latency and regret comparison
4. Cache hit/miss rates vs working-set size with capacity boundary
5. Modeled speedup vs Host-to-PIM transfer bandwidth with crossover point
6. Performance scaling vs PIM bank count
7. Per-bank workload distribution and imbalance
8. 2D architectural crossover heatmap
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.types import CPUCostBreakdown, PIMCostBreakdown, SimulationResult
from cachepim.workloads import WorkloadGenerator

# Standardized Theme Palette - Dark Graphite, Muted Blue, Sage Green & Soft Amber
PLOT_BG = "#151A22"
PAPER_BG = "#222B36"
GRID_COLOR = "rgba(57, 68, 83, 0.5)"
BORDER_COLOR = "#394453"
FONT_FAMILY = "Inter, -apple-system, sans-serif"
TEXT_COLOR = "#E2E8F0"
TEXT_MUTED = "#A8B3C2"

COLOR_CPU_PRIMARY = "#91B8D8"
COLOR_CPU_CYAN = "#91B8D8"
COLOR_CPU_LIGHT = "#A7C9E5"

COLOR_PIM_PRIMARY = "#8FB7A5"
COLOR_PIM_VIOLET = "#8FB7A5"
COLOR_PIM_LIGHT = "#A3C6B6"

COLOR_AMBER = "#D5AD72"
COLOR_EMERALD = "#8FB7A5"
COLOR_ROSE = "#D5AD72"


def apply_dark_layout(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    """Apply consistent clean dark theme to Plotly figures with collision-free spacing."""
    layout_title = (
        dict(
            text=f"<b>{title}</b>",
            font=dict(family=FONT_FAMILY, size=14, color="#FFFFFF"),
            x=0.02,
            y=0.96,
        )
        if title
        else None
    )
    fig.update_layout(
        title=layout_title,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        margin=dict(l=50, r=25, t=45 if title else 25, b=75),
        height=height,
        hovermode="x unified" if "scatter" in fig.data[0].type else "closest",
        legend=dict(
            bgcolor="rgba(34, 43, 54, 0.9)",
            bordercolor=BORDER_COLOR,
            borderwidth=1,
            font=dict(size=10, color=TEXT_COLOR),
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_MUTED),
        title_font=dict(color=TEXT_COLOR, size=11),
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_MUTED),
        title_font=dict(color=TEXT_COLOR, size=11),
        automargin=True,
    )
    return fig


def plot_component_breakdown(
    cpu_cost: CPUCostBreakdown,
    pim_cost: Optional[PIMCostBreakdown],
) -> go.Figure:
    """Component-level latency breakdown comparing CPU and PIM in microseconds."""
    categories = []
    values_us = []
    systems = []
    colors = []

    # CPU Components
    categories.extend(["Cache Service", "Arithmetic Compute", "Dirty Writeback"])
    values_us.extend([
        cpu_cost.cache_service_time_ns / 1000.0,
        cpu_cost.compute_time_ns / 1000.0,
        cpu_cost.writeback_time_ns / 1000.0,
    ])
    systems.extend(["CPU-Cache", "CPU-Cache", "CPU-Cache"])
    colors.extend([COLOR_CPU_CYAN, COLOR_CPU_PRIMARY, COLOR_AMBER])

    # PIM Components
    if pim_cost:
        categories.extend([
            "Host to PIM Transfer",
            "Internal DRAM Service",
            "Bank Compute",
            "PIM to Host Transfer",
            "Launch & Sync",
            "Bank Imbalance",
        ])
        values_us.extend([
            pim_cost.h2p_transfer_ns / 1000.0,
            pim_cost.internal_memory_service_ns / 1000.0,
            pim_cost.compute_ns / 1000.0,
            pim_cost.p2h_transfer_ns / 1000.0,
            (pim_cost.launch_overhead_ns + pim_cost.sync_overhead_ns) / 1000.0,
            pim_cost.imbalance_overhead_ns / 1000.0,
        ])
        systems.extend(["PIM-Always"] * 6)
        colors.extend([
            COLOR_PIM_LIGHT,
            COLOR_PIM_PRIMARY,
            COLOR_PIM_VIOLET,
            COLOR_PIM_LIGHT,
            "#779E8D",
            COLOR_AMBER,
        ])

    df = pd.DataFrame({
        "Component": categories,
        "Latency_us": values_us,
        "System": systems,
        "Color": colors,
    })

    fig = px.bar(
        df,
        x="Component",
        y="Latency_us",
        color="System",
        text_auto=".2f",
        color_discrete_map={"CPU-Cache": COLOR_CPU_LIGHT, "PIM-Always": COLOR_PIM_VIOLET},
    )
    max_val = df["Latency_us"].max() if not df.empty else 1.0
    fig.update_traces(
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Latency: %{y:.2f} μs<extra></extra>",
    )
    fig.update_yaxes(title_text="Modeled Latency (μs)", range=[0, max_val * 1.18], automargin=True)
    fig.update_xaxes(title_text="Architectural Execution Stage", automargin=True, tickangle=-15)
    return apply_dark_layout(fig, "Component-Level Analytical Cost Breakdown", height=380)


def plot_cache_event_donut(hits: int, misses: int, hit_rate: float, height: int = 380) -> go.Figure:
    """Cache Hit / Miss event donut chart with hit rate centered."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["LLC Hits", "LLC Misses"],
                values=[hits, misses],
                hole=0.68,
                marker=dict(colors=[COLOR_EMERALD, COLOR_ROSE]),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b>: %{value:,} accesses (%{percent})<extra></extra>",
            )
        ]
    )
    fig.add_annotation(
        text=f"<b>{hit_rate * 100.0:.1f}%</b><br><span style='font-size: 10px; color: #A8B3C2;'>Hit Rate</span>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=18, color="#FFFFFF"),
    )
    return apply_dark_layout(fig, f"LLC Access Outcomes ({hits + misses:,} Total)", height=height)


def plot_policy_comparison(results: List[SimulationResult], active_policy: str) -> go.Figure:
    """Bar chart comparing modeled latency across all six policies with regret indicator."""
    policies = [r.policy_name for r in results]
    latencies_us = [r.selected_model_ns / 1000.0 for r in results]
    paths = [r.selected_path for r in results]
    regrets_us = [r.regret_ns / 1000.0 for r in results]

    colors = []
    for p, path in zip(policies, paths):
        if p == active_policy:
            colors.append(COLOR_EMERALD)  # Highlight active policy
        elif path == "CPU":
            colors.append(COLOR_CPU_PRIMARY)
        else:
            colors.append(COLOR_PIM_PRIMARY)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=policies,
            y=latencies_us,
            marker=dict(color=colors, line=dict(color="#FFFFFF", width=[2 if p == active_policy else 0 for p in policies])),
            text=[f"{val:.2f} μs" for val in latencies_us],
            textposition="outside",
            name="Modeled Latency (μs)",
            hovertemplate="<b>%{x}</b><br>Path: " + "%{customdata[0]}<br>Latency: %{y:.2f} μs<br>Regret: %{customdata[1]:.2f} μs<extra></extra>",
            customdata=list(zip(paths, regrets_us)),
        )
    )

    max_lat = max(latencies_us) if latencies_us else 1.0
    fig.update_yaxes(title_text="Modeled Latency (μs)", range=[0, max_lat * 1.18], automargin=True)
    fig.update_xaxes(title_text="Execution Policy", automargin=True)
    return apply_dark_layout(fig, "Latency Across Six Execution Policies", height=380)


def normalize_pattern_name(pattern: str) -> str:
    """Ensure pattern is one of the four supported synthetic trace generator modes."""
    p_str = str(pattern).upper()
    if "REUSE" in p_str or "GEMV" in p_str:
        return "REUSE"
    elif "RANDOM" in p_str or "BS" in p_str:
        return "RANDOM"
    elif "MIXED" in p_str or "SEL" in p_str:
        return "MIXED_PHASE"
    else:
        return "STREAM"


def plot_hit_miss_vs_workingset(
    generator: WorkloadGenerator,
    simulator: Simulator,
    pattern: str,
    seed: int,
    capacity_kb: int,
) -> go.Figure:
    """Plot Cache Hit Rate and Miss Rate curves vs Working-Set Size."""
    ws_sizes = [8, 16, 24, 32, 48, 64, 96, 128, 192, 256]
    hit_rates = []
    miss_rates = []
    valid_pattern = normalize_pattern_name(pattern)

    for ws in ws_sizes:
        tr, dsc = generator.generate(
            pattern=valid_pattern,
            seed=seed,
            working_set_bytes=ws * 1024,
            access_count=2048,
        )
        simulator.cache_model.reset()
        stats = simulator.cache_model.run(tr)
        hit_rates.append(stats.hit_rate * 100.0)
        miss_rates.append(stats.miss_rate * 100.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ws_sizes,
            y=hit_rates,
            mode="lines+markers",
            name="Cache Hit Rate (%)",
            line=dict(color=COLOR_CPU_CYAN, width=2.5),
            marker=dict(size=7),
            hovertemplate="Working Set: %{x} KiB<br>Hit Rate: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ws_sizes,
            y=miss_rates,
            mode="lines+markers",
            name="Cache Miss Rate (%)",
            line=dict(color=COLOR_ROSE, width=2.5, dash="dash"),
            marker=dict(size=7),
            hovertemplate="Working Set: %{x} KiB<br>Miss Rate: %{y:.1f}%<extra></extra>",
        )
    )

    # LLC Capacity Threshold Line
    fig.add_vline(
        x=capacity_kb,
        line_width=1.5,
        line_dash="dot",
        line_color="#CBD5E1",
        annotation_text=f"LLC Capacity ({capacity_kb} KiB)",
        annotation_position="top right",
        annotation_font=dict(color="#A8B3C2", size=10),
    )

    fig.update_xaxes(title_text="Working-Set Size (KiB)")
    fig.update_yaxes(title_text="Rate (%)", range=[-5, 105])
    return apply_dark_layout(fig, f"LLC Locality Curve vs. Working-Set Size ({pattern})", height=380)


def plot_speedup_vs_bandwidth(
    trace: list,
    desc: any,
    base_config: CachePIMConfig,
) -> go.Figure:
    """Plot modeled speedup vs Host-to-PIM link bandwidth with parity crossover line."""
    bws = [1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0]
    speedups = []
    cpu_latencies = []
    pim_latencies = []

    for b in bws:
        cfg = CachePIMConfig.from_dict(base_config.to_dict())
        cfg.transfer.host_to_pim_bandwidth_bytes_per_ns = float(b)
        cfg.transfer.pim_to_host_bandwidth_bytes_per_ns = float(b)
        sim = Simulator(cfg)
        res = sim.run_all_policies_on_trace(trace, desc)
        rd = {r.policy_name: r.selected_model_ns for r in res}
        sp = rd["CPU-cache"] / rd["PIM-always"]
        speedups.append(sp)
        cpu_latencies.append(rd["CPU-cache"] / 1000.0)
        pim_latencies.append(rd["PIM-always"] / 1000.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=bws,
            y=speedups,
            mode="lines+markers",
            name="PIM Speedup over CPU-cache",
            line=dict(color=COLOR_PIM_LIGHT, width=3),
            marker=dict(size=8, color=COLOR_PIM_VIOLET),
            hovertemplate="Link BW: %{x} GB/s<br>Speedup: %{y:.2f}x<extra></extra>",
        )
    )

    # 1.0x Parity Crossover line
    fig.add_hline(
        y=1.0,
        line_width=1.5,
        line_dash="dash",
        line_color=COLOR_AMBER,
        annotation_text="Parity Crossover (1.0x)",
        annotation_position="bottom right",
        annotation_font=dict(color=COLOR_AMBER, size=10),
    )

    fig.update_xaxes(title_text="Host-to-PIM Link Bandwidth (GB/s)")
    fig.update_yaxes(title_text="Modeled Speedup (CPU Latency / PIM Latency)")
    return apply_dark_layout(fig, "Modeled Speedup Sensitivity to Interconnect Bandwidth", height=380)


def plot_performance_vs_bank_count(
    trace: list,
    desc: any,
    base_config: CachePIMConfig,
) -> go.Figure:
    """Plot modeled PIM latency and speedup vs configured PIM bank count."""
    bank_counts = [4, 8, 16, 32, 64]
    pim_latencies_us = []
    speedups = []

    for b in bank_counts:
        cfg = CachePIMConfig.from_dict(base_config.to_dict())
        cfg.pim.bank_count = b
        sim = Simulator(cfg)
        res = sim.run_all_policies_on_trace(trace, desc)
        rd = {r.policy_name: r.selected_model_ns for r in res}
        pim_latencies_us.append(rd["PIM-always"] / 1000.0)
        speedups.append(rd["CPU-cache"] / rd["PIM-always"])

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[f"{b} Banks" for b in bank_counts],
            y=pim_latencies_us,
            name="PIM Latency (μs)",
            marker=dict(color=COLOR_PIM_PRIMARY),
            text=[f"{v:.2f} μs" for v in pim_latencies_us],
            textposition="outside",
            hovertemplate="Banks: %{x}<br>Latency: %{y:.2f} μs<extra></extra>",
        )
    )

    max_b = max(pim_latencies_us) if pim_latencies_us else 1.0
    fig.update_xaxes(title_text="Configured PIM Bank Count", automargin=True)
    fig.update_yaxes(title_text="Modeled PIM Execution Latency (μs)", range=[0, max_b * 1.18], automargin=True)
    return apply_dark_layout(fig, "PIM Performance Scaling vs. Bank Count", height=380)


def plot_bank_distribution(per_bank_work: List[int], imbalance_factor: float) -> go.Figure:
    """Plot work assigned to each PIM bank with mean workload line."""
    bank_ids = [f"B{i}" for i in range(len(per_bank_work))]
    mean_work = sum(per_bank_work) / len(per_bank_work) if per_bank_work else 0

    colors = [
        COLOR_AMBER if w == max(per_bank_work) and imbalance_factor > 1.1 else COLOR_PIM_VIOLET
        for w in per_bank_work
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=bank_ids,
            y=per_bank_work,
            marker=dict(color=colors),
            hovertemplate="<b>%{x}</b>: %{y:,} operations<extra></extra>",
            name="Operations per Bank",
        )
    )

    # Mean line
    fig.add_hline(
        y=mean_work,
        line_dash="dash",
        line_color=COLOR_CPU_PRIMARY,
        annotation_text=f"Mean Workload ({mean_work:.0f} ops)",
        annotation_position="top left",
        annotation_font=dict(color=COLOR_CPU_PRIMARY, size=10),
        annotation_bgcolor="#1B222C",
        annotation_bordercolor="#394453",
        annotation_borderwidth=1,
    )

    max_w = max(per_bank_work) if per_bank_work else 1.0
    fig.update_xaxes(title_text="PIM Bank ID", automargin=True)
    fig.update_yaxes(title_text="Operation Count", range=[0, max_w * 1.18], automargin=True)
    return apply_dark_layout(
        fig,
        f"PIM Bank Workload Distribution (Imbalance Factor: {imbalance_factor:.3f}x)",
        height=320,
    )


def plot_3d_crossover_landscape(
    generator: WorkloadGenerator,
    simulator: Simulator,
    pattern: str,
    seed: int,
    base_config: CachePIMConfig,
    current_ws_kb: int = 32,
    current_link_bw_gb_s: float = 16.0,
    current_speedup: float = 1.0,
) -> go.Figure:
    """Generate an intuitive 3D architectural crossover terrain with a 1.0x Break-Even Plane.

    Physical Axes:
    - X-axis: Host-to-PIM Link Bandwidth (GB/s)
    - Y-axis: Working-Set Size (KiB)
    - Z-axis: PIM Speedup over Host CPU-cache (x)
    - Reference Plane: Semi-transparent amber sheet at Z = 1.0x (Break-Even Horizon)
    - Active Beacon: Glowing marker indicating the currently configured simulation point.
    """
    from cachepim.config import TransferConfig
    from cachepim.pim_model import PIMModel

    ws_sizes = [8, 16, 24, 32, 48, 64, 96, 128, 192, 256]
    bw_list = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0]

    valid_pattern = normalize_pattern_name(pattern)
    z_matrix = []

    for ws in ws_sizes:
        tr, dsc = generator.generate(
            pattern=valid_pattern,
            seed=seed,
            working_set_bytes=ws * 1024,
            access_count=1024,
        )
        res = simulator.run_all_policies_on_trace(tr, dsc)
        rd = {r.policy_name: r.selected_model_ns for r in res}
        cpu_lat = rd["CPU-cache"]

        row = []
        for bw in bw_list:
            t_cfg = TransferConfig(
                host_to_pim_bandwidth_bytes_per_ns=bw,
                pim_to_host_bandwidth_bytes_per_ns=bw,
            )
            pm = PIMModel(base_config.pim, t_cfg)
            pb = pm.evaluate(dsc)
            sp = cpu_lat / pb.total_pim_time_ns if pb and pb.total_pim_time_ns > 0 else 1.0
            row.append(sp)
        z_matrix.append(row)

    # Reference Plane at Z = 1.0x (Break-even threshold)
    z_plane = [[1.0 for _ in bw_list] for _ in ws_sizes]

    fig = go.Figure()

    # 1. 3D Continuous Performance Surface
    fig.add_trace(
        go.Surface(
            x=bw_list,
            y=ws_sizes,
            z=z_matrix,
            colorscale="Viridis",
            name="PIM Speedup Surface",
            showscale=True,
            colorbar=dict(
                title=dict(text="Speedup (x)", font=dict(color="#E2E8F0")),
                tickfont=dict(color="#E2E8F0"),
                len=0.75,
            ),
            contours=dict(
                z=dict(show=True, usecolormap=True, highlightcolor="#91B8D8", project_z=True)
            ),
            hovertemplate="Link Bandwidth: %{x} GB/s<br>Working Set: %{y} KiB<br>PIM Speedup: %{z:.2f}x<extra></extra>",
        )
    )

    # 2. Semi-Transparent Break-Even Reference Plane at Z = 1.0x
    fig.add_trace(
        go.Surface(
            x=bw_list,
            y=ws_sizes,
            z=z_plane,
            showscale=False,
            opacity=0.35,
            colorscale=[[0, "#D5AD72"], [1, "#D5AD72"]],
            name="Break-Even Plane (1.0x)",
            hovertemplate="<b>Break-Even Horizon (1.0x)</b><br>Above Plane: PIM Offload Advantage<br>Below Plane: CPU Cache Advantage<extra></extra>",
        )
    )

    # 3. Active Simulation Point Beacon
    fig.add_trace(
        go.Scatter3d(
            x=[current_link_bw_gb_s],
            y=[current_ws_kb],
            z=[current_speedup],
            mode="markers+text",
            marker=dict(size=8, color="#91B8D8", symbol="diamond", line=dict(color="#FFFFFF", width=2)),
            text=["Active Setup"],
            textposition="top center",
            name="Active Setup",
            hovertemplate=f"<b>Active Configuration</b><br>Link Bandwidth: {current_link_bw_gb_s:.1f} GB/s<br>Working Set: {current_ws_kb} KiB<br>Speedup: {current_speedup:.2f}x ({'PIM Advantage' if current_speedup >= 1.0 else 'CPU Advantage'})<extra></extra>",
        )
    )

    title_text = "3D Architectural Crossover Landscape (Speedup vs. Working Set & Link Bandwidth)"

    fig.update_layout(
        title=dict(
            text=f"<b>{title_text}</b>",
            font=dict(family=FONT_FAMILY, size=15, color="#FFFFFF"),
            x=0.02,
            y=0.96,
        ),
        paper_bgcolor=PAPER_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        margin=dict(l=20, r=20, t=50, b=20),
        height=540,
        scene=dict(
            xaxis=dict(
                title="Host-to-PIM Link Bandwidth (GB/s)",
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            yaxis=dict(
                title="Working-Set Size (KiB)",
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            zaxis=dict(
                title="PIM Speedup over CPU-cache (x)",
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            camera=dict(
                eye=dict(x=1.75, y=-1.65, z=1.2),
            ),
        ),
        legend=dict(
            bgcolor="rgba(11, 17, 32, 0.8)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )
    return fig


def plot_3d_policy_layer(
    generator: WorkloadGenerator,
    simulator: Simulator,
    pattern: str,
    seed: int,
    base_config: CachePIMConfig,
    metric: str = "latency",
    style: str = "ribbon",
    current_ws_kb: int = 32,
    current_link_bw_gb_s: float = 16.0,
    current_speedup: float = 1.0,
) -> go.Figure:
    """Generate an interactive 3D graph for the Policy Layer across working-set sizes."""
    if style == "crossover":
        return plot_3d_crossover_landscape(
            generator=generator,
            simulator=simulator,
            pattern=pattern,
            seed=seed,
            base_config=base_config,
            current_ws_kb=current_ws_kb,
            current_link_bw_gb_s=current_link_bw_gb_s,
            current_speedup=current_speedup,
        )

    policies = ["CPU-cache", "CPU-no-cache", "PIM-always", "Cost-based", "Reuse-aware", "Oracle"]
    ws_sizes = [8, 16, 24, 32, 48, 64, 96, 128, 192, 256]

    policy_colors = {
        "CPU-cache": COLOR_CPU_CYAN,
        "CPU-no-cache": "#A8B3C2",
        "PIM-always": COLOR_PIM_VIOLET,
        "Cost-based": COLOR_AMBER,
        "Reuse-aware": "#779E8D",
        "Oracle": "#CBD5E1",
    }

    z_matrix = []
    valid_pattern = normalize_pattern_name(pattern)
    for ws in ws_sizes:
        tr, dsc = generator.generate(
            pattern=valid_pattern,
            seed=seed,
            working_set_bytes=ws * 1024,
            access_count=1024,
        )
        res = simulator.run_all_policies_on_trace(tr, dsc)
        rd = {r.policy_name: r.selected_model_ns for r in res}
        cpu_lat = rd["CPU-cache"]

        row = []
        for p in policies:
            if metric == "speedup":
                val = cpu_lat / rd[p] if rd[p] > 0 else 1.0
            else:
                val = rd[p] / 1000.0
            row.append(val)
        z_matrix.append(row)

    fig = go.Figure()

    if style == "surface":
        fig.add_trace(
            go.Surface(
                z=z_matrix,
                x=list(range(len(policies))),
                y=ws_sizes,
                colorscale="Viridis",
                colorbar=dict(
                    title=dict(
                        text="Latency (μs)" if metric == "latency" else "Speedup (x)",
                        font=dict(color="#E2E8F0"),
                    ),
                    tickfont=dict(color="#E2E8F0"),
                ),
                contours=dict(
                    z=dict(show=True, usecolormap=True, highlightcolor="#91B8D8", project_z=True)
                ),
                hovertemplate="Policy: %{x}<br>Working Set: %{y} KiB<br>Value: %{z:.2f}<extra></extra>",
            )
        )
    else:
        for p_idx, p in enumerate(policies):
            p_z = [row[p_idx] for row in z_matrix]
            fig.add_trace(
                go.Scatter3d(
                    x=[p] * len(ws_sizes),
                    y=ws_sizes,
                    z=p_z,
                    mode="lines+markers",
                    name=p,
                    line=dict(color=policy_colors[p], width=6),
                    marker=dict(size=5, color=policy_colors[p]),
                    hovertemplate=f"<b>{p}</b><br>Working Set: %{{y}} KiB<br>{'Latency: %{z:.2f} μs' if metric == 'latency' else 'Speedup: %{z:.2f}x'}<extra></extra>",
                )
            )

    z_label = "Modeled Latency (μs)" if metric == "latency" else "Speedup vs. CPU-cache (x)"
    title_text = f"3D Policy Layer Landscape ({'Latency' if metric == 'latency' else 'Speedup'} vs. Working-Set Size)"

    fig.update_layout(
        title=dict(
            text=f"<b>{title_text}</b>",
            font=dict(family=FONT_FAMILY, size=15, color="#FFFFFF"),
            x=0.02,
            y=0.96,
        ),
        paper_bgcolor=PAPER_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        margin=dict(l=20, r=20, t=50, b=20),
        height=520,
        scene=dict(
            xaxis=dict(
                title="Policy Layer",
                tickmode="array" if style == "surface" else "auto",
                tickvals=list(range(len(policies))) if style == "surface" else None,
                ticktext=policies if style == "surface" else None,
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            yaxis=dict(
                title="Working-Set Size (KiB)",
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            zaxis=dict(
                title=z_label,
                gridcolor=GRID_COLOR,
                backgroundcolor=PLOT_BG,
                color="#CBD5E1",
            ),
            camera=dict(
                eye=dict(x=1.65, y=-1.55, z=1.15),
            ),
        ),
        legend=dict(
            bgcolor="rgba(11, 17, 32, 0.8)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )
    return fig


# =============================================================
# VOLUMETRIC 3D BAR & DONUT VISUALIZATIONS
# =============================================================

def build_3d_cuboid_mesh(x_center, y_center, dx, dy, height, color, name, hover_label="Latency"):
    """Generate a closed 3D cuboid mesh for volumetric bars."""
    x0, x1 = x_center - dx / 2, x_center + dx / 2
    y0, y1 = y_center - dy / 2, y_center + dy / 2
    z0, z1 = 0.0, max(float(height), 0.001)

    vx = [x0, x1, x1, x0, x0, x1, x1, x0]
    vy = [y0, y0, y1, y1, y0, y0, y1, y1]
    vz = [z0, z0, z0, z0, z1, z1, z1, z1]

    i = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
    j = [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6]
    k = [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5]

    return go.Mesh3d(
        x=vx,
        y=vy,
        z=vz,
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=1.0,
        flatshading=True,
        name=name,
        showlegend=True,
        lighting=dict(ambient=0.65, diffuse=0.8, specular=0.25, roughness=0.4),
        hovertemplate=f"<b>{name}</b><br>{hover_label}: {height:.2f} μs<extra></extra>",
    )


def build_3d_donut_slice(theta_start, theta_end, r_in, r_out, height, color, name, n_pts=36):
    """Generate an extruded 3D annulus slice (donut segment)."""
    import numpy as np

    arc = abs(theta_end - theta_start)
    n = max(4, int(n_pts * arc / (2 * np.pi)))
    angles = np.linspace(theta_start, theta_end, n)

    vx = np.concatenate([
        r_in * np.cos(angles),
        r_out * np.cos(angles),
        r_in * np.cos(angles),
        r_out * np.cos(angles),
    ])
    vy = np.concatenate([
        r_in * np.sin(angles),
        r_out * np.sin(angles),
        r_in * np.sin(angles),
        r_out * np.sin(angles),
    ])
    vz = np.concatenate([
        np.zeros(2 * n),
        np.full(2 * n, height),
    ])

    i, j, k = [], [], []
    for s in range(n - 1):
        bi0, bi1 = s, s + 1
        bo0, bo1 = n + s, n + s + 1
        ti0, ti1 = 2 * n + s, 2 * n + s + 1
        to0, to1 = 3 * n + s, 3 * n + s + 1
        # Bottom face
        i.extend([bi0, bi1])
        j.extend([bo0, bo0])
        k.extend([bi1, bo1])
        # Top face
        i.extend([ti0, ti1])
        j.extend([ti1, to0])
        k.extend([to0, to1])
        # Outer wall
        i.extend([bo0, bo1])
        j.extend([to0, to0])
        k.extend([bo1, to1])
        # Inner wall
        i.extend([bi0, ti0])
        j.extend([bi1, bi1])
        k.extend([ti0, ti1])

    # Start cap
    i.extend([0, 0])
    j.extend([n, 2 * n])
    k.extend([2 * n, 3 * n])
    # End cap
    i.extend([n - 1, n - 1])
    j.extend([3 * n - 1, 2 * n - 1])
    k.extend([2 * n - 1, 4 * n - 1])

    return go.Mesh3d(
        x=vx,
        y=vy,
        z=vz,
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=1.0,
        flatshading=True,
        name=name,
        showlegend=True,
        lighting=dict(ambient=0.7, diffuse=0.75, specular=0.3, roughness=0.35),
        hovertemplate=f"<b>{name}</b><extra></extra>",
    )


def plot_volumetric_policy_latency(results: List[SimulationResult], is_3d: bool = False) -> go.Figure:
    """Execution Latency by Policy - 2D Bar Chart (or Optional 3D Volumetric Cuboids)."""
    policies = [r.policy_name for r in results]
    latencies_us = [r.selected_model_ns / 1000.0 for r in results]
    paths = [r.selected_path for r in results]
    max_val = max(latencies_us) if latencies_us else 1.0

    # Muted Blue (#91B8D8) for CPU Path, Sage Green (#8FB7A5) for PIM Path
    colors = ["#91B8D8" if path == "CPU" else "#8FB7A5" for path in paths]

    fig = go.Figure()

    if is_3d:
        dx, dy = 0.55, 0.45
        label_x, label_y, label_z, label_text = [], [], [], []

        for idx, (p, val, col) in enumerate(zip(policies, latencies_us, colors)):
            fig.add_trace(build_3d_cuboid_mesh(idx, 0, dx, dy, val, col, p, "Execution Latency"))
            label_x.append(idx)
            label_y.append(0)
            label_z.append(val)
            label_text.append(f"{val:.1f} μs" if val >= 1 else f"{val:.2f} μs")

        fig.add_trace(
            go.Scatter3d(
                x=label_x,
                y=label_y,
                z=label_z,
                mode="text",
                text=label_text,
                textposition="top center",
                textfont=dict(color="#FFFFFF", size=11, family=FONT_FAMILY),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            margin=dict(l=15, r=15, t=30, b=45),
            height=390,
            scene=dict(
                xaxis=dict(
                    tickmode="array",
                    tickvals=list(range(len(policies))),
                    ticktext=policies,
                    title="Policy",
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                yaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                zaxis=dict(
                    title="Latency (μs)",
                    range=[0, max_val * 1.35],
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                camera=dict(eye=dict(x=-1.55, y=-1.8, z=1.25)),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.06,
                xanchor="center",
                x=0.5,
                font=dict(color="#E2E8F0", size=10),
            ),
        )
    else:
        fig.add_trace(
            go.Bar(
                x=policies,
                y=latencies_us,
                marker=dict(color=colors, line=dict(color="#FFFFFF", width=1)),
                text=[f"{val:.1f} μs" for val in latencies_us],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Latency: %{y:.2f} μs<extra></extra>",
            )
        )
        fig.update_yaxes(title_text="Latency (μs)", range=[0, max_val * 1.18], automargin=True)
        fig.update_xaxes(title_text="Policy", automargin=True)
        fig = apply_dark_layout(fig, "", height=390)

    return fig


def plot_volumetric_cache_donut(hits: int, misses: int, hit_rate: float, is_3d: bool = False) -> go.Figure:
    """CPU LLC Event Breakdown - 2D Donut Chart (or Optional 3D Volumetric Donut)."""
    import numpy as np

    total = hits + misses
    miss_rate = 1.0 - hit_rate if total > 0 else 0.0
    fig = go.Figure()

    if is_3d:
        r_in, r_out, height = 1.0, 2.2, 0.95
        split = 2 * np.pi * hit_rate

        m_hits = build_3d_donut_slice(0, split, r_in, r_out, height, "#8FB7A5", f"Hits ({hit_rate * 100:.1f}%)")
        m_misses = build_3d_donut_slice(split, 2 * np.pi, r_in, r_out, height, "#D5AD72", f"Misses ({miss_rate * 100:.1f}%)")

        fig.add_trace(m_hits)
        fig.add_trace(m_misses)

        mid_hits = split / 2.0
        hx = r_out * 1.25 * np.cos(mid_hits)
        hy = r_out * 1.25 * np.sin(mid_hits)

        mid_miss = split + (2 * np.pi - split) / 2.0
        mx = r_out * 1.25 * np.cos(mid_miss)
        my = r_out * 1.25 * np.sin(mid_miss)

        fig.add_trace(
            go.Scatter3d(
                x=[hx, mx],
                y=[hy, my],
                z=[height * 1.05, height * 1.05],
                mode="text",
                text=[f"Hits: {hits:,} ({hit_rate * 100:.1f}%)", f"Misses: {misses:,} ({miss_rate * 100:.1f}%)"],
                textfont=dict(color=["#8FB7A5", "#D5AD72"], size=11, family=FONT_FAMILY),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            margin=dict(l=15, r=15, t=30, b=45),
            height=390,
            scene=dict(
                xaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                yaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                zaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                camera=dict(eye=dict(x=1.35, y=-1.5, z=1.65)),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.06,
                xanchor="center",
                x=0.5,
                font=dict(color="#E2E8F0", size=10),
            ),
        )
    else:
        fig.add_trace(
            go.Pie(
                labels=[f"Hits ({hit_rate * 100:.1f}%)", f"Misses ({miss_rate * 100:.1f}%)"],
                values=[hits, misses],
                hole=0.68,
                marker=dict(colors=["#8FB7A5", "#D5AD72"]),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b>: %{value:,} accesses<extra></extra>",
            )
        )
        fig.add_annotation(
            text=f"<b>{hit_rate * 100.0:.1f}%</b><br><span style='font-size: 10px; color: #A8B3C2;'>Hit Rate</span>",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=18, color="#FFFFFF"),
        )
        fig = apply_dark_layout(fig, "", height=390)

    return fig


def plot_volumetric_cpu_cost(cpu_cost: CPUCostBreakdown, is_3d: bool = False) -> go.Figure:
    """CPU Cost Breakdown - 2D Bar Chart (or Optional 3D Volumetric Cuboids)."""
    categories = ["Cache Service", "Compute", "Writeback"]
    values = [
        cpu_cost.cache_service_time_ns / 1000.0,
        cpu_cost.compute_time_ns / 1000.0,
        cpu_cost.writeback_time_ns / 1000.0,
    ]
    max_val = max(values) if values else 1.0
    colors = ["#91B8D8", "#7A9EB8", "#A7C9E5"]

    fig = go.Figure()

    if is_3d:
        dx, dy = 0.55, 0.45
        label_x, label_y, label_z, label_text = [], [], [], []

        for idx, (cat, val, col) in enumerate(zip(categories, values, colors)):
            fig.add_trace(build_3d_cuboid_mesh(idx, 0, dx, dy, val, col, cat, "CPU Latency"))
            label_x.append(idx)
            label_y.append(0)
            label_z.append(val)
            label_text.append(f"{val:.1f} μs")

        fig.add_trace(
            go.Scatter3d(
                x=label_x,
                y=label_y,
                z=label_z,
                mode="text",
                text=label_text,
                textposition="top center",
                textfont=dict(color="#FFFFFF", size=11, family=FONT_FAMILY),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            margin=dict(l=15, r=15, t=30, b=45),
            height=390,
            scene=dict(
                xaxis=dict(
                    tickmode="array",
                    tickvals=list(range(len(categories))),
                    ticktext=categories,
                    title="Component",
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                yaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                zaxis=dict(
                    title="Latency (μs)",
                    range=[0, max_val * 1.35],
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                camera=dict(eye=dict(x=-1.5, y=-1.8, z=1.25)),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.06,
                xanchor="center",
                x=0.5,
                font=dict(color="#E2E8F0", size=10),
            ),
        )
    else:
        fig.add_trace(
            go.Bar(
                x=categories,
                y=values,
                marker=dict(color=colors),
                text=[f"{val:.1f} μs" for val in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Latency: %{y:.2f} μs<extra></extra>",
            )
        )
        fig.update_yaxes(title_text="Latency (μs)", range=[0, max_val * 1.18], automargin=True)
        fig.update_xaxes(title_text="Component", automargin=True)
        fig = apply_dark_layout(fig, "", height=390)

    return fig


def plot_volumetric_pim_cost(pim_cost: Optional[PIMCostBreakdown], is_3d: bool = False) -> go.Figure:
    """PIM Cost Breakdown - 2D Bar Chart (or Optional 3D Volumetric Cuboids)."""
    categories = [
        "Host to PIM",
        "Bank Compute",
        "PIM to Host",
        "Launch",
        "Sync",
        "Imbalance",
    ]
    if pim_cost:
        values = [
            pim_cost.h2p_transfer_ns / 1000.0,
            pim_cost.compute_ns / 1000.0,
            pim_cost.p2h_transfer_ns / 1000.0,
            pim_cost.launch_overhead_ns / 1000.0,
            pim_cost.sync_overhead_ns / 1000.0,
            pim_cost.imbalance_overhead_ns / 1000.0,
        ]
    else:
        values = [0.0] * 6

    max_val = max(values) if values else 1.0
    colors = ["#8FB7A5", "#779E8D", "#A3C6B6", "#91B8D8", "#6E9382", "#D5AD72"]

    fig = go.Figure()

    if is_3d:
        dx, dy = 0.55, 0.45
        label_x, label_y, label_z, label_text = [], [], [], []

        for idx, (cat, val, col) in enumerate(zip(categories, values, colors)):
            fig.add_trace(build_3d_cuboid_mesh(idx, 0, dx, dy, val, col, cat, "PIM Latency"))
            label_x.append(idx)
            label_y.append(0)
            label_z.append(val)
            label_text.append(f"{val:.1f} μs" if val >= 1 else f"{val:.2f} μs")

        fig.add_trace(
            go.Scatter3d(
                x=label_x,
                y=label_y,
                z=label_z,
                mode="text",
                text=label_text,
                textposition="top center",
                textfont=dict(color="#FFFFFF", size=11, family=FONT_FAMILY),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            margin=dict(l=15, r=15, t=30, b=45),
            height=390,
            scene=dict(
                xaxis=dict(
                    tickmode="array",
                    tickvals=list(range(len(categories))),
                    ticktext=categories,
                    title="Component",
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                yaxis=dict(showticklabels=False, title="", gridcolor=GRID_COLOR, backgroundcolor=PLOT_BG),
                zaxis=dict(
                    title="Latency (μs)",
                    range=[0, max_val * 1.35],
                    gridcolor=GRID_COLOR,
                    backgroundcolor=PLOT_BG,
                    color="#CBD5E1",
                ),
                camera=dict(eye=dict(x=-1.5, y=-1.8, z=1.25)),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.06,
                xanchor="center",
                x=0.5,
                font=dict(color="#E2E8F0", size=10),
            ),
        )
    else:
        fig.add_trace(
            go.Bar(
                x=categories,
                y=values,
                marker=dict(color=colors),
                text=[f"{val:.2f} μs" for val in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Latency: %{y:.2f} μs<extra></extra>",
            )
        )
        fig.update_yaxes(title_text="Latency (μs)", range=[0, max_val * 1.18], automargin=True)
        fig.update_xaxes(title_text="Component", automargin=True)
        fig = apply_dark_layout(fig, "", height=390)

    return fig
