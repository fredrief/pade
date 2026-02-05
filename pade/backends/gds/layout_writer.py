"""GDS layout writer - generates GDSII files from LayoutCell hierarchy."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import gdstk

from pade.backends.base import LayoutWriter
from pade.layout.shape import LayerMap

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.layout.shape import Layer


class GDSWriter(LayoutWriter):
    """
    Write LayoutCell hierarchy to GDSII files.

    Coordinates are stored internally in nm. GDS uses um, so we scale by 1e-3.

    Attributes:
        layer_map: LayerMap for converting generic layers to GDS layer/datatype
        unit: GDS database unit in meters (default 1e-9 = 1nm)
        precision: GDS precision in meters (default 1e-12)
        pin_texttype: GDS texttype for port labels (default 16, common for LVS)
    """

    def __init__(self,
                 layer_map: Optional[LayerMap] = None,
                 unit: float = 1e-9,
                 precision: float = 1e-12,
                 pin_texttype: int = 16):
        self.layer_map = layer_map
        self.unit = unit
        self.precision = precision
        self.pin_texttype = pin_texttype

    def write(self, cell: 'LayoutCell', output_dir: str | Path) -> Path:
        """Write cell hierarchy to a single GDS file.
        
        Args:
            cell: LayoutCell to write
            output_dir: Directory to write to
            
        Returns:
            Path to the written GDS file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f'{cell.cell_name}.gds'

        lib = gdstk.Library(unit=self.unit, precision=self.precision)
        self._add_cell_hierarchy(lib, cell, set())
        lib.write_gds(str(path))
        return path

    def write_hierarchy(self, cell: 'LayoutCell', output_dir: str | Path) -> list[Path]:
        """Write each cell to a separate GDS file.
        
        Returns:
            List of paths to written GDS files
        """
        output_dir = Path(output_dir)
        cells = self._collect_cells(cell)
        return [self.write(c, output_dir) for c in cells]

    def _collect_cells(self, cell: 'LayoutCell') -> list['LayoutCell']:
        """Collect all unique cells in hierarchy."""
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

    def _add_cell_hierarchy(self, lib: gdstk.Library, cell: 'LayoutCell',
                            visited: set) -> gdstk.Cell:
        """Recursively add cell and subcells to library."""
        if cell.cell_name in visited:
            return lib[cell.cell_name]
        visited.add(cell.cell_name)

        # Process subcells first (bottom-up)
        for subcell in cell.subcells.values():
            self._add_cell_hierarchy(lib, subcell, visited)

        # Create this cell
        gds_cell = lib.new_cell(cell.cell_name)

        # Add shapes
        for shape in cell.shapes:
            layer, datatype = self._get_gds_layer(shape.layer)
            b = shape.bounds
            # Coordinates in nm, GDS in database units (also nm with unit=1e-9)
            rect = gdstk.rectangle((b[0], b[1]), (b[2], b[3]),
                                   layer=layer, datatype=datatype)
            gds_cell.add(rect)

        # Add subcell references
        for inst_name, subcell in cell.subcells.items():
            t = subcell.transform
            # Create reference with transform
            ref = gdstk.Reference(
                subcell.cell_name,
                origin=(t.x, t.y),
                rotation=t.rotation * 3.14159265359 / 180,  # degrees to radians
                x_reflection=t.mirror_x
            )
            gds_cell.add(ref)

        # Add port labels (use pin datatype = 16 for LVS port recognition)
        for port_name, port in cell.ports.items():
            layer, _ = self._get_gds_layer(port.layer)
            b = port.bounds
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            label = gdstk.Label(port_name, (cx, cy), layer=layer, texttype=self.pin_texttype)
            gds_cell.add(label)

        return gds_cell

    def _get_gds_layer(self, layer: 'Layer') -> tuple[int, int]:
        """Get GDS layer and datatype for a Layer."""
        if self.layer_map:
            return self.layer_map.get_gds(layer)
        return (0, 0)
