"""
Save/output selection statement.
"""

from typing import Optional

from pade.statement.base import Statement


class Save(Statement):
    """
    Output selection statement.

    Args:
        signals: List of signals to save
        **settings: Additional save settings

    Examples:
        Save(['out', 'vdd', 'I0:drain'])
        Save(['out'], nestlvl=2)
    """

    def __init__(self, signals: Optional[list[str]] = None, **settings):
        super().__init__()
        self.signals = signals or []
        self.settings = settings

    def __repr__(self) -> str:
        return f"Save({self.signals!r})"
