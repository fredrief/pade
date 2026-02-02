"""
Ideal passive components.
"""

from pade.core import Cell


class R(Cell):
    """Ideal resistor."""

    def __init__(self,
                 instance_name: str,
                 parent: Cell,
                 r: float,
                 **kwargs):
        super().__init__(instance_name, parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('r', r)


class C(Cell):
    """Ideal capacitor."""

    def __init__(self,
                 instance_name: str,
                 parent: Cell,
                 c: float,
                 **kwargs):
        super().__init__(instance_name, parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('c', c)


class L(Cell):
    """Ideal inductor."""

    def __init__(self,
                 instance_name: str,
                 parent: Cell,
                 l: float,
                 **kwargs):
        super().__init__(instance_name, parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('l', l)
