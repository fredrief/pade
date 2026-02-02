"""
SKY130 device wrappers.

This module will be implemented after PDK installation is verified.
It will use the NGspice netlist reader to load device subcircuits.

SKY130 devices available:
- nfet_01v8: 1.8V NMOS transistor
- pfet_01v8: 1.8V PMOS transistor
- nfet_01v8_lvt: Low-Vt NMOS
- pfet_01v8_lvt: Low-Vt PMOS
- nfet_01v8_hvt: High-Vt NMOS
- pfet_01v8_hvt: High-Vt PMOS
- sky130_fd_pr__res_*: Resistors
- sky130_fd_pr__cap_*: Capacitors
"""

import os
from pathlib import Path

# Get PDK paths from environment
PDK_ROOT = os.environ.get('PDK_ROOT', os.path.expanduser('~/.ciel'))
PDK = os.environ.get('PDK', 'sky130A')

# Model library path
MODEL_PATH = Path(PDK_ROOT) / PDK / 'libs.tech' / 'ngspice' / 'sky130.lib.spice'


def _check_pdk():
    """Check if PDK is installed."""
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"SKY130 PDK not found at {MODEL_PATH}\n"
            f"Install with: ./scripts/install_sky130.sh\n"
            f"Or set PDK_ROOT environment variable"
        )


# Placeholder - will be replaced with actual device loading
# nfet_01v8 = None
# pfet_01v8 = None
