"""CPU vs PIM Execution Arena - Interactive 3D & 2D Architecture Visualizer.

Provides an architectural visualization of:
1. Host CPU processing unit and cache hierarchy
2. Last-Level Cache (LLC) module (differentiating hits vs misses)
3. Main Memory (Host DRAM)
4. High-speed Host-PIM Interconnect bus
5. Configurable PIM Memory Bank Array with individual DRAM and ALU layers
6. Complete 10-stage simulation timeline with moving data packet
7. Step-by-step playback controls (Start, Pause, Resume, Next, Previous, Restart)
8. Component inspector with detailed educational explanations
9. Live parameter and modeled execution comparison panel
10. Interactive camera controls and 2D canvas fallback.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def render_execution_arena_html(
    workload_type: str,
    working_set_kb: int,
    capacity_kb: int,
    line_size_bytes: int,
    bank_count: int,
    link_bw_gb_s: float,
    cache_hit_rate: float,
    cache_miss_rate: float,
    cache_hits: int,
    cache_misses: int,
    selected_path: str,
    policy_name: str,
    decision_reason: str,
    cpu_latency_us: float,
    pim_latency_us: float,
    speedup: float,
    h2p_time_us: float,
    bank_compute_time_us: float,
    p2h_time_us: float,
    bank_imbalance: float,
    per_bank_work: Optional[List[int]] = None,
) -> str:
    """Generate self-contained HTML for the CPU vs PIM Execution Arena."""
    if per_bank_work is None:
        per_bank_work = [100] * bank_count

    arena_data = {
        "workload": workload_type,
        "workingSetKb": working_set_kb,
        "capacityKb": capacity_kb,
        "lineSizeBytes": line_size_bytes,
        "bankCount": bank_count,
        "linkBwGbS": link_bw_gb_s,
        "hitRate": round(cache_hit_rate * 100.0, 1),
        "missRate": round(cache_miss_rate * 100.0, 1),
        "hits": cache_hits,
        "misses": cache_misses,
        "selectedPath": selected_path,
        "policyName": policy_name,
        "decisionReason": decision_reason,
        "cpuLatencyUs": round(cpu_latency_us, 2),
        "pimLatencyUs": round(pim_latency_us, 2),
        "speedup": round(speedup, 2),
        "h2pTimeUs": round(h2p_time_us, 2),
        "bankComputeTimeUs": round(bank_compute_time_us, 2),
        "p2hTimeUs": round(p2h_time_us, 2),
        "bankImbalance": round(bank_imbalance, 3),
        "perBankWork": per_bank_work,
    }
    data_json = json.dumps(arena_data)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>CPU vs PIM Execution Arena</title>
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        user-select: none;
    }}
    body {{
        background: #151A22;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        overflow: hidden;
        width: 100%;
        height: 100vh;
    }}
    #arena-container {{
        position: relative;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at 50% 40%, #1B222C 0%, #151A22 85%);
    }}
    #webgl-canvas {{
        width: 100%;
        height: 100%;
        display: block;
    }}

    /* Top Header Container & Toolbars */
    .arena-header-container {{
        position: absolute;
        top: 8px;
        left: 12px;
        right: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        z-index: 25;
        pointer-events: none;
    }}
    .arena-topbar {{
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
        pointer-events: none;
    }}
    .arena-toolbar {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
        background: rgba(27, 34, 44, 0.94);
        padding: 5px 9px;
        border-radius: 8px;
        border: 1px solid #394453;
        pointer-events: auto;
    }}
    .arena-title {{
        font-size: 0.82rem;
        font-weight: 700;
        color: #91B8D8;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-right: 6px;
    }}
    .ctrl-btn {{
        background: #222B36;
        border: 1px solid #394453;
        color: #E2E8F0;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }}
    .ctrl-btn:hover {{
        background: #2B3644;
        border-color: #91B8D8;
        color: #FFFFFF;
    }}
    .ctrl-btn.active {{
        background: #2B3644;
        border-color: #91B8D8;
        color: #FFFFFF;
    }}

    /* Pathway Status Banner (Flows directly below topbar without overlap) */
    .path-banner {{
        position: relative;
        background: rgba(34, 43, 54, 0.95);
        border: 1px solid #394453;
        border-radius: 8px;
        padding: 5px 14px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        pointer-events: auto;
        max-width: 480px;
        margin: 0 auto;
        transition: all 0.25s ease;
    }}
    .path-banner-badge {{
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }}
    .path-banner-text {{
        font-size: 0.68rem;
        color: #A8B3C2;
        line-height: 1.35;
    }}

    /* Right Telemetry & Parameter Panel */
    .arena-hud {{
        position: absolute;
        top: 96px;
        right: 12px;
        background: rgba(34, 43, 54, 0.95);
        border: 1px solid #394453;
        border-radius: 8px;
        padding: 8px 12px;
        z-index: 20;
        width: 275px;
        max-height: calc(100% - 210px);
        overflow-y: auto;
        word-wrap: break-word;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        transition: all 0.2s ease;
    }}
    .hud-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #394453;
        padding-bottom: 5px;
        margin-bottom: 7px;
    }}
    .hud-title {{
        font-size: 0.72rem;
        font-weight: 700;
        color: #A8B3C2;
        letter-spacing: 0.05em;
    }}
    .hud-badge {{
        font-size: 0.70rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
    }}
    .badge-cpu {{
        background: rgba(145, 184, 216, 0.15);
        color: #91B8D8;
        border: 1px solid rgba(145, 184, 216, 0.4);
    }}
    .badge-pim {{
        background: rgba(143, 183, 165, 0.15);
        color: #8FB7A5;
        border: 1px solid rgba(143, 183, 165, 0.4);
    }}
    .hud-row {{
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-bottom: 4px;
        gap: 6px;
    }}
    .hud-label {{
        color: #A8B3C2;
        white-space: nowrap;
    }}
    .hud-val {{
        font-family: 'Inter', -apple-system, sans-serif;
        font-weight: 600;
        color: #E2E8F0;
        text-align: right;
        word-break: break-word;
    }}
    .hud-notice {{
        margin-top: 6px;
        padding: 4px 8px;
        background: #1B222C;
        border: 1px solid #394453;
        border-radius: 4px;
        font-size: 0.68rem;
        color: #A8B3C2;
        line-height: 1.35;
    }}

    /* Component Info Panel (Popup when clicked or inspected) */
    .component-panel {{
        position: absolute;
        top: 96px;
        left: 12px;
        background: rgba(34, 43, 54, 0.96);
        border: 1px solid #394453;
        border-radius: 8px;
        padding: 10px 14px;
        z-index: 28;
        width: 300px;
        max-height: calc(100% - 210px);
        overflow-y: auto;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        display: none;
    }}
    .comp-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #394453;
        padding-bottom: 5px;
        margin-bottom: 7px;
    }}
    .comp-title {{
        font-size: 0.82rem;
        font-weight: 700;
        color: #91B8D8;
    }}
    .comp-close {{
        background: transparent;
        border: none;
        color: #A8B3C2;
        font-size: 0.9rem;
        font-weight: 700;
        cursor: pointer;
        padding: 0 4px;
        line-height: 1;
    }}
    .comp-close:hover {{
        color: #FFFFFF;
    }}
    .comp-desc {{
        font-size: 0.74rem;
        color: #E2E8F0;
        line-height: 1.4;
        margin-bottom: 6px;
        word-wrap: break-word;
    }}
    .comp-spec {{
        font-size: 0.70rem;
        color: #91B8D8;
        background: #1B222C;
        padding: 4px 8px;
        border-radius: 4px;
        border-left: 3px solid #91B8D8;
        word-wrap: break-word;
    }}

    /* Bottom Timeline Playback Panel */
    .arena-playback {{
        position: absolute;
        bottom: 8px;
        left: 12px;
        right: 295px;
        background: rgba(34, 43, 54, 0.95);
        border: 1px solid #394453;
        border-radius: 8px;
        padding: 7px 12px;
        z-index: 20;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    }}
    .playback-controls {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
        margin-bottom: 5px;
    }}
    .step-pills-bar {{
        display: flex;
        align-items: center;
        gap: 3px;
        flex-wrap: wrap;
        margin-left: 4px;
    }}
    .step-pill {{
        background: #222B36;
        border: 1px solid #394453;
        color: #A8B3C2;
        border-radius: 4px;
        padding: 2px 7px;
        font-size: 0.70rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
    }}
    .step-pill:hover {{
        background: #2B3644;
        color: #FFFFFF;
        border-color: #91B8D8;
    }}
    .step-pill.active {{
        background: #2B3644;
        border-color: #91B8D8;
        color: #FFFFFF;
    }}
    .playback-info {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
        border-top: 1px solid #394453;
        padding-top: 5px;
    }}
    .stage-title {{
        font-size: 0.76rem;
        font-weight: 700;
        color: #E2E8F0;
        margin-bottom: 2px;
    }}
    .stage-desc {{
        font-size: 0.70rem;
        color: #A8B3C2;
        line-height: 1.35;
        word-wrap: break-word;
    }}
    .stage-badge {{
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        white-space: nowrap;
        background: rgba(145, 184, 216, 0.12);
        color: #91B8D8;
        border: 1px solid rgba(145, 184, 216, 0.25);
    }}

    /* Legend strip */
    .legend-strip {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px 14px;
        margin-top: 5px;
        font-size: 0.68rem;
        color: #A8B3C2;
        border-top: 1px solid #394453;
        padding-top: 4px;
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }}
    .legend-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .dot-cyan {{ background: #91B8D8; }}
    .dot-green {{ background: #8FB7A5; }}
    .dot-amber {{ background: #D5AD72; }}
    .dot-grey {{ background: #CBD5E1; }}

    /* 2D Fallback Overlay */
    #fallback-canvas {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: none;
        z-index: 10;
        background: #151A22;
    }}

    @media (max-width: 1100px) {{
        .arena-playback {{
            right: 12px;
        }}
        .arena-hud {{
            top: auto;
            bottom: 140px;
            right: 12px;
            max-height: 220px;
        }}
    }}

    @media (max-width: 768px) {{
        .arena-topbar {{
            flex-direction: column;
            align-items: stretch;
            gap: 4px;
        }}
        .arena-toolbar {{
            justify-content: center;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        .path-banner {{
            max-width: 100%;
        }}
        .arena-hud {{
            width: calc(100% - 24px);
            left: 12px;
            right: 12px;
            bottom: 155px;
            max-height: 180px;
        }}
        .component-panel {{
            width: calc(100% - 24px);
            left: 12px;
            right: 12px;
            max-height: 180px;
        }}
        .arena-playback {{
            left: 8px;
            right: 8px;
            bottom: 6px;
            padding: 5px 8px;
        }}
        .step-pills-bar {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
    }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
<div id="arena-container">
    <!-- Top Header Container (Toolbars + Path Status Banner without overlap) -->
    <div class="arena-header-container">
        <div class="arena-topbar">
            <div class="arena-toolbar">
                <div class="arena-title">
                    <span>Execution Arena</span>
                </div>
                <button id="btn-view-mode" class="ctrl-btn" onclick="toggleViewMode()">View: Working Flow</button>
                <button class="ctrl-btn" onclick="setCameraView('iso')">Isometric</button>
                <button class="ctrl-btn" onclick="setCameraView('cpu')">Focus CPU</button>
                <button class="ctrl-btn" onclick="setCameraView('pim')">Focus PIM</button>
                <button class="ctrl-btn" onclick="setCameraView('top')">Top View</button>
                <button class="ctrl-btn" onclick="resetCamera()">Reset View</button>
                <button id="btn-toggle-2d" class="ctrl-btn" onclick="toggle2DFallback()">2D / 3D</button>
            </div>

            <div class="arena-toolbar">
                <span style="font-size: 0.72rem; color: #A8B3C2; margin-right: 4px;">Path:</span>
                <button id="btn-path-auto" class="ctrl-btn active" onclick="setPathMode('auto')">Auto ({arena_data["selectedPath"]})</button>
                <button id="btn-path-cpu" class="ctrl-btn" onclick="setPathMode('cpu')">CPU Path</button>
                <button id="btn-path-pim" class="ctrl-btn" onclick="setPathMode('pim')">PIM Path</button>
                <button id="btn-path-compare" class="ctrl-btn" onclick="setPathMode('compare')">Compare Both</button>
            </div>

            <div class="arena-toolbar">
                <span style="font-size: 0.72rem; color: #A8B3C2; margin-right: 4px;">Inspect:</span>
                <button class="ctrl-btn" onclick="inspectComponent('cpu')">CPU Core</button>
                <button class="ctrl-btn" onclick="inspectComponent('llc')">LLC Cache</button>
                <button class="ctrl-btn" onclick="inspectComponent('dram')">Host DRAM</button>
                <button class="ctrl-btn" onclick="inspectComponent('link')">Data Link</button>
                <button class="ctrl-btn" onclick="inspectComponent('pim')">PIM Banks</button>
            </div>
        </div>

        <!-- Pathway Comparison Banner (Flows directly beneath toolbars) -->
        <div id="path-status-banner" class="path-banner">
            <div id="path-banner-tag" class="path-banner-badge" style="color: {'#91B8D8' if arena_data['selectedPath'] == 'CPU' else '#8FB7A5'};">
                ACTIVE PATH: {'HOST CPU & CACHE' if arena_data['selectedPath'] == 'CPU' else 'PIM ACCELERATOR'}
            </div>
            <div id="path-banner-desc" class="path-banner-text">
                {arena_data["decisionReason"]}
            </div>
        </div>
    </div>

    <!-- Component Info Modal / Inspector -->
    <div id="comp-modal" class="component-panel">
        <div class="comp-header">
            <span id="comp-modal-title" class="comp-title">Component Name</span>
            <button class="comp-close" onclick="closeComponentInfo()">Dismiss</button>
        </div>
        <div id="comp-modal-desc" class="comp-desc">Description of architectural role.</div>
        <div id="comp-modal-spec" class="comp-spec">Active parameters and modeled metrics.</div>
    </div>

    <!-- Live Parameters and Modeled Results (Right Dock) -->
    <div class="arena-hud">
        <div class="hud-header">
            <span class="hud-title">Architectural Summary</span>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span class="hud-badge {"badge-cpu" if arena_data["selectedPath"] == "CPU" else "badge-pim"}">
                    {arena_data["policyName"]} → {arena_data["selectedPath"]}
                </span>
                <button id="hud-toggle-btn" class="comp-close" onclick="toggleHud()" title="Minimize / Expand panel" style="font-size: 0.85rem; padding: 0 4px; line-height: 1;">−</button>
            </div>
        </div>
        <div id="hud-body">
            <div class="hud-row">
                <span class="hud-label">Workload Pattern:</span>
                <span class="hud-val">{arena_data["workload"]}</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Working Set Size:</span>
                <span class="hud-val">{arena_data["workingSetKb"]} KiB</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Cache Capacity:</span>
                <span class="hud-val">{arena_data["capacityKb"]} KiB</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Cache Hit / Miss Rate:</span>
                <span class="hud-val">{arena_data["hitRate"]}% / {arena_data["missRate"]}%</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Number of PIM Banks:</span>
                <span class="hud-val">{arena_data["bankCount"]} Banks</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Data Link Bandwidth:</span>
                <span class="hud-val">{arena_data["linkBwGbS"]} GB/s</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Bank Imbalance Factor:</span>
                <span class="hud-val">{arena_data["bankImbalance"]}x</span>
            </div>
            <div style="border-top: 1px solid #394453; margin: 6px 0;"></div>
            <div class="hud-row">
                <span class="hud-label">CPU Time:</span>
                <span class="hud-val" style="color: #91B8D8;">{arena_data["cpuLatencyUs"]} μs</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">PIM Time:</span>
                <span class="hud-val" style="color: #8FB7A5;">{arena_data["pimLatencyUs"]} μs</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Data Transfer Time:</span>
                <span class="hud-val" style="color: #A8B3C2;">{round(arena_data["h2pTimeUs"] + arena_data["p2hTimeUs"], 2)} μs</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Modeled Speedup:</span>
                <span class="hud-val" style="color: #8FB7A5;">{arena_data["speedup"]}x</span>
            </div>
            <div class="hud-row">
                <span class="hud-label">Selected Policy:</span>
                <span class="hud-val" style="color: #E2E8F0;">{arena_data["policyName"]}</span>
            </div>
            <div class="hud-notice">
                Analytical estimates under configurable mathematical model assumptions.
            </div>
        </div>
    </div>

    <!-- Step-by-Step Timeline Playback Panel (Bottom Dock) -->
    <div id="playback-dock" class="arena-playback">
        <div class="playback-controls">
            <button id="btn-start" class="ctrl-btn" onclick="playTimeline()">Play</button>
            <button id="btn-pause" class="ctrl-btn" onclick="pauseTimeline()">Pause</button>
            <button id="btn-resume" class="ctrl-btn" onclick="resumeTimeline()">Resume</button>
            <button id="btn-prev" class="ctrl-btn" onclick="prevStage()">Previous Step</button>
            <button id="btn-next" class="ctrl-btn" onclick="nextStage()">Next Step</button>
            <button id="btn-restart" class="ctrl-btn" onclick="resetTimeline()">Reset</button>
            <div class="step-pills-bar">
                <span class="step-pill active" onclick="jumpToStage(1)">1</span>
                <span class="step-pill" onclick="jumpToStage(2)">2</span>
                <span class="step-pill" onclick="jumpToStage(3)">3</span>
                <span class="step-pill" onclick="jumpToStage(4)">4</span>
                <span class="step-pill" onclick="jumpToStage(5)">5</span>
                <span class="step-pill" onclick="jumpToStage(6)">6</span>
                <span class="step-pill" onclick="jumpToStage(7)">7</span>
                <span class="step-pill" onclick="jumpToStage(8)">8</span>
                <span class="step-pill" onclick="jumpToStage(9)">9</span>
                <span class="step-pill" onclick="jumpToStage(10)">10</span>
            </div>
        </div>

        <div class="playback-info">
            <div>
                <div id="stage-title-text" class="stage-title">Stage 1: Workload Starts</div>
                <div id="stage-desc-text" class="stage-desc">
                    Workload initialized: {arena_data["workload"]} with {arena_data["workingSetKb"]} KiB working set.
                </div>
            </div>
            <div id="stage-badge-tag" class="stage-badge">Setup</div>
        </div>

        <div class="legend-strip">
            <div class="legend-item"><span class="legend-dot dot-cyan"></span> CPU Request / Cache Lookup</div>
            <div class="legend-item"><span class="legend-dot dot-green"></span> Cache Hit (Fast Return)</div>
            <div class="legend-item"><span class="legend-dot dot-amber"></span> Cache Miss (Host DRAM)</div>
            <div class="legend-item"><span class="legend-dot dot-grey"></span> PIM Interconnect & Banks</div>
            <div style="margin-left: auto; color: #A8B3C2;">Illustrative trace demonstration based on analytical statistics.</div>
        </div>
    </div>

    <!-- 3D Canvas -->
    <canvas id="webgl-canvas"></canvas>

    <!-- 2D Fallback SVG/Canvas -->
    <canvas id="fallback-canvas"></canvas>
</div>

<script>
const DATA = {data_json};

let isPlaying = true;
let animSpeed = 1.0;
let currentStage = 1; // 1 to 10
let stageProgress = 0.0;
let viewMode = 'flow'; // 'flow' (Working Flow) or 'arch' (Architecture View)
let use2DFallback = false;

// -------------------------------------------------------------
// TIMELINE STAGE DEFINITIONS (STAGES 1 TO 10)
// -------------------------------------------------------------
const STAGES = [
    {{
        id: 1,
        title: "Stage 1: Workload Starts",
        badge: "Initialization",
        desc: "Workload initialized: " + DATA.workload + " with " + DATA.workingSetKb + " KiB working set. Memory access stream begins execution.",
        focus: "cpu",
        component: "cpu"
    }},
    {{
        id: 2,
        title: "Stage 2: CPU Requests Data",
        badge: "CPU Path",
        desc: "Host CPU generates memory reference for a " + DATA.lineSizeBytes + "-byte cache line. It queries the local cache hierarchy first.",
        focus: "cpu",
        component: "cpu"
    }},
    {{
        id: 3,
        title: "Stage 3: LLC Cache Tag Lookup",
        badge: "Cache Check",
        desc: "The Last-Level Cache (" + DATA.capacityKb + " KiB capacity) checks its tag directory to determine if requested address is resident.",
        focus: "cpu",
        component: "llc"
    }},
    {{
        id: 4,
        title: DATA.hitRate >= 50.0 ? "Stage 4: Cache Hit (Short Path)" : "Stage 4: Cache Miss (Host DRAM Access)",
        badge: DATA.hitRate >= 50.0 ? "Cache Hit" : "Cache Miss",
        desc: DATA.hitRate >= 50.0
            ? "Cache Hit (" + DATA.hitRate + "% hit rate): Requested block found in LLC. Served in 2.0 ns without accessing external memory."
            : "Cache Miss (" + DATA.missRate + "% miss rate): Block not in LLC. Incurs main memory DRAM latency (~80 ns) to load into cache.",
        focus: "cpu",
        component: DATA.hitRate >= 50.0 ? "llc" : "dram"
    }},
    {{
        id: 5,
        title: "Stage 5: Policy Decision Point",
        badge: "Alternative Paths",
        desc: "CachePIM evaluates CPU-cache and PIM as alternative execution choices. Active policy '" + DATA.policyName + "' selects " + DATA.selectedPath + " path.",
        focus: "iso",
        component: DATA.selectedPath === "CPU" ? "cpu" : "pim"
    }},
    {{
        id: 6,
        title: "Stage 6: Input Data Sent to PIM",
        badge: "PIM Path",
        desc: "Input data is transferred across the host-to-PIM interconnect (" + DATA.linkBwGbS + " GB/s). Modeled transfer time: " + DATA.h2pTimeUs + " μs.",
        focus: "pim",
        component: "link"
    }},
    {{
        id: 7,
        title: "Stage 7: Work Distributed Across Banks",
        badge: "PIM Array",
        desc: "Workload is divided across " + DATA.bankCount + " PIM memory banks in parallel. Bank imbalance skew factor is " + DATA.bankImbalance + "x.",
        focus: "pim",
        component: "pim"
    }},
    {{
        id: 8,
        title: "Stage 8: In-Memory Parallel Compute",
        badge: "PIM Processing",
        desc: "PIM ALUs compute directly adjacent to DRAM banks simultaneously. Modeled internal bank computation time: " + DATA.bankComputeTimeUs + " μs.",
        focus: "pim",
        component: "pim"
    }},
    {{
        id: 9,
        title: "Stage 9: Output Results Return to Host",
        badge: "PIM to Host",
        desc: "Output result dataset is transferred back across the interconnect to the Host CPU. Modeled return transfer time: " + DATA.p2hTimeUs + " μs.",
        focus: "pim",
        component: "link"
    }},
    {{
        id: 10,
        title: "Stage 10: Compare Results & Policy Decision",
        badge: "Final Decision",
        desc: "Comparison: CPU Time = " + DATA.cpuLatencyUs + " μs vs PIM Time = " + DATA.pimLatencyUs + " μs. Speedup = " + DATA.speedup + "x. Policy dispatched to " + DATA.selectedPath + ".",
        focus: "iso",
        component: DATA.selectedPath === "CPU" ? "cpu" : "pim"
    }}
];

// -------------------------------------------------------------
// COMPONENT INSPECTOR DATA
// -------------------------------------------------------------
const COMP_INFO = {{
    cpu: {{
        title: "Host CPU Core",
        desc: "Executes workload instructions on the Host CPU through an instruction execution pipeline. Operates at 2.5 GHz with arithmetic compute modeling.",
        spec: "Clock: 2.5 GHz • Execution Latency Modeling"
    }},
    llc: {{
        title: "Last-Level Cache (LLC)",
        desc: "High-speed SRAM buffer storing recently accessed cache lines to avoid expensive main-memory misses. Fully associative LRU replacement model.",
        spec: "Capacity: " + DATA.capacityKb + " KiB • Line Size: " + DATA.lineSizeBytes + " B • Hit Rate: " + DATA.hitRate + "%"
    }},
    dram: {{
        title: "Host Main Memory (DRAM)",
        desc: "Main system memory supplying data when an address reference is not found in the cache hierarchy. Cache misses incur full memory access latency.",
        spec: "DDR4 Subsystem • Service Latency: ~80.0 ns • Miss Rate: " + DATA.missRate + "%"
    }},
    link: {{
        title: "Host-PIM Interconnect (Data Link)",
        desc: "Bi-directional high-speed bus carrying input operands to PIM and returning final computed results to Host CPU.",
        spec: "Link Bandwidth: " + DATA.linkBwGbS + " GB/s • H2P Transfer: " + DATA.h2pTimeUs + " μs • P2H Transfer: " + DATA.p2hTimeUs + " μs"
    }},
    pim: {{
        title: "PIM Memory Bank Array",
        desc: "Array of " + DATA.bankCount + " memory banks equipped with in-memory arithmetic logic units (ALUs) executing operations directly in memory.",
        spec: DATA.bankCount + " Banks • Bank Imbalance: " + DATA.bankImbalance + "x • Bank Compute: " + DATA.bankComputeTimeUs + " μs"
    }}
}};

// -------------------------------------------------------------
// THREE.JS 3D SCENE IMPLEMENTATION
// -------------------------------------------------------------
let scene, camera, renderer, controls, raycaster, mouse;
let cpuCore, llcCache, mainMemory, bridgeMesh, pimSubstrate, pimBanks = [];
let hostPlatMesh, pimPlatMesh, hostAuraLine, pimAuraLine;
let pathMode = 'auto';
let dataPacket = null;
let clickableMeshes = [];

function init3D() {{
    const canvas = document.getElementById('webgl-canvas');
    if (!window.WebGLRenderingContext) {{
        console.warn('WebGL not supported, activating 2D fallback');
        toggle2DFallback(true);
        return;
    }}

    try {{
        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x151A22, 0.015);

        camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
        setCameraView('iso');

        renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;

        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxPolarAngle = Math.PI / 2.05;

        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2();

        // Lighting - Subtle and glare-free
        const ambientLight = new THREE.AmbientLight(0x1B222C, 2.2);
        scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0x91B8D8, 1.4);
        dirLight.position.set(20, 40, 20);
        scene.add(dirLight);

        const pimLight = new THREE.DirectionalLight(0x8FB7A5, 1.2);
        pimLight.position.set(-20, 30, -10);
        scene.add(pimLight);

        // Ground Grid
        const gridHelper = new THREE.GridHelper(60, 40, 0x394453, 0x1B222C);
        gridHelper.position.y = -0.5;
        scene.add(gridHelper);

        buildArchitectureBlocks();

        // Continuous Multi-Packet Dataflow Streams
        initAllPacketStreams();

        canvas.addEventListener('click', onCanvasClick);
        window.addEventListener('resize', onWindowResize);
        window.addEventListener('beforeunload', function() {{
            if (animationFrameId !== null) {{
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }}
        }});

        updateStageUI(currentStage);
        setPathMode('auto');
        playTimeline();
    }} catch (e) {{
        console.error('Error initializing Three.js:', e);
        toggle2DFallback(true);
    }}
}}

function createTextSprite(text, color, scaleX, scaleY) {{
    const sW = scaleX || 4.2;
    const sH = scaleY || 1.1;
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    // Rounded background pill for crisp high contrast
    ctx.fillStyle = 'rgba(27, 34, 44, 0.94)';
    ctx.strokeStyle = color || '#91B8D8';
    ctx.lineWidth = 4;

    const x = 8, y = 8, w = 496, h = 112, r = 20;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#E2E8F0';
    ctx.font = 'bold 30px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 256, 64);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({{ map: texture, depthTest: true }});
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(sW, sH, 1);
    return sprite;
}}

function createPacket(color) {{
    const geo = new THREE.SphereGeometry(0.4, 20, 20);
    const mat = new THREE.MeshStandardMaterial({{
        color: color,
        emissive: color,
        emissiveIntensity: 0.7,
        roughness: 0.2
    }});
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(-14, 1.2, -2);
    scene.add(mesh);
    return mesh;
}}

function buildArchitectureBlocks() {{
    clickableMeshes = [];

    // 1. Host Subsystem Substrate
    const hostPlatGeo = new THREE.BoxGeometry(18, 0.4, 20);
    const hostPlatMat = new THREE.MeshStandardMaterial({{ color: 0x1B222C, roughness: 0.6, metalness: 0.7 }});
    const hostPlat = new THREE.Mesh(hostPlatGeo, hostPlatMat);
    hostPlat.position.set(-11, -0.2, 0);
    scene.add(hostPlat);
    hostPlatMesh = hostPlat;

    const hostEdges = new THREE.EdgesGeometry(hostPlatGeo);
    hostAuraLine = new THREE.LineSegments(hostEdges, new THREE.LineBasicMaterial({{ color: 0x91B8D8, linewidth: 2, transparent: true, opacity: 0.9 }}));
    hostAuraLine.position.set(-11, -0.2, 0);
    scene.add(hostAuraLine);

    // Label Host Subsystem (Placed in the background to prevent overlap)
    const hostLabel = createTextSprite('Host CPU & Cache', '#91B8D8', 4.8, 1.15);
    hostLabel.position.set(-11, 4.2, -8.5);
    scene.add(hostLabel);

    // CPU Unit
    const cpuGeo = new THREE.BoxGeometry(5.5, 1.2, 5.5);
    const cpuMat = new THREE.MeshStandardMaterial({{
        color: 0x243B53,
        roughness: 0.3,
        metalness: 0.8,
        emissive: 0x3D5A80,
        emissiveIntensity: 0.25
    }});
    cpuCore = new THREE.Mesh(cpuGeo, cpuMat);
    cpuCore.position.set(-14, 0.6, -2);
    cpuCore.userData = {{ compId: 'cpu' }};
    scene.add(cpuCore);
    clickableMeshes.push(cpuCore);

    // CPU Tag (Isolated non-overlapping bounding volume)
    const cpuTag = createTextSprite('CPU Core (2.5 GHz)', '#E2E8F0', 3.8, 1.05);
    cpuTag.position.set(-14, 2.3, -2);
    scene.add(cpuTag);

    // LLC Cache Unit
    const llcGeo = new THREE.BoxGeometry(4.5, 0.9, 4.5);
    const llcMat = new THREE.MeshStandardMaterial({{
        color: 0x1E3A52,
        roughness: 0.2,
        metalness: 0.7,
        emissive: 0x4A6FA5,
        emissiveIntensity: 0.3
    }});
    llcCache = new THREE.Mesh(llcGeo, llcMat);
    llcCache.position.set(-8, 0.45, -2);
    llcCache.userData = {{ compId: 'llc' }};
    scene.add(llcCache);
    clickableMeshes.push(llcCache);

    // LLC Tag (Separated by 2.2 units buffer from CPU Tag)
    const llcTag = createTextSprite(`Cache (LLC: ${{DATA.capacityKb}} KiB)`, '#91B8D8', 3.8, 1.05);
    llcTag.position.set(-8, 2.1, -2);
    scene.add(llcTag);

    // Main Memory (Host DRAM)
    const dramGeo = new THREE.BoxGeometry(2.5, 1.6, 7.5);
    const dramMat = new THREE.MeshStandardMaterial({{
        color: 0x1B222C,
        roughness: 0.4,
        metalness: 0.6,
        emissive: 0x222B36,
        emissiveIntensity: 0.2
    }});
    mainMemory = new THREE.Mesh(dramGeo, dramMat);
    mainMemory.position.set(-3, 0.8, -2);
    mainMemory.userData = {{ compId: 'dram' }};
    scene.add(mainMemory);
    clickableMeshes.push(mainMemory);

    // DRAM Tag (Separated by 1.6 units buffer from LLC Tag)
    const dramTag = createTextSprite('Host DRAM', '#A8B3C2', 3.0, 1.0);
    dramTag.position.set(-3, 2.7, -2);
    scene.add(dramTag);

    // Host Internal PCB Buses
    createBusLine([-13.5, 0.05, -2.0], [-8.0, 0.05, -2.0], 0x91B8D8); // CPU to LLC request bus (Muted Blue)
    createBusLine([-8.0, 0.05, -1.6], [-13.5, 0.05, -1.6], 0x8FB7A5); // LLC to CPU hit return bus (Sage Green)
    createBusLine([-8.0, 0.05, -2.4], [-3.0, 0.05, -2.4], 0xD5AD72);  // LLC to Host DRAM miss bus (Soft Amber)
    createBusLine([-3.0, 0.05, -2.7], [-13.5, 0.05, -2.7], 0xD5AD72); // Host DRAM to CPU return bus (Soft Amber)

    // Host Subsystem to Interconnect Bridge Buses
    createBusLine([-13.5, 0.05, 0.0], [-11.5, 0.05, 0.0], 0xCBD5E1);
    createBusLine([-11.5, 0.05, 0.0], [-11.5, 0.05, 4.2], 0xCBD5E1);
    createBusLine([-11.5, 0.05, 4.2], [-2.0, 0.05, 4.2], 0xCBD5E1); // Forward input link to bridge (Neutral Light Grey)

    createBusLine([-2.0, 0.05, 3.4], [-11.5, 0.05, 3.4], 0x8FB7A5); // Return output link from bridge (Sage Green)
    createBusLine([-11.5, 0.05, 3.4], [-11.5, 0.05, 0.5], 0x8FB7A5);
    createBusLine([-11.5, 0.05, 0.5], [-13.5, 0.05, 0.5], 0x8FB7A5);

    // Across the Interconnect Bridge (PCIe 4.0 / CXL link lanes)
    createBusLine([-2.0, 0.18, 4.2], [4.0, 0.18, 4.2], 0xCBD5E1); // Forward lane (Neutral Light Grey)
    createBusLine([4.0, 0.18, 3.4], [-2.0, 0.18, 3.4], 0x8FB7A5); // Return lane (Sage Green)

    // PIM Substrate Distribution & Collection Bus Spines
    createBusLine([4.0, 0.05, 4.2], [5.2, 0.05, 4.2], 0xCBD5E1);
    createBusLine([5.2, 0.05, 4.5], [5.2, 0.05, -4.5], 0x8FB7A5);
    createBusLine([5.2, 0.05, 3.4], [4.0, 0.05, 3.4], 0x8FB7A5);

    // PIM Bank Row Distribution Branches
    createBusLine([5.2, 0.05, 4.5], [18.0, 0.05, 4.5], 0x779E8D);
    createBusLine([5.2, 0.05, 1.5], [18.0, 0.05, 1.5], 0x779E8D);
    createBusLine([5.2, 0.05, -1.5], [18.0, 0.05, -1.5], 0x779E8D);
    createBusLine([5.2, 0.05, -4.5], [18.0, 0.05, -4.5], 0x779E8D);

    // 2. High-Speed Interconnect Bus (PCIe 4.0 / CXL link)
    const linkWidth = Math.min(1.8, Math.max(0.6, DATA.linkBwGbS / 16.0));
    const bridgeGeo = new THREE.BoxGeometry(6, 0.15, linkWidth);
    const bridgeMat = new THREE.MeshStandardMaterial({{
        color: 0x22332B,
        emissive: 0x8FB7A5,
        emissiveIntensity: 0.3
    }});
    bridgeMesh = new THREE.Mesh(bridgeGeo, bridgeMat);
    bridgeMesh.position.set(1, 0.1, 4);
    bridgeMesh.userData = {{ compId: 'link' }};
    scene.add(bridgeMesh);
    clickableMeshes.push(bridgeMesh);

    // Data Link Tag (Z = 4, isolated from host components at Z = -2)
    const linkLabel = createTextSprite(`Data Link (${{DATA.linkBwGbS}} GB/s)`, '#8FB7A5', 4.0, 1.05);
    linkLabel.position.set(1, 1.8, 4);
    scene.add(linkLabel);

    // 3. PIM Accelerator Substrate
    const pimPlatGeo = new THREE.BoxGeometry(20, 0.4, 20);
    const pimPlatMat = new THREE.MeshStandardMaterial({{
        color: 0x1E2824,
        roughness: 0.5,
        metalness: 0.7
    }});
    pimSubstrate = new THREE.Mesh(pimPlatGeo, pimPlatMat);
    pimSubstrate.position.set(12, -0.2, 0);
    pimSubstrate.userData = {{ compId: 'pim' }};
    scene.add(pimSubstrate);
    clickableMeshes.push(pimSubstrate);
    pimPlatMesh = pimSubstrate;

    const pimEdges = new THREE.EdgesGeometry(pimPlatGeo);
    pimAuraLine = new THREE.LineSegments(pimEdges, new THREE.LineBasicMaterial({{ color: 0x8FB7A5, linewidth: 2, transparent: true, opacity: 0.9 }}));
    pimAuraLine.position.set(12, -0.2, 0);
    scene.add(pimAuraLine);

    // PIM Array Label (Placed in background matching hostLabel)
    const pimLabel = createTextSprite(`PIM Memory (${{DATA.bankCount}} Banks)`, '#8FB7A5', 4.8, 1.15);
    pimLabel.position.set(12, 4.2, -8.5);
    scene.add(pimLabel);

    // Build PIM Banks Grid
    buildPIMBanksGrid();
}}

function createBusLine(p1, p2, color) {{
    const points = [new THREE.Vector3(...p1), new THREE.Vector3(...p2)];
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({{ color: color, linewidth: 3 }});
    const line = new THREE.Line(geo, mat);
    scene.add(line);
}}

function buildPIMBanksGrid() {{
    pimBanks = [];
    const bCount = DATA.bankCount;
    const cols = bCount <= 8 ? bCount : (bCount <= 16 ? 4 : 8);
    const rows = Math.ceil(bCount / cols);
    const spacingX = 14 / cols;
    const spacingZ = 12 / rows;
    const startX = 5 + spacingX / 2;
    const startZ = -6 + spacingZ / 2;

    const maxWork = Math.max(...DATA.perBankWork);

    for (let i = 0; i < bCount; i++) {{
        const r = Math.floor(i / cols);
        const c = i % cols;
        const x = startX + c * spacingX;
        const z = startZ + r * spacingZ;

        const bankGroup = new THREE.Group();
        bankGroup.position.set(x, 0, z);

        const work = DATA.perBankWork[i] || 100;
        const workScale = maxWork > 0 ? (work / maxWork) : 1.0;
        const bankHeight = 0.8 + workScale * 0.8;

        // DRAM Layer (lower)
        const dramGeo = new THREE.BoxGeometry(spacingX * 0.75, bankHeight * 0.6, spacingZ * 0.7);
        const dramMat = new THREE.MeshStandardMaterial({{
            color: 0x1E2B25,
            roughness: 0.3,
            metalness: 0.8,
            emissive: 0x2A3F35,
            emissiveIntensity: 0.2
        }});
        const dramMesh = new THREE.Mesh(dramGeo, dramMat);
        dramMesh.position.y = bankHeight * 0.3;
        dramMesh.userData = {{ compId: 'pim', bankIdx: i }};
        bankGroup.add(dramMesh);
        clickableMeshes.push(dramMesh);

        // ALU Compute Core Layer (upper)
        const aluGeo = new THREE.BoxGeometry(spacingX * 0.65, bankHeight * 0.4, spacingZ * 0.6);
        const aluMat = new THREE.MeshStandardMaterial({{
            color: 0x2A3F35,
            roughness: 0.2,
            metalness: 0.9,
            emissive: 0x8FB7A5,
            emissiveIntensity: 0.35
        }});
        const aluMesh = new THREE.Mesh(aluGeo, aluMat);
        aluMesh.position.y = bankHeight * 0.6 + bankHeight * 0.2;
        aluMesh.userData = {{ compId: 'pim', bankIdx: i }};
        bankGroup.add(aluMesh);
        clickableMeshes.push(aluMesh);

        scene.add(bankGroup);
        pimBanks.push({{ group: bankGroup, dram: dramMesh, alu: aluMesh, work: work, basePos: new THREE.Vector3(x, bankHeight, z) }});
    }}
}}

// -------------------------------------------------------------
// CONTINUOUS MULTI-PACKET DATAFLOW & STREAMING SYSTEM
// -------------------------------------------------------------
let animationFrameId = null;
let lastTimestamp = 0;
let globalTime = 0.0;

let streamCpuReq = null;
let streamCacheHit = null;
let streamCacheMiss = null;
let streamPimIn1 = null;
let streamPimIn2 = null;
let streamPimOut = null;

// Path Sampler utility for smooth, constant-speed interpolation along multi-point polylines
function createPathSampler(points) {{
    const segments = [];
    let totalLength = 0;
    for (let i = 0; i < points.length - 1; i++) {{
        const p0 = points[i];
        const p1 = points[i + 1];
        const dist = p0.distanceTo(p1);
        segments.push({{
            p0: p0,
            p1: p1,
            dist: dist,
            startDist: totalLength,
            endDist: totalLength + dist
        }});
        totalLength += dist;
    }}
    return {{
        points: points,
        totalLength: totalLength,
        getPointAt: function(normProgress) {{
            let p = normProgress % 1.0;
            if (p < 0) p += 1.0;
            const targetDist = p * totalLength;
            for (let i = 0; i < segments.length; i++) {{
                const s = segments[i];
                if (targetDist <= s.endDist || i === segments.length - 1) {{
                    const localT = s.dist > 0.0001 ? (targetDist - s.startDist) / s.dist : 0;
                    return new THREE.Vector3().lerpVectors(s.p0, s.p1, Math.min(Math.max(localT, 0), 1));
                }}
            }}
            return points[points.length - 1].clone();
        }}
    }};
}}

function PacketStream(sampler, count, color, speed, radius) {{
    this.sampler = sampler;
    this.count = count;
    this.speed = speed;
    this.color = color;
    this.packets = [];
    this.visible = true;

    const geo = new THREE.SphereGeometry(radius || 0.22, 16, 16);
    for (let i = 0; i < count; i++) {{
        const mat = new THREE.MeshStandardMaterial({{
            color: color,
            emissive: color,
            emissiveIntensity: 0.85,
            roughness: 0.2,
            metalness: 0.3
        }});
        const mesh = new THREE.Mesh(geo, mat);
        scene.add(mesh);
        this.packets.push({{
            mesh: mesh,
            offset: i / count
        }});
    }}
}}

PacketStream.prototype.update = function(timeSec, speedMult) {{
    if (!this.visible) {{
        for (let i = 0; i < this.packets.length; i++) {{
            this.packets[i].mesh.visible = false;
        }}
        return;
    }}
    const effectiveSpeed = this.speed * (speedMult || 1.0);
    for (let i = 0; i < this.packets.length; i++) {{
        this.packets[i].mesh.visible = true;
        const progress = (timeSec * effectiveSpeed + this.packets[i].offset) % 1.0;
        const pos = this.sampler.getPointAt(progress);
        this.packets[i].mesh.position.copy(pos);
    }}
}};

PacketStream.prototype.reset = function() {{
    for (let i = 0; i < this.packets.length; i++) {{
        const pos = this.sampler.getPointAt(this.packets[i].offset);
        this.packets[i].mesh.position.copy(pos);
    }}
}};

PacketStream.prototype.setEmissive = function(val) {{
    for (let i = 0; i < this.packets.length; i++) {{
        this.packets[i].mesh.material.emissiveIntensity = val;
    }}
}};

PacketStream.prototype.setVisible = function(val) {{
    this.visible = val;
    for (let i = 0; i < this.packets.length; i++) {{
        this.packets[i].mesh.visible = val;
    }}
}};

function initAllPacketStreams() {{
    // 1. CPU Core -> LLC Cache request path (Muted Blue)
    const cpuReqPoints = [
        new THREE.Vector3(-13.5, 0.45, -2.0),
        new THREE.Vector3(-11.25, 0.45, -2.0),
        new THREE.Vector3(-10.25, 0.45, -2.0),
        new THREE.Vector3(-8.0, 0.45, -2.0)
    ];
    streamCpuReq = new PacketStream(createPathSampler(cpuReqPoints), 3, 0x91B8D8, 0.16, 0.18);

    // 2. LLC Cache -> CPU Core cache hit return path (Sage Green)
    const cacheHitPoints = [
        new THREE.Vector3(-8.0, 0.45, -1.6),
        new THREE.Vector3(-10.25, 0.45, -1.6),
        new THREE.Vector3(-11.25, 0.45, -1.6),
        new THREE.Vector3(-13.5, 0.45, -1.6)
    ];
    streamCacheHit = new PacketStream(createPathSampler(cacheHitPoints), 3, 0x8FB7A5, 0.20, 0.18);

    // 3. LLC Cache -> Host DRAM -> Return to CPU miss path (Soft Amber)
    const cacheMissPoints = [
        new THREE.Vector3(-8.0, 0.45, -2.4),
        new THREE.Vector3(-5.75, 0.45, -2.4),
        new THREE.Vector3(-4.25, 0.45, -2.4),
        new THREE.Vector3(-3.0, 0.65, -2.4),
        new THREE.Vector3(-3.0, 0.65, -2.7),
        new THREE.Vector3(-4.25, 0.45, -2.7),
        new THREE.Vector3(-5.75, 0.45, -2.7),
        new THREE.Vector3(-8.0, 0.45, -2.7),
        new THREE.Vector3(-10.25, 0.45, -2.7),
        new THREE.Vector3(-11.25, 0.45, -2.7),
        new THREE.Vector3(-13.5, 0.45, -2.7)
    ];
    streamCacheMiss = new PacketStream(createPathSampler(cacheMissPoints), 4, 0xD5AD72, 0.14, 0.18);

    // 4. Host-to-PIM Interconnect forward stream (Neutral Light Grey, Row 1 branch)
    const pimIn1Points = [
        new THREE.Vector3(-13.5, 0.45, 0.0),
        new THREE.Vector3(-11.5, 0.35, 0.0),
        new THREE.Vector3(-11.5, 0.35, 4.2),
        new THREE.Vector3(-2.0, 0.30, 4.2),
        new THREE.Vector3(1.0, 0.30, 4.2),
        new THREE.Vector3(4.0, 0.30, 4.2),
        new THREE.Vector3(5.2, 0.35, 4.2),
        new THREE.Vector3(5.2, 0.35, 1.5),
        new THREE.Vector3(10.25, 0.55, 1.5),
        new THREE.Vector3(13.75, 0.55, 1.5)
    ];
    streamPimIn1 = new PacketStream(createPathSampler(pimIn1Points), 7, 0xCBD5E1, 0.12, 0.22);

    // 5. Host-to-PIM secondary branch (Neutral Light Grey, Row 0 branch)
    const pimIn2Points = [
        new THREE.Vector3(-13.5, 0.45, 0.0),
        new THREE.Vector3(-11.5, 0.35, 0.0),
        new THREE.Vector3(-11.5, 0.35, 4.2),
        new THREE.Vector3(-2.0, 0.30, 4.2),
        new THREE.Vector3(1.0, 0.30, 4.2),
        new THREE.Vector3(4.0, 0.30, 4.2),
        new THREE.Vector3(5.2, 0.35, 4.2),
        new THREE.Vector3(5.2, 0.35, -1.5),
        new THREE.Vector3(10.25, 0.55, -1.5),
        new THREE.Vector3(13.75, 0.55, -1.5)
    ];
    streamPimIn2 = new PacketStream(createPathSampler(pimIn2Points), 5, 0xE2E8F0, 0.12, 0.20);

    // 6. PIM-to-Host Interconnect return stream (Sage Green)
    const pimOutPoints = [
        new THREE.Vector3(13.75, 0.55, -1.5),
        new THREE.Vector3(10.25, 0.55, -1.5),
        new THREE.Vector3(5.2, 0.35, -1.5),
        new THREE.Vector3(5.2, 0.35, 3.4),
        new THREE.Vector3(4.0, 0.30, 3.4),
        new THREE.Vector3(1.0, 0.30, 3.4),
        new THREE.Vector3(-2.0, 0.30, 3.4),
        new THREE.Vector3(-11.5, 0.35, 3.4),
        new THREE.Vector3(-11.5, 0.35, 0.5),
        new THREE.Vector3(-13.5, 0.45, 0.5)
    ];
    streamPimOut = new PacketStream(createPathSampler(pimOutPoints), 6, 0x8FB7A5, 0.12, 0.22);

    // Alias lead packet for backwards compatibility
    if (streamPimIn1 && streamPimIn1.packets.length > 0) {{
        dataPacket = streamPimIn1.packets[0].mesh;
    }}
}}

function updateAllPacketStreams(timeSec) {{
    const spd = animSpeed;
    if (streamCpuReq) streamCpuReq.update(timeSec, spd);
    if (streamCacheHit) streamCacheHit.update(timeSec, spd);
    if (streamCacheMiss) streamCacheMiss.update(timeSec, spd);
    if (streamPimIn1) streamPimIn1.update(timeSec, spd);
    if (streamPimIn2) streamPimIn2.update(timeSec, spd);
    if (streamPimOut) streamPimOut.update(timeSec, spd);

    // Dynamic stage spotlighting & ALU pulsing
    if (streamCpuReq) streamCpuReq.setEmissive(currentStage === 2 ? 1.5 : 0.85);
    if (streamCacheHit) streamCacheHit.setEmissive(currentStage === 4 && DATA.hitRate >= 50.0 ? 1.6 : 0.85);
    if (streamCacheMiss) streamCacheMiss.setEmissive(currentStage === 4 && DATA.hitRate < 50.0 ? 1.6 : 0.85);
    if (streamPimIn1) streamPimIn1.setEmissive((currentStage === 6 || currentStage === 7) ? 1.5 : 0.85);
    if (streamPimIn2) streamPimIn2.setEmissive((currentStage === 6 || currentStage === 7) ? 1.5 : 0.85);
    if (streamPimOut) streamPimOut.setEmissive(currentStage === 9 ? 1.6 : 0.85);

    // Parallel ALU compute pulse during stages 7 & 8
    const aluIntensity = (currentStage === 7 || currentStage === 8)
        ? (0.35 + Math.sin(timeSec * 7.0) * 0.45)
        : (0.20 + Math.sin(timeSec * 2.0) * 0.15);
    for (let i = 0; i < pimBanks.length; i++) {{
        if (pimBanks[i].alu && pimBanks[i].alu.material) {{
            pimBanks[i].alu.material.emissiveIntensity = aluIntensity;
        }}
    }}
}}

function resetAllPacketStreams() {{
    if (streamCpuReq) streamCpuReq.reset();
    if (streamCacheHit) streamCacheHit.reset();
    if (streamCacheMiss) streamCacheMiss.reset();
    if (streamPimIn1) streamPimIn1.reset();
    if (streamPimIn2) streamPimIn2.reset();
    if (streamPimOut) streamPimOut.reset();
}}

// -------------------------------------------------------------
// PATHWAY HIGHLIGHTING & COMPARISON (CPU VS PIM)
// -------------------------------------------------------------
function setPathMode(mode) {{
    pathMode = mode;

    const btnAuto = document.getElementById('btn-path-auto');
    const btnCpu = document.getElementById('btn-path-cpu');
    const btnPim = document.getElementById('btn-path-pim');
    const btnComp = document.getElementById('btn-path-compare');
    if (btnAuto) btnAuto.classList.toggle('active', mode === 'auto');
    if (btnCpu) btnCpu.classList.toggle('active', mode === 'cpu');
    if (btnPim) btnPim.classList.toggle('active', mode === 'pim');
    if (btnComp) btnComp.classList.toggle('active', mode === 'compare');

    const effectivePath = mode === 'auto' ? DATA.selectedPath : (mode === 'cpu' ? 'CPU' : (mode === 'pim' ? 'PIM' : 'COMPARE'));

    const bannerTag = document.getElementById('path-banner-tag');
    const bannerDesc = document.getElementById('path-banner-desc');
    const banner = document.getElementById('path-status-banner');

    if (effectivePath === 'CPU') {{
        if (hostAuraLine) {{
            hostAuraLine.material.color.setHex(0x91B8D8);
            hostAuraLine.material.opacity = 1.0;
            hostAuraLine.visible = true;
        }}
        if (pimAuraLine) {{
            pimAuraLine.material.color.setHex(0x1E2824);
            pimAuraLine.material.opacity = 0.25;
        }}
        if (cpuCore) cpuCore.material.emissiveIntensity = 0.55;
        if (llcCache) llcCache.material.emissiveIntensity = 0.6;
        if (bridgeMesh) bridgeMesh.material.emissiveIntensity = 0.15;

        if (streamCpuReq) streamCpuReq.setVisible(true);
        if (streamCacheHit) streamCacheHit.setVisible(true);
        if (streamCacheMiss) streamCacheMiss.setVisible(true);
        if (streamPimIn1) streamPimIn1.setVisible(false);
        if (streamPimIn2) streamPimIn2.setVisible(false);
        if (streamPimOut) streamPimOut.setVisible(false);

        if (bannerTag) {{
            bannerTag.innerText = "PATHWAY: HOST CPU & CACHE (LOCAL EXECUTION)";
            bannerTag.style.color = "#91B8D8";
        }}
        if (bannerDesc) {{
            bannerDesc.innerText = "Workload executed on Host CPU Core. Fast " + DATA.hitRate + "% LLC hits avoid memory bus traffic. PIM accelerator in standby.";
        }}
        if (banner) banner.style.borderColor = "rgba(145, 184, 216, 0.5)";

    }} else if (effectivePath === 'PIM') {{
        if (hostAuraLine) {{
            hostAuraLine.material.color.setHex(0x1B222C);
            hostAuraLine.material.opacity = 0.25;
        }}
        if (pimAuraLine) {{
            pimAuraLine.material.color.setHex(0x8FB7A5);
            pimAuraLine.material.opacity = 1.0;
            pimAuraLine.visible = true;
        }}
        if (cpuCore) cpuCore.material.emissiveIntensity = 0.15;
        if (llcCache) llcCache.material.emissiveIntensity = 0.15;
        if (bridgeMesh) bridgeMesh.material.emissiveIntensity = 0.7;

        if (streamCpuReq) streamCpuReq.setVisible(false);
        if (streamCacheHit) streamCacheHit.setVisible(false);
        if (streamCacheMiss) streamCacheMiss.setVisible(false);
        if (streamPimIn1) streamPimIn1.setVisible(true);
        if (streamPimIn2) streamPimIn2.setVisible(true);
        if (streamPimOut) streamPimOut.setVisible(true);

        if (bannerTag) {{
            bannerTag.innerText = "PATHWAY: PIM ACCELERATOR (IN-MEMORY PARALLEL)";
            bannerTag.style.color = "#8FB7A5";
        }}
        if (bannerDesc) {{
            bannerDesc.innerText = "Data dispatched across " + DATA.linkBwGbS + " GB/s interconnect. Computed in parallel across " + DATA.bankCount + " memory banks without CPU cache bottleneck.";
        }}
        if (banner) banner.style.borderColor = "rgba(143, 183, 165, 0.5)";

    }} else {{
        if (hostAuraLine) {{
            hostAuraLine.material.color.setHex(0x91B8D8);
            hostAuraLine.material.opacity = 0.8;
            hostAuraLine.visible = true;
        }}
        if (pimAuraLine) {{
            pimAuraLine.material.color.setHex(0x8FB7A5);
            pimAuraLine.material.opacity = 0.8;
            pimAuraLine.visible = true;
        }}
        if (cpuCore) cpuCore.material.emissiveIntensity = 0.35;
        if (llcCache) llcCache.material.emissiveIntensity = 0.4;
        if (bridgeMesh) bridgeMesh.material.emissiveIntensity = 0.5;

        if (streamCpuReq) streamCpuReq.setVisible(true);
        if (streamCacheHit) streamCacheHit.setVisible(true);
        if (streamCacheMiss) streamCacheMiss.setVisible(true);
        if (streamPimIn1) streamPimIn1.setVisible(true);
        if (streamPimIn2) streamPimIn2.setVisible(true);
        if (streamPimOut) streamPimOut.setVisible(true);

        if (bannerTag) {{
            bannerTag.innerText = "PATH COMPARISON: CPU VS PIM ALTERNATIVES";
            bannerTag.style.color = "#D5AD72";
        }}
        if (bannerDesc) {{
            bannerDesc.innerText = "CPU Time: " + DATA.cpuLatencyUs + " μs vs PIM Time: " + DATA.pimLatencyUs + " μs • Modeled Speedup: " + DATA.speedup + "x • Selected by " + DATA.policyName + ": " + DATA.selectedPath;
        }}
        if (banner) banner.style.borderColor = "rgba(213, 173, 114, 0.5)";
    }}
}}

// -------------------------------------------------------------
// TIMELINE PLAYBACK & ANIMATION CONTROLLER
// -------------------------------------------------------------
function startAnimationLoop() {{
    if (animationFrameId !== null) return; // Prevent duplicate loops
    lastTimestamp = performance.now();

    function renderLoop(now) {{
        animationFrameId = requestAnimationFrame(renderLoop);

        const dt = Math.min((now - lastTimestamp) / 1000.0, 0.1);
        lastTimestamp = now;

        if (isPlaying) {{
            globalTime += dt * animSpeed;
            stageProgress += dt * 0.14 * animSpeed;
            if (stageProgress >= 1.0) {{
                stageProgress = 0.0;
                // Seamless continuous cycle from Stage 10 back to Stage 1!
                const nextS = currentStage < 10 ? currentStage + 1 : 1;
                setStage(nextS);
            }}
        }}

        updateAllPacketStreams(globalTime);

        if (controls) controls.update();
        if (renderer && scene && camera) renderer.render(scene, camera);
    }}

    animationFrameId = requestAnimationFrame(renderLoop);
}}

function playTimeline() {{
    isPlaying = true;
    lastTimestamp = performance.now();
    startAnimationLoop();
    updatePlaybackButtonStates();
}}

function startTimeline() {{
    playTimeline();
}}

function pauseTimeline() {{
    isPlaying = false;
    updatePlaybackButtonStates();
}}

function resumeTimeline() {{
    isPlaying = true;
    lastTimestamp = performance.now();
    startAnimationLoop();
    updatePlaybackButtonStates();
}}

function resetTimeline() {{
    isPlaying = false;
    globalTime = 0.0;
    stageProgress = 0.0;
    setStage(1);
    resetAllPacketStreams();
    updatePlaybackButtonStates();
}}

function restartTimeline() {{
    resetTimeline();
    playTimeline();
}}

function nextStage() {{
    isPlaying = false;
    const nextS = currentStage < 10 ? currentStage + 1 : 1;
    setStage(nextS);
    updatePlaybackButtonStates();
}}

function prevStage() {{
    isPlaying = false;
    const prevS = currentStage > 1 ? currentStage - 1 : 10;
    setStage(prevS);
    updatePlaybackButtonStates();
}}

function jumpToStage(n) {{
    isPlaying = false;
    setStage(n);
    updatePlaybackButtonStates();
}}

function setStage(stageNum) {{
    currentStage = Math.max(1, Math.min(10, stageNum));
    stageProgress = 0.0;
    updateStageUI(currentStage);
}}

function updateStageUI(stageNum) {{
    const s = STAGES[stageNum - 1];
    document.getElementById('stage-title-text').innerText = s.title;
    document.getElementById('stage-desc-text').innerText = s.desc;
    document.getElementById('stage-badge-tag').innerText = s.badge;

    // Update Step Pills active class
    const pills = document.querySelectorAll('.step-pill');
    pills.forEach((p, idx) => {{
        if (idx + 1 === stageNum) {{
            p.classList.add('active');
        }} else {{
            p.classList.remove('active');
        }}
    }});
}}

function updatePlaybackButtonStates() {{
    const btnPlay = document.getElementById('btn-start');
    const btnPause = document.getElementById('btn-pause');
    const btnResume = document.getElementById('btn-resume');
    if (btnPlay) btnPlay.classList.toggle('active', isPlaying);
    if (btnPause) btnPause.classList.toggle('active', !isPlaying);
    if (btnResume) btnResume.classList.toggle('active', isPlaying);
}}

// -------------------------------------------------------------
// COMPONENT INSPECTOR & INTERACTION
// -------------------------------------------------------------
function inspectComponent(compId) {{
    const info = COMP_INFO[compId];
    if (!info) return;

    document.getElementById('comp-modal-title').innerText = info.title;
    document.getElementById('comp-modal-desc').innerText = info.desc;
    document.getElementById('comp-modal-spec').innerText = info.spec;
    document.getElementById('comp-modal').style.display = 'block';

    if (compId === 'cpu' || compId === 'llc' || compId === 'dram') {{
        setCameraView('cpu');
    }} else if (compId === 'pim' || compId === 'link') {{
        setCameraView('pim');
    }}
}}

function closeComponentInfo() {{
    document.getElementById('comp-modal').style.display = 'none';
}}

function toggleHud() {{
    const body = document.getElementById('hud-body');
    const btn = document.getElementById('hud-toggle-btn');
    if (!body) return;
    if (body.style.display === 'none') {{
        body.style.display = 'block';
        if (btn) btn.innerText = '−';
    }} else {{
        body.style.display = 'none';
        if (btn) btn.innerText = '+';
    }}
}}

function onCanvasClick(event) {{
    if (!raycaster || !camera) return;

    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(clickableMeshes, true);

    if (intersects.length > 0) {{
        let obj = intersects[0].object;
        while (obj && !obj.userData.compId && obj.parent) {{
            obj = obj.parent;
        }}
        if (obj && obj.userData.compId) {{
            inspectComponent(obj.userData.compId);
        }}
    }}
}}

// -------------------------------------------------------------
// CAMERA VIEWS & MODES
// -------------------------------------------------------------
function setCameraView(view) {{
    if (!camera) return;
    if (view === 'iso') {{
        camera.position.set(24, 26, 26);
        camera.lookAt(0, 0, 0);
    }} else if (view === 'cpu') {{
        camera.position.set(-9, 12, 16);
        camera.lookAt(-10, 0, -2);
    }} else if (view === 'pim') {{
        camera.position.set(13, 14, 18);
        camera.lookAt(12, 0, 0);
    }} else if (view === 'top') {{
        camera.position.set(0, 42, 1);
        camera.lookAt(0, 0, 0);
    }}
}}

function resetCamera() {{
    setCameraView('iso');
}}

function toggleViewMode() {{
    viewMode = (viewMode === 'flow') ? 'arch' : 'flow';
    const btn = document.getElementById('btn-view-mode');
    btn.innerText = viewMode === 'flow' ? 'View: Working Flow' : 'View: Architecture';
    if (viewMode === 'arch') {{
        pauseTimeline();
        setCameraView('iso');
    }} else {{
        startTimeline();
    }}
}}

function onWindowResize() {{
    if (!camera || !renderer) return;
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}}

function toggle2DFallback(force) {{
    use2DFallback = force !== undefined ? force : !use2DFallback;
    const fb = document.getElementById('fallback-canvas');
    const wgl = document.getElementById('webgl-canvas');
    if (use2DFallback) {{
        fb.style.display = 'block';
        wgl.style.display = 'none';
        init2DFallback();
    }} else {{
        fb.style.display = 'none';
        wgl.style.display = 'block';
    }}
}}

// -------------------------------------------------------------
// 2D CANVAS ISOMETRIC & TIMELINE FALLBACK
// -------------------------------------------------------------
let animationFrame2DId = null;
let lastTimestamp2D = 0;
let globalTime2D = 0.0;

function init2DFallback() {{
    const canvas = document.getElementById('fallback-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    if (animationFrame2DId !== null) return;
    lastTimestamp2D = performance.now();

    function render2D(now) {{
        animationFrame2DId = requestAnimationFrame(render2D);

        const dt = Math.min((now - lastTimestamp2D) / 1000.0, 0.1);
        lastTimestamp2D = now;

        if (isPlaying) {{
            globalTime2D += dt * animSpeed;
        }}

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const cx = canvas.width / 2;
        const cy = canvas.height / 2;

        const effPath = pathMode === 'auto' ? DATA.selectedPath : (pathMode === 'cpu' ? 'CPU' : (pathMode === 'pim' ? 'PIM' : 'COMPARE'));

        // Host Subsystem Box
        ctx.fillStyle = '#1B222C';
        ctx.strokeStyle = (effPath === 'PIM') ? '#394453' : '#91B8D8';
        ctx.lineWidth = (effPath === 'CPU') ? 3 : 2;
        ctx.strokeRect(cx - 380, cy - 140, 320, 280);
        ctx.fillRect(cx - 380, cy - 140, 320, 280);

        ctx.fillStyle = (effPath === 'PIM') ? '#A8B3C2' : '#91B8D8';
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText('Host CPU & Cache' + (effPath === 'CPU' ? ' [ACTIVE]' : ''), cx - 360, cy - 110);

        // CPU Core
        ctx.fillStyle = (effPath === 'PIM') ? '#222B36' : '#243B53';
        ctx.fillRect(cx - 350, cy - 80, 80, 180);
        ctx.fillStyle = '#E2E8F0';
        ctx.fillText('CPU', cx - 330, cy + 20);

        // LLC Cache
        ctx.fillStyle = (effPath === 'PIM') ? '#1B222C' : '#1E3A52';
        ctx.fillRect(cx - 240, cy - 80, 80, 180);
        ctx.fillStyle = (effPath === 'PIM') ? '#A8B3C2' : '#91B8D8';
        ctx.fillText('LLC', cx - 220, cy);
        ctx.font = '11px sans-serif';
        ctx.fillText(DATA.capacityKb + ' KiB', cx - 230, cy + 20);

        // Host DRAM
        ctx.fillStyle = '#1B222C';
        ctx.fillRect(cx - 130, cy - 80, 50, 180);
        ctx.fillStyle = '#A8B3C2';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText('DRAM', cx - 125, cy + 20);

        // Link
        ctx.fillStyle = (effPath === 'CPU') ? 'rgba(143, 183, 165, 0.2)' : (DATA.linkBwGbS <= 4.0 ? '#D5AD72' : '#22332B');
        ctx.fillRect(cx - 60, cy - 20, 120, 40);
        ctx.fillStyle = '#E2E8F0';
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText('Data Link (' + DATA.linkBwGbS + ' GB/s)', cx - 50, cy + 5);

        // PIM Subsystem Box
        ctx.fillStyle = '#1E2824';
        ctx.strokeStyle = (effPath === 'CPU') ? '#394453' : '#8FB7A5';
        ctx.lineWidth = (effPath === 'PIM') ? 3 : 2;
        ctx.strokeRect(cx + 60, cy - 140, 340, 280);
        ctx.fillRect(cx + 60, cy - 140, 340, 280);

        ctx.fillStyle = (effPath === 'CPU') ? '#A8B3C2' : '#8FB7A5';
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText('PIM Memory (' + DATA.bankCount + ' Banks)' + (effPath === 'PIM' ? ' [ACTIVE]' : ''), cx + 80, cy - 110);

        // Banks Grid 2D
        const bCount = Math.min(DATA.bankCount, 16);
        for (let i = 0; i < bCount; i++) {{
            const bx = cx + 80 + (i % 4) * 75;
            const by = cy - 80 + Math.floor(i / 4) * 50;
            ctx.fillStyle = (effPath === 'CPU') ? '#1E2B25' : '#2A3F35';
            ctx.fillRect(bx, by, 65, 40);
            ctx.fillStyle = '#E2E8F0';
            ctx.font = '10px sans-serif';
            ctx.fillText('B' + i, bx + 6, by + 16);
            ctx.fillStyle = (effPath === 'CPU') ? '#A8B3C2' : '#8FB7A5';
            ctx.fillText('ALU', bx + 36, by + 16);
        }}

        // Continuous Multi-Packet Dataflow Streams (2D)
        const t2d = globalTime2D;

        if (effPath !== 'PIM') {{
            // 1. CPU -> LLC Requests (Muted Blue, 3 packets)
            ctx.fillStyle = '#91B8D8';
            for (let i = 0; i < 3; i++) {{
                const p = (t2d * 0.25 + i / 3) % 1.0;
                ctx.beginPath();
                ctx.arc((cx - 270) + p * 110, cy - 20, 5, 0, Math.PI * 2);
                ctx.fill();
            }}

            // 2. LLC -> CPU Cache Hits (Sage Green, 3 packets)
            ctx.fillStyle = '#8FB7A5';
            for (let i = 0; i < 3; i++) {{
                const p = (t2d * 0.30 + i / 3) % 1.0;
                ctx.beginPath();
                ctx.arc((cx - 160) - p * 110, cy + 30, 5, 0, Math.PI * 2);
                ctx.fill();
            }}

            // 3. LLC -> Host DRAM Misses (Soft Amber, 3 packets)
            ctx.fillStyle = '#D5AD72';
            for (let i = 0; i < 3; i++) {{
                const p = (t2d * 0.20 + i / 3) % 1.0;
                ctx.beginPath();
                ctx.arc((cx - 160) + p * 80, cy - 40, 5, 0, Math.PI * 2);
                ctx.fill();
            }}
        }}

        if (effPath !== 'CPU') {{
            // 4. Host -> PIM Interconnect Stream (Neutral Light Grey, 6 packets)
            ctx.fillStyle = '#CBD5E1';
            for (let i = 0; i < 6; i++) {{
                const p = (t2d * 0.15 + i / 6) % 1.0;
                ctx.beginPath();
                ctx.arc((cx - 180) + p * 360, cy - 8, 6, 0, Math.PI * 2);
                ctx.fill();
            }}

            // 5. PIM -> Host Return Stream (Sage Green, 5 packets)
            ctx.fillStyle = '#8FB7A5';
            for (let i = 0; i < 5; i++) {{
                const p = (t2d * 0.15 + i / 5) % 1.0;
                ctx.beginPath();
                ctx.arc((cx + 180) - p * 360, cy + 12, 6, 0, Math.PI * 2);
                ctx.fill();
            }}
        }}
    }}
    animationFrame2DId = requestAnimationFrame(render2D);
}}

// Initialize
window.addEventListener('load', init3D);
</script>
</body>
</html>
"""
    return html_content
