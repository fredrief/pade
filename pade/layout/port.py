"""
Port - A routing reference point on a layout cell.

Ports are purely Python-side references for convenient routing between cells.
They have no direct LVS significance; layout writers generate labels from
schematic terminals and shape nets instead.
"""

from dataclasses import dataclass
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


@dataclass
class Port:
    """
    A routing reference on a layout cell.

    Attributes:
        name: Python access key (e.g., 'G0', 'IN', 'D')
        cell: The LayoutCell this port belongs to
        layer: Layer the port is on
        x0, y0, x1, y1: Port geometry bounds (in cell's local coordinates, nm)
        net: Net name for connectivity (from shape or schematic)
    """
    name: str
    cell: 'LayoutCell'
    layer: 'Layer'
    x0: int
    y0: int
    x1: int
    y1: int
    net: str

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return bounds in local coordinates."""
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def center(self) -> Tuple[int, int]:
        """Return center point in local coordinates."""
        return ((self.x0 + self.x1) // 2, (self.y0 + self.y1) // 2)

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    def get_center_absolute(self) -> Tuple[int, int]:
        """
        Get center point in root cell coordinates.

        Traverses hierarchy and applies transforms.
        """
        cx, cy = self.center
        cell = self.cell

        while cell is not None:
            cx, cy = cell.transform.apply_point(cx, cy)
            cell = cell.parent

        return (cx, cy)

    def __repr__(self):
        return f"Port({self.name}, layer={self.layer.name}, center={self.center})"
