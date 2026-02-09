#!/usr/bin/env python3
"""Test inverter layout: DRC and LVS."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layers import sky130_layers
from src.components.digital.schematic import IVX
from src.components.digital.layout import IVXLayout
from utils.drc import DRC
from utils.lvs import LVS


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


def run_lvs(layout, schematic, writer, lvs):
    """Run LVS, return True if matched."""
    writer.write(layout, config.layout_dir)
    result = lvs.run(layout, schematic)
    print(f"  LVS: {'MATCH' if result.matched else 'MISMATCH'}")
    if not result.matched:
        with open(result.report_path) as f:
            for line in f.readlines()[:30]:
                print(f"    {line.rstrip()}")
    return result.matched


def test_drc():
    """Test inverter DRC."""
    print("\n" + "=" * 60)
    print("DRC: Inverter")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (1.0, 2.0, 0.15, 1, "wn=1, wp=2, l=0.15, nf=1"),
        (1.0, 2.0, 0.15, 2, "wn=1, wp=2, l=0.15, nf=2"),
        (0.42, 1.0, 0.15, 3, "wn=0.42, wp=1, l=0.15, nf=3"),
        (1.0, 2.0, 0.5, 4, "wn=1, wp=2, l=0.5, nf=4"),
    ]

    all_passed = True
    for wn, wp, l, nf, desc in test_cases:
        print(f"\n{desc}:")
        sch = IVX('inv', wn=wn, wp=wp, l=l, nf=nf)
        layout = IVXLayout('inv', schematic=sch)
        if not run_drc(layout, writer, drc):
            all_passed = False
    return all_passed


def test_lvs():
    """Test inverter LVS."""
    print("\n" + "=" * 60)
    print("LVS: Inverter")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()

    test_cases = [
        (1.0, 2.0, 0.15, 1, "wn=1, wp=2, l=0.15, nf=1"),
        (1.0, 2.0, 0.15, 2, "wn=1, wp=2, l=0.15, nf=2"),
        (0.42, 1.0, 0.15, 3, "wn=0.42, wp=1, l=0.15, nf=3"),
        (1.0, 2.0, 0.5, 4, "wn=1, wp=2, l=0.5, nf=4"),
    ]

    all_passed = True
    for wn, wp, l, nf, desc in test_cases:
        print(f"\n{desc}:")
        sch = IVX('inv', wn=wn, wp=wp, l=l, nf=nf)
        layout = IVXLayout('inv', schematic=sch)
        if not run_lvs(layout, sch, writer, lvs):
            all_passed = False
    return all_passed


if __name__ == '__main__':
    results = {
        'DRC': test_drc(),
        'LVS': test_lvs(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    sys.exit(0 if all(results.values()) else 1)
