"""SKY130 Inverter Testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V
from pdk.sky130 import Nfet01v8, Pfet01v8


class InverterSky130TB(Testbench):
    """SKY130 CMOS Inverter Testbench."""

    def __init__(self, vdd: float = 1.8, wn: float = 1, wp: float = 2, l: float = 0.15):
        super().__init__('tb_inverter_sky130')

        self.Vdd = V('Vdd', self, dc=vdd)
        self.Vdd.connect(['p', 'n'], ['vdd', '0'])

        self.Vin = V('Vin', self, type='pulse', v1=0, v2=vdd,
                     td='1n', tr='100p', tf='100p', pw='5n', per='10n')
        self.Vin.connect(['p', 'n'], ['inp', '0'])

        self.MP = Pfet01v8('MP', self, w=wp, l=l)
        self.MP.connect(['d', 'g', 's', 'b'], ['out', 'inp', 'vdd', 'vdd'])

        self.MN = Nfet01v8('MN', self, w=wn, l=l)
        self.MN.connect(['d', 'g', 's', 'b'], ['out', 'inp', '0', '0'])
