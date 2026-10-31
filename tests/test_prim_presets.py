"""Tests for PrIM benchmark presets integration."""

import pytest
from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.workloads import PRIM_PRESETS, WorkloadGenerator


def test_all_prim_presets_exist_and_generate():
    """Verify that every defined PrIM preset generates valid traces and descriptors."""
    generator = WorkloadGenerator(line_size_bytes=64)
    expected_presets = [
        "PrIM-VA",
        "PrIM-GEMV",
        "PrIM-BS",
        "PrIM-SEL",
    ]
    for name in expected_presets:
        assert name in PRIM_PRESETS, f"Expected preset {name} missing from PRIM_PRESETS"
        trace, desc = generator.generate_preset(name, seed=42)
        assert len(trace) > 0, f"Preset {name} generated an empty trace"
        assert desc.operation_count == len(trace)
        assert desc.working_set_bytes > 0
        assert desc.pim_eligible is True
        assert desc.params.get("preset_name") == name


def test_prim_presets_simulation_execution():
    """Verify that all policies can execute on every PrIM preset without errors or regret invariants violated."""
    config = CachePIMConfig()
    config.validate()
    sim = Simulator(config)
    generator = WorkloadGenerator(line_size_bytes=config.cache.line_size_bytes)

    for name in PRIM_PRESETS:
        trace, desc = generator.generate_preset(name, seed=42)
        results = sim.run_all_policies_on_trace(trace, desc)
        assert len(results) == 6, f"Expected 6 policy results for {name}, got {len(results)}"
        for res in results:
            assert res.selected_model_ns > 0
            assert res.regret_ns >= 0.0, f"Regret must be non-negative for {name} under {res.policy_name}"


def test_invalid_prim_preset_raises():
    """Verify that requesting an unknown preset name raises ValueError."""
    generator = WorkloadGenerator(line_size_bytes=64)
    with pytest.raises(ValueError, match="Unknown PrIM preset"):
        generator.generate_preset("NonExistentPreset")
