"""
LayoutCell - Base class for hierarchical layout.
"""

from typing import Optional, List, Tuple
from pade.layout.transform import Transform
from pade.layout.shape import Shape, Layer
from pade.layout.port import Port


class LayoutCell:
    """
    Base class for layout cells.

    Contains shapes, ports, and subcells. All coordinates in nanometers.
    """

    def __init__(self,
                 instance_name: str,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 **kwargs):
        """
        Create a layout cell.

        Args:
            instance_name: Instance name (unique within parent)
            parent: Parent cell in hierarchy
            cell_name: Type name (defaults to class name)
            **kwargs: Additional parameters stored in self.params
        """
        self.cell_name = cell_name or type(self).__name__
        self.instance_name = instance_name
        self.parent = parent
        self.params = kwargs

        # Transform relative to parent (identity by default)
        self.transform = Transform()

        # Contents
        self.shapes: List[Shape] = []
        self.ports: dict[str, Port] = {}
        self.subcells: dict[str, 'LayoutCell'] = {}

        # Register with parent
        if parent is not None:
            parent._add_subcell(self)

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

    def add_port(self, name: str, layer: Layer,
                 x0: int, y0: int, x1: int, y1: int,
                 net: Optional[str] = None) -> Port:
        """
        Add a port to this cell.

        Ports are labels for LVS. All coordinates are explicit.
        
        Args:
            name: Port name
            layer: Layer for the port
            x0, y0: Lower-left corner (nm)
            x1, y1: Upper-right corner (nm)
            net: Net name (defaults to port name)

        Returns:
            The created Port
        """
        if net is None:
            net = name
        
        port = Port(name=name, cell=self, layer=layer,
                    x0=x0, y0=y0, x1=x1, y1=y1, net=net)
        self.ports[name] = port
        return port

    def get_port(self, name: str) -> Port:
        """Get port by name."""
        if name not in self.ports:
            raise ValueError(f"No port named '{name}' in {self}")
        return self.ports[name]

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
