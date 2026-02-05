"""SKY130 layer definitions for layout."""

import os
from pade.layout.shape import Layer
from pade.utils.layermap import create_layermap_from_pdk

PDK_ROOT = os.environ.get('PDK_ROOT', os.path.expanduser('~/.ciel'))

# Auto-generate layer map from PDK
sky130_layers = create_layermap_from_pdk(f'{PDK_ROOT}/sky130A')

# Convenience layer constants (shorter names for common layers)
M1 = Layer('MET1', 'drawing')
M2 = Layer('MET2', 'drawing')
M3 = Layer('MET3', 'drawing')
M4 = Layer('MET4', 'drawing')
M5 = Layer('MET5', 'drawing')

VIA1 = Layer('VIA', 'drawing')
VIA2 = Layer('VIA2', 'drawing')
VIA3 = Layer('VIA3', 'drawing')
VIA4 = Layer('VIA4', 'drawing')

POLY = Layer('POLY', 'drawing')
DIFF = Layer('DIFF', 'drawing')
NWELL = Layer('NWELL', 'drawing')
LI = Layer('LI1', 'drawing')
LICON = Layer('LICON1', 'drawing')
MCON = Layer('MCON', 'drawing')

CAPM = Layer('CAPM', 'drawing')
CAPM2 = Layer('CAPM2', 'drawing')
