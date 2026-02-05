"""SKY130 Transistor Layout Primitives (placeholder)."""

from pade.layout.cell import LayoutCell
from pade.layout import UM


class NFET_01V8(LayoutCell):
    """SKY130 1.8V NMOS transistor layout."""
    
    def __init__(self, instance_name: str, parent: LayoutCell = None,
                 w: int = 1 * UM, l: int = 150, nf: int = 1):
        super().__init__(instance_name, parent, cell_name='nfet_01v8')
        self.w, self.l, self.nf = w, l, nf
        raise NotImplementedError("NFET layout not yet implemented")


class PFET_01V8(LayoutCell):
    """SKY130 1.8V PMOS transistor layout."""
    
    def __init__(self, instance_name: str, parent: LayoutCell = None,
                 w: int = 1 * UM, l: int = 150, nf: int = 1):
        super().__init__(instance_name, parent, cell_name='pfet_01v8')
        self.w, self.l, self.nf = w, l, nf
        raise NotImplementedError("PFET layout not yet implemented")
