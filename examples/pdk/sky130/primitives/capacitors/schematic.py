"""SKY130 capacitor schematic primitives."""

from pathlib import Path
from pade.backends.ngspice.netlist_reader import load_subckt
from pdk.sky130.pex import pex_enabled

_DEVICE_DIR = Path(__file__).parent

CapMimM4 = pex_enabled(load_subckt(_DEVICE_DIR / 'cap_mim_m4.spice'))
