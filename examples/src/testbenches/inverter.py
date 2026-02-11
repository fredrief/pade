"""SKY130 Inverter AC Testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V, C
from src.components.digital.schematic import IVX


class InverterACTB(Testbench):
    """Inverter biased at VDD/2 with AC stimulus for small-signal gain."""

    def __init__(self, vdd: float = 1.8, wn: float = 1, wp: float = 2, l: float = 0.15, cl: float = 100e-15):
        super().__init__()

        self.Vdd = V('Vdd', self, dc=vdd)
        self.Vdd.connect(['p', 'n'], ['vdd', '0'])

        self.Vin = V('Vin', self, dc=vdd / 2, ac=1)
        self.Vin.connect(['p', 'n'], ['inp', '0'])

        self.I0 = IVX('I0', self, wn=wn, wp=wp, l=l)
        self.I0.connect(['IN', 'OUT', 'VDD', 'VSS'], ['inp', 'out', 'vdd', '0'])

        self.CL = C('CL', self, c=cl)
        self.CL.connect(['p', 'n'], ['out', '0'])
