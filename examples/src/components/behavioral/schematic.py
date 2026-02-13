"""Behavioral schematic components (B-source based)."""

from pade.core.cell import Cell
from pade.stdlib import B, C, R, V


class IdealComparator(Cell):
    """Clocked comparator: sample on phi2, compare on phi1, latch full period.

    1. During phi2: S&H tracks inp onto C_sample.
    2. phi2 falls: C_sample holds the sampled value.
    3. phi1 rises: internal tanh comparator settles; latch switches
       charge internal latch caps.
    4. phi1 falls: latch caps hold; output buffers drive out/outb.
    """

    def __init__(self, instance_name=None, parent=None, vdd: float = 1.8, k: float = 10000,
                 c_sample: float = 100e-15, c_latch: float = 1e-12, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='ideal_comparator', **kwargs)
        self.add_terminal(['inp', 'inn', 'out', 'outb', 'clk', 'vdd', 'vss'])

        vth = vdd / 2

        # --- Internal comparison (continuous on held value) ---
        self.B1 = B(expr=f'{vdd/2}*(1+tanh({k}*V(inp,inn)))', type='V')
        self.B1.connect(['p', 'n'], ['comp_int', 'vss'])
        self.B2 = B(expr=f'{vdd/2}*(1-tanh({k}*V(inp,inn)))', type='V')
        self.B2.connect(['p', 'n'], ['comp_intb', 'vss'])

        self.S_latch_p = IdealSwitch(vth=vth, roff=1e12)
        self.S_latch_p.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'],
                               ['comp_int', 'latch_p', 'clk', 'vss', 'vdd', 'vss'])
        self.C_latch_p = C(c=c_latch)
        self.C_latch_p.connect(['p', 'n'], ['latch_p', 'vss'])

        self.S_latch_n = IdealSwitch(vth=vth, roff=1e12)
        self.S_latch_n.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'],
                               ['comp_intb', 'latch_n', 'clk', 'vss', 'vdd', 'vss'])
        self.C_latch_n = C(c=c_latch)
        self.C_latch_n.connect(['p', 'n'], ['latch_n', 'vss'])

        # --- Output buffers (isolate latch caps from external load) ---
        self.B_buf_p = B(expr='V(latch_p,vss)', type='V')
        self.B_buf_p.connect(['p', 'n'], ['out', 'vss'])
        self.B_buf_n = B(expr='V(latch_n,vss)', type='V')
        self.B_buf_n.connect(['p', 'n'], ['outb', 'vss'])


class Ota(Cell):
    """Single-ended OTA with inverter-compatible interface (negative gain).
    Terminals: in, out, vdd, vss — same as CMOS inverter for drop-in replacement.
    Internally derives Vcm = vdd/2. Iout = -Gm * V(in, vcm). DC gain = -Gm * R.
    Negative gain mimics CMOS inverter: Vin up -> Vout down.
    """

    def __init__(self, instance_name=None, parent=None, gm: float = 1e-3, r: float = 1e6,
                 vdd: float = 1.8, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='ota', **kwargs)
        self.add_terminal(['in', 'out', 'vdd', 'vss'])

        vcm = vdd / 2
        self.Vref = V(dc=vcm)
        self.Vref.connect(['p', 'n'], ['vcm_int', 'vss'])
        self.B1 = B(expr=f'-{gm}*V(in,vcm_int)', type='I')
        self.B1.connect(['p', 'n'], ['out', 'vcm_int'])
        self.R1 = R(r=r)
        self.R1.connect(['p', 'n'], ['out', 'vcm_int'])


class IdealSwitch(Cell):
    """Voltage-controlled switch. On when V(ctrl,vss) > vth.
    Uses smooth tanh transition for convergence (no hard discontinuity).
    Includes ctrl_bar to get same interface as transmission gate.
    """

    def __init__(self, instance_name=None, parent=None, ron: float = 100, roff: float = 1e8,
                 vth: float = 0.9, k: float = 20, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='ideal_switch', **kwargs)
        self.add_terminal(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'])

        gon = 1 / ron
        goff = 1 / roff
        expr = f'V(a,b)*({goff}+({gon}-{goff})*(1+tanh({k}*(V(ctrl,vss)-{vth})))/2)'
        self.B1 = B(expr=expr, type='I')
        self.B1.connect(['p', 'n'], ['a', 'b'])


class SigmaDelta1(Cell):
    """First-order SC delta-sigma modulator with auto-zeroing.

    Single-ended, inverter-based topology (Chae & Han, JSSC 2009).
    Behavioral model using ideal OTA, switches, and comparator.

    Phi1 (sampling):
        S1: sample Vin onto Cs bottom plate
        S3: connect Cs top plate to Vref

    Phi2 (charge transfer + auto-zero):
        S2: connect DAC output to Cs bottom plate
        S4: connect Cs top plate to Cf
        S5: OTA unity-gain feedback (auto-zero)

    DAC (comparator-controlled):
        S6: connect Vss to DAC node when out high
        S7: connect Vdd to DAC node when outb high
    """

    def __init__(self, instance_name=None, parent=None, vdd: float = 1.8,
                 cs: float = 1e-12, cf: float = 2e-12, caz: float = 0.5e-12,
                 gm: float = 1e-3, r: float = 1e6, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='sigma_delta_1', **kwargs)
        self.add_terminal(['vin', 'out', 'outb', 'phi1', 'phi2', 'phi1_bar', 'phi2_bar', 'vref', 'vdd', 'vss', 'vint'])

        vth = vdd / 2

        # --- Capacitors ---

        self.Cs = C(c=cs)
        self.Cs.connect(['p', 'n'], ['vg', 'A'])

        self.Cf = C(c=cf)
        self.Cf.connect(['p', 'n'], ['C', 'vint'])

        self.Caz = C(c=caz)
        self.Caz.connect(['p', 'n'], ['vx', 'vg'])

        # --- OTA (inverter interface, supply-clamped) ---
        self.OTA = Ota(gm=gm, r=r, vdd=vdd)
        self.OTA.connect(['in', 'out', 'vdd', 'vss'], ['vx', 'vint', 'vdd', 'vss'])

        # --- Phi1 switches (sampling) ---
        self.S1 = IdealSwitch(vth=vth)
        self.S1.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vin', 'A', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S2 = IdealSwitch(vth=vth)
        self.S2.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['B', 'A', 'phi2', 'phi2_bar', 'vdd', 'vss'])

        self.S3 = IdealSwitch(vth=vth)
        self.S3.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vg', 'vref', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S4 = IdealSwitch(vth=vth)
        self.S4.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vg', 'C', 'phi2', 'phi2_bar', 'vdd', 'vss'])

        self.S5 = IdealSwitch(vth=vth)
        self.S5.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vx', 'vint', 'phi1', 'phi1_bar', 'vdd', 'vss'])

        self.S6 = IdealSwitch(vth=vth)
        self.S6.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vss', 'B', 'outb', 'out', 'vdd', 'vss'])

        self.S7 = IdealSwitch(vth=vth)
        self.S7.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vdd', 'B', 'out', 'outb', 'vdd', 'vss'])


        # --- Comparator (sample phi2, compare phi1, latch full period) ---
        # Sample vint on phi2 before comparator
        self.S8 = IdealSwitch(vth=vth)
        self.S8.connect(['a', 'b', 'ctrl', 'ctrl_bar', 'vdd', 'vss'], ['vint', 'vint_sampled', 'phi2', 'phi2_bar', 'vdd', 'vss'])
        self.Csc = C(c=100e-15)
        self.Csc.connect(['p', 'n'], ['vint_sampled', 'vss'])

        self.COMP = IdealComparator(vdd=vdd)
        self.COMP.connect(['inp', 'inn', 'out', 'outb', 'clk', 'vdd', 'vss'],
                          ['vint_sampled', 'vref', 'out', 'outb', 'phi1', 'vdd', 'vss'])
