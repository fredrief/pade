from pade.core.cell import Cell
from src.components.digital.schematic import IVX, TGX, NSALCMP
from pdk.sky130.primitives.capacitors.schematic import CapMim
from pade.stdlib import C, R, V

class Mod1(Cell):
    """
    Modulator 1.
    """
    def __init__(self, instance_name=None, parent=None, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, **kwargs)
        self.add_terminal(['vin', 'out', 'outb', 'phi1', 'phi2', 'phi1_bar', 'phi2_bar', 'vref', 'vdd', 'vss', 'vint'])

        # --- Capacitors ---
        w = 20
        l = 20

        self.Cs = CapMim(w=w, l=l, metal=4)
        self.Cs.connect(['TOP', 'BOT'], ['vg', 'A'])

        self.Cf = CapMim(w=w, l=l, metal=4)
        self.Cf.connect(['TOP', 'BOT'], ['C', 'vint'])

        self.Caz = CapMim(w=w, l=l, metal=4)
        self.Caz.connect(['TOP', 'BOT'], ['vx', 'vg'])

        self.IVAMP = IVX(wn=2.0, wp=10.0, l=0.6)
        self.IVAMP.connect(['IN', 'OUT', 'VDD', 'VSS'], ['vx', 'vint', 'vdd', 'vss'])

        # --- Phi1 switches (sampling) ---
        self.S1 = TGX()
        self.S1.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vin', 'A', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S2 = TGX()
        self.S2.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['B', 'A', 'phi2', 'phi2_bar', 'vdd', 'vss'])

        self.S3 = TGX()
        self.S3.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vg', 'vref', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S4 = TGX()
        self.S4.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vg', 'C', 'phi2', 'phi2_bar', 'vdd', 'vss'])

        self.S5 = TGX()
        self.S5.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vx', 'vint', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S6 = TGX()
        self.S6.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vss', 'B', 'outb', 'out', 'vdd', 'vss'])

        self.S7 = TGX()
        self.S7.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vdd', 'B', 'out', 'outb', 'vdd', 'vss'])

        # --- Comparator (sample phi2, compare phi1, latch full period) ---
        # Sample vint on phi2 before comparator
        self.S8 = TGX()
        self.S8.connect(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'], ['vint', 'vint_sampled', 'phi2', 'phi2_bar', 'vdd', 'vss'])
        self.Csc = CapMim(w=w, l=l, metal=4)
        self.Csc.connect(['TOP', 'BOT'], ['vint_sampled', 'vss'])

        self.COMP = NSALCMP()
        self.COMP.connect(['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'OP', 'ON'],
                          ['vdd', 'vss', 'phi1', 'vref', 'vint_sampled', 'out', 'outb'])
