"""SKY130 Strong Arm Comparator Transient Testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V, C
from src.components.digital.schematic import NSALCMP


class ComparatorTranTB(Testbench):
    """NSALCMP with CLK pulse and differential DC input.

    Args:
        vdd: Supply voltage
        vcm: Input common-mode voltage
        vdiff: Differential input voltage (INP - INN)
        fclk: Clock frequency
        cl: Output load capacitance
    """

    def __init__(self, vdd: float = 1.8, vcm: float = 0.9,
                 vdiff: float = 10e-3, fclk: float = 1e9, cl: float = 50e-15):
        super().__init__()

        period = 1.0 / fclk

        # Supply
        self.Vdd = V('Vdd', self, dc=vdd)
        self.Vdd.connect(['p', 'n'], ['vdd', '0'])

        # Clock (pulse: low=0, high=VDD, 50% duty)
        self.Vclk = V('Vclk', self,
                       type='pulse', v1=0, v2=vdd,
                       td=0, tr=50e-12, tf=50e-12,
                       pw=period / 2, per=period)
        self.Vclk.connect(['p', 'n'], ['clk', '0'])

        # Differential input
        self.Vinp = V('Vinp', self, dc=vcm + vdiff / 2)
        self.Vinp.connect(['p', 'n'], ['inp', '0'])

        self.Vinn = V('Vinn', self, dc=vcm - vdiff / 2)
        self.Vinn.connect(['p', 'n'], ['inn', '0'])

        # DUT
        self.DUT = NSALCMP('DUT', self)
        self.DUT.connect(
            ['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'OP', 'ON'],
            ['vdd', '0', 'clk', 'inp', 'inn', 'outp', 'outn'])

        # Load caps
        self.CLP = C('CLP', self, c=cl)
        self.CLP.connect(['p', 'n'], ['outp', '0'])

        self.CLN = C('CLN', self, c=cl)
        self.CLN.connect(['p', 'n'], ['outn', '0'])
