"""SKY130 Capacitor Layout Primitives."""

from pdk.sky130.rules import sky130_rules
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import M4, M5, CAPM2, VIA4


class CapMimM4Layout(SKY130LayoutCell):
    """
    MiM capacitor layout using M4/M5 with CAPM2 and VIA4 contact.

    Parameters (dimensions in um):
        width: Cap width (default 10 um)
        height: Cap height (default 10 um)
        schematic: Optional schematic Cell instance (extracts w, l as width, height)
    """

    def __init__(self,
                 instance_name: str,
                 parent: SKY130LayoutCell = None,
                 schematic=None,
                 width: float = 10.0,
                 height: float = 10.0):
        if schematic is not None:
            width = float(schematic.get_parameter('w'))
            height = float(schematic.get_parameter('l'))

        super().__init__(instance_name, parent, cell_name='cap_mim_m4',
                         schematic=schematic)

        w_nm = self.to_nm(width)
        h_nm = self.to_nm(height)
        self.width = w_nm
        self.height = h_nm

        m4_enc = sky130_rules.CAPM2.ENC_BY_M4
        m5_enc = sky130_rules.VIA4.ENC_TOP

        self.add_rect(M4, -m4_enc, -m4_enc, w_nm + m4_enc, h_nm + m4_enc, net='MINUS')
        self.add_rect(CAPM2, 0, 0, w_nm, h_nm)

        via_margin = m5_enc
        self._add_via4_array(via_margin)

        self.add_rect(M5, 0, 0, w_nm, h_nm, net='PLUS')

        self.add_port('MINUS', M4, 0, 0)
        self.add_port('PLUS', M5, w_nm // 2, h_nm // 2)

    def _add_via4_array(self, margin: int):
        """Add VIA4 array inside the cap region."""
        via_w = sky130_rules.VIA4.W
        via_s = sky130_rules.VIA4.S
        pitch = via_w + via_s

        x = margin
        while x + via_w <= self.width - margin:
            y = margin
            while y + via_w <= self.height - margin:
                self.add_rect(VIA4, x, y, x + via_w, y + via_w, net='PLUS')
                y += pitch
            x += pitch
