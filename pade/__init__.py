"""
PADE - Python-based Analog Design Environment

A framework for programmatic analog circuit design, simulation, and analysis.
"""

__version__ = '1.0.0-dev'

from pade.logging import set_log_level

from pade.core import (
    Cell,
    Testbench,
    Terminal,
    Net,
    Parameter,
)

from pade.stdlib import R, C, L, V, I

from pade.statement import (
    Statement,
    Analysis,
    Options,
    Save,
    Include,
    IC,
)

from pade.utils import run_parallel

__all__ = [
    '__version__',
    'set_log_level',
    # Core
    'Cell',
    'Testbench',
    'Terminal',
    'Net',
    'Parameter',
    # Stdlib
    'R', 'C', 'L', 'V', 'I',
    # Statements
    'Statement',
    'Analysis',
    'Options',
    'Save',
    'Include',
    'IC',
    # Utils
    'run_parallel',
]
