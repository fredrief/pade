"""
Initial condition statement.
"""

from pade.statement.base import Statement


class IC(Statement):
    """
    Initial conditions statement.

    Args:
        **conditions: Node=value pairs

    Examples:
        IC(out=0, vdd=1.8)
        IC(**{'net1': 0.5, 'net2': 1.0})
    """

    def __init__(self, **conditions):
        super().__init__()
        self.conditions = conditions

    def __repr__(self) -> str:
        cond_str = ', '.join(f'{k}={v!r}' for k, v in self.conditions.items())
        return f"IC({cond_str})"
