"""SKY130 MiM capacitor schematic primitive."""

from pathlib import Path

from pade.core.cell import Cell
from pade.backends.ngspice.netlist_reader import load_subckt
from pdk.sky130.pex import pex_enabled

_DEVICE_DIR = Path(__file__).parent

_PDK_CLASSES = {
    3: load_subckt(_DEVICE_DIR / 'cap_mim_m3_1.spice'),  # M3/M4 (CAPM)
    4: load_subckt(_DEVICE_DIR / 'cap_mim_m3_2.spice'),  # M4/M5 (CAPM2)
}


@pex_enabled
class CapMim(Cell):
    """
    SKY130 MiM capacitor.

    Parameters:
        instance_name: Instance name
        parent: Parent cell
        w: Width in um (default 10)
        l: Length in um (default 10)
        metal: Metal layer - 3 (M3/M4) or 4 (M4/M5)
        mult: Multiplier (default 1)
    """

    def __init__(self, instance_name=None, parent=None, w: float = 10.0, l: float = 10.0,
                 metal: int = 4, mult: int = 1, **kwargs):
        if metal not in _PDK_CLASSES:
            raise ValueError(f"Invalid metal layer {metal}. Must be 3 or 4.")
        super().__init__(instance_name=instance_name, parent=parent, cell_name=f'cap_mim_m{metal}', **kwargs)
        self.add_terminal(['TOP', 'BOT'])
        self._metal = metal

        self.set_parameter('w', w)
        self.set_parameter('l', l)
        self.set_parameter('mult', mult)

        self.XC = _PDK_CLASSES[metal](w=w, l=l, mf=mult)
        self.XC.connect(['c0', 'c1'], ['TOP', 'BOT'])

    @property
    def metal(self) -> int:
        return self._metal
