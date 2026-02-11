"""
Shape and Layer classes for layout geometry.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
import shapely
from shapely import box


@dataclass
class Layer:
    """
    Layer definition.

    Attributes:
        name: Generic layer name (e.g., 'M1', 'POLY', 'DIFF')
        purpose: Layer purpose (e.g., 'drawing', 'pin', 'label')
        connectivity: Whether this layer carries electrical connectivity.
            Set to True for conductive layers (metals, poly, diffusion,
            vias). Defaults to False — PDK code must opt-in.
    """
    name: str
    purpose: str = 'drawing'
    connectivity: bool = False

    def __hash__(self):
        return hash((self.name, self.purpose))

    def __eq__(self, other):
        if isinstance(other, Layer):
            return self.name == other.name and self.purpose == other.purpose
        return False

    def __str__(self):
        return f"{self.name}:{self.purpose}"


@dataclass
class LayerMap:
    """
    Maps generic layer names to PDK-specific layer info.

    Example:
        layer_map = LayerMap('sky130', {
            'M1': {'magic': 'met1', 'gds': (68, 20)},
            'M2': {'magic': 'met2', 'gds': (69, 20)},
            'VIA1': {'magic': 'via', 'gds': (68, 44)},
        })
    """
    pdk_name: str
    mapping: dict = field(default_factory=dict)

    def get_magic_layer(self, layer: Layer) -> str:
        """Get Magic layer name."""
        if layer.name in self.mapping:
            info = self.mapping[layer.name]
            if isinstance(info, dict) and 'magic' in info:
                return info['magic']
        return layer.name.lower()

    def get_gds(self, layer: Layer) -> Tuple[int, int]:
        """Get GDS layer and datatype."""
        if layer.name in self.mapping:
            info = self.mapping[layer.name]
            if isinstance(info, dict) and 'gds' in info:
                return info['gds']
        return (0, 0)


@dataclass
class Shape:
    """
    A geometric shape with layer and net information.

    Uses Shapely for geometry operations internally.
    All coordinates in nanometers (integers).

    Attributes:
        geometry: Shapely geometry (Polygon, typically a rectangle)
        layer: Layer this shape is on
        net: Net name for connectivity (optional)
        source: Instance hierarchy path for provenance (set during flatten)
    """
    geometry: shapely.Geometry
    layer: Layer
    net: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def rect(cls, layer: Layer, x0: int, y0: int, x1: int, y1: int,
             net: Optional[str] = None) -> 'Shape':
        """
        Create a rectangular shape.

        Args:
            layer: Layer for this shape
            x0, y0: Lower-left corner (nm)
            x1, y1: Upper-right corner (nm)
            net: Optional net name
        """
        geom = box(x0, y0, x1, y1)
        return cls(geometry=geom, layer=layer, net=net)

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return bounding box as (x0, y0, x1, y1)."""
        b = self.geometry.bounds
        return (int(b[0]), int(b[1]), int(b[2]), int(b[3]))

    @property
    def width(self) -> int:
        """Width of bounding box."""
        b = self.bounds
        return b[2] - b[0]

    @property
    def height(self) -> int:
        """Height of bounding box."""
        b = self.bounds
        return b[3] - b[1]

    @property
    def center(self) -> Tuple[int, int]:
        """Center point of geometry."""
        c = self.geometry.centroid
        return (int(c.x), int(c.y))

    def transformed(self, transform: 'Transform') -> 'Shape':
        """Return a new Shape with transform applied.

        Preserves net, source, and layer.
        """
        from pade.layout.transform import Transform
        new_geom = transform.apply(self.geometry)
        return Shape(geometry=new_geom, layer=self.layer,
                     net=self.net, source=self.source)

    def __repr__(self):
        src = f", source='{self.source}'" if self.source else ''
        return f"Shape({self.layer}, bounds={self.bounds}, net={self.net}{src})"
