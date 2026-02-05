"""SKY130 Capacitor Layout Primitives."""

from pade.layout import UM
from pdk.sky130.rules import sky130_rules
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import M4, M5, CAPM2, VIA4


class CapMimM4Layout(SKY130LayoutCell):
    """
    MiM capacitor layout using M4/M5 with CAPM2 and VIA4 contact.
    
    Structure (cross-section):
        M5 (top plate, PLUS) ----+
        VIA4 (mim2cc contact)    |
        CAPM2 (dielectric)       | capacitor
        M4 (bottom plate, MINUS)-+
    
    M4 extends beyond CAPM2 per DRC rules.
    """
    
    def __init__(self,
                 instance_name: str,
                 parent: SKY130LayoutCell = None,
                 width: int = 10 * UM,
                 height: int = 10 * UM):
        super().__init__(instance_name, parent, cell_name='cap_mim_m4')
        
        # Cap dimensions (CAPM2 size)
        self.width = width
        self.height = height
        
        # Calculate layer sizes
        m4_enc = sky130_rules.CAPM2.ENC_BY_M4  # M4 extends beyond CAPM2
        m5_enc = sky130_rules.VIA4.ENC_TOP     # M5 enclosure of VIA4
        
        # Bottom plate (M4) - extends beyond CAPM2
        self.add_rect(M4, -m4_enc, -m4_enc, width + m4_enc, height + m4_enc, net='MINUS')
        
        # MiM cap marker layer (defines capacitor area)
        self.add_rect(CAPM2, 0, 0, width, height)
        
        # VIA4 array (forms mim2cc contact inside CAPM2)
        via_margin = m5_enc  # VIA4 must be enclosed by M5
        self._add_via4_array(via_margin)
        
        # Top plate (M5) - sized to enclose VIA4 array
        self.add_rect(M5, 0, 0, width, height, net='PLUS')
        
        # Ports for LVS (must be inside the metal region)
        self.add_port('MINUS', M4, 0, 0)  # Inside M4 overlap with CAPM2
        self.add_port('PLUS', M5, width // 2, height // 2)  # Center of M5
    
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
