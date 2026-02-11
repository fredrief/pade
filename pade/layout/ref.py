"""
Ref and Pin - Layout reference points and cell interface pins.

Ref (reference point) is a named pointer to a shape location, used for
routing and placement.  It has no schematic significance.

Pin is a Ref that additionally represents a cell terminal for LVS.
The GDS writer generates labels from pins.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer, Shape


@dataclass
class Ref:
    """
    A named reference point on a layout cell.

    Points to a shape's location and layer.  Used for routing and
    placement convenience (e.g., ``self.MN.D``, ``self.MN.DBOT``).

    Attributes:
        name: Access key (e.g., 'G0', 'D', 'DBOT')
        cell: The LayoutCell this ref belongs to
        shape: The underlying Shape (carries layer, bounds, net)
    """
    name: str
    cell: 'LayoutCell'
    shape: 'Shape' = field(repr=False)

    @property
    def layer(self) -> 'Layer':
        return self.shape.layer

    @property
    def net(self) -> Optional[str]:
        return self.shape.net

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return bounds in local coordinates."""
        return self.shape.bounds

    @property
    def x0(self) -> int:
        return self.shape.bounds[0]

    @property
    def y0(self) -> int:
        return self.shape.bounds[1]

    @property
    def x1(self) -> int:
        return self.shape.bounds[2]

    @property
    def y1(self) -> int:
        return self.shape.bounds[3]

    @property
    def center(self) -> Tuple[int, int]:
        """Return center point in local coordinates."""
        b = self.shape.bounds
        return ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)

    @property
    def width(self) -> int:
        b = self.shape.bounds
        return b[2] - b[0]

    @property
    def height(self) -> int:
        b = self.shape.bounds
        return b[3] - b[1]

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
        return f"Ref({self.name}, layer={self.layer.name}, center={self.center})"


@dataclass
class Pin(Ref):
    """
    A cell interface pin — a Ref with LVS significance.

    Maps to a schematic terminal.  The GDS writer generates labels
    from pins.  A Pin is also a Ref, so it can be used for routing.

    Attributes:
        terminal: Schematic terminal name (same as name by default)
    """
    terminal: str = ''

    def __post_init__(self):
        if not self.terminal:
            self.terminal = self.name

    def __repr__(self):
        return f"Pin({self.name}, terminal={self.terminal}, layer={self.layer.name}, center={self.center})"
