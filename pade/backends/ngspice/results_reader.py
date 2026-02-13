"""
NGspice simulation results reader.

Parses ngspice raw output files (ASCII format) into numpy arrays.
"""

from pathlib import Path

import numpy as np


def read_raw(path: str | Path) -> dict[str, np.ndarray]:
    """
    Read an ngspice ASCII raw file.

    Handles both real-valued analyses (tran, dc, op) and complex-valued
    analyses (ac, noise).  Complex data is returned as ``numpy.complex128``
    arrays; real data as ``numpy.float64``.

    Args:
        path: Path to the raw file (produced with .options filetype=ascii).

    Returns:
        Dict mapping variable name (e.g. 'time', 'v(out)') to numpy array.

    Example:
        data = read_raw('sim/run/output.raw')
        time = data['time']
        vout = data['v(out)']
    """
    path = Path(path)
    text = path.read_text()

    # A raw file may contain multiple datasets (ngspice appends on re-run).
    # Parse only the last one.
    sections = text.split('Title:')
    if len(sections) > 1:
        text = 'Title:' + sections[-1]

    # --- Parse header (everything before the first Variables: section) ---
    # ngspice may repeat the Variables:/Values: block multiple times;
    # the actual numeric data follows the last Values: line.
    idx = text.rfind('Values:\n')
    if idx < 0:
        raise ValueError(f'No "Values:" section found in {path}')
    header = text[:idx]
    body = text[idx + len('Values:\n'):]

    n_vars = None
    n_points = None
    is_complex = False
    var_names: list[str] = []
    in_vars = False

    for line in header.splitlines():
        stripped = line.strip()

        if stripped.startswith('Flags:') and 'complex' in stripped.lower():
            is_complex = True
        elif stripped.startswith('No. Variables:'):
            n_vars = int(stripped.split(':')[1])
        elif stripped.startswith('No. Points:'):
            n_points = int(stripped.split(':')[1])
        elif stripped == 'Variables:':
            in_vars = True
        elif in_vars:
            if not stripped or stripped.startswith('Values') or stripped.startswith('Binary'):
                break
            parts = stripped.split()
            # Format: index  name  type
            var_names.append(parts[1])

    if n_vars is None or n_points is None:
        raise ValueError(f'Could not parse header in {path}')
    if len(var_names) != n_vars:
        raise ValueError(
            f'Expected {n_vars} variables, found {len(var_names)} in {path}'
        )

    # --- Parse values ---
    if is_complex:
        return _parse_complex(body, n_points, n_vars, var_names)
    return _parse_real(body, n_points, n_vars, var_names)


def _parse_real(body: str, n_points: int, n_vars: int,
                var_names: list[str]) -> dict[str, np.ndarray]:
    """Parse real-valued data (tran, dc, op)."""
    values = np.empty((n_points, n_vars), dtype=np.float64)
    tokens = body.split()

    pos = 0
    for i in range(n_points):
        pos += 1  # skip point index
        for j in range(n_vars):
            values[i, j] = float(tokens[pos])
            pos += 1

    return {name: values[:, i] for i, name in enumerate(var_names)}


def _parse_complex(body: str, n_points: int, n_vars: int,
                   var_names: list[str]) -> dict[str, np.ndarray]:
    """Parse complex-valued data (ac, noise).

    Each value is a ``real,imag`` pair (comma-separated, no space).
    The sweep variable (e.g. frequency) is also stored as complex
    with zero imaginary part; we return its real part as float64.
    """
    values = np.empty((n_points, n_vars), dtype=np.complex128)
    tokens = body.split()

    pos = 0
    for i in range(n_points):
        pos += 1  # skip point index
        for j in range(n_vars):
            tok = tokens[pos]
            if ',' in tok:
                re_str, im_str = tok.split(',')
                values[i, j] = complex(float(re_str), float(im_str))
            else:
                values[i, j] = float(tok)
            pos += 1

    result: dict[str, np.ndarray] = {}
    for i, name in enumerate(var_names):
        col = values[:, i]
        # Sweep variable (frequency): return as real float
        if name == 'frequency' or np.all(col.imag == 0):
            result[name] = col.real
        else:
            result[name] = col
    return result
