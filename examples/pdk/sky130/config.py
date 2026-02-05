"""SKY130 tool configuration (paths for Magic, Netgen, etc.)."""

import os
from pathlib import Path


class SKY130Config:
    """Configuration for SKY130 PDK tools (Magic, Netgen).

    Manages paths for layout files, work directories, and PDK tool files.
    Project root is auto-detected relative to this file (examples/).

    Attributes:
        project_root: Root directory for project files (examples/)
        pdk_root: Root directory for PDK installation
        tech_file: Magic technology file
        netgen_setup: Netgen LVS setup file
        layout_dir: Directory for GDS layout files
        work_dir: Working directory for tool outputs
        pex_dir: Directory for PEX netlists

    Example:
        from pdk.sky130.config import config
        drc = DRC()
        result = drc.run(layout_cell)
    """

    def __init__(self, pdk_root: str | Path = None):
        # Project root is examples/ (parent of pdk/sky130/)
        self.project_root = Path(__file__).parent.parent.parent
        self.pdk_root = Path(
            pdk_root or os.environ.get('PDK_ROOT', os.path.expanduser('~/.ciel'))
        )
        self.sky130_lib = self.pdk_root / 'sky130A/libs.tech/combined/sky130.lib.spice'

        # PDK tool paths
        self.tech_file = self.pdk_root / 'sky130A/libs.tech/magic/sky130A.tech'
        self.netgen_setup = self.pdk_root / 'sky130A/libs.tech/netgen/sky130A_setup.tcl'

        # Project directory paths
        self.layout_dir = self.project_root / 'layout'
        self.work_dir = self.project_root / 'work'
        self.pex_dir = self.project_root / 'pex'
        self.sim_data_dir = self.project_root / 'sim_data'

        # Make all directories on initialization
        self._mkdir()

    def cell_work_dir(self, cell_name: str) -> Path:
        """Get work directory for a specific cell."""
        path = self.work_dir / cell_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cell_pex_dir(self, cell_name: str) -> Path:
        """Get PEX output directory for a specific cell."""
        path = self.pex_dir / cell_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _mkdir(self) -> None:
        """Create all project directories if they don't exist."""
        for path in [self.layout_dir, self.work_dir, self.pex_dir, self.sim_data_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        return f"SKY130Config(project_root='{self.project_root}')"


# Module-level singleton - import this directly
config = SKY130Config()
