"""Trace loader and parser for CachePIM.

Parses real memory access traces from:
1. Valgrind Lackey traces (L = Load/READ, S = Store/WRITE, M = Modify/READ+WRITE, skipping I)
2. Intel PIN / pinatrace formats
3. Generic CSV/TSV or space-delimited address traces (address, op)
Converts them into CachePIM List[TraceRecord] and a WorkloadDescriptor.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional, Tuple, Union

from cachepim.types import KernelType, OperationType, TraceRecord, WorkloadDescriptor


def parse_valgrind_lackey_line(line: str) -> List[Tuple[str, int]]:
    """Parse a single Valgrind lackey trace line.

    Format:
        ' I  00401230,3'  -> Instruction fetch (skipped)
        ' L  07fffe20,8'  -> Load (READ) at 0x07fffe20
        ' S  07fffe40,4'  -> Store (WRITE) at 0x07fffe40
        ' M  07fffe60,8'  -> Modify (READ then WRITE) at 0x07fffe60
    Returns list of (operation, address) pairs.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("="):
        return []

    parts = stripped.split()
    if not parts:
        return []

    op_code = parts[0]
    if op_code == "I":
        # Skip instruction fetches; CachePIM models data LLC
        return []

    if op_code in ("L", "S", "M") and len(parts) >= 2:
        addr_part = parts[1].split(",")[0]
        try:
            addr = int(addr_part, 16)
        except ValueError:
            return []

        if op_code == "L":
            return [(OperationType.READ.value, addr)]
        elif op_code == "S":
            return [(OperationType.WRITE.value, addr)]
        elif op_code == "M":
            return [(OperationType.READ.value, addr), (OperationType.WRITE.value, addr)]

    return []


def parse_pin_or_generic_line(line: str) -> List[Tuple[str, int]]:
    """Parse generic CSV or space-separated or PIN format lines.

    Supported formats:
        '0x7ffd5a024180 READ'
        '0x7ffd5a024180, R'
        'READ 0x7ffd5a024180'
        '0x401020: R 0x12fe80' (PIN format: IP: OP ADDR)
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("//"):
        return []

    # Clean punctuation / commas
    cleaned = stripped.replace(",", " ").replace(":", " ")
    tokens = cleaned.split()
    if len(tokens) < 2:
        return []

    op = None
    addr = None

    for tok in tokens:
        upper = tok.upper()
        if upper in ("R", "READ", "LOAD", "L"):
            op = OperationType.READ.value
        elif upper in ("W", "WRITE", "STORE", "S"):
            op = OperationType.WRITE.value
        elif tok.startswith("0x") or tok.startswith("0X"):
            try:
                addr = int(tok, 16)
            except ValueError:
                pass
        elif tok.isdigit():
            addr = int(tok)

    if op is not None and addr is not None:
        return [(op, addr)]

    # If first token is address and second is integer operation (e.g. 0=READ, 1=WRITE)
    if len(tokens) >= 2:
        try:
            if tokens[0].startswith("0x") or tokens[0].isdigit():
                a = int(tokens[0], 16) if tokens[0].startswith("0x") else int(tokens[0])
                if tokens[1] in ("0", "1"):
                    o = OperationType.READ.value if tokens[1] == "0" else OperationType.WRITE.value
                    return [(o, a)]
        except ValueError:
            pass

    return []


def load_trace(
    source: Union[str, Path, io.StringIO, io.TextIOBase],
    max_records: Optional[int] = None,
    kernel_type: str = "VECTOR_OP",
    workload_name: str = "REAL_TRACE",
    line_size_bytes: int = 64,
) -> Tuple[List[TraceRecord], WorkloadDescriptor]:
    """Parse a real memory trace file or text stream into CachePIM trace records.

    Automatically detects Valgrind Lackey format vs. generic/PIN trace formats.
    """
    records: List[TraceRecord] = []

    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.is_file():
            # If string contains newline, treat as content directly
            if "\n" in str(source):
                lines = str(source).splitlines()
            else:
                raise FileNotFoundError(f"Trace file not found: {source}")
        else:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
    else:
        lines = source.readlines()

    # Detect format by inspecting first 50 lines
    is_valgrind = False
    for l in lines[:50]:
        s = l.strip()
        if s.startswith(("I ", "L ", "S ", "M ")) and ("," in s or "0" in s):
            is_valgrind = True
            break

    parser_fn = parse_valgrind_lackey_line if is_valgrind else parse_pin_or_generic_line

    seq = 0
    unique_cache_lines = set()
    reads = 0
    writes = 0

    for line in lines:
        parsed_ops = parser_fn(line)
        for op, addr in parsed_ops:
            records.append(
                TraceRecord(
                    sequence_number=seq,
                    address=addr,
                    operation=op,
                    task_id="real_task",
                    phase_id="main",
                )
            )
            unique_cache_lines.add(addr // line_size_bytes)
            if op == OperationType.READ.value:
                reads += 1
            else:
                writes += 1
            seq += 1

            if max_records and seq >= max_records:
                break
        if max_records and seq >= max_records:
            break

    if not records:
        raise ValueError(
            "No valid memory access records could be parsed from trace source. "
            "Ensure the file contains Valgrind lackey (L/S/M address,size) or (address op) lines."
        )

    working_set_bytes = len(unique_cache_lines) * line_size_bytes
    total_ops = len(records)
    read_write_ratio = (reads / total_ops) if total_ops > 0 else 1.0

    # Kernel-level input/output volumes
    element_size = 8
    elements = max(1, working_set_bytes // element_size)
    if kernel_type == KernelType.REDUCTION.value:
        pim_input_bytes = working_set_bytes
        pim_output_bytes = 8
    elif kernel_type == KernelType.FILTER.value:
        pim_input_bytes = working_set_bytes
        pim_output_bytes = working_set_bytes // 2
    else:
        pim_input_bytes = working_set_bytes
        pim_output_bytes = working_set_bytes // 2

    descriptor = WorkloadDescriptor(
        workload_type=workload_name,
        seed=0,
        kernel_type=kernel_type,
        element_count=elements,
        bytes_read=reads * line_size_bytes,
        bytes_written=writes * line_size_bytes,
        operation_count=total_ops,
        read_write_ratio=read_write_ratio,
        working_set_bytes=working_set_bytes,
        trace_length=total_ops,
        pim_eligible=True,
        reusable_bytes=max(0, working_set_bytes - (len(unique_cache_lines) * 64)),
        pim_input_bytes=pim_input_bytes,
        pim_output_bytes=pim_output_bytes,
        params={
            "source": "REAL_TRACE_FILE",
            "format": "valgrind" if is_valgrind else "generic",
            "unique_lines": len(unique_cache_lines),
            "access_count": total_ops,
        },
    )

    return records, descriptor
