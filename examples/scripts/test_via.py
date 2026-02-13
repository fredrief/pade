#!/usr/bin/env python3
"""Test via generation: standalone add_via and auto-via in route."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layers import sky130_layers, M1, M2
from pdk.sky130.layout import SKY130LayoutCell
from src.components.digital.schematic import IVX
from src.components.digital.layout import IVXLayout
from utils.drc import DRC


def run_drc(cell, writer, drc):
    """Write GDS and run DRC, return True if passed."""
    writer.write(cell, config.layout_dir)
    result = drc.run(cell)
    print(f"  Shapes: {len(cell.shapes)}, bbox: {cell.bbox()}")
    print(f"  DRC: {'PASS' if result.passed else 'FAIL'}")
    if not result.passed:
        with open(result.report_path) as f:
            for line in f.readlines()[:20]:
                print(f"    {line.rstrip()}")
    return result.passed


def test_standalone_via():
    """Test standalone add_via: single, multi-cut, and area-fill VIA1 (M1→M2)."""
    cell = SKY130LayoutCell('test_via', cell_name='TEST_VIA')

    # Single VIA1 (M1 → M2)
    cell.add_via(M1, M2, cx=0, cy=0, net='A')

    # 2×2 VIA1 (M1 → M2)
    cell.add_via(M1, M2, cx=1000, cy=0, nx=2, ny=2, net='B')

    # Area-fill VIA1 (M1 → M2), 500×500nm area
    cell.add_via(M1, M2, cx=2000, cy=0, area=(500, 500), net='C')

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    print("Standalone VIA1 (M1→M2):")
    return run_drc(cell, writer, drc)


def test_auto_via_route():
    """Test auto-via in route: inverter with M2 drain connection."""
    sch = IVX(instance_name='dut', wn=1.0, wp=2.0, l=0.15, nf=2)
    layout = IVXLayout_M2Drain('dut', schematic=sch)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    print("\nAuto-via route (IVX drain on M2):")
    return run_drc(layout, writer, drc)


class IVXLayout_M2Drain(IVXLayout):
    """IVX variant that routes drain on M2 to exercise auto-via."""

    def _route(self, schematic):
        from pdk.sky130.layers import POLY
        nf = int(schematic.MN.get_parameter('nf'))
        gate_l = self.to_nm(float(schematic.MN.get_parameter('l')))

        # Gates on poly (no via needed)
        self.route(self.MN.DBOT, self.MP.DBOT, POLY, how='-', width=gate_l, net='IN')
        for i in range(nf):
            self.route(getattr(self.MN, f'G{i}'), getattr(self.MP, f'G{i}'),
                       POLY, how='-', width=gate_l, net='IN')
        self.route(self.MN.DTOP, self.MP.DTOP, POLY, how='-', width=gate_l, net='IN')

        # Drain on M2 — should auto-insert VIA1 at both M1 refs
        MN_DPORT = self.MN.DBUS if nf > 2 else self.MN.D
        MP_DPORT = self.MP.DBUS if nf > 2 else self.MP.D
        self.route(MN_DPORT, MP_DPORT, M2, how='-', net='OUT')

        # Source to tap on M1 (no via)
        self.route(self.MN.S, self.MN.B, M1, how='-', net='VSS')
        self.route(self.MP.S, self.MP.B, M1, how='-', net='VDD')


if __name__ == '__main__':
    r1 = test_standalone_via()
    r2 = test_auto_via_route()

    print(f"\n{'=' * 40}")
    print(f"Standalone VIA1 DRC: {'PASS' if r1 else 'FAIL'}")
    print(f"Auto-via route DRC:  {'PASS' if r2 else 'FAIL'}")
    sys.exit(0 if r1 and r2 else 1)
