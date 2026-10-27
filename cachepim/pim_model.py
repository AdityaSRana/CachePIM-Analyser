"""Analytical Processing-in-Memory (PIM) execution model.

The model keeps external transfers, internal PIM memory service, arithmetic
service, launch/synchronization, and bank imbalance as explicit components.
All results are modeled nanoseconds, not hardware measurements.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from cachepim.config import PIMConfig, TransferConfig
from cachepim.types import PIMCostBreakdown, WorkloadDescriptor


class PIMModel:
    """Analytical PIM execution and data movement model."""

    def __init__(self, pim_config: PIMConfig, transfer_config: TransferConfig):
        pim_config.validate()
        transfer_config.validate()
        self.pim_config = pim_config
        self.transfer_config = transfer_config
        self.bank_count = pim_config.bank_count
        self.internal_bandwidth = pim_config.effective_bandwidth_bytes_per_ns
        self.compute_ops_per_ns_per_bank = pim_config.compute_ops_per_ns_per_bank
        self.launch_overhead_ns = pim_config.launch_overhead_ns
        self.sync_overhead_ns = pim_config.sync_overhead_ns
        self.imbalance_model = pim_config.bank_imbalance_model
        self.h2p_bandwidth = transfer_config.host_to_pim_bandwidth_bytes_per_ns
        self.p2h_bandwidth = transfer_config.pim_to_host_bandwidth_bytes_per_ns
        self.h2p_fixed_ns = transfer_config.host_to_pim_fixed_ns
        self.p2h_fixed_ns = transfer_config.pim_to_host_fixed_ns

    def distribute_work(self, operation_count: int, skew_factor: float = 0.0) -> Tuple[List[int], float]:
        """Deterministically distribute operations and calculate max/mean imbalance.

        ``skew_factor=0`` produces a round-robin-equivalent balanced allocation.
        Positive skew increasingly favors higher-index banks. ``uniform`` mode
        intentionally ignores skew and models a perfectly balanced placement.
        Largest-remainder apportionment ensures per-bank work sums exactly to
        operation_count without concentrating all rounding error in bank zero.
        """
        if operation_count < 0:
            raise ValueError("operation_count must be non-negative")
        if not math.isfinite(skew_factor) or skew_factor < 0:
            raise ValueError("skew_factor must be finite and non-negative")
        B = self.bank_count
        if operation_count == 0:
            return [0] * B, 1.0

        if self.imbalance_model == "uniform" or skew_factor == 0.0:
            base, remainder = divmod(operation_count, B)
            loads = [base + (1 if b < remainder else 0) for b in range(B)]
        else:
            weights = [1.0 + skew_factor * (b / max(1, B - 1)) for b in range(B)]
            total_weight = sum(weights)
            exact = [operation_count * w / total_weight for w in weights]
            loads = [math.floor(v) for v in exact]
            leftover = operation_count - sum(loads)
            order = sorted(range(B), key=lambda b: (exact[b] - loads[b], -b), reverse=True)
            for b in order[:leftover]:
                loads[b] += 1

        mean_load = sum(loads) / B
        imbalance = max(loads) / mean_load if mean_load > 0 else 1.0
        return loads, float(imbalance)

    def evaluate(
        self,
        descriptor: WorkloadDescriptor,
        input_data_resident: bool = False,
    ) -> Optional[PIMCostBreakdown]:
        """Return component costs, or ``None`` if the kernel is not PIM-eligible.

        Kernel-level PIM transfer volumes are explicit descriptor fields. For
        older hand-built descriptors, they fall back to trace read/write bytes.
        The model serially sums internal memory service and arithmetic service;
        this deliberately simple assumption is reported as a model limitation.
        """
        if not descriptor.pim_eligible:
            return None

        input_bytes = 0 if input_data_resident else descriptor.effective_pim_input_bytes
        output_bytes = descriptor.effective_pim_output_bytes
        t_h2p = input_bytes / self.h2p_bandwidth
        if input_bytes > 0:
            t_h2p += self.h2p_fixed_ns
        t_p2h = output_bytes / self.p2h_bandwidth
        if output_bytes > 0:
            t_p2h += self.p2h_fixed_ns

        skew = float(descriptor.params.get("bank_skew_factor", 0.0))
        per_bank_work, imbalance_factor = self.distribute_work(descriptor.operation_count, skew)

        # Internal bank/memory service and arithmetic are represented as
        # separate, serialized components; their assumptions are explicit.
        internal_bytes = descriptor.effective_pim_input_bytes + descriptor.effective_pim_output_bytes
        t_internal_memory = internal_bytes / self.internal_bandwidth
        t_compute_base = descriptor.operation_count / (self.bank_count * self.compute_ops_per_ns_per_bank)
        t_imbalance = t_compute_base * (imbalance_factor - 1.0)

        t_launch = self.launch_overhead_ns
        t_sync = self.sync_overhead_ns
        total = t_h2p + t_internal_memory + t_compute_base + t_p2h + t_launch + t_sync + t_imbalance

        return PIMCostBreakdown(
            h2p_transfer_ns=float(t_h2p),
            compute_ns=float(t_compute_base),
            internal_memory_service_ns=float(t_internal_memory),
            p2h_transfer_ns=float(t_p2h),
            launch_overhead_ns=float(t_launch),
            sync_overhead_ns=float(t_sync),
            imbalance_overhead_ns=float(t_imbalance),
            total_pim_time_ns=float(total),
            bank_imbalance_factor=imbalance_factor,
            per_bank_work=per_bank_work,
        )
