"""PEX (Parasitic Extraction) using Magic."""

import re
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
class PEXResult:
    """Result of a PEX run."""
    success: bool
    netlist_path: Path
    log_path: Path

    def __str__(self) -> str:
        if self.success:
            return f"""{GREEN}PEX extraction successful{RESET}
Netlist: {self.netlist_path}"""
        else:
            return f"""{RED}PEX extraction failed{RESET}
See log: {self.log_path}"""

    def __repr__(self) -> str:
        return f"PEXResult(success={self.success}, netlist_path='{self.netlist_path}')"


class PEX:
    """Run parasitic extraction using Magic.

    The extracted netlist is post-processed to replace SUB (substrate)
    with 0 (ground), making it directly usable in simulation.

    Example:
        pex = PEX()
        result = pex.run(layout_cell)
        print(result.netlist_path)
    """

    def __init__(self):
        from pdk.sky130.config import config
        self.config = config

    def run(self, layout: 'LayoutCell',
            cthresh: float = 0, rthresh: float = 0) -> PEXResult:
        """Run parasitic extraction on a LayoutCell.

        Args:
            layout: LayoutCell to extract
            cthresh: Capacitance threshold in fF (0 = extract all)
            rthresh: Resistance threshold in ohms (0 = extract all)

        Returns:
            PEXResult with path to extracted netlist
        """
        cell_name = layout.cell_name
        work_dir = self.config.cell_work_dir(cell_name)
        pex_dir = self.config.cell_pex_dir(cell_name)
        gds_file = self.config.layout_dir / f'{cell_name}.gds'

        if not gds_file.exists():
            raise FileNotFoundError(f"GDS file not found: {gds_file}")

        # Paths
        work_spice = work_dir / 'pex_raw.spice'
        log_path = work_dir / 'pex.log'
        output_path = pex_dir / 'pex_rc.spice'

        # Clean up old files
        for f in [work_spice, work_dir / f'{cell_name}.ext']:
            if f.exists():
                f.unlink()

        # Use absolute path for GDS, relative filename for output (cwd=work_dir)
        gds_abs = gds_file.resolve()
        output_name = work_spice.name

        # Magic extraction script
        script = f'''
gds read {gds_abs}
load {cell_name}
select top cell
extract all
ext2spice lvs
ext2spice cthresh {cthresh}
ext2spice rthresh {rthresh}
ext2spice subcircuit top on
ext2spice -o {output_name}
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

        # Check if extraction succeeded
        if not work_spice.exists():
            return PEXResult(
                success=False,
                netlist_path=output_path,
                log_path=log_path
            )

        # Post-process: replace SUB with 0
        content = work_spice.read_text()
        content = self._replace_substrate(content)

        # Write final netlist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)

        return PEXResult(
            success=True,
            netlist_path=output_path,
            log_path=log_path
        )

    def _replace_substrate(self, content: str) -> str:
        """Replace SUB (substrate) node with 0 (ground).

        This handles common substrate node names: SUB, VSUBS, Vgnd
        """
        # Replace standalone SUB node references (not part of other words)
        # Pattern matches SUB surrounded by whitespace or line boundaries
        content = re.sub(r'\bSUB\b', '0', content)
        content = re.sub(r'\bVSUBS\b', '0', content, flags=re.IGNORECASE)
        content = re.sub(r'\bVgnd\b', '0', content, flags=re.IGNORECASE)

        return content
