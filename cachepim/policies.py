"""Execution offloading policies for CachePIM.

Implements six distinct execution policies sharing a unified interface:
1. CPU-cache: Always execute through the CPU cache.
2. CPU-no-cache: Direct-memory baseline without cache reuse.
3. PIM-always: Offload all supported kernels to PIM.
4. Cost-based: Analytical cost comparison using estimated parameters.
5. Reuse-aware: Candidate policy incorporating a dimensionally consistent reuse penalty.
6. Oracle: Optimal offline reference using actual simulated costs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from cachepim.config import CachePIMConfig
from cachepim.cpu_model import CPUModel
from cachepim.pim_model import PIMModel
from cachepim.types import (
    CacheStats,
    ExecutionPath,
    PolicyDecision,
    WorkloadDescriptor,
)


def estimate_cache_hits_and_misses(
    descriptor: WorkloadDescriptor,
    capacity_bytes: int,
    line_size_bytes: int,
) -> tuple[int, int]:
    """Estimate cache hits/misses from workload metadata without using oracle costs.

    This is a deliberately transparent profile-level estimate. It preserves
    spatial locality for streaming traces and uses simple expected-hit models
    for uniform random and hot-set traces. It is not a substitute for the exact
    LRU trace replay used to score actual modeled CPU execution time.
    """
    accesses = int(descriptor.trace_length or descriptor.operation_count)
    if accesses <= 0:
        return 0, 0
    if capacity_bytes <= 0 or line_size_bytes <= 0:
        raise ValueError("Cache capacity and line size must be positive")

    unique_lines = max(1, int((descriptor.working_set_bytes + line_size_bytes - 1) // line_size_bytes))
    cache_lines = max(1, capacity_bytes // line_size_bytes)
    compulsory = min(accesses, unique_lines)
    pattern = descriptor.workload_type.upper()

    if pattern == "STREAM":
        passes = max(1, int(descriptor.params.get("passes", 1)))
        # If the full line working set fits, it is retained after the first
        # pass. Otherwise each sequential pass reloads the lines, while word
        # references within a cache line still benefit from spatial locality.
        misses_per_pass = unique_lines
        estimated_misses = unique_lines if unique_lines <= cache_lines else unique_lines * passes
        misses = min(accesses, estimated_misses)
        hits = accesses - misses
    elif pattern in ("REUSE", "MIXED_PHASE") and descriptor.reusable_bytes > 0:
        hot_lines = max(1, int((descriptor.reusable_bytes + line_size_bytes - 1) // line_size_bytes))
        cold_lines = max(1, unique_lines - hot_lines)
        hot_ratio = descriptor.hot_cold_ratio
        if hot_ratio is None:
            hot_ratio = 0.5 if pattern == "MIXED_PHASE" else 0.8
        hot_ratio = min(1.0, max(0.0, float(hot_ratio)))
        hot_accesses = int(accesses * hot_ratio)
        cold_accesses = accesses - hot_accesses
        if hot_lines <= cache_lines:
            # Hot set fits: account for warm-up misses, then repeated hits.
            hot_hits = max(0, hot_accesses - min(hot_accesses, hot_lines))
            spare = max(0, cache_lines - hot_lines)
            cold_repeats = max(0, cold_accesses - min(cold_accesses, cold_lines))
            cold_hit_probability = min(1.0, spare / cold_lines)
            cold_hits = int(cold_repeats * cold_hit_probability)
        else:
            # Hot set does not fit: use cache coverage as an expected hit ratio.
            hot_hit_probability = min(1.0, cache_lines / hot_lines)
            hot_hits = max(0, int((hot_accesses - min(hot_accesses, hot_lines)) * hot_hit_probability))
            cold_hits = 0
        hits = min(accesses - compulsory, hot_hits + cold_hits)
        misses = accesses - hits
    elif pattern == "RANDOM":
        # Approximate steady-state hit probability for uniform references over
        # the working set, after compulsory misses.
        remaining = max(0, accesses - compulsory)
        hit_probability = min(1.0, cache_lines / unique_lines)
        hits = min(remaining, int(remaining * hit_probability))
        misses = accesses - hits
    else:
        # No temporal-reuse claim: retain only spatial/compulsory locality.
        misses = compulsory
        hits = accesses - misses

    hits = max(0, min(accesses, int(hits)))
    misses = accesses - hits
    return hits, misses


class BasePolicy(ABC):
    """Abstract base class for all offloading policies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        """Make an offloading decision between CPU and PIM."""
        pass


class CPUCachePolicy(BasePolicy):
    """Always execute through CPU cache."""

    def __init__(self) -> None:
        super().__init__("CPU-cache")

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        hits_est, misses_est = estimate_cache_hits_and_misses(
            descriptor, config.cache.capacity_bytes, config.cache.line_size_bytes
        )
        stats = CacheStats(
            accesses=descriptor.trace_length or descriptor.operation_count,
            hits=hits_est,
            misses=misses_est,
            dirty_evictions=0,
        )
        cpu_cost = CPUModel(config.cpu).evaluate(stats, descriptor.operation_count)

        pim_model = PIMModel(config.pim, config.transfer)
        pim_cost = pim_model.evaluate(descriptor)
        pim_est = pim_cost.total_pim_time_ns if pim_cost else None

        return PolicyDecision(
            policy_name=self.name,
            selected_path=ExecutionPath.CPU.value,
            decision_reason="ALWAYS_CPU_CACHE",
            cpu_estimated_ns=cpu_cost.total_cpu_time_ns,
            pim_estimated_ns=pim_est if pim_est is not None else 0.0,
            policy_overhead_ns=0.0,
        )


class CPUNoCachePolicy(BasePolicy):
    """Baseline executing directly through memory without cache reuse."""

    def __init__(self) -> None:
        super().__init__("CPU-no-cache")

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        cpu_cost = CPUModel(config.cpu).evaluate_no_cache(
            descriptor.operation_count, descriptor.operation_count
        )
        pim_model = PIMModel(config.pim, config.transfer)
        pim_cost = pim_model.evaluate(descriptor)
        pim_est = pim_cost.total_pim_time_ns if pim_cost else None

        return PolicyDecision(
            policy_name=self.name,
            selected_path=ExecutionPath.CPU.value,
            decision_reason="DIRECT_MEMORY_BASELINE",
            cpu_estimated_ns=cpu_cost.total_cpu_time_ns,
            pim_estimated_ns=pim_est if pim_est is not None else 0.0,
            policy_overhead_ns=0.0,
        )


class PIMAlwaysPolicy(BasePolicy):
    """Always offload eligible kernels to PIM; fallback to CPU if unsupported."""

    def __init__(self) -> None:
        super().__init__("PIM-always")

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        hits_est, misses_est = estimate_cache_hits_and_misses(
            descriptor, config.cache.capacity_bytes, config.cache.line_size_bytes
        )
        stats = CacheStats(
            accesses=descriptor.trace_length or descriptor.operation_count,
            hits=hits_est,
            misses=misses_est,
            dirty_evictions=0,
        )
        cpu_cost = CPUModel(config.cpu).evaluate(stats, descriptor.operation_count)

        if not descriptor.pim_eligible:
            return PolicyDecision(
                policy_name=self.name,
                selected_path=ExecutionPath.CPU.value,
                decision_reason="UNSUPPORTED_BY_PIM",
                cpu_estimated_ns=cpu_cost.total_cpu_time_ns,
                pim_estimated_ns=0.0,
                policy_overhead_ns=0.0,
            )

        pim_model = PIMModel(config.pim, config.transfer)
        pim_cost = pim_model.evaluate(descriptor)
        pim_est = pim_cost.total_pim_time_ns if pim_cost else 0.0

        return PolicyDecision(
            policy_name=self.name,
            selected_path=ExecutionPath.PIM.value,
            decision_reason="ALWAYS_PIM",
            cpu_estimated_ns=cpu_cost.total_cpu_time_ns,
            pim_estimated_ns=pim_est,
            policy_overhead_ns=0.0,
        )


class CostBasedPolicy(BasePolicy):
    """Offload to PIM if estimated PIM latency < estimated CPU latency; ties choose CPU."""

    def __init__(self) -> None:
        super().__init__("Cost-based")

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        hits_est, misses_est = estimate_cache_hits_and_misses(
            descriptor, config.cache.capacity_bytes, config.cache.line_size_bytes
        )
        stats = CacheStats(
            accesses=descriptor.trace_length or descriptor.operation_count,
            hits=hits_est,
            misses=misses_est,
            dirty_evictions=0,
        )
        cpu_cost = CPUModel(config.cpu).evaluate(stats, descriptor.operation_count)
        cpu_est = cpu_cost.total_cpu_time_ns

        if not descriptor.pim_eligible:
            return PolicyDecision(
                policy_name=self.name,
                selected_path=ExecutionPath.CPU.value,
                decision_reason="UNSUPPORTED_BY_PIM",
                cpu_estimated_ns=cpu_est,
                pim_estimated_ns=0.0,
                policy_overhead_ns=0.0,
            )

        pim_model = PIMModel(config.pim, config.transfer)
        pim_cost = pim_model.evaluate(descriptor)
        pim_est = pim_cost.total_pim_time_ns if pim_cost else float("inf")

        if pim_est < cpu_est:
            selected = ExecutionPath.PIM.value
            reason = "COST_PIM_LOWER"
        else:
            selected = ExecutionPath.CPU.value
            reason = "COST_CPU_LOWER_OR_EQUAL"

        return PolicyDecision(
            policy_name=self.name,
            selected_path=selected,
            decision_reason=reason,
            cpu_estimated_ns=cpu_est,
            pim_estimated_ns=pim_est,
            policy_overhead_ns=0.0,
        )


class ReuseAwarePolicy(BasePolicy):
    """Candidate policy incorporating dimensionally consistent reuse preservation cost.

    T_PIM_adjusted = T_PIM_estimated + lambda * R_cost
    R_cost = (effective_reusable_bytes / cache_capacity_bytes) * estimated_CPU_reuse_benefit_ns
    """

    def __init__(self) -> None:
        super().__init__("Reuse-aware")

    def calculate_reuse_cost(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        estimated_hits: int,
    ) -> float:
        """Compute dimensionally consistent reuse cost, gated by estimated hit ratio."""
        cap_bytes = config.cache.capacity_bytes
        accesses = int(descriptor.trace_length or descriptor.operation_count)
        if cap_bytes <= 0 or descriptor.working_set_bytes <= 0 or estimated_hits <= 0 or accesses <= 0:
            return 0.0

        # The configured threshold is an explicit gate: only apply a reuse
        # preservation penalty when the estimated hit fraction reaches it.
        estimated_hit_fraction = min(1.0, max(0.0, estimated_hits / accesses))
        if estimated_hit_fraction < config.policy.reuse_threshold:
            return 0.0

        # Cache coverage ratio: how much of the working set can be retained in cache
        fit_ratio = min(1.0, cap_bytes / descriptor.working_set_bytes)
        effective_reusable_bytes = descriptor.reusable_bytes * fit_ratio

        # Time saved per hit in nanoseconds
        hit_benefit_per_access = config.cpu.miss_service_ns - config.cpu.hit_service_ns
        estimated_cpu_reuse_benefit_ns = estimated_hits * hit_benefit_per_access

        # Normalization by cache capacity ensures dimension is in nanoseconds:
        # (bytes / bytes) * nanoseconds = nanoseconds
        reusable_fraction = min(1.0, effective_reusable_bytes / cap_bytes)
        r_cost = reusable_fraction * estimated_cpu_reuse_benefit_ns
        return max(0.0, r_cost)

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        hits_est, misses_est = estimate_cache_hits_and_misses(
            descriptor, config.cache.capacity_bytes, config.cache.line_size_bytes
        )
        stats = CacheStats(
            accesses=descriptor.trace_length or descriptor.operation_count,
            hits=hits_est,
            misses=misses_est,
            dirty_evictions=0,
        )
        cpu_cost = CPUModel(config.cpu).evaluate(stats, descriptor.operation_count)
        cpu_est = cpu_cost.total_cpu_time_ns

        if not descriptor.pim_eligible:
            return PolicyDecision(
                policy_name=self.name,
                selected_path=ExecutionPath.CPU.value,
                decision_reason="UNSUPPORTED_BY_PIM",
                cpu_estimated_ns=cpu_est,
                pim_estimated_ns=0.0,
                policy_overhead_ns=0.0,
            )

        pim_model = PIMModel(config.pim, config.transfer)
        pim_cost = pim_model.evaluate(descriptor)
        pim_est = pim_cost.total_pim_time_ns if pim_cost else float("inf")

        # Dynamic Working-Set Footprint Estimator (M2)
        use_footprint = getattr(config.policy, "use_footprint_estimator", True)
        accesses = max(1, int(descriptor.trace_length or descriptor.operation_count))
        hit_fraction = hits_est / accesses
        is_resident = descriptor.working_set_bytes <= config.cache.capacity_bytes
        reusability = max(0.0, float(descriptor.reusable_bytes or 0)) / max(1, descriptor.working_set_bytes)
        fit_ratio = min(1.0, config.cache.capacity_bytes / max(1, descriptor.working_set_bytes))

        if use_footprint and is_resident and (hit_fraction >= config.policy.reuse_threshold or reusability >= 0.4):
            # When working set fits in cache with high temporal locality, repeated hits
            # benefit from innermost cache residency without bus arbitration.
            # Clamped physically to never exceed total hit service time (M2 repair).
            # Tuned credit multiplier is 0.25 based on dev seeds 42-46.
            raw_credit = hits_est * (config.cpu.hit_service_ns * 0.25 * fit_ratio)
            temporal_credit = min(hits_est * config.cpu.hit_service_ns, raw_credit)
            refined_cpu_est = max(0.0, cpu_est - temporal_credit)
            pim_adjusted = pim_est
        else:
            refined_cpu_est = cpu_est
            lam = config.policy.reuse_penalty_weight
            r_cost = self.calculate_reuse_cost(descriptor, config, hits_est)
            pim_adjusted = pim_est + (lam * r_cost)

        if pim_adjusted < refined_cpu_est:
            selected = ExecutionPath.PIM.value
            reason = "REUSE_AWARE_PIM_LOWER"
        else:
            selected = ExecutionPath.CPU.value
            if pim_est < cpu_est:
                reason = "REUSE_AWARE_PRESERVED_CPU_DUE_TO_FOOTPRINT" if use_footprint else "REUSE_AWARE_PRESERVED_CPU_DUE_TO_REUSE"
            else:
                reason = "REUSE_AWARE_CPU_LOWER_NATURALLY"

        return PolicyDecision(
            policy_name=self.name,
            selected_path=selected,
            decision_reason=reason,
            cpu_estimated_ns=refined_cpu_est,
            pim_estimated_ns=pim_est,
            policy_overhead_ns=0.0,  # Zero runtime overhead for analytical descriptor inspection
        )


class OraclePolicy(BasePolicy):
    """Optimal offline reference selecting min(T_CPU_actual, T_PIM_actual)."""

    def __init__(self) -> None:
        super().__init__("Oracle")

    def decide(
        self,
        descriptor: WorkloadDescriptor,
        config: CachePIMConfig,
        actual_cpu_ns: Optional[float] = None,
        actual_pim_ns: Optional[float] = None,
    ) -> PolicyDecision:
        if actual_cpu_ns is None or actual_pim_ns is None:
            raise ValueError("OraclePolicy requires actual modeled costs to make optimal decision")

        if not descriptor.pim_eligible:
            return PolicyDecision(
                policy_name=self.name,
                selected_path=ExecutionPath.CPU.value,
                decision_reason="ORACLE_UNSUPPORTED_BY_PIM",
                cpu_estimated_ns=actual_cpu_ns,
                pim_estimated_ns=0.0,
                policy_overhead_ns=0.0,
            )

        if actual_pim_ns < actual_cpu_ns:
            selected = ExecutionPath.PIM.value
            reason = "ORACLE_PIM_OPTIMAL"
        else:
            selected = ExecutionPath.CPU.value
            reason = "ORACLE_CPU_OPTIMAL"

        return PolicyDecision(
            policy_name=self.name,
            selected_path=selected,
            decision_reason=reason,
            cpu_estimated_ns=actual_cpu_ns,
            pim_estimated_ns=actual_pim_ns,
            policy_overhead_ns=0.0,
        )
