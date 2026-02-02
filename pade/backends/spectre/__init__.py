"""
Spectre backend for PADE.
"""

from pade.backends.spectre.netlist_reader import (
    load_subckt,
    NetlistCell,
    SpectreNetlistReader,
)
from pade.backends.spectre.netlist_writer import SpectreNetlistWriter
from pade.backends.spectre.simulator import SpectreSimulator

__all__ = [
    # Primary API
    'load_subckt',
    'NetlistCell',
    # Classes
    'SpectreNetlistReader',
    'SpectreNetlistWriter',
    'SpectreSimulator',
]
