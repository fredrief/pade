"""SKY130 LayoutCell with config support."""

from typing import Optional, List, Tuple, Union
from pade.layout.cell import LayoutCell
from pade.layout.shape import Shape, Layer
from pade.layout.ref import Ref
from pade.layout.route import Route
from pdk.sky130.rules import sky130_rules
from pdk.sky130.vias import ViaDefinition, get_via_stack, layer_in_stack

NM_PER_UM = 1000


class SKY130LayoutCell(LayoutCell):
    """LayoutCell with SKY130 config and convenience methods."""

    def __init__(self,
                 instance_name: str,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 **kwargs):
        super().__init__(instance_name, parent, cell_name, **kwargs)
        self.rules = sky130_rules

    def to_nm(self, um_value: float) -> int:
        """Convert user-facing um value to internal nm coordinates."""
        return int(um_value * NM_PER_UM)

    # ------------------------------------------------------------------
    # Placement helpers
    # ------------------------------------------------------------------

    def stack_column(self, cells: list, margin: Optional[int] = None) -> None:
        """Stack cells vertically (cells[1..] above cells[0]).

        By default, uses anchor-based placement so the top dummy poly
        of each cell exactly overlaps the bottom dummy poly of the cell
        above (requires ``DTOP`` / ``DBOT`` refs, as on MOSFET_Layout).

        If *margin* is given, falls back to bbox-based ``align('above')``.

        Args:
            cells: List of child LayoutCells to stack.
            margin: If provided, use ``align('above', margin=margin)``
                    instead of dummy-poly overlap.
        """
        if len(cells) < 2:
            return
        if margin is not None:
            for i in range(1, len(cells)):
                cells[i].align('above', cells[i - 1], margin=margin)
        else:
            for i in range(1, len(cells)):
                cells[i].place(at=cells[i - 1].DTOP, anchor=cells[i].DBOT)

    # ------------------------------------------------------------------
    # Via placement
    # ------------------------------------------------------------------

    def add_via(self, bot_layer: Layer, top_layer: Layer,
                cx: int, cy: int, *,
                nx: int = None, ny: int = None,
                area: Tuple[int, int] = None,
                net: str = None) -> List[Shape]:
        """Add a via stack between two routing layers, centered at (cx, cy).

        For non-adjacent layers (e.g. LI → M3) the full intermediate stack
        is inserted automatically (MCON + VIA1 + VIA2).

        Via count per level is determined by (in priority order):
          1. nx, ny — explicit cut count
          2. area = (w, h) — fill that area with maximum cuts
          3. Default: single cut per level

        Args:
            bot_layer: Bottom routing layer
            top_layer: Top routing layer
            cx, cy: Center position (nm)
            nx, ny: Explicit cut count in x / y
            area: (width, height) area to fill with cuts (nm)
            net: Net name for all generated shapes

        Returns:
            List of all shapes created (cuts + enclosure metals)
        """
        stack = get_via_stack(bot_layer, top_layer)
        if not stack:
            return []

        # Determine cut counts per level
        counts = []
        for vdef in stack:
            if nx is not None and ny is not None:
                counts.append((nx, ny))
            elif area is not None:
                counts.append(vdef.max_cuts(*area))
            else:
                counts.append((1, 1))

        shapes: List[Shape] = []
        for i, (vdef, (_nx, _ny)) in enumerate(zip(stack, counts)):
            # Draw cuts
            arr_w, arr_h = vdef.array_extent(_nx, _ny)
            half_w = arr_w // 2
            half_h = arr_h // 2
            x_start = cx - half_w
            y_start = cy - half_h
            for ix in range(_nx):
                for iy in range(_ny):
                    x0 = x_start + ix * (vdef.cut_w + vdef.cut_space)
                    y0 = y_start + iy * (vdef.cut_h + vdef.cut_space)
                    shapes.append(
                        self.add_rect(vdef.cut_layer,
                                      x0, y0,
                                      x0 + vdef.cut_w, y0 + vdef.cut_h,
                                      net=net))

            # Bottom metal: draw only for the first level in the stack
            # (intermediate metals are handled as the top enclosure of
            # the previous level, merged with this level's requirements)
            if i == 0:
                enc_x, enc_y = self._enforce_min_width(
                    vdef.bot_layer, arr_w, arr_h,
                    vdef.bot_enc_adj, vdef.bot_enc)
                shapes.append(
                    self.add_rect(vdef.bot_layer,
                                  cx - half_w - enc_x,
                                  cy - half_h - enc_y,
                                  cx - half_w + arr_w + enc_x,
                                  cy - half_h + arr_h + enc_y,
                                  net=net))

            # Top metal: for intermediate levels, merge this level's
            # top enclosure with the next level's bottom enclosure
            top_enc_adj = vdef.top_enc_adj
            top_enc = vdef.top_enc
            if i + 1 < len(stack):
                next_vdef = stack[i + 1]
                next_arr_w, next_arr_h = next_vdef.array_extent(*counts[i + 1])
                # Use the larger enclosure of both levels
                top_enc_adj = max(top_enc_adj, next_vdef.bot_enc_adj)
                top_enc = max(top_enc, next_vdef.bot_enc)
                # Use the larger cut array extent
                arr_w = max(arr_w, next_arr_w)
                arr_h = max(arr_h, next_arr_h)
                half_w = arr_w // 2
                half_h = arr_h // 2

            enc_x, enc_y = self._enforce_min_width(
                vdef.top_layer, arr_w, arr_h, top_enc_adj, top_enc)
            shapes.append(
                self.add_rect(vdef.top_layer,
                              cx - half_w - enc_x,
                              cy - half_h - enc_y,
                              cx - half_w + arr_w + enc_x,
                              cy - half_h + arr_h + enc_y,
                              net=net))

        return shapes

    # ------------------------------------------------------------------
    # Routing (with auto-via)
    # ------------------------------------------------------------------

    def route(self, start: Union[Tuple[int, int], Ref, str],
              end: Union[Tuple[int, int], Ref, str],
              layer: Layer,
              width: Optional[int] = None,
              how: str = '-|',
              jog_start: int = 0,
              jog_end: int = 0,
              track: int = 0,
              track_end: int = 0,
              net: Optional[str] = None,
              end_style: str = 'extend') -> Route:
        """Create and draw a route with automatic via insertion.

        If start or end is a Ref on a different layer than *layer*,
        a via stack is inserted at that endpoint.  The via fills the
        ref's bounding area by default.

        Args:
            start: Starting point — (x, y) tuple, Ref, or ref name string
            end: Ending point — (x, y) tuple, Ref, or ref name string
            layer: Routing layer for the wire
            width: Route width in nm (default: layer minimum from rules)
            how: Route pattern: '-', '|', '-|', '|-'
            jog_start: Perpendicular offset at start (nm)
            jog_end: Perpendicular offset at end (nm)
            track: Integer track offset at start (pitch = width + min_spacing)
            track_end: Integer track offset at end
            net: Net name (auto-detected from Ref if not specified)
            end_style: ``'extend'`` (default) or ``'flush'``

        Returns:
            The drawn Route object
        """
        if width is None:
            width = self._get_layer_min_width(layer)

        # Resolve net early so vias get it too
        if net is None:
            if isinstance(start, Ref):
                net = start.net
            elif isinstance(end, Ref):
                net = end.net

        # Auto-via at start (only for layers in the routing stack)
        start_ref = self._as_ref(start)
        if (start_ref is not None
                and start_ref.layer != layer
                and layer_in_stack(start_ref.layer)
                and layer_in_stack(layer)):
            sx, sy = self._ref_center_in_self(start_ref)
            area = (start_ref.width, start_ref.height)
            self.add_via(start_ref.layer, layer, sx, sy, area=area, net=net)

        # Auto-via at end (only for layers in the routing stack)
        end_ref = self._as_ref(end)
        if (end_ref is not None
                and end_ref.layer != layer
                and layer_in_stack(end_ref.layer)
                and layer_in_stack(layer)):
            ex, ey = self._ref_center_in_self(end_ref)
            area = (end_ref.width, end_ref.height)
            self.add_via(end_ref.layer, layer, ex, ey, area=area, net=net)

        return super().route(start, end, layer, width, how, jog_start, jog_end,
                             track, track_end, net, end_style=end_style)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _enforce_min_width(self, layer: Layer, arr_w: int, arr_h: int,
                           enc_x: int, enc_y: int) -> Tuple[int, int]:
        """Enlarge enclosures so the metal rect meets the layer's MIN_W.

        Returns (enc_x, enc_y), possibly enlarged.
        """
        try:
            min_w = self._get_layer_min_width(layer)
        except ValueError:
            return enc_x, enc_y
        total_w = arr_w + 2 * enc_x
        total_h = arr_h + 2 * enc_y
        if total_w < min_w:
            enc_x = (min_w - arr_w + 1) // 2
        if total_h < min_w:
            enc_y = (min_w - arr_h + 1) // 2
        return enc_x, enc_y

    def _ref_center_in_self(self, ref: Ref) -> Tuple[int, int]:
        """Get ref center transformed into self's coordinate system."""
        cx, cy = ref.center
        cell = ref.cell
        while cell is not None and cell is not self:
            cx, cy = cell.transform.apply_point(cx, cy)
            cell = cell.parent
        return cx, cy

    # Map layer names to rules attribute names
    _LAYER_RULE_MAP = {
        'LI1': 'LI', 'LI': 'LI',
        'MET1': 'M1', 'M1': 'M1',
        'MET2': 'M2', 'M2': 'M2',
        'MET3': 'M3', 'M3': 'M3',
        'MET4': 'M4', 'M4': 'M4',
        'MET5': 'M5', 'M5': 'M5',
    }

    def _get_layer_min_width(self, layer: Layer) -> int:
        """Get minimum width for a layer from rules."""
        rule_name = self._LAYER_RULE_MAP.get(layer.name)

        if rule_name and hasattr(self.rules, rule_name):
            layer_rules = getattr(self.rules, rule_name)
            if hasattr(layer_rules, 'MIN_W'):
                return layer_rules.MIN_W

        raise ValueError(f"No minimum width rule found for layer '{layer.name}'")

    def _get_layer_min_spacing(self, layer: Layer, width: int) -> int:
        """Get minimum spacing for a layer from rules."""
        rule_name = self._LAYER_RULE_MAP.get(layer.name)

        if rule_name and hasattr(self.rules, rule_name):
            layer_rules = getattr(self.rules, rule_name)
            if hasattr(layer_rules, 'MIN_S'):
                return layer_rules.MIN_S

        return width  # fallback
