"""SKY130 MiM capacitor schematic primitive."""

from pade.core.cell import Cell
from pdk.sky130.pex import pex_enabled


_PDK_MODELS = {
    3: 'sky130_fd_pr__cap_mim_m3_1',  # M3/M4 (CAPM)
    4: 'sky130_fd_pr__cap_mim_m3_2',  # M4/M5 (CAPM2)
}


class _PdkCapMim(Cell):
    """Direct PDK MiM capacitor model instantiation."""

    def __init__(self, instance_name: str, parent: Cell, metal: int,
                 w: float, l: float, mult: int):
        super().__init__(instance_name, parent, cell_name=_PDK_MODELS[metal])
        self.add_terminal(['c0', 'c1'])
        self.set_parameter('w', w)
        self.set_parameter('l', l)
        self.set_parameter('mf', mult)


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

    def __init__(self,
                 instance_name: str,
                 parent: Cell = None,
                 w: float = 10.0,
                 l: float = 10.0,
                 metal: int = 4,
                 mult: int = 1):
        if metal not in _PDK_MODELS:
            raise ValueError(f"Invalid metal layer {metal}. Must be 3 or 4.")

        super().__init__(instance_name, parent, cell_name=f'cap_mim_m{metal}')
        self.add_terminal(['TOP', 'BOT'])
        self._metal = metal

        self.set_parameter('w', w)
        self.set_parameter('l', l)
        self.set_parameter('mult', mult)

        cap = _PdkCapMim('XC', self, metal=metal, w=w, l=l, mult=mult)
        cap.connect(['c0', 'c1'], ['TOP', 'BOT'])

    @property
    def metal(self) -> int:
        return self._metal


# CapMimPex = pex_enabled(CapMim)
