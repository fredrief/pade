"""
Options statement.
"""

from pade.statement.base import Statement


class Options(Statement):
    """
    Simulator options statement.

    Args:
        name: Instance name (defaults to 'opts')
        **params: Option parameters

    Examples:
        Options(reltol=1e-6, vabstol=1e-9)
        Options('myopts', temp=27)
    """

    def __init__(self, name: str = 'opts', **params):
        super().__init__()
        self.name = name
        self.params = params

    def __repr__(self) -> str:
        params_str = ', '.join(f'{k}={v!r}' for k, v in self.params.items())
        return f"Options({self.name!r}, {params_str})"
