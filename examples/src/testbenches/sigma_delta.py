"""First-order sigma-delta modulator transient testbench."""

from pade.core.testbench import Testbench
from pade.stdlib import V
from src.components.behavioral.schematic import SigmaDelta1


class SigmaDeltaTranTB(Testbench):
    """Sigma-delta modulator driven by sine input with non-overlapping two-phase clocks.

    Args:
        dut_class: Cell class to instantiate as DUT (default: SigmaDelta1).
            Must have terminals: vin, out, outb, phi1, phi2, phi1_bar, phi2_bar,
            vref, vdd, vss, vint.
        vdd: Supply voltage.
        fin: Input sine frequency (Hz).
        ampl: Input sine amplitude (peak, around vdd/2).
        fs: Sampling clock frequency (Hz).
        cs, cf, caz: Capacitor values (F).
        gm, r: OTA transconductance and output resistance.
    """

    def __init__(self, dut_class=SigmaDelta1, vdd: float = 1.8, fin: float = 1e3,
                 ampl: float = 0.1, fs: float = 128e3,
                 cs: float = 1e-12, cf: float = 1e-12,
                 caz: float = 0.5e-12, gm: float = 1e-3, r: float = 1e6):
        super().__init__()

        vcm = vdd / 2
        T = 1 / fs
        tr = T / 100
        guard = T / 20
        pw = T / 2 - guard

        self.Vdd = V(dc=vdd)
        self.Vdd.connect(['p', 'n'], ['vdd', '0'])

        self.Vref = V(dc=vcm)
        self.Vref.connect(['p', 'n'], ['vref', '0'])

        self.Vin = V(dc=vdd / 2, type='sine', ampl=ampl, freq=fin)
        self.Vin.connect(['p', 'n'], ['vin', '0'])

        # Non-overlapping clocks
        self.Vphi1 = V(type='pulse', v1=0, v2=vdd, td=0, tr=tr, tf=tr, pw=pw, per=T)
        self.Vphi1.connect(['p', 'n'], ['phi1', '0'])

        self.Vphi2 = V(type='pulse', v1=0, v2=vdd, td=T / 2, tr=tr, tf=tr, pw=pw, per=T)
        self.Vphi2.connect(['p', 'n'], ['phi2', '0'])

        # Complementary clocks
        self.Vphi1b = V(type='pulse', v1=vdd, v2=0, td=0, tr=tr, tf=tr, pw=pw, per=T)
        self.Vphi1b.connect(['p', 'n'], ['phi1_bar', '0'])

        self.Vphi2b = V(type='pulse', v1=vdd, v2=0, td=T / 2, tr=tr, tf=tr, pw=pw, per=T)
        self.Vphi2b.connect(['p', 'n'], ['phi2_bar', '0'])

        # DUT
        self.DUT = dut_class(vdd=vdd, cs=cs, cf=cf, caz=caz, gm=gm, r=r)
        self.DUT.connect(
            ['vin', 'out', 'outb', 'phi1', 'phi2', 'phi1_bar', 'phi2_bar', 'vref', 'vdd', 'vss', 'vint'],
            ['vin', 'out', 'outb', 'phi1', 'phi2', 'phi1_bar', 'phi2_bar', 'vref', 'vdd', '0', 'vint'])
