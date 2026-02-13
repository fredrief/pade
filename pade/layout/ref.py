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


class Point(tuple):
    """Tuple with element-wise arithmetic for layout coordinates.

    Optionally carries ``layer`` and ``net`` metadata so that route
    endpoints remember which layer they live on.  Indexing and unpacking
    still yield ``(x, y)``; layer/net are attributes only.
    """

    def __new__(cls, x, y, layer=None, net=None, ref=None):
        pt = super().__new__(cls, (x, y))
        pt.layer = layer
        pt.net = net
        pt.ref = ref
        return pt

    def __add__(self, other):
        return Point(self[0] + other[0], self[1] + other[1],
                     layer=self.layer, net=self.net, ref=self.ref)

    def __radd__(self, other):
        return Point(self[0] + other[0], self[1] + other[1],
                     layer=self.layer, net=self.net, ref=self.ref)

    def __sub__(self, other):
        return Point(self[0] - other[0], self[1] - other[1],
                     layer=self.layer, net=self.net, ref=self.ref)

    def __rsub__(self, other):
        return Point(other[0] - self[0], other[1] - self[1],
                     layer=self.layer, net=self.net, ref=self.ref)

    def on_layer(self, layer) -> 'Point':
        """Return a new Point with the same coordinates but a different layer."""
        return Point(self[0], self[1], layer=layer, net=self.net, ref=self.ref)

    def __repr__(self):
        extra = ''
        if self.layer is not None:
            extra += f', layer={self.layer.name}'
        if self.net is not None:
            extra += f', net={self.net!r}'
        return f"Point({self[0]}, {self[1]}{extra})"


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
    def local_center(self) -> Tuple[int, int]:
        """Center in local (cell) coordinates."""
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

    def _to_absolute(self, lx: int, ly: int) -> Point:
        """Transform a local point to absolute (root) coordinates.

        The returned Point carries this Ref's layer and net.
        """
        x, y = lx, ly
        cell = self.cell
        while cell is not None:
            x, y = cell.transform.apply_point(x, y)
            cell = cell.parent
        return Point(x, y, layer=self.layer, net=self.net, ref=self)

    # -- Compass properties (absolute coordinates) --

    @property
    def center(self) -> Point:
        """Center in absolute (root) coordinates."""
        cx, cy = self.local_center
        return self._to_absolute(cx, cy)

    @property
    def north(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute((b[0] + b[2]) // 2, b[3])

    @property
    def south(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute((b[0] + b[2]) // 2, b[1])

    @property
    def east(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[2], (b[1] + b[3]) // 2)

    @property
    def west(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[0], (b[1] + b[3]) // 2)

    @property
    def ne(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[2], b[3])

    @property
    def nw(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[0], b[3])

    @property
    def se(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[2], b[1])

    @property
    def sw(self) -> Point:
        b = self.shape.bounds
        return self._to_absolute(b[0], b[1])

    def __repr__(self):
        return f"Ref({self.name}, layer={self.layer.name}, center={self.local_center})"


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
        return f"Pin({self.name}, terminal={self.terminal}, layer={self.layer.name}, center={self.local_center})"
