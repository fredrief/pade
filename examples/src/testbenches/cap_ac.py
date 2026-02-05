"""Capacitor AC testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V
from pdk.sky130.primitives.capacitors.schematic import CapMimM4


class CapacitorAC(Testbench):
    """AC impedance measurement testbench for MiM capacitor."""

    def __init__(self, w=10, l=10, **kwargs):
        super().__init__(**kwargs)

        self.Vac = V('Vac', self, dc=0, ac=1, **kwargs)
        self.Vac.connect(['p', 'n'], ['inp', '0'])

        self.C1 = CapMimM4('C1', self, w=w, l=l, **kwargs)
        self.C1.connect(['PLUS', 'MINUS'], ['inp', '0'])
