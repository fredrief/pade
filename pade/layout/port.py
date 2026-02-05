"""
Port class for layout connectivity and LVS.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


@dataclass
class Port:
    """
    A port/pin on a layout cell for connectivity.

    Ports are used for:
    - LVS pin recognition
    - Routing connection points
    - Hierarchical connectivity

    Attributes:
        name: Port name (e.g., 'D', 'G', 'S', 'PLUS', 'MINUS')
        cell: The LayoutCell this port belongs to
        layer: Layer the port is on
        x0, y0, x1, y1: Port geometry bounds (in cell's local coordinates, nm)
        net: Net name for this port
    """
    name: str
    cell: 'LayoutCell'
    layer: 'Layer'
    x0: int
    y0: int
    x1: int
    y1: int
    net: Optional[str] = None

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
