"""Mod1 layout skeleton."""

import sys
from pathlib import Path
_examples = Path(__file__).resolve().parents[3]
if str(_examples) not in sys.path:
    sys.path.insert(0, str(_examples.parent))
    sys.path.insert(0, str(_examples))

from pade.core.cell import Cell
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import M1, M2, M3, M4, M5
from pdk.sky130.primitives.capacitors.layout import CapMimLayout
from src.components.digital.layout import IVXLayout, TGXLayout, NSALCMPLayout


class Mod1Layout(SKY130LayoutCell):
    """
    Mod1 modulator layout: COMP, IVAMP, capacitors, switches.
    Skeleton: subcells instantiated and placed; routing and pins TODO.
    """

    def __init__(self, instance_name=None, parent=None, schematic: Cell = None):
        super().__init__(instance_name, parent, cell_name='Mod1', schematic=schematic)

        m1 = self.to_nm(1.0)
        m2 = self.to_nm(4.0)

        self.COMP = NSALCMPLayout.instantiate(self, schematic=schematic.COMP)
        self.IVAMP = IVXLayout.instantiate(self, schematic=schematic.IVAMP)
        self.Cs = CapMimLayout.instantiate(self, schematic=schematic.Cs)
        self.Cf = CapMimLayout.instantiate(self, schematic=schematic.Cf)
        self.Caz = CapMimLayout.instantiate(self, schematic=schematic.Caz)
        self.Csc = CapMimLayout.instantiate(self, schematic=schematic.Csc)
        self.S1 = TGXLayout.instantiate(self, schematic=schematic.S1)
        self.S2 = TGXLayout.instantiate(self, schematic=schematic.S2)
        self.S3 = TGXLayout.instantiate(self, schematic=schematic.S3)
        self.S4 = TGXLayout.instantiate(self, schematic=schematic.S4)
        self.S5 = TGXLayout.instantiate(self, schematic=schematic.S5)
        self.S6 = TGXLayout.instantiate(self, schematic=schematic.S6)
        self.S7 = TGXLayout.instantiate(self, schematic=schematic.S7)
        self.S8 = TGXLayout.instantiate(self, schematic=schematic.S8)

        self.Cs.align('right', self.COMP, margin=2*m2)
        self.Cf.align('right', self.Cs, margin=2*m2)
        self.Caz.align('above', self.Cs, margin=2*m2, match=True)
        self.Csc.align('right', self.Caz, margin=2*m2, match=True)

        self.S1.place(at=self.COMP.RSTL.MN3B.DTOP, anchor=self.S1.MN.DBOT)
        tgxs = [self.S1, self.S2, self.S3, self.S4, self.S5, self.S6, self.S7, self.S8]

        self.IVAMP.align('below', self.COMP, margin=m2)

        self.stack_column(tgxs)

        self._route()

    def _route(self):
        m2 = self.to_nm(4.0)


        # Per-cap: route from TOP.north straight up by m2; save endpoint
        def cap_top_route(cap, net):
            return self.route(cap.TOP.north, cap.TOP.north + (0, 1.2*m2), M5, how='|', net=net).end

        self.Cs_top = cap_top_route(self.Cs, 'vg')
        self.Cf_top = cap_top_route(self.Cf, 'C')
        self.Caz_top = cap_top_route(self.Caz, 'vx')
        self.Csc_top = cap_top_route(self.Csc, 'vint_sampled')

        # Power (M4): vdd, vss
        self.route(self.COMP.AVDD, self.IVAMP.VDD, M1, how='|-', net='vdd', track_end=1)
        self.route(self.COMP.AVSS, self.IVAMP.VSS, M1, how='|', net='vss')

        self.route(self.S7.MP.D, self.S8.VDD.north, M2, how='-|', track=7, via_ny_end=2, via_nx_end=1, net='vdd')
        self.route(self.S6.A, self.S8.VSS.north, M3, how='|-', via_ny_end=2, via_nx_end=1, track=1, net='vss')

        # Internal nets (M4 for TGX-related)
        self.route(self.Cs.BOT, self.S1.B, (M3, M4), how='|-', net='A', track=-7)
        self.route(self.S1.MN.S, self.S2.MN.S, M1, how='|-', net='A', track=-1)
        self.route(self.S2.MN.D, self.S6.MN.S, M2, how='|-', net='B', track=2)
        self.route(self.S6.MN.S, self.S7.MN.S, M1, how='|-', net='B', track=-1)

        self.route(self.Cf_top, self.S4.B, (M4, M3), how='-|', net='C', track_end=6, track=-3)

        self.route(self.Cs_top, self.Caz.BOT, M4, how='|-', net='vg')

        self.route(self.Caz.BOT, self.S3.MP.D, M4, how='|-', net='vg')

        self.route(self.S3.MN.D, self.S4.MN.D, M1, how='|-', net='vg', track=-1)

        self.route(self.IVAMP.MP.G, self.Caz_top, (M3, M4), how='|-', net='vx', track = -2)

        self.route(self.IVAMP.IN, self.S5.MN.D, (M3, M4), how='|-', net='vx', track=-2)

        self.route(self.IVAMP.OUT, self.Cf.BOT, M4, how='-|', net='vint', track=2)

        self.route(self.Cf.BOT, self.S5.MP.S, (M3, M4), how='|-', net='vint', track=4, track_end=17)
        self.route(self.S5.MP.S, self.S8.MP.D, M1, how='|-', net='vint', track=1)

        self.route(self.Csc_top, self.COMP.INN, (M4, M3), how='-|', net='vint_sampled', track_end=-3, track=-3)

        r = self.route(self.Csc.BOT, self.IVAMP.VSS.south + (0,-1000), (M3, M4), how='|-', net='vss', track=5, track_end=-1)
        self.route(r.end, self.IVAMP.VSS, M1, how='|', net='vss')

        self.route(self.COMP.INN, self.S8.MN.S, (M3, M4), how='|-', net='vint_sampled', track=-4)

        # Clocks and feedback (M4)
        self.route(self.COMP.CLK, self.S1.MN.G, (M3, M4), how='|-', net='phi1', track=-5)
        self.route(self.S1.MN.G, self.S3.MN.G, M2, how='|-', net='phi1', track=1.3)
        self.route(self.S3.MN.G, self.S5.MN.G, M1, how='|-', net='phi1', track=-1)
        self.route(self.S1.MP.G, self.S3.MP.G, M1, how='|-', net='phi1_bar', track=-1)
        self.route(self.S3.MP.G, self.S5.MP.G, M1, how='|-', net='phi1_bar', track=1)
        self.route(self.S2.MN.G, self.S4.MN.G, M2, how='|-', net='phi2', track=-1)
        self.route(self.S4.MN.G, self.S8.MN.G, M2, how='|-', net='phi2', track=-1.5)
        self.route(self.S2.MP.G, self.S4.MP.G, M2, how='|-', net='phi2_bar', track=-1)
        self.route(self.S4.MP.G, self.S8.MP.G, M2, how='|-', net='phi2_bar', track=1.5)
        self.route(self.COMP.RSTL.MN3B.G, self.S6.MP.G, (M3, M4), how='|-', net='out', track=6)
        self.route(self.S6.MP.G, self.S7.MN.G, M2, how='|-', net='out', track=-2)
        self.route(self.COMP.RSTL.MP1A[1].G, self.S7.MP.G, (M3, M4), how='|-', net='outb', track=3.5)
        self.route(self.S6.MN.G, self.S7.MP.G, M4, how='|-', net='outb')
        self.route(self.COMP.INP, self.S3.MN.S, (M3, M4), how='|-', net='vref', track=-6)

        # Check off power nets (connected via tap overlap, not explicit routes)
        self.check_off_net('vdd')
        self.check_off_net('vss')



        # Top-level pins
        self.add_pin('vin', self.S1.MN.D)
        self.add_pin('vref', self.COMP.INP)
        self.add_pin('phi1', self.COMP.CLK)
        self.add_pin('phi1_bar', self.S1.MP.G)
        self.add_pin('phi2', self.S2.MN.G)
        self.add_pin('phi2_bar', self.S2.MP.G)
        self.add_pin('out', self.COMP.RSTL.MP1A[0].D.west.on_layer(M2))
        self.add_pin('outb', self.COMP.ON)
        self.add_pin('vdd', self.COMP.AVDD)
        self.add_pin('vss', self.COMP.AVSS)
        self.add_pin('vint', self.Cf.BOT)


def _main():
    from pade.backends.gds.layout_writer import GDSWriter
    from pdk.sky130.config import config
    from pdk.sky130.layers import sky130_layers
    from src.components.mod1.schematic import Mod1
    from utils.design_runner import DesignRunner

    sch = Mod1('dut')
    layout = Mod1Layout('dut', schematic=sch)
    writer = GDSWriter(layer_map=sky130_layers)
    writer.write(layout, config.layout_dir)

    print('Connectivity:')
    layout.print_connectivity_report()
    missing = layout.check_connectivity()
    print(f"  {'PASS' if not missing else 'FAIL'}")

    print('Shorts:')
    result = layout.check_shorts()
    print(f"    {result.summary()}  {'PASS' if result.clean else 'FAIL'}")

    runner = DesignRunner(layout, sch)
    dr = runner.run_all(drc=True, lvs=True, pex=False)
    print(dr)
    sys.exit(0 if dr.passed else 1)


if __name__ == '__main__':
    _main()
