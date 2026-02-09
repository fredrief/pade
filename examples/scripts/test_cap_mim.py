#!/usr/bin/env python3
"""Test MiM capacitor layout generation, DRC, and LVS."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layers import sky130_layers
from pdk.sky130.primitives.capacitors.layout import CapMimLayout
from pdk.sky130.primitives.capacitors.schematic import CapMim
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


def test_drc_m4():
    """Test M4/M5 capacitor DRC."""
    print("\n" + "=" * 60)
    print("DRC: M4/M5 MiM Capacitor")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (10.0, 10.0, "10x10 um"),
        (5.0, 5.0, "5x5 um"),
        (2.0, 10.0, "2x10 um"),
        (20.0, 20.0, "20x20 um"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc} (metal=4):")
        sch = CapMim('C1', w=w, l=l, metal=4)
        cap = CapMimLayout('C1', None, schematic=sch)
        if not run_drc(cap, writer, drc):
            all_passed = False
    return all_passed


def test_drc_m3():
    """Test M3/M4 capacitor DRC."""
    print("\n" + "=" * 60)
    print("DRC: M3/M4 MiM Capacitor")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()

    test_cases = [
        (10.0, 10.0, "10x10 um"),
        (5.0, 5.0, "5x5 um"),
        (2.0, 10.0, "2x10 um"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc} (metal=3):")
        sch = CapMim('C1', w=w, l=l, metal=3)
        cap = CapMimLayout('C1', None, schematic=sch)
        if not run_drc(cap, writer, drc):
            all_passed = False
    return all_passed


def test_lvs_m4():
    """Test M4/M5 capacitor LVS."""
    print("\n" + "=" * 60)
    print("LVS: M4/M5 MiM Capacitor")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()

    test_cases = [
        (10.0, 10.0, "10x10 um"),
        (5.0, 5.0, "5x5 um"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc} (metal=4):")
        schematic = CapMim('C1', w=w, l=l, metal=4)
        layout = CapMimLayout('C1', None, schematic=schematic)
        if not run_lvs(layout, schematic, writer, lvs):
            all_passed = False
    return all_passed


def test_lvs_m3():
    """Test M3/M4 capacitor LVS."""
    print("\n" + "=" * 60)
    print("LVS: M3/M4 MiM Capacitor")
    print("=" * 60)

    writer = GDSWriter(layer_map=sky130_layers)
    lvs = LVS()

    test_cases = [
        (10.0, 10.0, "10x10 um"),
        (5.0, 5.0, "5x5 um"),
    ]

    all_passed = True
    for w, l, desc in test_cases:
        print(f"\n{desc} (metal=3):")
        schematic = CapMim('C1', w=w, l=l, metal=3)
        layout = CapMimLayout('C1', None, schematic=schematic)
        if not run_lvs(layout, schematic, writer, lvs):
            all_passed = False
    return all_passed


if __name__ == '__main__':
    results = {
        'DRC M4': test_drc_m4(),
        'DRC M3': test_drc_m3(),
        'LVS M4': test_lvs_m4(),
        'LVS M3': test_lvs_m3(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
