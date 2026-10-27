"""CachePIM UI Theme and Design System.

Provides consistent styling adhering to the design requirements:
- Dark graphite background (#151A22) with secondary surfaces (#1B222C, #222B36)
- Muted blue accents (#91B8D8) for CPU/cache operations
- Muted sage green accents (#8FB7A5) for PIM and parallel memory
- Soft amber highlights (#D5AD72) for warnings, bottlenecks, and crossover
- Clean borders (#394453) and readable high-contrast text (#E2E8F0, #A8B3C2)
"""

from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """Inject premium CSS styling into the Streamlit app."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --bg-dark: #151A22;
        --surface-dark: #1B222C;
        --surface-card: #222B36;
        --surface-card-hover: #2B3644;
        --border-subtle: #394453;
        --border-blue: rgba(145, 184, 216, 0.4);
        --border-green: rgba(143, 183, 165, 0.4);
        --border-amber: rgba(213, 173, 114, 0.4);
        
        --blue-accent: #91B8D8;
        --blue-dim: #6088A8;
        
        --green-accent: #8FB7A5;
        --green-dim: #5E8775;
        
        --amber-accent: #D5AD72;
        --amber-dim: #9E7D47;
        
        --text-primary: #E2E8F0;
        --text-secondary: #A8B3C2;
        --text-muted: #7E8B9B;
    }

    /* Overall App Background & Typography */
    .stApp {
        background: #151A22 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1400px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: #1B222C !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
    }

    /* Streamlit Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: var(--text-primary) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: #1B222C !important;
        padding: 6px !important;
        border-radius: 10px !important;
        border: 1px solid var(--border-subtle) !important;
        margin-bottom: 1.5rem !important;
        overflow-x: auto !important;
        scrollbar-width: thin !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.90rem !important;
        color: var(--text-secondary) !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 16px !important;
        transition: all 0.15s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(145, 184, 216, 0.14) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--blue-accent) !important;
        box-shadow: none !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }

    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* Cards & Containers */
    .cachepim-card {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    .cachepim-card:hover {
        border-color: rgba(145, 184, 216, 0.35);
    }

    .cachepim-card-cyan {
        border-left: 3px solid var(--blue-accent);
    }

    .cachepim-card-violet {
        border-left: 3px solid var(--green-accent);
    }

    .cachepim-card-amber {
        border-left: 3px solid var(--amber-accent);
    }

    .cachepim-card-emerald {
        border-left: 3px solid var(--green-accent);
    }

    /* KPI Metric Tiles */
    .kpi-tile {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem 1.15rem;
        text-align: left;
        position: relative;
        overflow: hidden;
        word-wrap: break-word;
        overflow-wrap: break-word;
        min-height: auto;
        min-width: 0;
    }

    .kpi-tile:hover {
        border-color: rgba(145, 184, 216, 0.35);
    }

    .kpi-label {
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 0.35rem;
        display: flex;
        align-items: center;
        gap: 6px;
        white-space: normal;
        word-break: break-word;
    }

    .kpi-value {
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.15;
        white-space: normal;
        word-break: break-word;
    }

    .kpi-unit {
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--text-secondary);
        margin-left: 4px;
    }

    .kpi-delta {
        font-size: 0.75rem;
        margin-top: 0.35rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 4px;
        white-space: normal;
        word-break: break-word;
    }

    .delta-cyan {
        color: var(--blue-accent);
        background: rgba(145, 184, 216, 0.12);
        border: 1px solid rgba(145, 184, 216, 0.25);
    }

    .delta-violet {
        color: var(--green-accent);
        background: rgba(143, 183, 165, 0.12);
        border: 1px solid rgba(143, 183, 165, 0.25);
    }

    .delta-amber {
        color: var(--amber-accent);
        background: rgba(213, 173, 114, 0.12);
        border: 1px solid rgba(213, 173, 114, 0.25);
    }

    .delta-emerald {
        color: var(--green-accent);
        background: rgba(143, 183, 165, 0.12);
        border: 1px solid rgba(143, 183, 165, 0.25);
    }

    /* Hero Section */
    .hero-container {
        background: var(--surface-dark);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }

    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #91B8D8 0%, #8FB7A5 100%);
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(145, 184, 216, 0.1);
        border: 1px solid rgba(145, 184, 216, 0.3);
        color: var(--blue-accent);
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 4px 12px;
        border-radius: 9999px;
        margin-bottom: 0.85rem;
    }

    .hero-title {
        font-size: clamp(1.4rem, 2.5vw, 2.0rem);
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #FFFFFF;
        margin-bottom: 0.4rem;
        line-height: 1.25;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    .hero-subtitle {
        font-size: 1.0rem;
        color: var(--text-secondary);
        font-weight: 400;
        line-height: 1.5;
        max-width: 900px;
        margin-bottom: 1.25rem;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Scientific Disclaimer Banner */
    .disclaimer-banner {
        background: rgba(213, 173, 114, 0.08);
        border: 1px solid rgba(213, 173, 114, 0.25);
        border-left: 4px solid var(--amber-accent);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.84rem;
        color: #E2E8F0;
        line-height: 1.45;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }

    /* Config Summary Chips Bar */
    .chip-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 0.75rem;
        align-items: center;
    }

    .config-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 5px 11px;
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    .config-chip strong {
        color: #FFFFFF;
        font-weight: 600;
    }

    .chip-cyan { border-color: rgba(145, 184, 216, 0.35); color: var(--blue-accent); }
    .chip-violet { border-color: rgba(143, 183, 165, 0.35); color: var(--green-accent); }
    .chip-amber { border-color: rgba(213, 173, 114, 0.35); color: var(--amber-accent); }

    /* Custom Streamlit Buttons */
    .stButton>button {
        background: var(--surface-card) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        padding: 0.5rem 1.25rem !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }

    .stButton>button:hover {
        background: var(--surface-card-hover) !important;
        border-color: var(--blue-accent) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
    }

    /* Primary Accent Run Button */
    .run-btn-container button {
        background: linear-gradient(135deg, #243B53 0%, #1D3A2F 100%) !important;
        border: 1px solid var(--blue-accent) !important;
        color: #FFFFFF !important;
        font-size: 1rem !important;
        padding: 0.65rem 1.75rem !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25) !important;
    }

    .run-btn-container button:hover {
        background: linear-gradient(135deg, #2B4866 0%, #24483B 100%) !important;
        border-color: #FFFFFF !important;
    }

    /* Dataframe & Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 8px !important;
        border: 1px solid var(--border-subtle) !important;
        background: var(--surface-card) !important;
        overflow-x: auto !important;
    }

    /* Plotly Chart Containers */
    .js-plotly-plot {
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* Decision Pipeline Stepper */
    .stepper-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        background: var(--surface-dark);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem;
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
        min-width: 0;
    }

    .stepper-step {
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        position: relative;
        word-wrap: break-word;
        overflow-wrap: break-word;
        min-width: 0;
    }

    .stepper-step:hover {
        border-color: rgba(145, 184, 216, 0.35);
    }

    .step-active-cyan { border-left: 3px solid var(--blue-accent); }
    .step-active-violet { border-left: 3px solid var(--green-accent); }
    .step-active-amber { border-left: 3px solid var(--amber-accent); }
    .step-active-emerald { border-left: 3px solid var(--green-accent); }

    .step-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 4px;
    }

    .step-value {
        font-size: 0.95rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 3px;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    .step-detail {
        font-size: 0.74rem;
        color: var(--text-secondary);
        line-height: 1.35;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Responsive Layout for Tablets & Mobile Devices */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        .hero-container {
            padding: 1.15rem 1.25rem !important;
        }
        .hero-title {
            font-size: 1.4rem !important;
        }
        .hero-subtitle {
            font-size: 0.88rem !important;
        }
        .chip-bar {
            gap: 6px !important;
        }
        .config-chip {
            padding: 4px 8px !important;
            font-size: 0.72rem !important;
        }
        .stepper-container {
            grid-template-columns: 1fr !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            -webkit-overflow-scrolling: touch !important;
        }
    }

    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #151A22;
    }
    ::-webkit-scrollbar-thumb {
        background: #394453;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #4A586B;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def clean_html(raw_html: str) -> str:
    """Strip all leading and trailing whitespace from each line and remove blank lines.

    Markdown treats any line indented by 4 or more spaces after a newline as an
    indented code block (<pre><code>). Stripping leading whitespace guarantees
    that HTML templates are never rendered as raw code snippets.
    """
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_hero(
    workload_name: str,
    working_set_kb: int,
    capacity_kb: int,
    bank_count: int,
    link_bw: float,
    policy_name: str,
    decision_path: str,
) -> None:
    """Render the hero section with branding and active architecture chips."""
    path_chip_class = "chip-cyan" if decision_path == "CPU" else "chip-violet"
    
    html = f"""
    <div class="hero-container">
        <div class="hero-badge">
            <span>CachePIM Architecture Exploration Platform</span>
            <span>•</span>
            <span>Version 1.1.0</span>
        </div>
        <div class="hero-title">Understand Where Computation Belongs</div>
        <div class="hero-subtitle">
            Trace-driven analytical modeling and crossover characterization comparing Host CPU execution through a capacity-limited Last-Level Cache (LLC) against offloading to Processing-in-Memory (PIM).
        </div>
        <div class="disclaimer-banner">
            <div>
                <strong>Notice:</strong> Results are analytical estimates derived under configurable mathematical model assumptions, not physical-hardware measurements. Designed for architectural sensitivity analysis, offloading policy characterization, and crossover boundary exploration.
            </div>
        </div>
        <div class="chip-bar">
            <span style="font-size: 0.8rem; color: #A8B3C2; font-weight: 600; text-transform: uppercase;">Active Profile:</span>
            <div class="config-chip chip-cyan">
                <span>Workload:</span> <strong>{workload_name}</strong>
            </div>
            <div class="config-chip">
                <span>Working Set:</span> <strong>{working_set_kb} KiB</strong>
            </div>
            <div class="config-chip chip-cyan">
                <span>LLC Capacity:</span> <strong>{capacity_kb} KiB</strong>
            </div>
            <div class="config-chip chip-violet">
                <span>PIM:</span> <strong>{bank_count} Banks @ {link_bw:.1f} GB/s Link</strong>
            </div>
            <div class="config-chip {path_chip_class}">
                <span>Policy Choice:</span> <strong>{policy_name} → {decision_path}</strong>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(html), unsafe_allow_html=True)


def render_kpi_card(
    label: str,
    value: str,
    unit: str = "",
    delta: str = "",
    delta_type: str = "cyan",
    subtext: str = "",
    icon: str = "",
) -> str:
    """Generate HTML for an individual KPI metric card."""
    delta_html = ""
    if delta:
        delta_html = f'<div class="kpi-delta delta-{delta_type}">{delta}</div>'
    
    subtext_html = ""
    if subtext:
        subtext_html = f'<div style="font-size: 0.72rem; color: #A8B3C2; margin-top: 5px;">{subtext}</div>'

    icon_html = f'<span style="margin-right: 4px;">{icon}</span>' if icon else ""

    html = f"""
    <div class="kpi-tile">
        <div class="kpi-label">{icon_html}{label}</div>
        <div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>
        {delta_html}
        {subtext_html}
    </div>
    """
    return clean_html(html)


def render_decision_pipeline_stepper(
    workload_name: str,
    working_set_kb: int,
    operation_count: int,
    cache_hit_rate: float,
    cache_hits: int,
    cache_misses: int,
    cpu_latency_us: float,
    pim_latency_us: float,
    speedup: float,
    selected_path: str,
    policy_name: str,
    decision_reason_humanized: str,
) -> None:
    """Render a visual 4-stage architectural decision pipeline."""
    hit_pct = cache_hit_rate * 100.0
    cache_step_class = "step-active-emerald" if hit_pct >= 50.0 else "step-active-amber"
    path_step_class = "step-active-cyan" if selected_path == "CPU" else "step-active-violet"
    path_badge_color = "#91B8D8" if selected_path == "CPU" else "#8FB7A5"

    html = f"""
    <div class="stepper-container">
        <!-- Stage 1 -->
        <div class="stepper-step step-active-cyan">
            <div class="step-header">
                <span>Stage 1: Workload Profiling</span>
            </div>
            <div class="step-value">{workload_name}</div>
            <div class="step-detail">{working_set_kb} KiB Working Set • {operation_count:,} Operations</div>
        </div>

        <!-- Stage 2 -->
        <div class="stepper-step {cache_step_class}">
            <div class="step-header">
                <span>Stage 2: Cache Simulation</span>
            </div>
            <div class="step-value">{hit_pct:.1f}% Cache Hit Rate</div>
            <div class="step-detail">{cache_hits:,} Hits vs {cache_misses:,} Misses (LRU)</div>
        </div>

        <!-- Stage 3 -->
        <div class="stepper-step step-active-amber">
            <div class="step-header">
                <span>Stage 3: Latency Modeling</span>
            </div>
            <div class="step-value">CPU: {cpu_latency_us:.1f} μs vs PIM: {pim_latency_us:.1f} μs</div>
            <div class="step-detail">Speedup: {speedup:.2f}x ({'PIM Faster' if speedup >= 1.0 else 'CPU Faster'})</div>
        </div>

        <!-- Stage 4 -->
        <div class="stepper-step {path_step_class}">
            <div class="step-header">
                <span>Stage 4: Policy Dispatch</span>
            </div>
            <div class="step-value" style="color: {path_badge_color};">Selected: {selected_path}</div>
            <div class="step-detail">{policy_name}: {decision_reason_humanized}</div>
        </div>
    </div>
    """
    st.markdown(clean_html(html), unsafe_allow_html=True)
