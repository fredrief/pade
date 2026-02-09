from pade.core.cell import Cell
from pdk.sky130.primitives.transistors.schematic import Nfet01v8, Pfet01v8


class IVX(Cell):
    """
    CMOS Inverter.

    Parameters:
        instance_name: Instance name
        parent: Parent cell
        wn: NFET width in um
        wp: PFET width in um
        l: Gate length in um
        nf: Number of fingers
    """

    def __init__(self,
                 instance_name: str,
                 parent: Cell = None,
                 wn: float = 1.0,
                 wp: float = 2.0,
                 l: float = 0.15,
                 nf: int = 1):
        super().__init__(instance_name, parent, cell_name='inverter')
        self.add_terminal(['IN', 'OUT', 'VDD', 'VSS'])

        self.set_parameter('wn', wn)
        self.set_parameter('wp', wp)
        self.set_parameter('l', l)
        self.set_parameter('nf', nf)

        self.MP = Pfet01v8('MP', self, w=wp, l=l, nf=nf)
        self.MP.connect(['d', 'g', 's', 'b'], ['OUT', 'IN', 'VDD', 'VDD'])

        self.MN = Nfet01v8('MN', self, w=wn, l=l, nf=nf)
        self.MN.connect(['d', 'g', 's', 'b'], ['OUT', 'IN', 'VSS', 'VSS'])
