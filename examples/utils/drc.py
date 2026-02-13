"""DRC (Design Rule Check) using Magic."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdk.sky130.config import SKY130Config
    from pade.layout.cell import LayoutCell


# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'


@dataclass
class DRCResult:
    """Result of a DRC run."""
    passed: bool
    error_count: int
    log_path: Path
    report_path: Path

    def __str__(self) -> str:
        if self.passed:
            return f"{GREEN}DRC PASS: 0 errors{RESET}"
        else:
            return f"{RED}DRC FAIL: {self.error_count} errors{RESET}\nSee report: {self.report_path}"

    def __repr__(self) -> str:
        return f"DRCResult(passed={self.passed}, error_count={self.error_count})"


class DRC:
    """Run DRC checks using Magic.

    Example:
        drc = DRC()
        result = drc.run(layout_cell)
        print(result)
    """

    def __init__(self):
        from pdk.sky130.config import config
        self.config = config

    def run(self, layout: 'LayoutCell') -> DRCResult:
        """Run DRC on a LayoutCell.

        Args:
            layout: LayoutCell to check

        Returns:
            DRCResult with pass/fail status and error count
        """
        cell_name = layout.cell_name
        work_dir = self.config.cell_work_dir(cell_name)
        gds_file = self.config.layout_dir / f'{cell_name}.gds'

        if not gds_file.exists():
            raise FileNotFoundError(f"GDS file not found: {gds_file}")

        log_path = work_dir / 'drc.log'
        report_path = work_dir / 'drc.rpt'

        # Magic DRC script
        script = f'''
gds read {gds_file}
load {cell_name}
select top cell
drc check
drc catchup
drc count total

# Write detailed report
set f [open "{report_path}" w]
puts $f "DRC Report for {cell_name}"
puts $f "========================="
puts $f ""
set errors [drc listall why]
puts $f $errors
close $f

quit -noprompt
'''

        result = subprocess.run(
            ['magic', '-dnull', '-noconsole', '-norcfile', '-T', str(self.config.tech_file)],
            input=script,
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

        # Parse error count from "Total DRC errors found: N" output
        error_count = 0
        for line in result.stdout.split('\n'):
            if 'Total DRC errors found:' in line:
                try:
                    error_count = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass

        return DRCResult(
            passed=(error_count == 0),
            error_count=error_count,
            log_path=log_path,
            report_path=report_path
        )
