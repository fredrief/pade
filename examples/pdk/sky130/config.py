"""SKY130 tool configuration (paths for Magic, Netgen, synthesis, etc.)."""

import os
from pathlib import Path


class SKY130Config:
    """Configuration for SKY130 PDK tools.

    Manages paths for layout files, work directories, PDK tool files,
    and standard cell libraries for digital synthesis and P&R.

    Attributes:
        project_root: Root directory for project files (examples/)
        pdk_root: Root directory for PDK installation
        tech_file: Magic technology file
        netgen_setup: Netgen LVS setup file
        layout_dir: Directory for GDS layout files
        work_dir: Working directory for tool outputs
        pex_dir: Directory for PEX netlists
        substrate_net_name: Net name used in schematics for substrate. Magic
            extracts the bulk node as SUB; LVS replaces SUB with this name in
            the layout netlist so pin names match. Set to "SUB" to accept
            Magic's default (no replacement).
        liberty_tt: Liberty timing file (typical corner)
        liberty_ff: Liberty timing file (fast corner)
        liberty_ss: Liberty timing file (slow corner)
        std_cell_lef: LEF file for sky130_fd_sc_hd
        std_cell_techlef: Tech LEF for sky130_fd_sc_hd
        std_cell_verilog: Verilog models for gate-level simulation
        std_cell_spice: SPICE models for gate-level co-simulation

    Example:
        from pdk.sky130.config import config
        drc = DRC()
        result = drc.run(layout_cell)
    """

    def __init__(self, pdk_root: str | Path = None, substrate_net_name: str = 'AVSS'):
        # Project root is examples/ (parent of pdk/sky130/)
        self.project_root = Path(__file__).parent.parent.parent
        self.pdk_root = Path(
            pdk_root or os.environ.get('PDK_ROOT', os.path.expanduser('~/.ciel'))
        )
        self.sky130_lib = self.pdk_root / 'sky130A/libs.tech/combined/sky130.lib.spice'
        self.sky130_slim_lib = self.project_root / 'pdk/sky130/sky130_slim.lib.spice'

        # PDK tool paths (analog)
        self.tech_file = self.pdk_root / 'sky130A/libs.tech/magic/sky130A.tech'
        self.netgen_setup = self.pdk_root / 'sky130A/libs.tech/netgen/sky130A_setup.tcl'

        # Standard cell library paths (digital)
        _sc = self.pdk_root / 'sky130A/libs.ref/sky130_fd_sc_hd'
        self.liberty_tt = _sc / 'lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
        self.liberty_ff = _sc / 'lib/sky130_fd_sc_hd__ff_100C_1v65.lib'
        self.liberty_ss = _sc / 'lib/sky130_fd_sc_hd__ss_100C_1v60.lib'
        self.std_cell_lef = _sc / 'lef/sky130_fd_sc_hd.lef'
        self.std_cell_lef_ef = _sc / 'lef/sky130_ef_sc_hd.lef'
        self.std_cell_techlef = _sc / 'techlef/sky130_fd_sc_hd__nom.tlef'
        self.std_cell_verilog = _sc / 'verilog/sky130_fd_sc_hd.v'
        self.std_cell_spice = _sc / 'spice/sky130_fd_sc_hd.spice'
        self.std_cell_gds = _sc / 'gds/sky130_fd_sc_hd.gds'

        # Project directory paths
        self.layout_dir = self.project_root / 'layout'
        self.work_dir = self.project_root / 'work'
        self.pex_dir = self.project_root / 'pex'
        self.sim_data_dir = self.project_root / 'sim_data'

        # LVS: Magic extracts substrate as SUB; replace with this name in layout netlist.
        self.substrate_net_name = substrate_net_name

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
