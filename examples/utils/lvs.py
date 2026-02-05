"""LVS (Layout vs Schematic) using Magic and Netgen."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdk.sky130.config import SKY130Config
    from pade.layout.cell import LayoutCell
    from pade.core.cell import Cell


# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'


@dataclass
class LVSResult:
    """Result of an LVS run."""
    matched: bool
    log_path: Path
    report_path: Path

    def __str__(self) -> str:
        if self.matched:
            return f"""{GREEN}
                         #       ###################       _   _
                        #        #                 #       *   *
                   #   #         #     CORRECT     #         |
                    # #          #                 #       \\___/
                     #           ###################
{RESET}"""
        else:
            return f"""{RED}
                  #   #         ###################
                   # #          #                 #
                    #           #    INCORRECT    #
                   # #          #                 #
                  #   #         ###################
{RESET}
See report: {self.report_path}"""

    def __repr__(self) -> str:
        return f"LVSResult(matched={self.matched})"


class LVS:
    """Run LVS comparison using Magic (extraction) and Netgen (comparison).

    Example:
        lvs = LVS()
        result = lvs.run(layout_cell, schematic_cell)
        print(result)
    """

    def __init__(self):
        from pdk.sky130.config import config
        self.config = config

    def run(self, layout: 'LayoutCell', schematic: 'Cell') -> LVSResult:
        """Run LVS comparison.

        Args:
            layout: LayoutCell to extract
            schematic: Schematic Cell to compare against

        Returns:
            LVSResult with match status
        """
        cell_name = layout.cell_name
        work_dir = self.config.cell_work_dir(cell_name)
        gds_file = self.config.layout_dir / f'{cell_name}.gds'

        if not gds_file.exists():
            raise FileNotFoundError(f"GDS file not found: {gds_file}")

        # Paths
        schematic_spice = work_dir / 'lvs_schematic.spice'
        layout_spice = work_dir / 'lvs_layout.spice'
        log_path = work_dir / 'lvs.log'
        report_path = work_dir / 'lvs.rpt'

        # Step 1: Generate schematic netlist
        self._write_schematic_netlist(schematic, schematic_spice)

        # Step 2: Extract layout netlist
        self._extract_layout(cell_name, gds_file, layout_spice, work_dir)

        # Step 3: Run Netgen comparison
        matched = self._run_netgen(
            cell_name, layout_spice, schematic_spice,
            log_path, report_path, work_dir
        )

        return LVSResult(
            matched=matched,
            log_path=log_path,
            report_path=report_path
        )

    def _write_schematic_netlist(self, cell: 'Cell', path: Path) -> None:
        """Generate schematic netlist from Cell.

        If the cell is a NetlistCell (loaded from external SPICE file),
        the original file is copied. Otherwise, a new netlist is generated.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Check if this is a NetlistCell (has source_path attribute)
        if hasattr(cell, 'source_path') and cell.source_path is not None:
            # Copy the original SPICE file
            import shutil
            shutil.copy(cell.source_path, path)
        else:
            # Generate netlist from Cell
            from pade.backends.ngspice.netlist_writer import SpiceNetlistWriter
            writer = SpiceNetlistWriter()
            netlist = writer.generate_subcircuit(cell)
            with open(path, 'w') as f:
                f.write(netlist)

    def _extract_layout(self, cell_name: str, gds_file: Path,
                        output_spice: Path, work_dir: Path) -> None:
        """Extract layout netlist using Magic."""
        # Clean up old extraction files
        for ext in ['.ext', '.spice']:
            old_file = work_dir / f'{cell_name}{ext}'
            if old_file.exists():
                old_file.unlink()

        # Use absolute path for GDS, relative filename for output (cwd=work_dir)
        gds_abs = gds_file.resolve()
        output_name = output_spice.name

        script = f'''
gds read {gds_abs}
load {cell_name}
select top cell
extract all
ext2spice lvs
ext2spice subcircuit top on
ext2spice -o {output_name}
quit -noprompt
'''

        result = subprocess.run(
            ['magic', '-dnull', '-noconsole', '-T', str(self.config.tech_file)],
            input=script,
            capture_output=True,
            text=True,
            cwd=work_dir
        )

        if not output_spice.exists():
            raise RuntimeError(f"Layout extraction failed:\n{result.stderr or result.stdout}")

    def _run_netgen(self, cell_name: str, layout_spice: Path,
                    schematic_spice: Path, log_path: Path,
                    report_path: Path, work_dir: Path) -> bool:
        """Run Netgen LVS comparison."""
        # Use filenames only since cwd=work_dir
        layout_name = layout_spice.name
        schematic_name = schematic_spice.name
        report_name = report_path.name

        result = subprocess.run(
            [
                'netgen', '-batch', 'lvs',
                f'{layout_name} {cell_name}',
                f'{schematic_name} {cell_name}',
                str(self.config.netgen_setup),
                report_name
            ],
            capture_output=True,
            text=True,
            cwd=work_dir
        )

        # Save log
        with open(log_path, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)

        # Parse result - look for "Circuits match uniquely" or similar
        output = result.stdout.lower()
        matched = 'match' in output and 'mismatch' not in output

        # Also check the report file for more reliable result
        if report_path.exists():
            report = report_path.read_text().lower()
            if 'circuits match uniquely' in report:
                matched = True
            elif 'mismatch' in report or 'failed' in report:
                matched = False

        return matched
