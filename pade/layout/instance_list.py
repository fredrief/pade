"""
LayoutInstanceList - Wrapper for multiple layout instances (mult > 1).

When a layout cell has mult > 1, LayoutCell.instantiate() returns this wrapper so that:
- self.MP1A[i] always works (mult=1 or mult>1).
- When mult=1: self.MP1A.G forwards to the single cell.
- When mult>1: self.MP1A.G raises (use self.MP1A[i].G); methods broadcast to all.
"""

from typing import List


class LayoutInstanceList:
    """
    List-like wrapper around multiple LayoutCells from a single schematic instance with mult > 1.

    - __getitem__(i), __len__, __iter__: access individual cells.
    - When len==1: attribute access (e.g. .G) forwards to the single cell.
    - When len>1: callable attributes broadcast to all cells; non-callable raise.
    """

    def __init__(self, cells: List) -> None:
        if not cells:
            raise ValueError("LayoutInstanceList requires at least one cell")
        self._cells = cells

    def __len__(self) -> int:
        return len(self._cells)

    def __getitem__(self, i: int):
        return self._cells[i]

    def __iter__(self):
        return iter(self._cells)

    def __getattr__(self, name: str):
        cells = self._cells
        if len(cells) == 1:
            return getattr(cells[0], name)
        val = getattr(cells[0], name)
        if callable(val):
            def broadcast(*args, **kwargs):
                for c in cells:
                    getattr(c, name)(*args, **kwargs)
                return self
            return broadcast
        raise AttributeError(
            f"'{name}' is ambiguous when mult > 1; use index, e.g. self.MP1A[i].{name}"
        )
