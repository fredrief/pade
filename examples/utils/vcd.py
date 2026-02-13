"""Lightweight VCD (Value Change Dump) parser.

Parses VCD files produced by Verilog simulators into numpy arrays
for analysis in Python. Handles integer signals (scalar and vector).
"""

import re
from pathlib import Path

import numpy as np


def parse_vcd(vcd_path: str | Path, signals: list[str] | None = None) -> dict:
    """Parse a VCD file into a dict of signal name -> (times, values).

    Args:
        vcd_path: Path to VCD file.
        signals: Optional list of signal names to extract (hierarchical,
            e.g. 'cic_filter_tb.dut.dout'). If None, extracts all signals.

    Returns:
        Dict mapping signal name to a dict with:
            'times': numpy array of timestamps (integer, in timescale units)
            'values': numpy array of signal values (integer)
            'width': bit width of the signal
    """
    vcd_path = Path(vcd_path)
    text = vcd_path.read_text()

    # Phase 1: parse header — map short IDs to signal names and widths
    id_to_signal = {}  # id_char -> (full_name, width)
    scope_stack = []

    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('$scope'):
            parts = line.split()
            if len(parts) >= 3:
                scope_stack.append(parts[2])
        elif line.startswith('$upscope'):
            if scope_stack:
                scope_stack.pop()
        elif line.startswith('$var'):
            # $var wire 16 ! dout [15:0] $end
            # $var wire 1 " valid $end
            parts = line.split()
            if len(parts) >= 5:
                width = int(parts[2])
                id_char = parts[3]
                name = parts[4]
                full_name = '.'.join(scope_stack + [name])
                id_to_signal[id_char] = (full_name, width)
        elif line.startswith('$enddefinitions'):
            break

    # Filter to requested signals
    if signals is not None:
        signal_set = set(signals)
        active_ids = {
            k: v for k, v in id_to_signal.items() if v[0] in signal_set
        }
    else:
        active_ids = id_to_signal

    # Phase 2: parse value changes
    changes = {id_char: [] for id_char in active_ids}
    current_time = 0

    # Find the start of value changes (after $enddefinitions ... $end)
    data_start = text.find('$enddefinitions')
    if data_start == -1:
        return {}
    # Skip past the $end after $enddefinitions
    data_start = text.find('$end', data_start)
    if data_start == -1:
        return {}
    data_start = text.index('\n', data_start) + 1

    for line in text[data_start:].split('\n'):
        line = line.strip()
        if not line or line.startswith('$'):
            continue

        # Timestamp: #<number>
        if line.startswith('#'):
            current_time = int(line[1:])
            continue

        # Scalar value change: 0<id> or 1<id> or x<id> or z<id>
        if len(line) >= 2 and line[0] in '01xXzZ':
            val_char = line[0]
            id_char = line[1:]
            if id_char in changes:
                val = int(val_char) if val_char in '01' else 0
                changes[id_char].append((current_time, val))
            continue

        # Vector value change: b<binary> <id>
        if line.startswith('b') or line.startswith('B'):
            m = re.match(r'[bB]([01xXzZ]+)\s+(.+)', line)
            if m:
                bits = m.group(1).replace('x', '0').replace('X', '0').replace('z', '0').replace('Z', '0')
                id_char = m.group(2)
                if id_char in changes:
                    val = int(bits, 2)
                    # Handle signed values
                    width = active_ids[id_char][1]
                    if width > 1 and val >= (1 << (width - 1)):
                        val -= (1 << width)
                    changes[id_char].append((current_time, val))
            continue

    # Phase 3: convert to numpy arrays
    result = {}
    for id_char, data in changes.items():
        name, width = active_ids[id_char]
        if data:
            times = np.array([t for t, _ in data], dtype=np.int64)
            values = np.array([v for _, v in data], dtype=np.int64)
        else:
            times = np.array([], dtype=np.int64)
            values = np.array([], dtype=np.int64)
        result[name] = {'times': times, 'values': values, 'width': width}

    return result
