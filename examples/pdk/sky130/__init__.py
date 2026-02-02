"""
SKY130 PDK device wrappers.

Requires SKY130 PDK installed via ciel:
    pip install ciel
    ciel enable --pdk-family=sky130 <version>

Environment variables:
    PDK_ROOT: Path to PDK installation (default: ~/.ciel)
    PDK: PDK variant (default: sky130A)

Usage:
    import sys
    sys.path.insert(0, './examples')

    from pdk.sky130 import nfet_01v8, pfet_01v8

    mn = nfet_01v8('MN', parent=tb, w='1u', l='150n')
    mp = pfet_01v8('MP', parent=tb, w='2u', l='150n')
"""

# Devices will be loaded after PDK installation is verified
# from examples.pdk.sky130.devices import nfet_01v8, pfet_01v8

__all__ = [
    # Will export device classes after implementation
]
