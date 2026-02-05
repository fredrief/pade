"""SKY130 transistor schematic primitives."""

from pathlib import Path
from pade.backends.ngspice.netlist_reader import load_subckt

_DEVICE_DIR = Path(__file__).parent

Nfet01v8 = load_subckt(_DEVICE_DIR / 'nfet_01v8.spice')
Pfet01v8 = load_subckt(_DEVICE_DIR / 'pfet_01v8.spice')
