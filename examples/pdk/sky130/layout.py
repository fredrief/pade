"""SKY130 LayoutCell with config support."""

from typing import Optional
from pade.layout.cell import LayoutCell
from pade.layout.shape import Layer
from pade.layout.port import Port
from pdk.sky130.rules import sky130_rules


class SKY130LayoutCell(LayoutCell):
    """LayoutCell with SKY130 config. add_port() uses sky130_rules.port_size as default."""
    
    def __init__(self,
                 instance_name: str,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 **kwargs):
        super().__init__(instance_name, parent, cell_name, **kwargs)
        self.rules = sky130_rules
    
    def add_port(self, name: str, layer: Layer,
                 x: int, y: int,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 net: Optional[str] = None) -> Port:
        """Add port at (x,y). Uses rules.port_size if width/height not provided."""
        if width is None:
            width = self.rules.port_size
        if height is None:
            height = self.rules.port_size
        
        x0 = x - width // 2
        y0 = y - height // 2
        x1 = x + width // 2
        y1 = y + height // 2
        
        return super().add_port(name, layer, x0, y0, x1, y1, net)
