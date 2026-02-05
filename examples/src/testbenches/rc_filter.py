"""
RC lowpass filter testbench.
"""

from pade.core.testbench import Testbench
from pade.stdlib import V, R, C


class RCTestbench(Testbench):
    """
    Parametrizable RC lowpass filter testbench.

    Args:
        r: Resistance in ohms (default: 1k)
        c: Capacitance in farads (default: 1u)
        freq: Sine source frequency in Hz (default: 1M)
        ampl: Sine source amplitude in V (default: 1.0)
    """

    def __init__(self, r: float = 1e3, c: float = 1e-6, freq: float = 1e6, ampl: float = 1.0):
        super().__init__('tb_rc')

        # Sine voltage source
        self.add_cell(V, 'V1', type='sine', sinedc=0, ampl=ampl, freq=freq)
        self.V1.connect(['p', 'n'], ['in', '0'])

        # Resistor
        self.add_cell(R, 'R1', r=r)
        self.R1.connect(['p', 'n'], ['in', 'out'])

        # Capacitor
        self.add_cell(C, 'C1', c=c)
        self.C1.connect(['p', 'n'], ['out', '0'])
