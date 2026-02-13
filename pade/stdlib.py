"""Standard library of ideal components."""

from pade.core.cell import Cell


class V(Cell):
    """
    Ideal voltage source.

    Args:
        instance_name: Instance name
        parent: Parent cell
        **params: Source parameters (dc, ac, type, ampl, freq, etc.)

    Examples:
        self.V1 = V(dc=1.8)
        self.V2 = V(dc=0.9, ac=1e-3)
    """

    def __init__(self, instance_name=None, parent=None, **params):
        config = {k: v for k, v in params.items() if k.startswith('_')}
        source_params = {k: v for k, v in params.items() if not k.startswith('_')}
        super().__init__(instance_name=instance_name, parent=parent, **config)
        self.add_terminal(['p', 'n'])
        for name, value in source_params.items():
            self.set_parameter(name, value)


class I(Cell):
    """
    Ideal current source.

    Args:
        instance_name: Instance name
        parent: Parent cell
        **params: Source parameters (dc, ac, type, ampl, freq, etc.)
    """

    def __init__(self, instance_name=None, parent=None, **params):
        config = {k: v for k, v in params.items() if k.startswith('_')}
        source_params = {k: v for k, v in params.items() if not k.startswith('_')}
        super().__init__(instance_name=instance_name, parent=parent, **config)
        self.add_terminal(['p', 'n'])
        for name, value in source_params.items():
            self.set_parameter(name, value)


class R(Cell):
    """Ideal resistor."""

    def __init__(self, instance_name=None, parent=None, r: float = None, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('r', r)


class C(Cell):
    """Ideal capacitor."""

    def __init__(self, instance_name=None, parent=None, c: float = None, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('c', c)


class L(Cell):
    """Ideal inductor."""

    def __init__(self, instance_name=None, parent=None, l: float = None, **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('l', l)


class B(Cell):
    """
    Behavioral voltage or current source (NGSpice B-source, Spectre equivalent).
    Expression may reference node voltages in the same (sub)circuit, e.g. V(in), V(vdd,0).
    """

    def __init__(self, instance_name=None, parent=None, expr: str = None, type: str = 'V', **kwargs):
        super().__init__(instance_name=instance_name, parent=parent, **kwargs)
        self.add_terminal(['p', 'n'])
        self.set_parameter('expr', expr)
        self.set_parameter('type', type)
