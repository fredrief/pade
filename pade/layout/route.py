"""
Route class for drawing connected path segments.
"""

from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


class Route:
    """
    A route consisting of connected path segments.
    
    Routes are defined by a list of waypoints. Segments are drawn between
    consecutive waypoints, with proper corner handling.
    """
    
    def __init__(self, points: List[Tuple[int, int]], layer: 'Layer',
                 width: int, net: Optional[str] = None,
                 end_style: str = 'extend'):
        """
        Create a route.
        
        Args:
            points: List of (x, y) waypoints in nm. Minimum 2 points.
            layer: Layer for all segments
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
        self.layer = layer
        self.width = width
        self.net = net
        self.end_style = end_style
    
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
            
            # Determine segment orientation
            if y0 == y1:
                # Horizontal segment
                left = min(x0, x1) - ext
                right = max(x0, x1) + ext
                cell.add_rect(self.layer, left, y0 - hw, right, y0 + hw, net=self.net)
            elif x0 == x1:
                # Vertical segment
                bottom = min(y0, y1) - ext
                top = max(y0, y1) + ext
                cell.add_rect(self.layer, x0 - hw, bottom, x0 + hw, top, net=self.net)
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
    
    def __repr__(self):
        return f"Route({len(self.points)} points, layer={self.layer.name}, width={self.width})"
