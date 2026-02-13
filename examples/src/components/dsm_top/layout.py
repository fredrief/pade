"""DSM top-level layout: analog Mod1 + digital CIC decimation filter."""

import sys
from pathlib import Path
_examples = Path(__file__).resolve().parents[3]
if str(_examples) not in sys.path:
    sys.path.insert(0, str(_examples.parent))
    sys.path.insert(0, str(_examples))

from pade.backends.gds.layout_reader import GDSReader
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import M3, M4, M5, sky130_layers
from src.components.mod1.layout import Mod1Layout
from src.components.mod1.schematic import Mod1

# Path to CIC filter GDS from OpenROAD P&R
CIC_GDS = _examples / 'work' / 'cic_pnr' / 'cic_filter.gds'


class DsmTopLayout(SKY130LayoutCell):
    """Top-level delta-sigma modulator + CIC decimation filter."""

    def __init__(self, instance_name=None, parent=None, mod1_schematic=None):
        super().__init__(instance_name, parent, cell_name='DsmTop')

        gap = self.to_nm(4.0)  # 4 um between blocks

        # --- Analog: Mod1 sigma-delta modulator ---
        self.MOD1 = Mod1Layout(schematic=mod1_schematic)

        # --- Digital: CIC filter (loaded from P&R GDS) ---
        reader = GDSReader(layer_map=sky130_layers, pin_texttypes={0, 5, 16})
        cic = reader.read(str(CIC_GDS), cell_name='cic_filter')
        cic.parent = self
        self.CIC = cic

        # --- Placement: CIC to the right of MOD1 ---
        self.CIC.align('right', self.MOD1, margin=gap)

        self._route()

    def _cic_pin(self, name):
        """Access CIC pin by name, with bus-notation fallback (name[0])."""
        if name in self.CIC.refs:
            return self.CIC.refs[name]
        bus = f'{name}[0]'
        if bus in self.CIC.refs:
            return self.CIC.refs[bus]
        raise KeyError(
            f"CIC pin '{name}' not found. "
            f"Available: {sorted(self.CIC.pins.keys())}"
        )

    def _route(self):
        # --- Signal interface: analog → digital ---
        # Bitstream: Mod1 comparator output → CIC input
        pass
        self.route(self.MOD1.out, self._cic_pin('din'), (M3, M4), how='|-', net='out', track_end=-10, track=-10, via_nx_start=2, via_ny_start=2)



def _main():
    from pade.backends.gds.layout_writer import GDSWriter
    from pdk.sky130.config import config
    from utils.design_runner import DesignRunner

    mod1_sch = Mod1('dut')
    layout = DsmTopLayout('dut', mod1_schematic=mod1_sch)

    # Debug: show what the GDS reader found on the CIC block
    print(f'CIC cell_name: {layout.CIC.cell_name}')
    print(f'CIC pins ({len(layout.CIC.pins)}): {sorted(layout.CIC.pins.keys())}')
    print(f'CIC subcells: {len(layout.CIC.subcells)}')
    print(f'CIC bbox: {layout.CIC.bbox()}')
    print()

    writer = GDSWriter(layer_map=sky130_layers)
    writer.write(layout, config.layout_dir)
    print(f'GDS written to {config.layout_dir / "DsmTop.gds"}')
    print(f'Top-level pins: {sorted(layout.pins.keys())}')
    print()

    print('Shorts:')
    result = layout.check_shorts()
    print(f'    {result.summary()}  {"PASS" if result.clean else "FAIL"}')

    runner = DesignRunner(layout)
    dr = runner.run_all(drc=True, lvs=False, pex=False)
    print(dr)
    sys.exit(0 if dr.passed else 1)


if __name__ == '__main__':
    _main()
