"""
Base Statement class.
"""


from typing import Optional

class Statement:
    """
    Base class for netlist statements.

    Can be used directly for raw text, or inherited for structured statements.

    Examples:
        Statement('// custom comment')
        Statement('simulator lang=spectre')
    """

    def __init__(self, raw: Optional[str] = None):
        self.raw = raw

    def __repr__(self) -> str:
        if self.raw:
            return f"Statement({self.raw!r})"
        return f"{self.__class__.__name__}()"
