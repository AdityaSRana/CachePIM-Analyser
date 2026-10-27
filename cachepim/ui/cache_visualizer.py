"""Working-Set vs LLC Capacity & Locality Visualizer.

Provides an intuitive architectural comparison between:
- Selected Working-Set Size (KiB)
- Configured LLC Cache Capacity (KiB)
- Cache Line Size (Bytes) & Total Cache Lines
- Measured Hit Rate vs Miss Rate
- Locality breakdown (Spatial vs Temporal)
"""

from __future__ import annotations

import streamlit as st

from cachepim.ui.theme import clean_html


def render_cache_capacity_visualizer(
    working_set_kb: int,
    capacity_kb: int,
    line_size_bytes: int,
    cache_hits: int,
    cache_misses: int,
    cache_hit_rate: float,
    cache_miss_rate: float,
    workload_type: str,
) -> None:
    """Render working-set vs cache-capacity visualization card."""
    ratio = working_set_kb / capacity_kb if capacity_kb > 0 else 1.0
    num_cache_lines = (capacity_kb * 1024) // line_size_bytes
    num_ws_lines = (working_set_kb * 1024) // line_size_bytes

    # Determine status & bar widths
    if ratio <= 1.0:
        fill_pct = min(100.0, ratio * 100.0)
        spill_pct = 0.0
        status_badge = '<span style="color: #8FB7A5; font-weight: 600;">Fits in Cache (Working set fits inside cache)</span>'
        status_desc = (
            f"The working set ({working_set_kb} KiB) completely fits within cache capacity ({capacity_kb} KiB). "
            f"After warm-up misses, capacity misses are 0. High cache reuse favors CPU execution."
        )
        bar_color = "#91B8D8"
    else:
        fill_pct = 100.0
        spill_pct = min(100.0, (ratio - 1.0) * 50.0)
        status_badge = '<span style="color: #D5AD72; font-weight: 600;">Exceeds Cache Capacity</span>'
        status_desc = (
            f"The working set ({working_set_kb} KiB) exceeds cache capacity ({capacity_kb} KiB) by {(ratio - 1.0) * 100.0:.0f}%. "
            f"Cache capacity misses occur as lines are repeatedly evicted, increasing CPU latency."
        )
        bar_color = "#D5AD72"

    # Locality notes
    if workload_type.upper() == "STREAM":
        locality_note = (
            f"<strong>Spatial Locality Effect:</strong> For streaming access (such as Vector Add), each {line_size_bytes}-byte cache line "
            f"holds {line_size_bytes // 4} 32-bit words. Sequential accesses achieve high hit rates within loaded lines."
        )
    elif workload_type.upper() == "REUSE":
        locality_note = (
            "<strong>Temporal Reuse Effect:</strong> Reused memory addresses remain resident if they fit within cache lines, "
            "producing high hit rates and low CPU execution time."
        )
    else:
        locality_note = (
            f"<strong>Capacity Pressure:</strong> The working set requires {num_ws_lines} cache lines vs {num_cache_lines} resident lines. "
            f"Excess lines trigger eviction on almost every non-contiguous reference."
        )

    html = f"""
    <div class="cachepim-card cachepim-card-cyan">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; flex-wrap: wrap; gap: 8px;">
            <div style="font-size: 1.05rem; font-weight: 700; color: #E2E8F0;">
                Working Set vs. Cache Capacity
            </div>
            <div>{status_badge}</div>
        </div>

        <div style="font-size: 0.84rem; color: #A8B3C2; margin-bottom: 1.1rem; line-height: 1.5;">
            {status_desc}
        </div>

        <!-- Footprint Progress Gauge -->
        <div style="margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; font-family: 'Inter', sans-serif; color: #A8B3C2; margin-bottom: 6px; flex-wrap: wrap; gap: 4px 12px;">
                <span>0 KiB</span>
                <span>LLC Capacity Threshold: <strong>{capacity_kb} KiB</strong> ({num_cache_lines} lines)</span>
                <span>Working-Set: <strong>{working_set_kb} KiB</strong> ({num_ws_lines} lines)</span>
            </div>
            <div style="height: 18px; width: 100%; background: #151A22; border-radius: 9px; overflow: hidden; border: 1px solid #394453; display: flex;">
                <div style="height: 100%; width: {min(100.0, (working_set_kb / max(capacity_kb * 1.5, working_set_kb)) * 100.0):.1f}%; background: {bar_color}; border-radius: 9px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: #A8B3C2; margin-top: 6px; flex-wrap: wrap; gap: 4px 12px;">
                <span>Line Size: {line_size_bytes} Bytes</span>
                <span>Footprint Ratio: <strong>{ratio:.2f}x</strong></span>
                <span>Resident Lines: <strong>{min(num_cache_lines, num_ws_lines)}</strong> / {num_ws_lines}</span>
            </div>
        </div>

        <!-- Locality Callout -->
        <div style="background: #1B222C; border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.82rem; color: #E2E8F0; border-left: 3px solid #91B8D8;">
            {locality_note}
        </div>
    </div>
    """
    st.markdown(clean_html(html), unsafe_allow_html=True)
