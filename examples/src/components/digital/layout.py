"""Digital standard cell layouts."""

from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.primitives.transistors.layout import NFET_01V8_Layout, PFET_01V8_Layout
from pdk.sky130.layers import POLY, M1, M2, M3
from pade.core.cell import Cell


class IVXLayout(SKY130LayoutCell):
    """
    CMOS Inverter layout: NFET left, PFET right.

    Parameters:
        instance_name: Instance name
        schematic: IVX schematic
        parent: Optional parent layout cell
    """

    def __init__(self, instance_name=None, parent=None, schematic: Cell = None):
        super().__init__(instance_name, parent, cell_name='IVX',
                         schematic=schematic)
        self.MN = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN, tap='left')
        self.MP = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP, tap='right')
        self.MP.align('right', self.MN, margin=self.rules.NWELL.S_DIFF)
        self._route(schematic)

    def _route(self, schematic):
        nf = int(schematic.MN.get_parameter('nf'))
        gate_l = self.to_nm(float(schematic.MN.get_parameter('l')))

        # Gate poly: bridge active gates between transistors
        for i in range(nf):
            self.route(getattr(self.MN, f'G{i}'), getattr(self.MP, f'G{i}'),
                       POLY, how='-', width=gate_l, net='IN')
        # Dummy poly bridges (no net — geometric fill only)
        self.route(self.MN.DBOT, self.MP.DBOT, POLY, how='-', width=gate_l)
        self.route(self.MN.DTOP, self.MP.DTOP, POLY, how='-', width=gate_l)

        # Drain: straight M1
        MN_DPORT = self.MN.DBUS if nf > 2 else self.MN.D
        MP_DPORT = self.MP.DBUS if nf > 2 else self.MP.D
        self.route(MN_DPORT, MP_DPORT, M1, how='-', net='OUT')

        # Source to tap: straight M1
        self.route(self.MN.S, self.MN.B, M1, how='-', net='VSS')
        self.route(self.MP.S, self.MP.B, M1, how='-', net='VDD')


        # Pins
        self.add_pin('IN', self.MN.G0)
        self.add_pin('OUT', MN_DPORT)
        self.add_pin('VDD', self.MP.B)
        self.add_pin('VSS', self.MN.B)

class TGXLayout(SKY130LayoutCell):
    """
    Transmission Gate layout: NFET left, PFET right.
    Source and drain both carry signals (not power).

    Parameters:
        instance_name: Instance name
        schematic: TGX schematic
        parent: Optional parent layout cell
    """

    def __init__(self, instance_name=None, parent=None, schematic: Cell = None):
        super().__init__(instance_name, parent, cell_name='TGX',
                         schematic=schematic)
        self.MN = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN, tap='left')
        self.MP = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP, tap='right')
        self.MP.align('right', self.MN, margin=self.rules.NWELL.S_DIFF)
        self._route(schematic)

    def _route(self, schematic):
        nf = int(schematic.MN.get_parameter('nf'))

        # Drain: MN.D to MP.D (net A)
        MN_DPORT = self.MN.DBUS if nf > 2 else self.MN.D
        MP_DPORT = self.MP.DBUS if nf > 2 else self.MP.D
        self.route(MN_DPORT, MP_DPORT, M1, how='-', net='A')

        # Source: MN.S to MP.S (net B)
        self.route(self.MN.S, self.MP.S, M1, how='-', net='B')
        # Pins
        self.add_pin('EN', self.MN.G)
        self.add_pin('EN_N', self.MP.G)
        self.add_pin('A', MN_DPORT)
        self.add_pin('B', self.MP.S)
        self.add_pin('VDD', self.MP.B)
        self.add_pin('VSS', self.MN.B)

# ---------------------------------------------------------------------------
# Comparator subcircuits
# ---------------------------------------------------------------------------


class NSALLayout(SKY130LayoutCell):
    """Strong Arm latch core layout (flat, all nf=1).

    NFET column (left):  MN0, MN1A, MN1B, MN2A, MN2B
    PFET column (right): MP2A, MP2B, MP3A, MP3B, MP1A, MP1B
    Inverters above:     I0, I1
    """

    def __init__(self, instance_name=None, parent=None, schematic=None):
        super().__init__(instance_name, parent, cell_name='NSAL',
                         schematic=schematic)
        self.gate_l = self.to_nm(float(schematic.MN0A.get_parameter('l')))
        self.gate_w = self.to_nm(float(schematic.MN0A.get_parameter('w')))

        # --- Instantiate transistors ---
        self.MN0A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN0A)
        self.MN0B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN0B)
        self.MN1A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN1A)
        self.MN1B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN1B)
        self.MN2A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN2A)
        self.MN2B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN2B)

        self.MP2A = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP2A)
        self.MP2B = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP2B)
        self.MP3A = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP3A)
        self.MP3B = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP3B)
        self.MP1A = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP1A)
        self.MP1B = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP1B)

        self.I0 = IVXLayout.instantiate(self, schematic=schematic.I0)
        self.I1 = IVXLayout.instantiate(self, schematic=schematic.I1)

        # --- Placement ---
        nfets = [self.MN0A, self.MN0B, self.MN1A, self.MN1B, self.MN2A, self.MN2B]
        pfets = [self.MP2A, self.MP2B, self.MP3A, self.MP3B, self.MP1A, self.MP1B]

        self.stack_column(nfets)
        self.MP2A.align('right', self.MN0A, margin=self.rules.NWELL.S_DIFF)  # shift MP2A right
        self.stack_column(pfets)

        # Inverters above NFET column (dummy-poly overlap via anchor)
        self.I0.place(at=self.MN2B.DTOP, anchor=self.I0.MN.DBOT)
        self.I1.place(at=self.I0.MN.DTOP, anchor=self.I1.MN.DBOT)

        # --- Routing ---
        self._route()

    def _route(self):
        # -- Power: source to tap --
        self.route(self.MN0A.S, self.MN0A.B, M1, how='-', net='AVSS')
        self.route(self.MN0B.S, self.MN0B.B, M1, how='-', net='AVSS')
        for mp in [self.MP2A, self.MP2B, self.MP3A, self.MP3B, self.MP1A, self.MP1B]:
            self.route(mp.S, mp.B, M1, how='-', net='AVDD')

        # -- Gate bridges (POLY, same-row NFET-PFET pairs sharing gate) --
        # MN0 & MP2A share CLK gate
        self.route(self.MN0A.G, self.MP2A.G, POLY, how='-', width=self.gate_l, net='CLK')
        self.route(self.MN0A.G, self.MN0B.G, M2, how='|', net='CLK')
        # -- NFET intra-column vertical routes (M1) --
        # TAIL: MN0.D → MN1A.S, MN0.D → MN1B.S
        self.route(self.MN0A.D, self.MN1A.S, M2, how='|', net='TAIL')
        self.route(self.MN0B.D, self.MN1A.S, M2, how='|', net='TAIL')
        self.route(self.MN1A.S, self.MN1B.S, M1, how='|-', net='TAIL', track=1)
        # P: MN1A.D → MN2A.S
        self.route(self.MN1A.D, self.MN2A.S, M2, how='|', net='P')
        # Q: MN1B.D → MN2B.S
        self.route(self.MN1B.D, self.MN2B.S, M1, how='|-', net='Q', track=1)

        # -- PFET intra-column vertical routes (M1) --
        # CLK chain: MP2A.G → MP2B.G → MP3A.G → MP3B.G
        self.route(self.MP2A.G, self.MP2B.G, M2, how='|', net='CLK')
        self.route(self.MP2B.G, self.MP3A.G, M2, how='|', net='CLK')
        self.route(self.MP3A.G, self.MP3B.G, M2, how='|', net='CLK')

        # -- Cross-column routes (M2 with auto-via) --
        # P: MN2A.S → MP2A.D
        self.route(self.MN1A.D, self.MP2A.D, M2, how='|-', net='P', track=1)
        # Q: MN2B.S → MP2B.D
        self.route(self.MN1B.D, self.MP2B.D, M1, how='|-', net='Q', track=2)
        # X: MN2A.D → MP3A.D, MP1A.D
        self.route(self.MN2A.D, self.MP3A.D, M2, how='|-', net='X', track=2)
        self.route(self.MP3A.D, self.MP1A.D, M2, how='|', net='X')
        # Y: MN2B.D → MP3B.D, MP1B.D
        self.route(self.MN2B.D, self.MP3B.D, M1, how='|-', net='Y', track=3)
        self.route(self.MN2B.D, self.MP1B.D, M1, how='-', net='Y')

        # -- Latch cross-coupling gates (M2) --
        # MP1A.G=Y, MP1B.G=X — need cross routes
        self.route(self.MN2B.D, self.MP1A.G, M2, how='|-', net='Y', track_end=3, track=1)
        self.route(self.MN2A.D, self.MP1B.G, M1, how='|-', net='X', track=-1, track_end=3)

        # -- Inverter input routing --
        # I0.MN.G connected to X, I1.MN.G connected to Y
        self.route(self.MN2A.D, self.I0.MN.G, M2, how='|-', net='X', track=-1)
        self.route(self.MN2B.D, self.I1.MN.G, M2, how='|-', net='Y', track=1)

        self.route(self.MN2A.G, self.I1.MN.G, M2, how='|-', net='Y', track=-1)
        self.route(self.MN2B.G, self.I0.MN.G, M2, how='|', net='X')

        # -- Pins --
        self.add_pin('CLK', self.MN0A.G)
        self.add_pin('INP', self.MN1A.G)
        self.add_pin('INN', self.MN1B.G)
        self.add_pin('OUTP', self.I1.MP.D)
        self.add_pin('OUTN', self.I0.MP.D)
        self.add_pin('AVSS', self.MN0A.B)
        self.add_pin('AVDD', self.MP2A.B)

        # Check off power nets (connected via tap overlap, not explicit routes)
        self.check_off_net('AVDD')
        self.check_off_net('AVSS')


class NSALRSTLLayout(SKY130LayoutCell):
    """Reset latch layout.

    NFET column (left):  MN1A, MN2A, MN3A, MN1B, MN2B, MN3B
    PFET column (right): MP1A, MP1B
    """

    def __init__(self, instance_name=None, parent=None, schematic=None):
        super().__init__(instance_name, parent, cell_name='NSALRSTL',
                         schematic=schematic)
        gate_l = self.to_nm(float(schematic.MN1A.get_parameter('l')))

        # --- Instantiate ---
        self.MN1A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN1A, tap='left')
        self.MN2A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN2A, tap='left')
        self.MN3A = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN3A, tap='left')
        self.MN1B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN1B, tap='left')
        self.MN2B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN2B, tap='left')
        self.MN3B = NFET_01V8_Layout.instantiate(self, schematic=schematic.MN3B, tap='left')

        self.MP1A = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP1A, tap='right')
        self.MP1B = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP1B, tap='right')
        self.MP_DUMMY = PFET_01V8_Layout.instantiate(self, schematic=schematic.MP_DUMMY, tap='right')


        # --- Placement ---
        nfets = [self.MN1A, self.MN2A, self.MN3A, self.MN1B, self.MN2B, self.MN3B]
        pfets = [self.MP_DUMMY[0], *self.MP1A, *self.MP1B, self.MP_DUMMY[1]]

        self.stack_column(nfets)
        self.MP_DUMMY[0].align('right', self.MN1A, margin=self.rules.NWELL.S_DIFF)
        self.stack_column(pfets)

        # --- Routing ---
        self._route(gate_l)

    def _route(self, gate_l):
        # -- Power --
        self.route(self.MN1A.S, self.MN1A.B, M1, how='-', net='AVSS')
        self.route(self.MN3A.S, self.MN3A.B, M1, how='-', net='AVSS')
        self.route(self.MN1B.S, self.MN1B.B, M1, how='-', net='AVSS')
        self.route(self.MN3B.S, self.MN3B.B, M1, how='-', net='AVSS')
        for i in range(len(self.MP1A)):
            self.route(self.MP1A[i].S, self.MP1A[i].B, M1, how='-', net='AVDD')
        for i in range(len(self.MP1B)):
            self.route(self.MP1B[i].S, self.MP1B[i].B, M1, how='-', net='AVDD')

        # Connect all terminals together for multipliers
        self.route(self.MP1A[0].G, self.MP1A[1].G, M2, how='|', net='ON')
        self.route(self.MP1A[0].D, self.MP1A[1].D, M2, how='|', net='OP')
        self.route(self.MP1B[0].G, self.MP1B[1].G, M2, how='|', net='OP')
        self.route(self.MP1B[0].D, self.MP1B[1].D, M2, how='|', net='ON')

        # -- NFET intra-column --
        # NA: MN1A.D → MN2A.S
        self.route(self.MN1A.D, self.MN2A.S, M1, how='|', net='NA')
        # NB: MN1B.D → MN2B.S
        self.route(self.MN1B.D, self.MN2B.S, M1, how='|', net='NB')

        # CLK: MN2A.G → MN2B.G
        self.route(self.MN2A.G, self.MN2B.G, M2, how='|-', net='CLK', track=1.5)

        # -- Cross-column --
        # OP: MN2A.D → MP1A.D, MN3A.D
        self.route(self.MN2A.D, self.MN3A.D, M2, how='|', net='OP')
        self.route(self.MN2A.D, self.MP1A[0].D, M1, how='-', net='OP', width=(self.rules.M1.MIN_W + 2 * self.rules.VIA1.ENC_BOT_ADJ))
        # # ON: MN2B.D → MP1B.D, MN3B.D
        self.route(self.MN2B.D, self.MN3B.D, M1, how='|-', net='ON', track=1)
        self.route(self.MN2B.D, self.MP1B[0].D, M1, how='-', net='ON')

        # Cross-coupling gates
        # MN3A.G=ON, MN3B.G=OP
        self.route(self.MN2B.D, self.MN3A.G, M1, how='|-', net='ON', track=1)
        self.route(self.MN2A.D, self.MN3B.G, M2, how='|-', net='OP', track=1)
    #     # MP1A.G=ON, MP1B.G=OP
        self.route(self.MP1B[0].D, self.MP1A[1].G, M1, how='|-', net='ON', track=-1)
        self.route(self.MP1A[1].D, self.MP1B[0].G, M2, how='-|', net='OP', track_end=-1)

        # Dummy routes
        r = self.route(self.MP_DUMMY[0].S, self.MP_DUMMY[0].D, M1, how='|', net='AVDD')
        self.route(r[0], self.MP_DUMMY[0].B, M1, how='-', net='AVDD')

        r = self.route(self.MP_DUMMY[1].S, self.MP_DUMMY[1].D, M1, how='|', net='AVDD')
        self.route(r[0], self.MP_DUMMY[1].B, M1, how='-', net='AVDD')

        # -- Pins --
        self.add_pin('CLK', self.MN2A.G)
        self.add_pin('IN', self.MN1A.G)
        self.add_pin('IP', self.MN1B.G)
        self.add_pin('OP', self.MN2A.D)
        self.add_pin('ON', self.MN2B.D)
        self.add_pin('AVSS', self.MN1A[0].B)
        self.add_pin('AVDD', self.MP1A[0].B)
    # Check off power nets (connected via tap overlap, not explicit routes)
        self.check_off_net('AVDD')
        self.check_off_net('AVSS')


class NSALCMPLayout(SKY130LayoutCell):
    """Full comparator layout: SAL + RSTL stacked vertically."""

    def __init__(self, instance_name=None, parent=None, schematic=None):
        super().__init__(instance_name, parent, cell_name='NSALCMP',
                         schematic=schematic)

        self.SAL = NSALLayout.instantiate(self, schematic=schematic.SAL)
        self.RSTL = NSALRSTLLayout.instantiate(self, schematic=schematic.RSTL)
        self.RSTL.place(at=self.SAL.I1.MN.DTOP, anchor=self.RSTL.MN1A.DBOT)

        self._route()

    def _route(self):
        # SAL.OUTP → RSTL.IP (M3 with auto-via)
        self.route(self.SAL.OUTP, self.RSTL.IP, M3, how='|-', net='SAL_VOP')
        # SAL.OUTN → RSTL.IN (M2 with auto-via)
        self.route(self.SAL.OUTN, self.RSTL.IN, M3, how='-|', net='SAL_VON')
        # # CLK: SAL.CLK → RSTL.CLK (M3)
        self.route(self.SAL.CLK, self.RSTL.CLK, M3, how='|-', net='CLK', track=-1)

        # -- Pins --
        self.add_pin('INP', self.SAL.INP)
        self.add_pin('INN', self.SAL.INN)
        self.add_pin('CLK', self.SAL.CLK)
        self.add_pin('OP', self.RSTL.OP)
        self.add_pin('ON', self.RSTL.ON)
        self.add_pin('AVDD', self.SAL.AVDD)
        self.add_pin('AVSS', self.SAL.AVSS)

        # Check off power nets (connected via tap overlap, not explicit routes)
        self.check_off_net('AVDD')
        self.check_off_net('AVSS')
