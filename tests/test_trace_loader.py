"""Tests for CachePIM real trace file loader."""

import pytest
from pathlib import Path
from cachepim.config import CachePIMConfig
from cachepim.simulator import Simulator
from cachepim.trace_loader import load_trace, parse_valgrind_lackey_line, parse_pin_or_generic_line


def test_valgrind_lackey_line_parser():
    """Verify parsing of individual Valgrind lackey lines."""
    # Instruction fetch lines should be skipped
    assert parse_valgrind_lackey_line(" I  00401000,4") == []

    # Load / Read
    loads = parse_valgrind_lackey_line(" L  07ff0000,8")
    assert len(loads) == 1
    assert loads[0] == ("READ", 0x07ff0000)

    # Store / Write
    stores = parse_valgrind_lackey_line(" S  07ff1000,4")
    assert len(stores) == 1
    assert stores[0] == ("WRITE", 0x07ff1000)

    # Modify (Read then Write)
    modifies = parse_valgrind_lackey_line(" M  07ff2000,8")
    assert len(modifies) == 2
    assert modifies[0] == ("READ", 0x07ff2000)
    assert modifies[1] == ("WRITE", 0x07ff2000)


def test_generic_and_pin_line_parser():
    """Verify parsing of PIN and generic text trace lines."""
    assert parse_pin_or_generic_line("0x7ffd5a024180 READ") == [("READ", 0x7ffd5a024180)]
    assert parse_pin_or_generic_line("WRITE 0x7ffd5a0241c0") == [("WRITE", 0x7ffd5a0241c0)]
    assert parse_pin_or_generic_line("0x401020: R 0x12fe80") == [("READ", 0x12fe80)]
    assert parse_pin_or_generic_line("# Comment") == []


def test_load_sample_valgrind_file():
    """Verify loading a real PrIM trace file and executing simulation on it."""
    sample_file = Path("data/traces/stream_va.txt")
    assert sample_file.exists(), "stream_va.txt trace file missing"

    records, desc = load_trace(sample_file, max_records=2048, line_size_bytes=64)
    assert len(records) > 0
    assert desc.operation_count == len(records)
    assert desc.working_set_bytes > 0

    config = CachePIMConfig()
    config.validate()
    sim = Simulator(config)
    results = sim.run_all_policies_on_trace(records, desc)

    assert len(results) == 6
    for r in results:
        assert r.selected_model_ns > 0
        assert r.regret_ns >= 0.0


def test_load_empty_trace_raises():
    """Verify ValueError when loading an empty trace."""
    with pytest.raises(ValueError, match="No valid memory access records"):
        load_trace("   \n# empty\n")
