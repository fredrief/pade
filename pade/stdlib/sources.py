"""
Ideal voltage and current sources.
"""

from pade.core import Cell


class V(Cell):
    """
    Ideal voltage source.

    Args:
        instance_name: Instance name
        parent: Parent cell
        **params: Source parameters (dc, ac, type, ampl, freq, etc.)

    Examples:
        V('V1', tb, dc=1.8)
        V('V2', tb, dc=0.9, ac=1e-3)
        V('V3', tb, type='sine', sinedc=0, ampl=1, freq=1e3)
    """

    def __init__(self,
                 instance_name: str,
                 parent: Cell,
                 **params):
        config = {k: v for k, v in params.items() if k.startswith('_')}
        source_params = {k: v for k, v in params.items() if not k.startswith('_')}

        super().__init__(instance_name, parent, **config)
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

    def __init__(self,
                 instance_name: str,
                 parent: Cell,
                 **params):
        config = {k: v for k, v in params.items() if k.startswith('_')}
        source_params = {k: v for k, v in params.items() if not k.startswith('_')}

        super().__init__(instance_name, parent, **config)
        self.add_terminal(['p', 'n'])

        for name, value in source_params.items():
            self.set_parameter(name, value)
