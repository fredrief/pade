"""SKY130 MiM Capacitor Layout."""

from pdk.sky130.rules import sky130_rules
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import M3, M4, M5, CAPM, CAPM2, VIA3, VIA4


class CapMimLayout(SKY130LayoutCell):
    """
    MiM capacitor layout.

    Parameters:
        instance_name: Instance name
        parent: Parent layout cell
        schematic: Schematic CapMim Cell (extracts w, l, metal)
    """

    def __init__(self,
                 instance_name: str,
                 parent: SKY130LayoutCell,
                 schematic):
        w = float(schematic.get_parameter('w'))
        l = float(schematic.get_parameter('l'))
        metal = schematic.metal

        if metal not in (3, 4):
            raise ValueError(f"Invalid metal layer {metal}. Must be 3 or 4.")

        super().__init__(instance_name, parent, cell_name=f'cap_mim_m{metal}',
                         schematic=schematic)

        w_nm = self.to_nm(w)
        h_nm = self.to_nm(l)

        if metal == 3:
            self._draw_m3_cap(w_nm, h_nm)
        else:
            self._draw_m4_cap(w_nm, h_nm)

    def _draw_m3_cap(self, w: int, h: int):
        """Draw M3/M4 capacitor (CAPM layer)."""
        m3_enc = sky130_rules.CAPM.ENC_BY_M3
        m4_enc = sky130_rules.VIA3.ENC_TOP

        bot = self.add_rect(M3, -m3_enc, -m3_enc, w + m3_enc, h + m3_enc, net='BOT')
        self.add_rect(CAPM, 0, 0, w, h)
        self._add_via_array(VIA3, sky130_rules.VIA3.W, sky130_rules.VIA3.S,
                            m4_enc, w, h, net='TOP')
        top = self.add_rect(M4, 0, 0, w, h, net='TOP')

        self.add_pin('TOP', top)
        self.add_pin('BOT', bot)

    def _draw_m4_cap(self, w: int, h: int):
        """Draw M4/M5 capacitor (CAPM2 layer)."""
        m4_enc = sky130_rules.CAPM2.ENC_BY_M4
        m5_enc = sky130_rules.VIA4.ENC_TOP

        bot = self.add_rect(M4, -m4_enc, -m4_enc, w + m4_enc, h + m4_enc, net='BOT')
        self.add_rect(CAPM2, 0, 0, w, h)
        self._add_via_array(VIA4, sky130_rules.VIA4.W, sky130_rules.VIA4.S,
                            m5_enc, w, h, net='TOP')
        top = self.add_rect(M5, 0, 0, w, h, net='TOP')

        self.add_pin('TOP', top)
        self.add_pin('BOT', bot)

    def _add_via_array(self, layer, via_w: int, via_s: int, margin: int,
                       cap_w: int, cap_h: int, net: str):
        """Add via array inside capacitor region."""
        pitch = via_w + via_s
        x = margin
        while x + via_w <= cap_w - margin:
            y = margin
            while y + via_w <= cap_h - margin:
                self.add_rect(layer, x, y, x + via_w, y + via_w, net=net)
                y += pitch
            x += pitch
