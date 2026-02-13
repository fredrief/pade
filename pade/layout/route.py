"""
Route class for drawing connected path segments.
"""

from typing import List, Tuple, Optional, Union, TYPE_CHECKING

from pade.layout.ref import Point

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


class RouteSegment:
    """A single segment of a route (between two consecutive waypoints).

    ``start`` and ``end`` are :class:`Point` objects that carry optional
    ``layer`` and ``net`` metadata.  ``segment.layer`` and
    ``segment.net`` are derived from ``start``.
    """

    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end

    @property
    def layer(self) -> Optional['Layer']:
        return getattr(self.start, 'layer', None)

    @property
    def net(self) -> Optional[str]:
        return getattr(self.start, 'net', None)

    @property
    def center(self) -> Point:
        x0, y0 = self.start
        x1, y1 = self.end
        return Point((x0 + x1) // 2, (y0 + y1) // 2,
                     layer=self.layer, net=self.net)

    @property
    def c(self) -> Point:
        """Alias for center."""
        return self.center


class Route:
    """
    A route consisting of connected path segments.

    Routes are defined by a list of waypoints. Segments are drawn between
    consecutive waypoints, with proper corner handling.

    ``layer`` may be a single :class:`Layer` (applied to every segment)
    or a list of layers (one per segment).
    """

    def __init__(self, points: List[Tuple[int, int]],
                 layer: Union['Layer', List['Layer']],
                 width: int, net: Optional[str] = None,
                 end_style: str = 'extend'):
        """
        Create a route.

        Args:
            points: List of (x, y) waypoints in nm. Minimum 2 points.
            layer: Single layer for all segments, or list of per-segment layers.
            width: Segment width in nm
            net: Optional net name for connectivity
            end_style: Segment endpoint handling:
                ``'extend'`` — each segment overshoots its endpoints
                by ``width/2``, filling corners and route ends (default).
                ``'flush'`` — segments end exactly at the waypoint
                coordinates.
        """
        if len(points) < 2:
            raise ValueError("Route requires at least 2 points")
        if end_style not in ('extend', 'flush'):
            raise ValueError(f"end_style must be 'extend' or 'flush', got '{end_style}'")

        self.points = points
        n_seg = len(points) - 1
        if isinstance(layer, list):
            self.layers = layer
        else:
            self.layers = [layer] * n_seg
        self.width = width
        self.net = net
        self.end_style = end_style

    @property
    def layer(self) -> 'Layer':
        """Primary layer (first segment)."""
        return self.layers[0]

    def draw(self, cell: 'LayoutCell') -> 'Route':
        """
        Draw route segments into cell.

        Returns self for chaining.
        """
        hw = self.width // 2  # half width
        ext = hw if self.end_style == 'extend' else 0

        for i in range(len(self.points) - 1):
            x0, y0 = self.points[i]
            x1, y1 = self.points[i + 1]
            ly = self.layers[i]

            # Determine segment orientation
            if y0 == y1:
                # Horizontal segment
                left = min(x0, x1) - ext
                right = max(x0, x1) + ext
                cell.add_rect(ly, left, y0 - hw, right, y0 + hw, net=self.net)
            elif x0 == x1:
                # Vertical segment
                bottom = min(y0, y1) - ext
                top = max(y0, y1) + ext
                cell.add_rect(ly, x0 - hw, bottom, x0 + hw, top, net=self.net)
            else:
                raise ValueError(f"Diagonal segments not supported: ({x0},{y0}) to ({x1},{y1})")

        return self

    @property
    def length(self) -> int:
        """Total route length in nm."""
        total = 0
        for i in range(len(self.points) - 1):
            x0, y0 = self.points[i]
            x1, y1 = self.points[i + 1]
            total += abs(x1 - x0) + abs(y1 - y0)
        return total

    @property
    def start(self) -> Point:
        """First point of the route (layer of first segment, with net)."""
        return Point(self.points[0][0], self.points[0][1],
                     layer=self.layers[0], net=self.net)

    @property
    def end(self) -> Point:
        """Last point of the route (layer of last segment, with net)."""
        return Point(self.points[-1][0], self.points[-1][1],
                     layer=self.layers[-1], net=self.net)

    def __getitem__(self, i: int) -> RouteSegment:
        """Return segment i with typed Point start/end (layer + net)."""
        if i < 0 or i >= len(self.points) - 1:
            raise IndexError(f"Route segment index {i} out of range [0, {len(self.points) - 2}]")
        ly = self.layers[i]
        start = Point(self.points[i][0], self.points[i][1],
                      layer=ly, net=self.net)
        end = Point(self.points[i + 1][0], self.points[i + 1][1],
                    layer=ly, net=self.net)
        return RouteSegment(start, end)

    def __len__(self) -> int:
        """Number of segments (len(points) - 1)."""
        return len(self.points) - 1

    def __repr__(self):
        return f"Route({len(self.points)} points, layer={self.layer.name}, width={self.width})"
