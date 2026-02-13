"""Capacitor AC testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V
from pdk.sky130.primitives.capacitors.schematic import CapMim


class CapacitorAC(Testbench):
    """AC impedance measurement testbench for MiM capacitor."""

    def __init__(self, w=10, l=10, metal=4, **kwargs):
        super().__init__(**kwargs)

        self.Vac = V(dc=0, ac=1, **kwargs)
        self.Vac.connect(['p', 'n'], ['inp', '0'])

        self.C1 = CapMim(w=w, l=l, metal=metal, **kwargs)
        self.C1.connect(['TOP', 'BOT'], ['inp', '0'])
