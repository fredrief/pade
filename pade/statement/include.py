"""
Include statement.
"""

from typing import Optional

from pade.statement.base import Statement


class Include(Statement):
    """
    Include file statement (for model files, corners, etc.)

    Args:
        path: Path to file to include
        selector: Optional selector string (appended after path in include statement)

    The selector is backend-specific and appended as-is. Examples:
        - Spectre section: 'section=tt'
        - Spectre corner: 'resistor=ff nmos=tt pmos=tt'

    Examples:
        Include('/path/to/models.scs')
        Include('/path/to/models.scs', selector='section=tt')
        Include('/path/to/wrapper.scs', selector='resistor=ff')
    """

    def __init__(self, path: str, selector: Optional[str] = None):
        super().__init__()
        self.path = path
        self.selector = selector

    def __repr__(self) -> str:
        if self.selector:
            return f"Include({self.path!r}, selector={self.selector!r})"
        return f"Include({self.path!r})"
