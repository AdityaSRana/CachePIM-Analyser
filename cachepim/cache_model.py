"""Fully associative Last-Level Cache (LLC) simulator with exact LRU replacement.

Models line-level mapping, cache capacity constraints, LRU eviction order,
hit/miss/eviction accounting, and memory fetch bytes.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from cachepim.config import CacheConfig
from cachepim.types import CacheEvent, CacheStats, OperationType, TraceRecord


@dataclass
class CacheLineEntry:
    line_id: int
    is_dirty: bool = False
    task_id: Optional[str] = None


class CacheModel:
    """Last-Level Cache (LLC) model with configurable associativity (fully associative or N-way set associative) and exact LRU replacement."""

    def __init__(self, config: CacheConfig):
        config.validate()
        self.config = config
        self.capacity_bytes: int = config.capacity_bytes
        self.line_size_bytes: int = config.line_size_bytes
        self.number_of_lines: int = config.number_of_lines
        self.ways: Optional[int] = config.ways

        if self.ways is not None and self.ways > 0:
            self.num_sets: int = self.number_of_lines // self.ways
            self._sets: List[OrderedDict[int, CacheLineEntry]] = [OrderedDict() for _ in range(self.num_sets)]
            self._lines: Optional[OrderedDict[int, CacheLineEntry]] = None
        else:
            self.num_sets = 1
            self._sets = []
            self._lines = OrderedDict()

        self._unique_lines_seen: Set[int] = set()

        # Running statistics
        self._seq: int = 0
        self._accesses: int = 0
        self._reads: int = 0
        self._writes: int = 0
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._dirty_evictions: int = 0

    def reset(self) -> None:
        """Reset cache to cold initial state and clear all counters."""
        if self._lines is not None:
            self._lines.clear()
        for s in self._sets:
            s.clear()
        self._unique_lines_seen.clear()
        self._seq = 0
        self._accesses = 0
        self._reads = 0
        self._writes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._dirty_evictions = 0

    def address_to_line_id(self, address: int) -> int:
        """Convert a byte address to an aligned cache line identifier."""
        return address // self.line_size_bytes

    def access(
        self,
        address: int,
        operation: str = "READ",
        task_id: Optional[str] = None,
    ) -> CacheEvent:
        """Process a single memory access and update LRU recency and statistics."""
        self._seq += 1
        seq = self._seq
        line_id = self.address_to_line_id(address)
        self._unique_lines_seen.add(line_id)
        self._accesses += 1

        is_write = operation.upper() == OperationType.WRITE.value
        if is_write:
            self._writes += 1
        else:
            self._reads += 1

        evicted_line_id: Optional[int] = None

        if self.ways is not None and self.ways > 0:
            set_idx = line_id % self.num_sets
            tag = line_id // self.num_sets
            target_set = self._sets[set_idx]

            if tag in target_set:
                entry = target_set[tag]
                if is_write:
                    entry.is_dirty = True
                if task_id:
                    entry.task_id = task_id
                target_set.move_to_end(tag, last=True)
                self._hits += 1
                return CacheEvent(
                    line_id=line_id,
                    hit=True,
                    miss=False,
                    evicted_line_id=None,
                    operation=operation,
                    sequence_number=seq,
                )
            else:
                self._misses += 1
                if len(target_set) >= self.ways:
                    evicted_tag, evicted_entry = target_set.popitem(last=False)
                    evicted_line_id = evicted_tag * self.num_sets + set_idx
                    self._evictions += 1
                    if evicted_entry.is_dirty:
                        self._dirty_evictions += 1

                new_entry = CacheLineEntry(line_id=line_id, is_dirty=is_write, task_id=task_id)
                target_set[tag] = new_entry
                return CacheEvent(
                    line_id=line_id,
                    hit=False,
                    miss=True,
                    evicted_line_id=evicted_line_id,
                    operation=operation,
                    sequence_number=seq,
                )
        else:
            # Fully associative LRU
            if line_id in self._lines:
                entry = self._lines[line_id]
                if is_write:
                    entry.is_dirty = True
                if task_id:
                    entry.task_id = task_id
                self._lines.move_to_end(line_id, last=True)
                self._hits += 1

                return CacheEvent(
                    line_id=line_id,
                    hit=True,
                    miss=False,
                    evicted_line_id=None,
                    operation=operation,
                    sequence_number=seq,
                )
            else:
                self._misses += 1

                if len(self._lines) >= self.number_of_lines:
                    evicted_id, evicted_entry = self._lines.popitem(last=False)
                    evicted_line_id = evicted_id
                    self._evictions += 1
                    if evicted_entry.is_dirty:
                        self._dirty_evictions += 1

                new_entry = CacheLineEntry(line_id=line_id, is_dirty=is_write, task_id=task_id)
                self._lines[line_id] = new_entry

                assert len(self._lines) <= self.number_of_lines, (
                    f"Cache invariant violated: resident lines ({len(self._lines)}) > capacity ({self.number_of_lines})"
                )

                return CacheEvent(
                    line_id=line_id,
                    hit=False,
                    miss=True,
                    evicted_line_id=evicted_line_id,
                    operation=operation,
                    sequence_number=seq,
                )

    def run(self, trace: Iterable[TraceRecord]) -> CacheStats:
        """Process an entire stream of trace records and return aggregated CacheStats."""
        for rec in trace:
            self.access(rec.address, rec.operation, rec.task_id)
        return self.get_stats()

    def get_stats(self) -> CacheStats:
        """Return the current cumulative cache statistics."""
        if self._accesses > 0:
            hit_rate = self._hits / self._accesses
            miss_rate = self._misses / self._accesses
        else:
            hit_rate = 0.0
            miss_rate = 0.0

        return CacheStats(
            accesses=self._accesses,
            reads=self._reads,
            writes=self._writes,
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            unique_lines=len(self._unique_lines_seen),
            bytes_fetched_from_memory=self._misses * self.line_size_bytes,
            dirty_evictions=self._dirty_evictions,
        )

    def snapshot(self) -> Dict[str, Any]:
        """Capture diagnostic snapshot of cache residency and recency order."""
        if self._lines is not None:
            res_count = len(self._lines)
            res_keys = list(self._lines.keys())
        else:
            res_count = sum(len(s) for s in self._sets)
            res_keys = [tag * self.num_sets + set_idx for set_idx, s in enumerate(self._sets) for tag in s.keys()]
        return {
            "capacity_bytes": self.capacity_bytes,
            "line_size_bytes": self.line_size_bytes,
            "number_of_lines": self.number_of_lines,
            "ways": self.ways,
            "resident_count": res_count,
            "resident_line_ids_lru_order": res_keys,
            "stats": self.get_stats(),
        }
