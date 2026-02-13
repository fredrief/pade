from pade.core.cell import Cell
from pdk.sky130.primitives.transistors.schematic import Nfet01v8, Pfet01v8


# ---------------------------------------------------------------------------
# Basic gates
# ---------------------------------------------------------------------------


class IVX(Cell):
    """
    CMOS Inverter.

    Parameters:
        instance_name: Instance name
        parent: Parent cell
        wn: NFET width in um
        wp: PFET width in um
        l: Gate length in um
        nf: Number of fingers
    """

    def __init__(self, instance_name=None, parent=None, wn: float = 1.0, wp: float = 2.0,
                 l: float = 0.15, nf: int = 1, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='inverter', **kwargs)
        self.add_terminal(['IN', 'OUT', 'VDD', 'VSS'])

        self.set_parameter('wn', wn)
        self.set_parameter('wp', wp)
        self.set_parameter('l', l)
        self.set_parameter('nf', nf)

        self.MP = Pfet01v8(w=wp, l=l, nf=nf)
        self.MP.connect(['d', 'g', 's', 'b'], ['OUT', 'IN', 'VDD', 'VDD'])

        self.MN = Nfet01v8(w=wn, l=l, nf=nf)
        self.MN.connect(['d', 'g', 's', 'b'], ['OUT', 'IN', 'VSS', 'VSS'])


class TGX(Cell):
    """
    Transmission Gate.

    Parameters:
        instance_name: Instance name
        parent: Parent cell
        wn: NFET width in um
        wp: PFET width in um
        l: Gate length in um
        nf: Number of fingers
    """

    def __init__(self, instance_name=None, parent=None, wn: float = 1.0, wp: float = 2.0,
                 l: float = 0.15, nf: int = 1, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='tgate', **kwargs)
        self.add_terminal(['A', 'B', 'EN', 'EN_N', 'VDD', 'VSS'])

        self.set_parameter('wn', wn)
        self.set_parameter('wp', wp)
        self.set_parameter('l', l)
        self.set_parameter('nf', nf)

        self.MN = Nfet01v8(w=wn, l=l, nf=nf)
        self.MN.connect(['d', 'g', 's', 'b'], ['A', 'EN', 'B', 'VSS'])

        self.MP = Pfet01v8(w=wp, l=l, nf=nf)
        self.MP.connect(['d', 'g', 's', 'b'], ['A', 'EN_N', 'B', 'VDD'])


# ---------------------------------------------------------------------------
# Comparator subcircuits
# ---------------------------------------------------------------------------


class NSAL(Cell):
    """N-type Strong Arm latch (flat structure, single diff-pair).

    All transistors use the same L and nf=1.  Wp = 2*Wn.

    Terminals: AVDD, AVSS, CLK, INP, INN, OUTP, OUTN
    """

    def __init__(self, instance_name=None, parent=None, wn: float = 1.0, l: float = 0.15, **kwargs):
        wp = 2 * wn
        super().__init__(instance_name=instance_name, parent=parent, cell_name='NSAL', **kwargs)
        self.add_terminal(['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'OUTP', 'OUTN'])

        # Tail switch
        self.MN0A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN0A.connect(['d', 'g', 's', 'b'], ['TAIL', 'CLK', 'AVSS', 'AVSS'])
        self.MN0B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN0B.connect(['d', 'g', 's', 'b'], ['TAIL', 'CLK', 'AVSS', 'AVSS'])

        # Input diff pair
        self.MN1A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN1A.connect(['d', 'g', 's', 'b'], ['P', 'INP', 'TAIL', 'AVSS'])

        self.MN1B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN1B.connect(['d', 'g', 's', 'b'], ['Q', 'INN', 'TAIL', 'AVSS'])

        # NMOS latch
        self.MN2A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN2A.connect(['d', 'g', 's', 'b'], ['X', 'Y', 'P', 'AVSS'])

        self.MN2B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN2B.connect(['d', 'g', 's', 'b'], ['Y', 'X', 'Q', 'AVSS'])

        # PMOS latch
        self.MP1A = Pfet01v8(w=wp, l=l, nf=1)
        self.MP1A.connect(['d', 'g', 's', 'b'], ['X', 'Y', 'AVDD', 'AVDD'])

        self.MP1B = Pfet01v8(w=wp, l=l, nf=1)
        self.MP1B.connect(['d', 'g', 's', 'b'], ['Y', 'X', 'AVDD', 'AVDD'])

        # PMOS precharge
        self.MP2A = Pfet01v8(w=wp, l=l, nf=1)
        self.MP2A.connect(['d', 'g', 's', 'b'], ['P', 'CLK', 'AVDD', 'AVDD'])

        self.MP2B = Pfet01v8(w=wp, l=l, nf=1)
        self.MP2B.connect(['d', 'g', 's', 'b'], ['Q', 'CLK', 'AVDD', 'AVDD'])

        # PMOS reset
        self.MP3A = Pfet01v8(w=wp, l=l, nf=1)
        self.MP3A.connect(['d', 'g', 's', 'b'], ['X', 'CLK', 'AVDD', 'AVDD'])

        self.MP3B = Pfet01v8(w=wp, l=l, nf=1)
        self.MP3B.connect(['d', 'g', 's', 'b'], ['Y', 'CLK', 'AVDD', 'AVDD'])

        # Output inverters
        self.I0 = IVX(wn=wn, wp=wp, l=l)
        self.I0.connect(['IN', 'OUT', 'VDD', 'VSS'], ['X', 'OUTN', 'AVDD', 'AVSS'])

        self.I1 = IVX(wn=wn, wp=wp, l=l)
        self.I1.connect(['IN', 'OUT', 'VDD', 'VSS'], ['Y', 'OUTP', 'AVDD', 'AVSS'])


class NSALRSTL(Cell):
    """Reset latch for N-type Strong Arm latch.

    SR latch with CLK-gated pass transistors for clean rail-to-rail output.
    All transistors use the same L and nf=1.  Wp = 2*Wn.

    Terminals: AVDD, AVSS, CLK, IP, IN, OP, ON
    """

    def __init__(self, instance_name=None, parent=None, wn: float = 1.0, l: float = 0.15, **kwargs):
        wp = 2 * wn
        super().__init__(instance_name=instance_name, parent=parent, cell_name='NSALRSTL', **kwargs)
        self.add_terminal(['AVDD', 'AVSS', 'CLK', 'IP', 'IN', 'OP', 'ON'])

        # A-side: IN → gated pass → latch
        self.MN1A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN1A.connect(['d', 'g', 's', 'b'], ['NA', 'IN', 'AVSS', 'AVSS'])

        self.MN2A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN2A.connect(['d', 'g', 's', 'b'], ['OP', 'CLK', 'NA', 'AVSS'])

        self.MN3A = Nfet01v8(w=wn, l=l, nf=1)
        self.MN3A.connect(['d', 'g', 's', 'b'], ['OP', 'ON', 'AVSS', 'AVSS'])

        # B-side: IP → gated pass → latch
        self.MN1B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN1B.connect(['d', 'g', 's', 'b'], ['NB', 'IP', 'AVSS', 'AVSS'])

        self.MN2B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN2B.connect(['d', 'g', 's', 'b'], ['ON', 'CLK', 'NB', 'AVSS'])

        self.MN3B = Nfet01v8(w=wn, l=l, nf=1)
        self.MN3B.connect(['d', 'g', 's', 'b'], ['ON', 'OP', 'AVSS', 'AVSS'])

        # PMOS cross-coupled pull-ups
        self.MP1A = Pfet01v8(w=wp, l=l, nf=1)
        self.MP1A.connect(['d', 'g', 's', 'b'], ['OP', 'ON', 'AVDD', 'AVDD'])
        self.MP1A.set_multiplier(2)

        self.MP1B = Pfet01v8(w=wp, l=l, nf=1)
        self.MP1B.connect(['d', 'g', 's', 'b'], ['ON', 'OP', 'AVDD', 'AVDD'])
        self.MP1B.set_multiplier(2)

        # Dummy transistors
        self.MP_DUMMY = Pfet01v8(w=wp, l=l, nf=1)
        self.MP_DUMMY.connect(['d', 'g', 's', 'b'], ['AVDD', 'AVDD', 'AVDD', 'AVDD'])
        self.MP_DUMMY.set_multiplier(2)



class NSALCMP(Cell):
    """N-type Strong Arm comparator with reset latch.

    Terminals: AVDD, AVSS, CLK, INP, INN, OP, ON
    """

    def __init__(self, instance_name=None, parent=None, wn: float = 1.0, l: float = 0.15, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, cell_name='NSALCMP', **kwargs)
        self.add_terminal(['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'OP', 'ON'])

        self.SAL = NSAL(wn=wn, l=l)
        self.SAL.connect(
            ['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'OUTP', 'OUTN'],
            ['AVDD', 'AVSS', 'CLK', 'INP', 'INN', 'SAL_VOP', 'SAL_VON'])

        self.RSTL = NSALRSTL(wn=wn, l=l)
        self.RSTL.connect(
            ['AVDD', 'AVSS', 'CLK', 'IP', 'IN', 'OP', 'ON'],
            ['AVDD', 'AVSS', 'CLK', 'SAL_VOP', 'SAL_VON', 'OP', 'ON'])
