#!/usr/bin/env python3
"""Test DRC rule checking with simple geometry violations."""

import sys
from pathlib import Path

examples_dir = Path(__file__).parent.parent
project_root = examples_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(examples_dir))

from pade.backends.gds.layout_writer import GDSWriter
from pdk.sky130.config import config
from pdk.sky130.layers import sky130_layers, M1, LI
from pdk.sky130.layout import SKY130LayoutCell
from utils.drc import DRC


def run_drc_test(cell, writer, drc, expect_pass: bool):
    """Run DRC and check if result matches expectation."""
    writer.write(cell, config.layout_dir)
    result = drc.run(cell)
    
    actual_pass = result.passed
    status = "OK" if (actual_pass == expect_pass) else "MISMATCH"
    
    expected_str = "PASS" if expect_pass else "FAIL"
    actual_str = "PASS" if actual_pass else f"FAIL ({result.error_count} errors)"
    
    print(f"  Expected: {expected_str}, Got: {actual_str} [{status}]")
    
    if status == "MISMATCH":
        print(f"  Report: {result.report_path}")
        if result.report_path.exists():
            with open(result.report_path) as f:
                for line in f.readlines()[:20]:
                    print(f"    {line.rstrip()}")
    
    return actual_pass == expect_pass


def test_m1_width():
    """Test M1 minimum width rule (140nm)."""
    print("\n" + "=" * 60)
    print("Testing M1 minimum width (140nm)")
    print("=" * 60)
    
    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()
    all_ok = True
    
    # Should FAIL: 100nm width (< 140nm minimum)
    # Use 1000nm height to satisfy min area (0.083um² = 83000nm²)
    print("\nM1 width=100nm (should FAIL):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_m1_width_fail')
    cell.add_rect(M1, 0, 0, 100, 1000)  # 100nm wide, 1000nm tall = 100000nm² (area OK)
    if not run_drc_test(cell, writer, drc, expect_pass=False):
        all_ok = False
    
    # Should PASS: 140nm width (exactly minimum)
    # 140nm x 600nm = 84000nm² > 83000nm² min area
    print("\nM1 width=140nm (should PASS):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_m1_width_pass')
    cell.add_rect(M1, 0, 0, 140, 600)  # 140nm wide, 600nm tall
    if not run_drc_test(cell, writer, drc, expect_pass=True):
        all_ok = False
    
    return all_ok


def test_m1_spacing():
    """Test M1 minimum spacing rule (140nm)."""
    print("\n" + "=" * 60)
    print("Testing M1 minimum spacing (140nm)")
    print("=" * 60)
    
    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()
    all_ok = True
    
    # Should FAIL: 100nm spacing (< 140nm minimum)
    # Use 200nm x 600nm = 120000nm² > 83000nm² min area
    print("\nM1 spacing=100nm (should FAIL):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_m1_space_fail')
    cell.add_rect(M1, 0, 0, 200, 600)      # First rect
    cell.add_rect(M1, 300, 0, 500, 600)    # Second rect, 100nm gap (300-200=100)
    if not run_drc_test(cell, writer, drc, expect_pass=False):
        all_ok = False
    
    # Should PASS: 140nm spacing (exactly minimum)
    print("\nM1 spacing=140nm (should PASS):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_m1_space_pass')
    cell.add_rect(M1, 0, 0, 200, 600)      # First rect
    cell.add_rect(M1, 340, 0, 540, 600)    # Second rect, 140nm gap (340-200=140)
    if not run_drc_test(cell, writer, drc, expect_pass=True):
        all_ok = False
    
    return all_ok


def test_li_width():
    """Test LI minimum width rule (170nm)."""
    print("\n" + "=" * 60)
    print("Testing LI minimum width (170nm)")
    print("=" * 60)
    
    writer = GDSWriter(layer_map=sky130_layers)
    drc = DRC()
    all_ok = True
    
    # Should FAIL: 100nm width (< 170nm minimum)
    # Use 600nm height to satisfy min area (0.0561um² = 56100nm²)
    print("\nLI width=100nm (should FAIL):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_li_width_fail')
    cell.add_rect(LI, 0, 0, 100, 600)  # 100nm x 600nm = 60000nm² (area OK)
    if not run_drc_test(cell, writer, drc, expect_pass=False):
        all_ok = False
    
    # Should PASS: 170nm width (exactly minimum)
    # 170nm x 400nm = 68000nm² > 56100nm² min area
    print("\nLI width=170nm (should PASS):")
    cell = SKY130LayoutCell('test', None, cell_name='drc_test_li_width_pass')
    cell.add_rect(LI, 0, 0, 170, 400)
    if not run_drc_test(cell, writer, drc, expect_pass=True):
        all_ok = False
    
    return all_ok


def main():
    print("DRC Rule Verification Test")
    print(f"Output dir: {config.layout_dir}")
    config.layout_dir.mkdir(parents=True, exist_ok=True)
    
    all_ok = True
    
    if not test_m1_width():
        all_ok = False
    if not test_m1_spacing():
        all_ok = False
    if not test_li_width():
        all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("ALL DRC TESTS MATCHED EXPECTATIONS")
    else:
        print("SOME DRC TESTS DID NOT MATCH - Check Magic setup")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
