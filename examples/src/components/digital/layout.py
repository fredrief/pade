"""CMOS Inverter layout."""

from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.primitives.transistors.layout import NFET_01V8_Layout, PFET_01V8_Layout
from pdk.sky130.layers import POLY, M1
from pade.core.cell import Cell


class IVXLayout(SKY130LayoutCell):
    """
    CMOS Inverter layout: NFET left, PFET right.

    Parameters:
        instance_name: Instance name
        schematic: IVX schematic
        parent: Optional parent layout cell
    """

    def __init__(self,
                 instance_name: str,
                 schematic: Cell,
                 parent: SKY130LayoutCell = None
                 ):
        super().__init__(instance_name, parent, cell_name='IVX',
                         schematic=schematic)
        self.MN = NFET_01V8_Layout('MN', self, schematic=schematic.MN, tap='left')
        self.MP = PFET_01V8_Layout('MP', self, schematic=schematic.MP, tap='right')
        self.MP.align('right', self.MN, margin=self.rules.NWELL.S_DIFF)
        self._route(schematic)

    def _route(self, schematic):
        nf = int(schematic.MN.get_parameter('nf'))
        gate_l = self.to_nm(float(schematic.MN.get_parameter('l')))

        # Gate and dummy poly: bridge all stripes between transistors
        self.route(self.MN.DBOT, self.MP.DBOT, POLY, how='-', width=gate_l, net='IN')
        for i in range(nf):
            self.route(getattr(self.MN, f'G{i}'), getattr(self.MP, f'G{i}'),
                       POLY, how='-', width=gate_l, net='IN')
        self.route(self.MN.DTOP, self.MP.DTOP, POLY, how='-', width=gate_l, net='IN')

        # Drain: straight M1
        MN_DPORT = self.MN.DBUS if nf > 2 else self.MN.D
        MP_DPORT = self.MP.DBUS if nf > 2 else self.MP.D
        self.route(MN_DPORT, MP_DPORT, M1, how='-', net='OUT')

        # Source to tap: straight M1
        self.route(self.MN.S, self.MN.B, M1, how='-', net='VSS')
        self.route(self.MP.S, self.MP.B, M1, how='-', net='VDD')
