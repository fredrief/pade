"""
LayoutCell - Base class for hierarchical layout.
"""

from typing import Optional, List, Tuple, Union
from pade.layout.transform import Transform
from pade.layout.shape import Shape, Layer
from pade.layout.port import Port
from pade.layout.route import Route


class LayoutCell:
    """
    Base class for layout cells.

    Contains shapes, ports, and subcells. All coordinates in nanometers.
    """

    def __init__(self,
                 instance_name: str,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 schematic=None,
                 layout_params: Optional[dict] = None,
                 **kwargs):
        """
        Create a layout cell.

        Args:
            instance_name: Instance name (unique within parent)
            parent: Parent cell in hierarchy
            cell_name: Base type name (defaults to schematic cell_name or class name)
            schematic: Schematic Cell instance (bidirectional link)
            layout_params: Layout-specific parameters encoded into cell_name
            **kwargs: Config options (forwarded through hierarchy, not encoded)
        """
        self.schematic = schematic
        self.layout_params = layout_params or {}
        base_name = cell_name or (schematic.cell_name if schematic else None) or type(self).__name__
        self.cell_name = self._generate_cell_name(base_name)
        self.instance_name = instance_name
        self.parent = parent

        # Bidirectional link
        if schematic is not None:
            schematic.layout_cell = self

        # Transform relative to parent (identity by default)
        self.transform = Transform()

        # Contents
        self.shapes: List[Shape] = []
        self.ports: dict[str, Port] = {}
        self.subcells: dict[str, 'LayoutCell'] = {}

        # Register with parent
        if parent is not None:
            parent._add_subcell(self)

    def _generate_cell_name(self, base_name: str) -> str:
        """Generate unique cell name by encoding all parameters.

        Encodes schematic parameters (w, l, nf, ...) and layout-specific
        parameters (tap, poly_contact, ...) into the name. This ensures
        unique GDS cell names for each distinct geometry.

        Format: base_W1_L015_NF1_TAP_LEFT
        """
        parts = [base_name]

        if self.schematic is not None:
            for name, param in self.schematic.parameters.items():
                parts.append(self._encode_param(name, param.value))

        for name, value in self.layout_params.items():
            if value is not None:
                parts.append(self._encode_param(name, value))

        if len(parts) == 1:
            return base_name
        return '_'.join(parts)

    def _encode_param(self, name: str, value) -> str:
        """Encode a single parameter as NAMEVALUE string.

        Subclasses can override for custom encoding formats.
        """
        name_str = name.upper()
        if isinstance(value, float):
            val_str = f'{value:g}'.replace('.', 'p').replace('-', 'm')
        elif isinstance(value, str):
            # Handle numeric strings (e.g. '1.0', '0.15' from SPICE)
            val_str = value.replace('.', 'p').replace('-', 'm').upper()
        else:
            val_str = str(value)
        return f'{name_str}{val_str}'

    def __repr__(self):
        return f"LayoutCell({self.instance_name}, type={self.cell_name})"

    def __getattr__(self, name: str):
        """
        Allow attribute access to ports and subcells.

        Enables: self.M1 (subcell), self.M1.D (port of subcell)
        """
        # Check subcells
        if 'subcells' in self.__dict__ and name in self.__dict__['subcells']:
            return self.__dict__['subcells'][name]
        # Check ports
        if 'ports' in self.__dict__ and name in self.__dict__['ports']:
            return self.__dict__['ports'][name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def add_shape(self, shape: Shape) -> Shape:
        """Add a shape to this cell."""
        self.shapes.append(shape)
        return shape

    def add_rect(self, layer: Layer, x0: int, y0: int, x1: int, y1: int,
                 net: Optional[str] = None) -> Shape:
        """
        Add a rectangle shape.

        Args:
            layer: Layer for this shape
            x0, y0: Lower-left corner (nm)
            x1, y1: Upper-right corner (nm)
            net: Optional net name for connectivity

        Returns:
            The created Shape
        """
        shape = Shape.rect(layer, x0, y0, x1, y1, net=net)
        self.shapes.append(shape)
        return shape

    def add_port(self, name: str = None, *,
                 shape: Shape = None,
                 port: Port = None) -> Port:
        """
        Add a routing reference port to this cell.

        Ports are Python-side routing references. LVS labels are generated
        automatically by layout writers from schematic terminals and shape nets.

        Net is derived from the source:
        - shape: uses shape.net (must exist)
        - port: resolved from schematic connectivity

        Name defaults to the resolved net name.

        Args:
            name: Port access name (defaults to net name)
            shape: Create port from this shape's layer and bounds
            port: Create port from a subcell's port

        Returns:
            The created Port
        """
        if shape is not None and port is not None:
            raise ValueError("Specify either shape= or port=, not both")
        if shape is None and port is None:
            raise ValueError("Must specify shape= or port=")

        if shape is not None:
            if shape.net is None:
                raise ValueError("Shape must have a net to create a port")
            net = shape.net
            layer = shape.layer
            x0, y0, x1, y1 = shape.bounds
        else:
            net = self._resolve_port_net(port)
            layer = port.layer
            x0, y0, x1, y1 = self._transform_port_bounds(port)

        if name is None:
            name = net

        new_port = Port(name=name, cell=self, layer=layer,
                        x0=x0, y0=y0, x1=x1, y1=y1, net=net)
        self.ports[name] = new_port
        return new_port

    def _resolve_port_net(self, port: Port) -> str:
        """Resolve net name for a subcell port via schematic connectivity."""
        if self.schematic is None:
            return port.net

        # Walk up to find the direct subcell of self
        subcell = port.cell
        while subcell.parent is not None and subcell.parent is not self:
            subcell = subcell.parent
        if subcell.parent is not self:
            raise ValueError(f"Port's cell is not a descendant of {self}")

        schem = subcell.schematic
        if schem is None:
            return port.net

        # Map port.net to schematic terminal (case-insensitive)
        term_name = next(
            (t for t in schem.terminals if t.lower() == port.net.lower()),
            None
        )
        if term_name and schem.terminals[term_name].net is not None:
            return schem.terminals[term_name].net.name

        return port.net

    def _transform_port_bounds(self, port: Port) -> tuple:
        """Transform port bounds from source cell to self's coordinate system."""
        corners = [
            (port.x0, port.y0), (port.x1, port.y0),
            (port.x0, port.y1), (port.x1, port.y1),
        ]
        transformed = []
        for cx, cy in corners:
            x, y = cx, cy
            cell = port.cell
            while cell is not None and cell is not self:
                x, y = cell.transform.apply_point(x, y)
                cell = cell.parent
            if cell is not self:
                raise ValueError(
                    f"Port '{port.name}' on '{port.cell}' is not a subcell of '{self}'")
            transformed.append((x, y))
        xs = [t[0] for t in transformed]
        ys = [t[1] for t in transformed]
        return min(xs), min(ys), max(xs), max(ys)

    def get_port(self, name: str) -> Port:
        """Get port by name."""
        if name not in self.ports:
            raise ValueError(f"No port named '{name}' in {self}")
        return self.ports[name]

    def route(self, start: Union[Tuple[int, int], Port, str],
              end: Union[Tuple[int, int], Port, str],
              layer: Layer, width: int,
              how: str = '-|',
              jog_start: int = 0,
              jog_end: int = 0,
              net: Optional[str] = None) -> Route:
        """
        Create and draw a route between two points.
        
        Args:
            start: Starting point - (x, y) tuple, Port, or port name string
            end: Ending point - (x, y) tuple, Port, or port name string
            layer: Layer for the route
            width: Route width in nm
            how: Route pattern:
                 '-'  : horizontal (straight in x, ignores end y)
                 '|'  : vertical (straight in y, ignores end x)
                 '-|' : horizontal first, then vertical
                 '|-' : vertical first, then horizontal
            jog_start: Perpendicular offset at start (nm). Sign determines direction.
            jog_end: Perpendicular offset at end (nm). Sign determines direction.
            net: Net name. Auto-detected from Port if not specified.
        
        Returns:
            The drawn Route object
        """
        # Resolve start point
        x0, y0, net0 = self._resolve_route_point(start)
        x1, y1, net1 = self._resolve_route_point(end)
        
        # Auto-detect net from ports
        if net is None:
            net = net0 or net1
        
        # Compute waypoints
        points = self._compute_route_points(x0, y0, x1, y1, how, jog_start, jog_end)
        
        # Create and draw route
        route = Route(points, layer, width, net)
        route.draw(self)
        return route
    
    def _resolve_route_point(self, point: Union[Tuple[int, int], Port, str]
                             ) -> Tuple[int, int, Optional[str]]:
        """
        Resolve a route point to (x, y, net).

        Handles subcell ports by transforming coordinates to self's system.
        
        Args:
            point: (x, y) tuple, Port object, or port name string
        
        Returns:
            (x, y, net) where net may be None
        """
        if isinstance(point, Port):
            cx, cy = point.center
            # Transform through hierarchy if port belongs to a subcell
            cell = point.cell
            while cell is not None and cell is not self:
                cx, cy = cell.transform.apply_point(cx, cy)
                cell = cell.parent
            return cx, cy, point.net
        if isinstance(point, str):
            port = self.get_port(point)
            cx, cy = port.center
            return cx, cy, port.net
        # Assume tuple
        return point[0], point[1], None
    
    def _compute_route_points(self, x0: int, y0: int, x1: int, y1: int,
                              how: str, jog_start: int, jog_end: int
                              ) -> List[Tuple[int, int]]:
        """
        Compute waypoints for a route.
        
        Args:
            x0, y0: Start coordinates
            x1, y1: End coordinates
            how: Route pattern ('-', '|', '-|', '|-')
            jog_start: Perpendicular offset at start
            jog_end: Perpendicular offset at end
        
        Returns:
            List of (x, y) waypoints
        """
        points = [(x0, y0)]
        
        # Apply jog_start (perpendicular to first segment direction)
        if jog_start != 0:
            if how in ('-', '-|'):
                points.append((x0, y0 + jog_start))
                x0, y0 = x0, y0 + jog_start
            elif how in ('|', '|-'):
                points.append((x0 + jog_start, y0))
                x0, y0 = x0 + jog_start, y0

        # Apply jog_end (perpendicular to last segment direction)
        if jog_end != 0:
            if how == '-|':
                x1 = x1 + jog_end
            elif how == '|-':
                y1 = y1 + jog_end

        # Main routing pattern
        if how == '-':
            # Horizontal: straight in x at start y, ignore end y
            points.append((x1, y0))
        elif how == '|':
            # Vertical: straight in y at start x, ignore end x
            points.append((x0, y1))
        elif how == '-|':
            # Horizontal first, then vertical
            points.append((x1, y0))  # Go horizontal to x1
            points.append((x1, y1))  # Then vertical to y1
        elif how == '|-':
            # Vertical first, then horizontal
            points.append((x0, y1))  # Go vertical to y1
            points.append((x1, y1))  # Then horizontal to x1
        else:
            raise ValueError(f"Unknown route pattern: '{how}'. Use '-', '|', '-|', or '|-'")
        
        return points

    def move(self, dx: int = 0, dy: int = 0) -> 'LayoutCell':
        """Shift position by (dx, dy) relative to current location."""
        self.transform.x += dx
        self.transform.y += dy
        return self

    def rotate(self, degrees: int) -> 'LayoutCell':
        """Rotate by degrees (0, 90, 180, 270). Composes with current rotation."""
        self.transform.rotation = (self.transform.rotation + degrees) % 360
        return self

    def mirror_x(self) -> 'LayoutCell':
        """Mirror about X axis (flip vertically). Toggles current mirror state."""
        self.transform.mirror_x = not self.transform.mirror_x
        return self

    def transformed_bbox(self) -> Tuple[int, int, int, int]:
        """Bounding box in parent coordinates (with transform applied)."""
        b = self.bbox()
        corners = [
            self.transform.apply_point(b[0], b[1]),
            self.transform.apply_point(b[2], b[1]),
            self.transform.apply_point(b[0], b[3]),
            self.transform.apply_point(b[2], b[3]),
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    def align(self, direction: str, other: 'LayoutCell', margin: int = 0) -> 'LayoutCell':
        """
        Align self relative to other cell (both must share the same parent).

        Directions:
            'right': self's left edge at other's right edge + margin
            'left':  self's right edge at other's left edge - margin
            'above': self's bottom edge at other's top edge + margin
            'below': self's top edge at other's bottom edge - margin

        Returns self for chaining.
        """
        sb = self.transformed_bbox()
        ob = other.transformed_bbox()

        if direction == 'right':
            self.move(dx=ob[2] + margin - sb[0])
        elif direction == 'left':
            self.move(dx=ob[0] - margin - sb[2])
        elif direction == 'above':
            self.move(dy=ob[3] + margin - sb[1])
        elif direction == 'below':
            self.move(dy=ob[1] - margin - sb[3])
        else:
            raise ValueError(f"Unknown direction: '{direction}'. Use 'right', 'left', 'above', 'below'.")
        return self

    def _add_subcell(self, cell: 'LayoutCell') -> None:
        """Internal: register a subcell."""
        if cell.instance_name in self.subcells:
            raise ValueError(f"Subcell '{cell.instance_name}' already exists in {self}")
        self.subcells[cell.instance_name] = cell

    def get_subcells(self) -> List['LayoutCell']:
        """Return list of all subcells."""
        return list(self.subcells.values())

    def bbox(self) -> Tuple[int, int, int, int]:
        """
        Get bounding box of this cell (local coordinates).

        Includes all shapes and subcells.

        Returns:
            (x0, y0, x1, y1) in nm
        """
        if not self.shapes and not self.subcells:
            return (0, 0, 0, 0)

        x0, y0, x1, y1 = None, None, None, None

        # Shapes
        for shape in self.shapes:
            b = shape.bounds
            if x0 is None:
                x0, y0, x1, y1 = b
            else:
                x0 = min(x0, b[0])
                y0 = min(y0, b[1])
                x1 = max(x1, b[2])
                y1 = max(y1, b[3])

        # Subcells (transformed)
        for subcell in self.subcells.values():
            sb = subcell.bbox()
            # Transform subcell bbox corners
            corners = [
                subcell.transform.apply_point(sb[0], sb[1]),
                subcell.transform.apply_point(sb[2], sb[1]),
                subcell.transform.apply_point(sb[0], sb[3]),
                subcell.transform.apply_point(sb[2], sb[3]),
            ]
            for cx, cy in corners:
                if x0 is None:
                    x0, y0, x1, y1 = cx, cy, cx, cy
                else:
                    x0 = min(x0, cx)
                    y0 = min(y0, cy)
                    x1 = max(x1, cx)
                    y1 = max(y1, cy)

        return (x0 or 0, y0 or 0, x1 or 0, y1 or 0)

    def get_all_shapes(self, transform: Optional[Transform] = None) -> List[Shape]:
        """
        Get all shapes flattened with transforms applied.

        Args:
            transform: Additional transform to apply (for hierarchy)

        Returns:
            List of Shape objects in absolute coordinates
        """
        if transform is None:
            transform = Transform()

        result = []

        # Own shapes
        for shape in self.shapes:
            result.append(shape.transformed(transform))

        # Subcell shapes (recursively)
        for subcell in self.subcells.values():
            # Compose transforms
            sub_transform = subcell.transform.compose(transform)
            result.extend(subcell.get_all_shapes(sub_transform))

        return result

    def get_hierarchy_name(self) -> str:
        """Get hierarchical name from top level."""
        parts = [self.instance_name]
        cell = self.parent
        while cell is not None:
            parts.insert(0, cell.instance_name)
            cell = cell.parent
        return '.'.join(parts)
