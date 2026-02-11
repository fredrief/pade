"""SKY130 layer definitions for layout."""

import os
from pade.layout.shape import Layer
from pade.utils.layermap import create_layermap_from_pdk

PDK_ROOT = os.environ.get('PDK_ROOT', os.path.expanduser('~/.ciel'))

# Auto-generate layer map from PDK
sky130_layers = create_layermap_from_pdk(f'{PDK_ROOT}/sky130A')

# Convenience layer constants (shorter names for common layers)
# connectivity=True marks layers that carry electrical connectivity.

# Metals
M1 = Layer('MET1', 'drawing', connectivity=True)
M2 = Layer('MET2', 'drawing', connectivity=True)
M3 = Layer('MET3', 'drawing', connectivity=True)
M4 = Layer('MET4', 'drawing', connectivity=True)
M5 = Layer('MET5', 'drawing', connectivity=True)

# Vias
VIA1 = Layer('VIA', 'drawing', connectivity=True)
VIA2 = Layer('VIA2', 'drawing', connectivity=True)
VIA3 = Layer('VIA3', 'drawing', connectivity=True)
VIA4 = Layer('VIA4', 'drawing', connectivity=True)

# Device layers
POLY = Layer('POLY', 'drawing', connectivity=True)
DIFF = Layer('DIFF', 'drawing', connectivity=True)
TAP = Layer('TAP', 'drawing', connectivity=True)
NWELL = Layer('NWELL', 'drawing')
PWELL = Layer('PWELL', 'drawing')

# Implant layers
NSDM = Layer('NSDM', 'drawing')
PSDM = Layer('PSDM', 'drawing')

# Local interconnect
LI = Layer('LI1', 'drawing', connectivity=True)
LICON = Layer('LICON1', 'drawing', connectivity=True)
MCON = Layer('MCON', 'drawing', connectivity=True)
NPC = Layer('NPC', 'drawing')

# Capacitor layers
CAPM = Layer('CAPM', 'drawing')
CAPM2 = Layer('CAPM2', 'drawing')
