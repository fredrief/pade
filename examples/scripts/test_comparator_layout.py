#!/usr/bin/env python3
"""Test comparator layout: DRC and LVS for NSAL, NSALRSTL, NSALCMP."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layers import sky130_layers
from src.components.digital.schematic import NSAL, NSALRSTL, NSALCMP
from src.components.digital.layout import NSALLayout, NSALRSTLLayout, NSALCMPLayout
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


WN = 1.0
L = 0.15




def test_shorts():
    """Run compile-time short detection for all cells."""
    all_passed = True
    for name, sch_cls, lay_cls, kw in CELLS:
        print(f"\n{'=' * 60}")
        print(f"Short check: {name}")
        print('=' * 60)
        sch = sch_cls('dut', **kw)
        layout = lay_cls('dut', schematic=sch)
        result = layout.check_shorts()
        print(f"  {result.summary()}")
        if not result.clean:
            all_passed = False
    return all_passed


def test_connectivity():
    """Run compile-time connectivity check for all cells."""
    all_passed = True
    for name, sch_cls, lay_cls, kw in CELLS:
        print(f"\n{'=' * 60}")
        print(f"Connectivity: {name}")
        print('=' * 60)
        sch = sch_cls('dut', **kw)
        layout = lay_cls('dut', schematic=sch)
        layout.print_connectivity_report()
        missing = layout.check_connectivity()
        if missing:
            all_passed = False
    return all_passed


def test_drc():
    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()
    all_passed = True
    for name, sch_cls, lay_cls, kw in CELLS:
        print(f"\n{'=' * 60}")
        print(f"DRC: {name}")
        print('=' * 60)
        sch = sch_cls('dut', **kw)
        layout = lay_cls('dut', schematic=sch)
        if not run_drc(layout, writer, drc):
            all_passed = False
    return all_passed


def test_lvs():
    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()
    all_passed = True
    for name, sch_cls, lay_cls, kw in CELLS:
        print(f"\n{'=' * 60}")
        print(f"LVS: {name}")
        print('=' * 60)
        sch = sch_cls('dut', **kw)
        layout = lay_cls('dut', schematic=sch)
        if not run_lvs(layout, sch, writer, lvs):
            all_passed = False
    return all_passed

CELLS = [
    ('NSAL', NSAL, NSALLayout, {'wn': WN, 'l': L}),
    ('NSALRSTL', NSALRSTL, NSALRSTLLayout, {'wn': WN, 'l': L}),
    ('NSALCMP', NSALCMP, NSALCMPLayout, {'wn': WN, 'l': L}),
]

if __name__ == '__main__':
    results = {
        'Connectivity': test_connectivity(),
        'Shorts': test_shorts(),
        'DRC': test_drc(),
        'LVS': test_lvs(),
    }

    print(f"\n{'=' * 60}")
    print("Summary")
    print('=' * 60)
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    sys.exit(0 if all(results.values()) else 1)
