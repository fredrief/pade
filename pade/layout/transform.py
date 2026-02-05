"""
Transform - Position, rotation, and mirroring for layout cells.
"""

from dataclasses import dataclass
from typing import Tuple
import shapely
from shapely import affinity


@dataclass
class Transform:
    """
    2D transform: translation, rotation, and mirroring.

    All coordinates in nanometers (integers).
    Rotation in degrees (0, 90, 180, 270).
    """
    x: int = 0
    y: int = 0
    rotation: int = 0  # Degrees: 0, 90, 180, 270
    mirror_x: bool = False  # Mirror about X axis (flip vertically)

    def apply(self, geom: shapely.Geometry) -> shapely.Geometry:
        """Apply transform to a Shapely geometry."""
        result = geom

        # Mirror first (about x-axis, i.e., flip y)
        if self.mirror_x:
            result = affinity.scale(result, xfact=1, yfact=-1, origin=(0, 0))

        # Then rotate about origin
        if self.rotation != 0:
            result = affinity.rotate(result, self.rotation, origin=(0, 0))

        # Then translate
        if self.x != 0 or self.y != 0:
            result = affinity.translate(result, self.x, self.y)

        return result

    def apply_point(self, px: int, py: int) -> Tuple[int, int]:
        """Apply transform to a point."""
        x, y = px, py

        # Mirror
        if self.mirror_x:
            y = -y

        # Rotate
        if self.rotation == 90:
            x, y = -y, x
        elif self.rotation == 180:
            x, y = -x, -y
        elif self.rotation == 270:
            x, y = y, -x

        # Translate
        x += self.x
        y += self.y

        return int(x), int(y)

    def compose(self, other: 'Transform') -> 'Transform':
        """Compose two transforms (self applied first, then other)."""
        # This is a simplified composition - full implementation would handle
        # rotation and mirror interactions properly
        # For now, just handle translation
        x, y = other.apply_point(self.x, self.y)
        return Transform(
            x=x,
            y=y,
            rotation=(self.rotation + other.rotation) % 360,
            mirror_x=self.mirror_x != other.mirror_x  # XOR for mirror
        )

    @staticmethod
    def identity() -> 'Transform':
        """Return identity transform."""
        return Transform()
