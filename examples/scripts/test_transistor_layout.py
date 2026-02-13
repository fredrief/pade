#!/usr/bin/env python3
"""Test transistor layout generation, DRC, and LVS."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import sky130_layers
from pdk.sky130.primitives.transistors.layout import NFET_01V8_Layout, PFET_01V8_Layout
from pdk.sky130.primitives.transistors.schematic import Nfet01v8, Pfet01v8
from utils.drc import DRC
from utils.lvs import LVS


def run_drc(cell, writer, drc):
    """Write GDS and run DRC, return True if passed."""
    writer.write(cell, config.layout_dir)
    result = drc.run(cell)
    print(f"  Shapes: {len(cell.get_all_shapes())}, bbox: {cell.bbox()}")
    print(f"  {result}")
    if not result.passed:
        with open(result.report_path) as f:
            for line in f.readlines()[:30]:
                print(f"    {line.rstrip()}")
    return result.passed


def run_lvs(layout, schematic, writer, lvs):
    """Write GDS and run LVS, return True if matched."""
    writer.write(layout, config.layout_dir)
    result = lvs.run(layout, schematic)
    print(f"  {result}")
    if not result.matched:
        with open(result.report_path) as f:
            for line in f.readlines()[:50]:
                print(f"    {line.rstrip()}")
    return result.matched


def test_nfet_single():
    """Test single-finger NFET at various sizes."""
    print("\n" + "=" * 60)
    print("Testing NFET single finger")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (1.0, 0.15, "1um x 150nm"),
        (0.42, 0.15, "420nm (min W) x 150nm"),
        (2.0, 0.15, "2um x 150nm"),
        (1.0, 0.5, "1um x 500nm"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc}:")
        sch = Nfet01v8(instance_name='M1', w=w, l=l, nf=1)
        root = SKY130LayoutCell(instance_name='top', parent=None)
        root.M1 = NFET_01V8_Layout.instantiate(root, schematic=sch)
        if not run_drc(root, writer, drc):
            all_passed = False

    return all_passed


def test_pfet_single():
    """Test single-finger PFET (with NWELL, tap on right)."""
    print("\n" + "=" * 60)
    print("Testing PFET single finger")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (1.0, 0.15, "1um x 150nm"),
        (0.42, 0.15, "420nm (min W) x 150nm"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc}:")
        sch = Pfet01v8(instance_name='M1', w=w, l=l, nf=1)
        root = SKY130LayoutCell(instance_name='top', parent=None)
        root.M1 = PFET_01V8_Layout.instantiate(root, schematic=sch)

        has_nwell = any(s.layer.name == 'NWELL' for s in root.get_all_shapes())
        print(f"  NWELL present: {has_nwell}")
        if not has_nwell:
            print("  ERROR: PFET should have NWELL")
            all_passed = False
            continue

        if not run_drc(root, writer, drc):
            all_passed = False

    return all_passed


def test_tap_configurations():
    """Test different tap configurations."""
    print("\n" + "=" * 60)
    print("Testing tap configurations")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (Nfet01v8, NFET_01V8_Layout, 'left', 'NFET tap=left'),
        (Nfet01v8, NFET_01V8_Layout, 'right', 'NFET tap=right'),
        (Nfet01v8, NFET_01V8_Layout, 'both', 'NFET tap=both'),
        (Pfet01v8, PFET_01V8_Layout, 'left', 'PFET tap=left'),
        (Pfet01v8, PFET_01V8_Layout, 'right', 'PFET tap=right'),
        (Pfet01v8, PFET_01V8_Layout, 'both', 'PFET tap=both'),
    ]

    all_passed = True
    for sch_cls, lay_cls, tap, desc in test_cases:
        print(f"\n{desc}:")
        try:
            sch = sch_cls('M1', None, w=1.0, l=0.15, nf=1)
            root = SKY130LayoutCell(instance_name='top', parent=None)
            root.M1 = lay_cls.instantiate(root, schematic=sch, tap=tap)
            if not run_drc(root, writer, drc):
                all_passed = False
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_multi_finger():
    """Test multi-finger layouts."""
    print("\n" + "=" * 60)
    print("Testing multi-finger layouts")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    # (sch_cls, lay_cls, w, l, nf, poly_contact, desc)
    test_cases = [
        (Nfet01v8, NFET_01V8_Layout, 1.0, 0.15, 2, None, "NFET 1um x 150nm, nf=2"),
        (Nfet01v8, NFET_01V8_Layout, 1.0, 0.15, 4, None, "NFET 1um x 150nm, nf=4"),
        (Nfet01v8, NFET_01V8_Layout, 0.42, 0.15, 3, None, "NFET min W, nf=3"),
        (Pfet01v8, PFET_01V8_Layout, 1.0, 0.15, 2, None, "PFET 1um x 150nm, nf=2"),
        (Pfet01v8, PFET_01V8_Layout, 1.0, 0.15, 4, None, "PFET 1um x 150nm, nf=4"),
        # poly_contact='right' tests (verifies S/D bus fix)
        (Nfet01v8, NFET_01V8_Layout, 1.0, 0.15, 2, 'right', "NFET nf=2, contact=right"),
        (Pfet01v8, PFET_01V8_Layout, 1.0, 0.15, 2, 'right', "PFET nf=2, contact=right"),
        # poly_contact='both' tests
        (Nfet01v8, NFET_01V8_Layout, 1.0, 0.15, 2, 'both', "NFET nf=2, contact=both"),
        (Nfet01v8, NFET_01V8_Layout, 1.0, 0.15, 4, 'both', "NFET nf=4, contact=both"),
        (Pfet01v8, PFET_01V8_Layout, 1.0, 0.15, 2, 'both', "PFET nf=2, contact=both"),
        (Pfet01v8, PFET_01V8_Layout, 1.0, 0.15, 4, 'both', "PFET nf=4, contact=both"),
    ]

    all_passed = True
    for sch_cls, lay_cls, w, l, nf, poly_contact, desc in test_cases:
        print(f"\n{desc}:")
        try:
            sch = sch_cls('M1', None, w=w, l=l, nf=nf)
            root = SKY130LayoutCell(instance_name='top', parent=None)
            root.M1 = lay_cls.instantiate(root, schematic=sch, poly_contact=poly_contact)
            if not run_drc(root, writer, drc):
                all_passed = False
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_lvs_nfet():
    """Test LVS for NFET with various parametrizations."""
    print("\n" + "=" * 60)
    print("Testing LVS: NFET")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()

    test_cases = [
        (1.0, 0.15, 1, "1um x 150nm, nf=1"),
        (0.42, 0.15, 1, "420nm x 150nm, nf=1"),
        (1.0, 0.15, 2, "1um x 150nm, nf=2"),
        (0.42, 0.15, 3, "420nm x 150nm, nf=3"),
        (2.0, 0.5, 4, "2um x 500nm, nf=4"),
    ]

    all_passed = True
    for w, l, nf, desc in test_cases:
        print(f"\n{desc}:")
        try:
            sch = Nfet01v8(instance_name='M1', w=w, l=l, nf=nf)
            root = SKY130LayoutCell(instance_name='top', parent=None)
            root.M1 = NFET_01V8_Layout.instantiate(root, schematic=sch)
            if not run_lvs(root.M1[0], sch, writer, lvs):
                all_passed = False
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_lvs_pfet():
    """Test LVS for PFET with various parametrizations."""
    print("\n" + "=" * 60)
    print("Testing LVS: PFET")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()

    test_cases = [
        (1.0, 0.15, 1, "1um x 150nm, nf=1"),
        (0.42, 0.15, 1, "420nm x 150nm, nf=1"),
        (1.0, 0.15, 2, "1um x 150nm, nf=2"),
        (0.42, 0.15, 3, "420nm x 150nm, nf=3"),
        (2.0, 0.5, 4, "2um x 500nm, nf=4"),
    ]

    all_passed = True
    for w, l, nf, desc in test_cases:
        print(f"\n{desc}:")
        try:
            sch = Pfet01v8(instance_name='M1', w=w, l=l, nf=nf)
            root = SKY130LayoutCell(instance_name='top', parent=None)
            root.M1 = PFET_01V8_Layout.instantiate(root, schematic=sch)
            if not run_lvs(root.M1[0], sch, writer, lvs):
                all_passed = False
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


def main():
    print("Transistor Layout Test (DRC + LVS)")
    print(f"Output dir: {config.layout_dir}")
    config.layout_dir.mkdir(parents=True, exist_ok=True)

    passed = True

    if not test_nfet_single():
        passed = False
    if not test_pfet_single():
        passed = False
    if not test_tap_configurations():
        passed = False
    if not test_multi_finger():
        passed = False
    if not test_lvs_nfet():
        passed = False
    if not test_lvs_pfet():
        passed = False

    if passed:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TESTS FAILED - Check DRC/LVS reports")
        print("=" * 60)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
