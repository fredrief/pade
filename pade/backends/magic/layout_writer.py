"""
Magic layout writer - generates .mag files from LayoutCell hierarchy.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional
from collections import defaultdict

from pade.backends.base import LayoutWriter
from pade.layout.shape import LayerMap

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


class MagicLayoutWriter(LayoutWriter):
    """
    Write LayoutCell hierarchy to Magic .mag files.

    Magic file format uses integer units (typically centimicrons or nm).
    We use nm internally and convert based on scale factor.

    Attributes:
        tech: Technology name for Magic (e.g., 'sky130A')
        layer_map: LayerMap for converting generic layers to Magic layers
        scale: Scale factor (nm per Magic unit, default 1)
    """

    def __init__(self,
                 tech: str = 'sky130A',
                 layer_map: Optional[LayerMap] = None,
                 scale: int = 1):
        """
        Create Magic layout writer.

        Args:
            tech: Technology name for Magic header
            layer_map: Layer mapping (generic -> Magic layer names)
            scale: nm per Magic database unit (default 1 = 1nm)
        """
        self.tech = tech
        self.layer_map = layer_map
        self.scale = scale

    def write(self, cell: 'LayoutCell', output_dir: str | Path) -> Path:
        """
        Write a single cell to a .mag file.

        Args:
            cell: LayoutCell to write
            output_dir: Directory to write to
            
        Returns:
            Path to the written .mag file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f'{cell.cell_name}.mag'

        content = self._generate_mag(cell)
        path.write_text(content)
        return path

    def write_hierarchy(self, cell: 'LayoutCell', output_dir: str | Path) -> list[Path]:
        """
        Write cell and all subcells to separate .mag files.

        Args:
            cell: Top-level cell
            output_dir: Directory for output files
            
        Returns:
            List of paths to written .mag files
        """
        output_dir = Path(output_dir)
        cells_to_write = self._collect_cells(cell)
        return [self.write(c, output_dir) for c in cells_to_write]

    def _collect_cells(self, cell: 'LayoutCell') -> list['LayoutCell']:
        """Collect all unique cells in hierarchy (by cell_name)."""
        seen = {}
        result = []

        def visit(c):
            if c.cell_name not in seen:
                seen[c.cell_name] = c
                result.append(c)
                for subcell in c.subcells.values():
                    visit(subcell)

        visit(cell)
        return result

    def _generate_mag(self, cell: 'LayoutCell') -> str:
        """Generate .mag file content for a cell."""
        lines = []

        # Header
        lines.append('magic')
        lines.append(f'tech {self.tech}')
        lines.append('timestamp 0')

        # Group shapes by layer
        shapes_by_layer = defaultdict(list)
        for shape in cell.shapes:
            layer_name = self._get_magic_layer(shape.layer)
            shapes_by_layer[layer_name].append(shape)

        # Write shapes for each layer
        for layer_name in sorted(shapes_by_layer.keys()):
            lines.append(f'<< {layer_name} >>')
            for shape in shapes_by_layer[layer_name]:
                b = shape.bounds
                # Convert from nm to Magic units
                x0, y0, x1, y1 = [v // self.scale for v in b]
                lines.append(f'rect {x0} {y0} {x1} {y1}')

        # Write subcell instances
        if cell.subcells:
            for inst_name, subcell in cell.subcells.items():
                t = subcell.transform
                x, y = t.x // self.scale, t.y // self.scale

                # Magic transform string
                transform_str = self._get_magic_transform(t)

                lines.append(f'use {subcell.cell_name} {inst_name}')
                if transform_str:
                    lines.append(f'transform {transform_str}')
                else:
                    lines.append(f'transform 1 0 {x} 0 1 {y}')
                lines.append('box 0 0 0 0')

        # Write LVS labels from schematic terminals
        labels = self._collect_labels(cell)
        if labels:
            lines.append('<< labels >>')
            for net_name, layer, x0, y0, x1, y1 in labels:
                layer_name = self._get_magic_layer(layer)
                x0, y0, x1, y1 = [v // self.scale for v in (x0, y0, x1, y1)]
                lines.append(f'rlabel {layer_name} {x0} {y0} {x1} {y1} 0 {net_name}')

        lines.append('<< end >>')

        return '\n'.join(lines)

    def _get_magic_layer(self, layer: 'Layer') -> str:
        """Get Magic layer name for a Layer."""
        if self.layer_map:
            return self.layer_map.get_magic_layer(layer)
        # Default: lowercase layer name
        return layer.name.lower()

    def _get_magic_transform(self, t: 'Transform') -> str:
        """
        Convert Transform to Magic transform matrix.

        Magic uses: a b c d e f
        where the transform is:
            x' = a*x + b*y + c
            y' = d*x + e*y + f
        """
        x, y = t.x // self.scale, t.y // self.scale

        # Build rotation matrix
        if t.rotation == 0:
            a, b, d, e = 1, 0, 0, 1
        elif t.rotation == 90:
            a, b, d, e = 0, -1, 1, 0
        elif t.rotation == 180:
            a, b, d, e = -1, 0, 0, -1
        elif t.rotation == 270:
            a, b, d, e = 0, 1, -1, 0
        else:
            a, b, d, e = 1, 0, 0, 1

        # Apply mirror (about x-axis = flip y)
        if t.mirror_x:
            d, e = -d, -e

        return f'{a} {b} {x} {d} {e} {y}'
