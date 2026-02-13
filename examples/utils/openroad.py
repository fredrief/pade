"""OpenROAD P&R and STA wrapper for Sky130."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdk.sky130.config import SKY130Config


# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


@dataclass
class STAResult:
    """Result of a static timing analysis run."""
    success: bool
    log_path: Path
    wns: float | None = None          # worst negative slack (ns)
    tns: float | None = None          # total negative slack (ns)
    max_freq_mhz: float | None = None # max achievable clock frequency
    clock_period: float | None = None  # constrained clock period (ns)
    critical_path: str = ''

    def __str__(self) -> str:
        if not self.success:
            return f"{RED}STA failed{RESET}\nSee log: {self.log_path}"
        if self.wns is None:
            return f"{YELLOW}STA complete — no timing paths found{RESET}"
        color = GREEN if self.wns >= 0 else RED
        lines = [f"{color}STA complete — WNS = {self.wns:.3f} ns{RESET}"]
        if self.tns is not None:
            lines.append(f"  TNS = {self.tns:.3f} ns")
        if self.max_freq_mhz is not None:
            lines.append(f"  Max frequency = {self.max_freq_mhz:.1f} MHz")
        if self.critical_path:
            lines.append(f"  Critical path: {self.critical_path}")
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"STAResult(success={self.success}, wns={self.wns})"


@dataclass
class PnRResult:
    """Result of a place-and-route run."""
    success: bool
    log_path: Path
    def_path: Path | None = None
    gds_path: Path | None = None
    sta: STAResult | None = None
    report: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.success:
            return f"{RED}P&R failed{RESET}\nSee log: {self.log_path}"
        lines = [f"{GREEN}P&R successful{RESET}"]
        if self.def_path:
            lines.append(f"  DEF: {self.def_path}")
        if self.gds_path:
            lines.append(f"  GDS: {self.gds_path}")
        for key, val in self.report.items():
            lines.append(f"  {key}: {val}")
        if self.sta:
            lines.append(f"  Post-route WNS = {self.sta.wns:.3f} ns")
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"PnRResult(success={self.success}, def_path='{self.def_path}')"


class OpenROADRunner:
    """Run place-and-route and STA using OpenROAD targeting Sky130.

    Example:
        from utils.openroad import OpenROADRunner
        runner = OpenROADRunner()
        result = runner.place_and_route(
            netlist=Path('work/cic_synth/cic_filter_synth.v'),
            sdc=Path('src/components/digital/rtl/cic_filter.sdc'),
            top_module='cic_filter',
            output_dir=Path('work/cic_pnr'),
        )
        print(result)
    """

    def __init__(self):
        from pdk.sky130.config import config
        self.config = config

    def run_sta(
        self,
        netlist: str | Path,
        sdc: str | Path,
        top_module: str,
        output_dir: str | Path,
        liberty: str | Path | None = None,
    ) -> STAResult:
        """Run standalone STA on a gate-level netlist.

        Args:
            netlist: Gate-level Verilog netlist (from synthesis or post-P&R).
            sdc: SDC timing constraints file.
            top_module: Top-level module name.
            output_dir: Directory for STA outputs.
            liberty: Liberty file. Defaults to typical corner.

        Returns:
            STAResult with slack, max frequency, critical path.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        liberty = Path(liberty) if liberty else self.config.liberty_tt
        netlist = Path(netlist).resolve()
        sdc = Path(sdc).resolve()

        lef = self.config.std_cell_lef.resolve()
        techlef = self.config.std_cell_techlef.resolve()

        log_path = output_dir / 'sta.log'
        script_path = output_dir / 'sta.tcl'
        report_path = output_dir / 'sta_report.txt'

        script = f"""\
read_liberty {liberty.resolve()}
read_lef {techlef}
read_lef {lef}
read_verilog {netlist}
link_design {top_module}
read_sdc {sdc}

report_checks -path_delay max -format full > {report_path.resolve()}
report_checks -path_delay max
report_tns
report_wns

exit
"""
        script_path.write_text(script)

        result = subprocess.run(
            ['openroad', '-no_splash', '-exit', script_path.name],
            capture_output=True,
            text=True,
            cwd=output_dir,
        )

        with open(log_path, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)

        success = result.returncode == 0
        sta_result = self._parse_sta(result.stdout) if success else STAResult(
            success=False, log_path=log_path
        )
        sta_result.log_path = log_path
        sta_result.success = success

        # Compute max frequency from clock period and WNS
        period = self._parse_clock_period(sdc)
        if period and sta_result.wns is not None:
            sta_result.clock_period = period
            min_period = period - sta_result.wns
            if min_period > 0:
                sta_result.max_freq_mhz = 1000.0 / min_period

        return sta_result

    def place_and_route(
        self,
        netlist: str | Path,
        sdc: str | Path,
        top_module: str,
        output_dir: str | Path,
        liberty: str | Path | None = None,
        utilization: float = 40,
        aspect_ratio: float = 1.0,
        core_margin: int = 10,
    ) -> PnRResult:
        """Run full P&R flow: floorplan -> place -> CTS -> route -> GDS.

        Args:
            netlist: Gate-level Verilog netlist.
            sdc: SDC constraints file.
            top_module: Top-level module name.
            output_dir: Directory for P&R outputs.
            liberty: Liberty file. Defaults to typical corner.
            utilization: Target core utilization (percent). Default 40.
            aspect_ratio: Core aspect ratio. Default 1.0 (square).
            core_margin: Margin around core in um. Default 10.

        Returns:
            PnRResult with DEF, GDS paths and post-route STA.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        liberty = Path(liberty) if liberty else self.config.liberty_tt
        netlist = Path(netlist).resolve()
        sdc = Path(sdc).resolve()

        log_path = output_dir / 'openroad.log'
        script_path = output_dir / 'pnr.tcl'
        def_path = output_dir / f'{top_module}.def'
        gds_path = output_dir / f'{top_module}.gds'
        sta_report_path = output_dir / 'sta_report.txt'

        script = self._generate_pnr_script(
            netlist=netlist,
            sdc=sdc,
            top_module=top_module,
            utilization=utilization,
            aspect_ratio=aspect_ratio,
            core_margin=core_margin,
            def_path=def_path.resolve(),
            sta_report_path=sta_report_path.resolve(),
            liberty=liberty.resolve() if liberty else None,
        )
        script_path.write_text(script)

        result = subprocess.run(
            ['openroad', '-no_splash', '-exit', script_path.name],
            capture_output=True,
            text=True,
            cwd=output_dir,
        )

        with open(log_path, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)

        success = result.returncode == 0 and def_path.exists()

        # Convert DEF to GDS via KLayout (headless)
        if success:
            self._def_to_gds(def_path, gds_path, log_path)

        # Parse post-route STA from log
        sta = self._parse_sta(result.stdout) if success else None
        if sta:
            period = self._parse_clock_period(sdc)
            if period and sta.wns is not None:
                sta.clock_period = period
                min_period = period - sta.wns
                if min_period > 0:
                    sta.max_freq_mhz = 1000.0 / min_period
            sta.log_path = log_path
            sta.success = True

        # Parse design stats
        report = self._parse_design_stats(result.stdout) if success else {}

        return PnRResult(
            success=success,
            log_path=log_path,
            def_path=def_path if def_path.exists() else None,
            gds_path=gds_path if gds_path.exists() else None,
            sta=sta,
            report=report,
        )

    def _generate_pnr_script(
        self,
        netlist, sdc, top_module,
        utilization, aspect_ratio, core_margin,
        def_path, sta_report_path,
        liberty=None,
    ) -> str:
        """Generate OpenROAD TCL script for full P&R flow."""
        liberty = liberty or self.config.liberty_tt.resolve()
        techlef = self.config.std_cell_techlef.resolve()
        lef = self.config.std_cell_lef.resolve()
        lef_ef = self.config.std_cell_lef_ef.resolve()
        site_name = 'unithd'

        return f"""\
# OpenROAD P&R script - generated by PADE
# Target: sky130_fd_sc_hd

# Read design
read_liberty {liberty}
read_lef {techlef}
read_lef {lef}
read_lef {lef_ef}
read_verilog {netlist}
link_design {top_module}
read_sdc {sdc}

# Floorplan
initialize_floorplan -utilization {utilization} \\
    -aspect_ratio {aspect_ratio} \\
    -core_space {core_margin} \\
    -site {site_name}
make_tracks

# Place IO pins
place_pins -hor_layers met3 -ver_layers met2

# Tap cells (well ties at regular intervals) and endcaps
tapcell -distance 14 \
    -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1 \
    -endcap_master sky130_fd_sc_hd__decap_4

# Power distribution network
add_global_connection -net VDD -pin_pattern "^VPWR$" -power
add_global_connection -net VSS -pin_pattern "^VGND$" -ground
add_global_connection -net VDD -pin_pattern "^VPB$" -power
add_global_connection -net VSS -pin_pattern "^VNB$" -ground

define_pdn_grid -name core_grid -voltage_domains "Core"
add_pdn_stripe -grid core_grid -layer met1 -width 0.48 -followpins
add_pdn_stripe -grid core_grid -layer met4 -width 1.6 -spacing 2 -pitch 40 -offset 10
add_pdn_stripe -grid core_grid -layer met5 -width 1.6 -spacing 2 -pitch 40 -offset 10
add_pdn_connect -grid core_grid -layers {{met1 met4}}
add_pdn_connect -grid core_grid -layers {{met4 met5}}
pdngen

# Wire RC for timing estimation
set_wire_rc -layer met3

# Placement
global_placement -density 0.6
repair_design
detailed_placement
optimize_mirroring

# Clock tree synthesis
clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_4 \\
    -buf_list sky130_fd_sc_hd__clkbuf_4 \\
    -sink_clustering_enable
repair_clock_nets
detailed_placement

# Post-CTS timing repair
repair_timing
detailed_placement
check_placement

# Routing
set_routing_layers -signal met1-met5 -clock met1-met5
set_global_routing_layer_adjustment met1 0.8
set_global_routing_layer_adjustment met2 0.7
set_global_routing_layer_adjustment met3 0.5
set_global_routing_layer_adjustment met4 0.5
set_global_routing_layer_adjustment met5 0.5
global_route -congestion_iterations 100
detailed_route -droute_end_iter 64

# Fill gaps in standard cell rows (decap first for free capacitance)
filler_placement -prefix FILLER {{sky130_fd_sc_hd__decap_12 sky130_fd_sc_hd__decap_8 sky130_fd_sc_hd__decap_6 sky130_fd_sc_hd__decap_4 sky130_fd_sc_hd__decap_3 sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}}

# Post-route STA
report_checks -path_delay max -format full > {sta_report_path}
report_checks -path_delay max
report_tns
report_wns

# Write DEF
write_def {def_path}

exit
"""

    def _def_to_gds(self, def_path: Path, gds_path: Path, log_path: Path) -> bool:
        """Convert DEF to GDS using KLayout (batch) + gdstk cleanup.

        KLayout reads the DEF with the Sky130 layer map and standard cell
        GDS library, producing a full GDS with routing and via geometry.
        gdstk then trims unused standard cells to leave a clean hierarchy.
        """
        cell_gds = self.config.std_cell_gds.resolve()
        techlef = self.config.std_cell_techlef.resolve()
        lef = self.config.std_cell_lef.resolve()
        lef_ef = self.config.std_cell_lef_ef.resolve()
        layer_map = (
            self.config.pdk_root / 'sky130A/libs.tech/klayout/tech/sky130A.map'
        ).resolve()

        raw_gds = def_path.parent / f'{def_path.stem}_raw.gds'

        klayout_script = f"""\
import pya

layout = pya.Layout()

opt = pya.LoadLayoutOptions()
opt.lefdef_config.map_file = "{layer_map}"
opt.lefdef_config.lef_files = [
    "{techlef}",
    "{lef}",
    "{lef_ef}",
]
opt.lefdef_config.read_lef_with_def = True
opt.lefdef_config.produce_via_geometry = True
opt.lefdef_config.produce_cell_outlines = True

layout.read("{cell_gds}")
layout.read("{def_path.resolve()}", opt)
layout.write("{raw_gds}")
"""
        script_path = def_path.parent / 'def2gds.py'
        script_path.write_text(klayout_script)

        result = subprocess.run(
            ['klayout', '-b', '-r', str(script_path)],
            capture_output=True,
            text=True,
        )

        with open(log_path, 'a') as f:
            f.write('\n=== DEF to GDS (KLayout) ===\n')
            f.write(result.stdout)
            if result.stderr:
                f.write(result.stderr)

        if not raw_gds.exists():
            return False

        # Clean up: keep only cells in the design hierarchy
        import gdstk

        src = gdstk.read_gds(str(raw_gds))
        top_name = def_path.stem
        top_cell = None
        for c in src.cells:
            if c.name == top_name:
                top_cell = c
                break
        if top_cell is None:
            return False

        needed: set[str] = set()

        def _collect(cell):
            if cell.name in needed:
                return
            needed.add(cell.name)
            for ref in cell.references:
                _collect(ref.cell)

        _collect(top_cell)

        # Add power pin labels from DEF SPECIALNETS
        self._add_power_labels(top_cell, def_path)

        out = gdstk.Library(name=top_name)
        for c in src.cells:
            if c.name in needed:
                out.add(c)
        out.write_gds(str(gds_path))
        raw_gds.unlink(missing_ok=True)

        return gds_path.exists()

    @staticmethod
    def _add_power_labels(top_cell, def_path: Path) -> None:
        """Add GDS labels for power nets parsed from DEF SPECIALNETS.

        OpenROAD doesn't emit pin labels for power nets.  This parses
        the SPECIALNETS section of the DEF, picks the first M4 stripe
        for each power net (VDD, VSS), and adds a label at its midpoint
        so that :class:`GDSReader` can find them as pins.
        """
        import gdstk

        # GDS layer/texttype for pin labels (MET4 pin = 71/5)
        MET4_GDS = 71
        MET5_GDS = 72
        PIN_TEXTTYPE = 5

        text = def_path.read_text()

        # Extract SPECIALNETS block
        m = re.search(r'SPECIALNETS.*?END SPECIALNETS', text, re.DOTALL)
        if not m:
            return

        snet_block = m.group(0)

        # Parse each net and its first met4 STRIPE
        for net_name in ('VDD', 'VSS'):
            # Find the net definition
            pat = rf'- {net_name}\b.*?;'
            nm = re.search(pat, snet_block, re.DOTALL)
            if not nm:
                continue

            net_text = nm.group(0)

            # Find first met4 stripe with coordinates (vertical stripe)
            stripe = re.search(
                r'met4\s+1600\s+\+\s+SHAPE\s+STRIPE\s+\(\s*(\d+)\s+(\d+)\s*\)\s+\(\s*\1\s+(\d+)\s*\)',
                net_text,
            )
            if stripe:
                x = int(stripe.group(1))
                y0 = int(stripe.group(2))
                y1 = int(stripe.group(3))
                # Label at midpoint, DEF units are nm, GDS units are um
                lx = x / 1000.0
                ly = (y0 + y1) / 2000.0
                top_cell.add(gdstk.Label(
                    net_name, (lx, ly),
                    layer=MET4_GDS, texttype=PIN_TEXTTYPE,
                ))
                continue

            # Fallback: first met5 horizontal stripe
            stripe = re.search(
                r'met5\s+1600\s+\+\s+SHAPE\s+STRIPE\s+\(\s*(\d+)\s+(\d+)\s*\)\s+\(\s*(\d+)\s+\2\s*\)',
                net_text,
            )
            if stripe:
                x0 = int(stripe.group(1))
                y = int(stripe.group(2))
                x1 = int(stripe.group(3))
                lx = (x0 + x1) / 2000.0
                ly = y / 1000.0
                top_cell.add(gdstk.Label(
                    net_name, (lx, ly),
                    layer=MET5_GDS, texttype=PIN_TEXTTYPE,
                ))

    @staticmethod
    def _parse_sta(log: str) -> STAResult:
        """Parse WNS, TNS from OpenROAD/OpenSTA output."""
        result = STAResult(success=True, log_path=Path('.'))

        # Parse WNS: "wns max <value>" or "wns <value>"
        m = re.search(r'^wns\s+(?:max\s+)?([-\d.]+)', log, re.MULTILINE)
        if m:
            result.wns = float(m.group(1))

        # Parse TNS: "tns max <value>" or "tns <value>"
        m = re.search(r'^tns\s+(?:max\s+)?([-\d.]+)', log, re.MULTILINE)
        if m:
            result.tns = float(m.group(1))

        # Parse critical path endpoint from report_checks output
        m = re.search(r'Endpoint:\s+(\S+)', log)
        if m:
            result.critical_path = m.group(1)

        return result

    @staticmethod
    def _parse_clock_period(sdc_path: Path) -> float | None:
        """Extract clock period from SDC file."""
        sdc_path = Path(sdc_path)
        if not sdc_path.exists():
            return None
        text = sdc_path.read_text()
        m = re.search(r'create_clock.*-period\s+([\d.]+)', text)
        return float(m.group(1)) if m else None

    @staticmethod
    def _parse_design_stats(log: str) -> dict:
        """Parse design statistics from OpenROAD log."""
        report = {}

        m = re.search(r'Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%\s+utilization', log)
        if m:
            report['design_area_um2'] = float(m.group(1))
            report['utilization_pct'] = float(m.group(2))

        m = re.search(r'Number of instances:\s+(\d+)', log)
        if m:
            report['instances'] = int(m.group(1))

        return report
