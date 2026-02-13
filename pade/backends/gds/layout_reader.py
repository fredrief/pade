"""GDS layout reader - imports GDSII files into LayoutCell hierarchy."""

from pathlib import Path
from typing import Optional

import gdstk
import shapely

from pade.layout.cell import LayoutCell
from pade.layout.shape import Layer, LayerMap, Shape
from pade.layout.ref import Pin
from pade.layout.transform import Transform


class GDSReader:
    """Read a GDSII file into a :class:`LayoutCell` hierarchy.

    Coordinates in the GDS are converted to nanometers (matching
    LayoutCell conventions).  A :class:`LayerMap` provides the mapping
    from ``(gds_layer, gds_datatype)`` to PADE :class:`Layer` objects.
    GDS layers not present in the map are assigned auto-generated names
    (``L<layer>_<datatype>``) and added to the map so that a subsequent
    :class:`GDSWriter` round-trip preserves them.

    Labels whose *texttype* matches *pin_texttypes* are converted to
    :class:`Pin` objects on the cell.

    Attributes:
        layer_map: LayerMap for GDS layer/datatype → Layer conversion.
        unit: Target coordinate unit in meters (default 1e-9 = 1 nm).
        pin_texttypes: Set of GDS texttypes recognised as port labels.
    """

    def __init__(
        self,
        layer_map: Optional[LayerMap] = None,
        unit: float = 1e-9,
        pin_texttypes: Optional[set[int]] = None,
    ):
        self.layer_map = layer_map
        self.unit = unit
        self.pin_texttypes: set[int] = pin_texttypes if pin_texttypes is not None else {5, 16}
        self._reverse_map: Optional[dict[tuple[int, int], Layer]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self, gds_path: str | Path, cell_name: Optional[str] = None) -> LayoutCell:
        """Read a GDS file and return a :class:`LayoutCell`.

        Args:
            gds_path: Path to the GDSII file.
            cell_name: Name of the cell to import.  If *None*, the first
                top-level cell is used.

        Returns:
            LayoutCell representing the imported cell, with pins
            derived from GDS labels and full sub-cell hierarchy.
        """
        lib = gdstk.read_gds(str(gds_path))
        scale = lib.unit / self.unit  # e.g. 1e-6 / 1e-9 = 1000

        # Resolve target cell
        if cell_name:
            gds_cell = None
            for c in lib.cells:
                if c.name == cell_name:
                    gds_cell = c
                    break
            if gds_cell is None:
                names = [c.name for c in lib.cells]
                raise ValueError(
                    f"Cell '{cell_name}' not found in {gds_path}. "
                    f"Available: {names[:20]}{'...' if len(names) > 20 else ''}"
                )
        else:
            top = lib.top_level()
            if not top:
                raise ValueError(f"No top-level cell found in {gds_path}")
            gds_cell = top[0]

        masters: dict[str, LayoutCell] = {}
        return self._build_master(gds_cell, scale, masters)

    # ------------------------------------------------------------------
    # Hierarchy builder
    # ------------------------------------------------------------------

    def _build_master(
        self,
        gds_cell: gdstk.Cell,
        scale: float,
        masters: dict[str, LayoutCell],
    ) -> LayoutCell:
        """Build a master LayoutCell for *gds_cell* (with shapes & subcells).

        Masters are cached in *masters* so that each unique GDS cell is
        processed only once.
        """
        if gds_cell.name in masters:
            return masters[gds_cell.name]

        cell = LayoutCell(cell_name=gds_cell.name)
        masters[gds_cell.name] = cell

        # --- Polygons ---
        for poly in gds_cell.polygons:
            layer = self._gds_to_layer(poly.layer, poly.datatype)
            pts = [
                (int(round(x * scale)), int(round(y * scale)))
                for x, y in poly.points
            ]
            geom = shapely.Polygon(pts)
            cell.shapes.append(Shape(geometry=geom, layer=layer))

        # --- Paths (expand to polygons) ---
        for path in gds_cell.paths:
            expanded = path.to_polygons()
            for i, gpoly in enumerate(expanded):
                layer_idx = min(i, len(path.layers) - 1)
                layer = self._gds_to_layer(
                    path.layers[layer_idx], path.datatypes[layer_idx]
                )
                pts = [
                    (int(round(x * scale)), int(round(y * scale)))
                    for x, y in gpoly.points
                ]
                geom = shapely.Polygon(pts)
                cell.shapes.append(Shape(geometry=geom, layer=layer))

        # --- Sub-cell references ---
        ref_count: dict[str, int] = {}
        for ref in gds_cell.references:
            sub_master = self._build_master(ref.cell, scale, masters)
            base = sub_master.cell_name
            idx = ref_count.get(base, 0)
            ref_count[base] = idx + 1
            inst_name = f'{base}_{idx}'

            inst = LayoutCell(
                cell_name=sub_master.cell_name,
                instance_name=inst_name,
                parent=cell,
            )
            # Share geometry with master (writer deduplicates by cell_name)
            inst.shapes = sub_master.shapes
            inst.subcells = sub_master.subcells

            # Transform
            ox, oy = ref.origin
            rot_rad = ref.rotation  # radians in gdstk
            rot_deg = int(round(rot_rad * 180 / 3.14159265358979)) % 360 if rot_rad else 0
            inst.transform = Transform(
                x=int(round(ox * scale)),
                y=int(round(oy * scale)),
                rotation=rot_deg,
                mirror_x=bool(ref.x_reflection),
            )

        # --- Pins from labels ---
        for label in gds_cell.labels:
            if label.texttype not in self.pin_texttypes:
                continue
            pin_name = label.text
            if pin_name in cell.pins:
                continue  # first label wins

            lx = int(round(label.origin[0] * scale))
            ly = int(round(label.origin[1] * scale))
            # Use the label's layer as a drawing layer for the pin
            pin_layer = self._gds_to_layer(label.layer, 20)

            # Try to find the metal shape under the label
            pin_shape = self._find_shape_at(cell.shapes, pin_layer, lx, ly)
            if pin_shape is None:
                # Fallback: create a small rectangle at the label point
                pin_shape = Shape.rect(pin_layer, lx - 50, ly - 50, lx + 50, ly + 50)
                cell.shapes.append(pin_shape)

            pin = Pin(name=pin_name, cell=cell, shape=pin_shape, terminal=pin_name)
            cell.pins[pin_name] = pin
            cell.refs[pin_name] = pin

        return cell

    # ------------------------------------------------------------------
    # Layer mapping
    # ------------------------------------------------------------------

    def _build_reverse_map(self) -> dict[tuple[int, int], Layer]:
        """Build ``(gds_layer, gds_datatype) → Layer`` from the LayerMap."""
        reverse: dict[tuple[int, int], Layer] = {}
        if self.layer_map is None:
            return reverse
        for name, info in self.layer_map.mapping.items():
            if isinstance(info, dict) and 'gds' in info:
                gds_pair = info['gds']
                reverse[gds_pair] = Layer(name=name, purpose='drawing')
        return reverse

    def _gds_to_layer(self, gds_layer: int, gds_datatype: int) -> Layer:
        """Map a GDS layer/datatype pair to a PADE Layer.

        Unknown pairs are auto-registered in the LayerMap.
        """
        if self._reverse_map is None:
            self._reverse_map = self._build_reverse_map()

        key = (gds_layer, gds_datatype)
        if key in self._reverse_map:
            return self._reverse_map[key]

        # Auto-generate name for unknown layers
        name = f'L{gds_layer}_{gds_datatype}'
        layer = Layer(name=name, purpose='drawing')
        self._reverse_map[key] = layer
        # Register in LayerMap for round-trip fidelity
        if self.layer_map is not None:
            self.layer_map.mapping[name] = {'gds': (gds_layer, gds_datatype)}
        return layer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_shape_at(
        shapes: list[Shape],
        layer: Layer,
        x: int,
        y: int,
    ) -> Optional[Shape]:
        """Find a shape on *layer* that contains point *(x, y)*."""
        pt = shapely.Point(x, y)
        for shape in shapes:
            if shape.layer == layer and shape.geometry.contains(pt):
                return shape
        return None
