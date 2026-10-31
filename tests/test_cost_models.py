"""Tests for CPU and PIM analytical cost models."""

import pytest
from cachepim.config import CPUConfig, PIMConfig, TransferConfig
from cachepim.cpu_model import CPUModel
from cachepim.pim_model import PIMModel
from cachepim.types import CacheStats, KernelType, WorkloadDescriptor


def test_cpu_model_accounting():
    config = CPUConfig(
        hit_service_ns=2.0,
        miss_service_ns=80.0,
        compute_ns_per_op=0.4,
    )
    model = CPUModel(config)

    # 10 hits, 5 misses, 100 ops, 2 dirty evictions
    stats = CacheStats(
        accesses=15,
        hits=10,
        misses=5,
        dirty_evictions=2,
    )
    breakdown = model.evaluate(stats, operation_count=100)

    expected_cache_time = (10 * 2.0) + (5 * 80.0)  # 20 + 400 = 420 ns
    expected_compute_time = 100 * 0.4  # 40 ns
    expected_writeback = 2 * 80.0  # 160 ns
    expected_total = 420.0 + 40.0 + 160.0  # 620 ns

    assert pytest.approx(breakdown.cache_service_time_ns) == expected_cache_time
    assert pytest.approx(breakdown.compute_time_ns) == expected_compute_time
    assert pytest.approx(breakdown.writeback_time_ns) == expected_writeback
    assert pytest.approx(breakdown.total_cpu_time_ns) == expected_total

    # CPU-no-cache baseline
    no_cache_breakdown = model.evaluate_no_cache(access_count=15, operation_count=100)
    assert pytest.approx(no_cache_breakdown.cache_service_time_ns) == 15 * 80.0
    assert pytest.approx(no_cache_breakdown.compute_time_ns) == 100 * 0.4
    assert pytest.approx(no_cache_breakdown.total_cpu_time_ns) == 1200.0 + 40.0


def test_pim_model_accounting_and_imbalance():
    p_cfg = PIMConfig(
        bank_count=4,
        effective_bandwidth_bytes_per_ns=100.0,
        compute_ops_per_ns_per_bank=1.0,
        launch_overhead_ns=50.0,
        sync_overhead_ns=20.0,
        bank_imbalance_model="max_over_mean",
    )
    t_cfg = TransferConfig(
        host_to_pim_bandwidth_bytes_per_ns=10.0,
        pim_to_host_bandwidth_bytes_per_ns=10.0,
        host_to_pim_fixed_ns=100.0,
        pim_to_host_fixed_ns=100.0,
    )
    model = PIMModel(p_cfg, t_cfg)

    desc = WorkloadDescriptor(
        workload_type="STREAM",
        seed=42,
        kernel_type=KernelType.VECTOR_OP.value,
        element_count=1000,
        bytes_read=1000,
        bytes_written=500,
        operation_count=1000,
        read_write_ratio=1.0,
        working_set_bytes=1000,
        trace_length=1000,
        pim_eligible=True,
    )

    breakdown = model.evaluate(desc)
    assert breakdown is not None

    # H2P: 1000 / 10 + 100 = 200 ns
    assert pytest.approx(breakdown.h2p_transfer_ns) == 200.0
    # P2H: 500 / 10 + 100 = 150 ns
    assert pytest.approx(breakdown.p2h_transfer_ns) == 150.0
    # Compute: 1000 / (4 * 1.0) = 250 ns
    assert pytest.approx(breakdown.compute_ns) == 250.0
    # Work per bank: 1000 evenly divides into 4 banks -> 250 each, imbalance = 1.0
    assert breakdown.bank_imbalance_factor == 1.0
    assert pytest.approx(breakdown.imbalance_overhead_ns) == 0.0
    assert pytest.approx(breakdown.launch_overhead_ns) == 50.0
    assert pytest.approx(breakdown.sync_overhead_ns) == 20.0

    # Internal PIM memory service: (1000 input + 500 output) / 100 bytes/ns = 15 ns.
    assert pytest.approx(breakdown.internal_memory_service_ns) == 15.0
    expected_total = 200.0 + 15.0 + 250.0 + 150.0 + 50.0 + 20.0
    assert pytest.approx(breakdown.total_pim_time_ns) == expected_total


def test_pim_unsupported_kernel_returns_none():
    p_cfg = PIMConfig()
    t_cfg = TransferConfig()
    model = PIMModel(p_cfg, t_cfg)

    desc = WorkloadDescriptor(
        workload_type="STREAM",
        seed=42,
        kernel_type=KernelType.UNSUPPORTED_KERNEL.value,
        element_count=100,
        bytes_read=100,
        bytes_written=0,
        operation_count=100,
        read_write_ratio=1.0,
        working_set_bytes=100,
        trace_length=100,
        pim_eligible=False,
    )

    assert model.evaluate(desc) is None


def test_pim_generated_kernel_has_output_transfer_even_for_read_only_trace():
    from cachepim.workloads import WorkloadGenerator

    gen = WorkloadGenerator(line_size_bytes=64)
    trace, desc = gen.generate(
        pattern="STREAM", seed=7, working_set_bytes=4096, passes=1,
        read_write_ratio=1.0, kernel_type=KernelType.VECTOR_OP.value,
    )
    assert all(r.operation == "READ" for r in trace)
    assert desc.bytes_written == 0  # CPU access trace is read-only.
    assert desc.effective_pim_input_bytes == 2 * desc.element_count * 8
    assert desc.effective_pim_output_bytes == desc.element_count * 8
    breakdown = PIMModel(PIMConfig(), TransferConfig()).evaluate(desc)
    assert breakdown is not None
    assert breakdown.p2h_transfer_ns > 0.0


def test_bank_skew_changes_load_distribution_and_total_work_is_preserved():
    model = PIMModel(PIMConfig(bank_count=8, bank_imbalance_model="max_over_mean"), TransferConfig())
    balanced, balanced_factor = model.distribute_work(1000, skew_factor=0.0)
    skewed, skewed_factor = model.distribute_work(1000, skew_factor=4.0)
    assert sum(balanced) == 1000
    assert sum(skewed) == 1000
    assert balanced_factor == 1.0
    assert skewed_factor > balanced_factor
    assert skewed != balanced


def test_pim_row_buffer_locality_factor():
    """Verify that row-buffer locality factor eta_row differentiates STREAM and RANDOM internal memory service (M7)."""
    p_cfg_enabled = PIMConfig(
        effective_bandwidth_bytes_per_ns=100.0,
        row_buffer_locality_enabled=True,
    )
    t_cfg = TransferConfig()
    model = PIMModel(p_cfg_enabled, t_cfg)

    desc_stream = WorkloadDescriptor(
        workload_type="STREAM", seed=42, kernel_type=KernelType.VECTOR_OP.value,
        element_count=1000, bytes_read=1000, bytes_written=500, operation_count=1000,
        read_write_ratio=1.0, working_set_bytes=1000, trace_length=1000, pim_eligible=True,
    )
    desc_random = WorkloadDescriptor(
        workload_type="RANDOM", seed=42, kernel_type=KernelType.VECTOR_OP.value,
        element_count=1000, bytes_read=1000, bytes_written=500, operation_count=1000,
        read_write_ratio=1.0, working_set_bytes=1000, trace_length=1000, pim_eligible=True,
    )

    bd_stream = model.evaluate(desc_stream)
    bd_random = model.evaluate(desc_random)
    assert bd_stream is not None and bd_random is not None
    # 1500 bytes / (100 * 0.90) = 16.67 ns for STREAM
    # 1500 bytes / (100 * 0.25) = 60.00 ns for RANDOM
    assert bd_random.internal_memory_service_ns > bd_stream.internal_memory_service_ns
    assert pytest.approx(bd_stream.internal_memory_service_ns) == 1500.0 / 90.0
    assert pytest.approx(bd_random.internal_memory_service_ns) == 1500.0 / 25.0


def test_pim_overlap_pipelining_model():
    """Verify that PIM overlap factor alpha reduces total execution time via pipelining (M8)."""
    t_cfg = TransferConfig(host_to_pim_bandwidth_bytes_per_ns=10.0, host_to_pim_fixed_ns=0.0)
    p_cfg_serial = PIMConfig(overlap_factor=0.0, launch_overhead_ns=0.0, sync_overhead_ns=0.0)
    p_cfg_pipelined = PIMConfig(overlap_factor=1.0, launch_overhead_ns=0.0, sync_overhead_ns=0.0)

    desc = WorkloadDescriptor(
        workload_type="STREAM", seed=42, kernel_type=KernelType.VECTOR_OP.value,
        element_count=1000, bytes_read=1000, bytes_written=0, operation_count=1000,
        read_write_ratio=1.0, working_set_bytes=1000, trace_length=1000, pim_eligible=True,
    )

    bd_serial = PIMModel(p_cfg_serial, t_cfg).evaluate(desc)
    bd_pipelined = PIMModel(p_cfg_pipelined, t_cfg).evaluate(desc)
    assert bd_serial is not None and bd_pipelined is not None
    # Pipelined must be faster or equal to serial execution
    assert bd_pipelined.total_pim_time_ns < bd_serial.total_pim_time_ns
