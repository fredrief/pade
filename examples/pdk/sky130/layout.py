"""SKY130 LayoutCell with config support."""

from typing import Optional, List, Tuple, Union, Sequence
from pade.layout.cell import LayoutCell
from pade.layout.shape import Shape, Layer
from pade.layout.ref import Ref, Point
from pade.layout.route import Route, RouteSegment
from pdk.sky130.rules import sky130_rules
from pdk.sky130.vias import ViaDefinition, get_via_stack, layer_in_stack

class SKY130LayoutCell(LayoutCell):
    """LayoutCell with SKY130 config and convenience methods."""

    def __init__(self,
                 instance_name: Optional[str] = None,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 **kwargs):
        super().__init__(instance_name, parent, cell_name, **kwargs)
        self.rules = sky130_rules

    @staticmethod
    def to_nm(um_value: float) -> int:
        """Convert user-facing um value to internal nm coordinates."""
        return int(um_value * 1000)

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
                try:
                    cells[i].place(at=cells[i - 1].DTOP, anchor=cells[i].DBOT)
                except:
                    cells[i].place(at=cells[i - 1].MN.DTOP, anchor=cells[i].MN.DBOT)

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
              layer: Union[Layer, Sequence[Layer]],
              width: Optional[int] = None,
              how: str = '-|',
              jog_start: int = 0,
              jog_end: int = 0,
              track: int = 0,
              track_end: int = 0,
              net: Optional[str] = None,
              end_style: str = 'extend',
              via_nx_start: Optional[int] = None,
              via_ny_start: Optional[int] = None,
              via_nx_end: Optional[int] = None,
              via_ny_end: Optional[int] = None) -> Route:
        """Create and draw a route with automatic via insertion.

        Multi-layer support:

        * **1 layer** — all segments on that layer, no corner vias.
        * **2 layers** — direction-based assignment.  The first layer maps
          to the first character of *how*, the second to the other
          direction.  E.g. ``(M3, M2)`` with ``how='-|'`` puts horizontal
          segments on M3 and vertical segments on M2.  A 1×2 corner via
          is inserted at every layer transition.
        * **N layers** (one per segment) — explicit per-segment assignment.

        If start or end is a Ref on a different layer than the route's
        first/last layer, a via stack is inserted at that endpoint.

        For multi-layer routes the default width is bumped up so that
        corner vias (1×2) fit entirely within the route.

        Args:
            start: Starting point — (x, y) tuple, Ref, or ref name string
            end: Ending point — (x, y) tuple, Ref, or ref name string
            layer: Routing layer, or sequence of layers (1, 2, or N)
            width: Route width in nm (default: max of layer min width and
                corner via requirement)
            how: Route pattern: '-', '|', '-|', '|-'
            jog_start: Perpendicular offset at start (nm)
            jog_end: Perpendicular offset at end (nm)
            track: Integer track offset at start.  Uses PDK min_spacing
                and width rules to compute the perpendicular offset.
                See ``LayoutCell._track_to_jog`` for details.
            track_end: Integer track offset at end (same convention)
            net: Net name (auto-detected from Ref if not specified)
            end_style: ``'extend'`` (default) or ``'flush'``
            via_nx_start, via_ny_start: Via cut count at start (overrides ref area)
            via_nx_end, via_ny_end: Via cut count at end (overrides ref area)

        Returns:
            The drawn Route object
        """
        layers = list(layer) if isinstance(layer, (list, tuple)) else [layer]
        first_layer = layers[0]
        last_layer = layers[-1]
        if width is None:
            width = self._get_layer_min_width(first_layer)

        # For multi-layer routes, ensure width fits corner vias (1×2)
        if len(layers) >= 2:
            for la, lb in zip(layers, layers[1:]):
                if la != lb:
                    for vdef in get_via_stack(la, lb):
                        width = max(width, vdef.min_route_width())

        # For 2-layer direction-based routes, a jog from track/jog_start
        # flips the first segment to the perpendicular direction (and thus
        # the other layer).  Recompute first_layer/last_layer accordingly.
        if len(layers) == 2:
            if how[0] == '-':
                dir_layer = {'-': layers[0], '|': layers[1]}
            else:
                dir_layer = {'|': layers[0], '-': layers[1]}
            first_dir = how[0]
            if track != 0 or jog_start != 0:
                first_dir = '|' if first_dir == '-' else '-'
            first_layer = dir_layer[first_dir]
            last_how = how[-1] if len(how) > 1 else how[0]
            last_dir = last_how
            if track_end != 0 or jog_end != 0:
                last_dir = '|' if last_dir == '-' else '-'
            last_layer = dir_layer[last_dir]

        # Resolve net early so vias get it too
        if net is None:
            if isinstance(start, Ref):
                net = start.net
            elif isinstance(end, Ref):
                net = end.net
            elif getattr(start, 'net', None) is not None:
                net = start.net
            elif getattr(end, 'net', None) is not None:
                net = end.net

        # Auto-via at start (connect ref/point to first segment layer)
        start_ref = self._as_ref(start)
        if start_ref is not None and start_ref.layer != first_layer and layer_in_stack(start_ref.layer) and layer_in_stack(first_layer):
            sx, sy = self._ref_center_in_self(start_ref)
            via_kw = dict(net=net)
            if via_nx_start is not None and via_ny_start is not None:
                via_kw['nx'], via_kw['ny'] = via_nx_start, via_ny_start
            else:
                via_kw['area'] = (start_ref.width, start_ref.height)
            self.add_via(start_ref.layer, first_layer, sx, sy, **via_kw)
        elif isinstance(start, RouteSegment) and start.layer is not None and start.layer != first_layer and layer_in_stack(start.layer) and layer_in_stack(first_layer):
            sx, sy = start.center
            nx, ny = (via_nx_start, via_ny_start) if (via_nx_start is not None and via_ny_start is not None) else ((1, 2) if start.start[0] == start.end[0] else (2, 1))
            self.add_via(start.layer, first_layer, sx, sy, nx=nx, ny=ny, net=net)
        elif isinstance(start, Point) and getattr(start, 'layer', None) is not None and start.layer != first_layer and layer_in_stack(start.layer) and layer_in_stack(first_layer):
            via_stack = get_via_stack(start.layer, first_layer)
            if via_stack:
                cnx, cny = via_stack[0].corner_cuts()
                if via_nx_start is not None and via_ny_start is not None:
                    cnx, cny = via_nx_start, via_ny_start
                self.add_via(start.layer, first_layer, start[0], start[1],
                             nx=cnx, ny=cny, net=net)

        # Auto-via at end (connect last segment layer to ref/point)
        end_ref = self._as_ref(end)
        if end_ref is not None and end_ref.layer != last_layer and layer_in_stack(end_ref.layer) and layer_in_stack(last_layer):
            ex, ey = self._ref_center_in_self(end_ref)
            via_kw = dict(net=net)
            if via_nx_end is not None and via_ny_end is not None:
                via_kw['nx'], via_kw['ny'] = via_nx_end, via_ny_end
            else:
                via_kw['area'] = (end_ref.width, end_ref.height)
            self.add_via(end_ref.layer, last_layer, ex, ey, **via_kw)
        elif isinstance(end, RouteSegment) and end.layer is not None and end.layer != last_layer and layer_in_stack(end.layer) and layer_in_stack(last_layer):
            ex, ey = end.center
            nx, ny = (via_nx_end, via_ny_end) if (via_nx_end is not None and via_ny_end is not None) else ((1, 2) if end.start[0] == end.end[0] else (2, 1))
            self.add_via(end.layer, last_layer, ex, ey, nx=nx, ny=ny, net=net)
        elif isinstance(end, Point) and getattr(end, 'layer', None) is not None and end.layer != last_layer and layer_in_stack(end.layer) and layer_in_stack(last_layer):
            via_stack = get_via_stack(end.layer, last_layer)
            if via_stack:
                cnx, cny = via_stack[0].corner_cuts()
                if via_nx_end is not None and via_ny_end is not None:
                    cnx, cny = via_nx_end, via_ny_end
                self.add_via(end.layer, last_layer, end[0], end[1],
                             nx=cnx, ny=cny, net=net)

        if len(layers) == 1:
            return super().route(start, end, first_layer, width, how, jog_start, jog_end,
                                 track, track_end, net, end_style=end_style)

        # Multi-layer route with direction-based layer assignment
        min_s = self._get_layer_min_spacing(first_layer, width)
        pitch = width + min_s
        if track != 0:
            jog_start += self._track_to_jog(track, start, how[0], width, min_s, pitch)
        last_dir = how[-1] if len(how) > 1 else how[0]
        if track_end != 0:
            jog_end += self._track_to_jog(track_end, end, last_dir, width, min_s, pitch)

        x0, y0, net0 = self._resolve_route_point(start)
        x1, y1, net1 = self._resolve_route_point(end)
        if net is None:
            net = net0 or net1
        self._check_off_ref(start, net)
        self._check_off_ref(end, net)
        self._check_off_external(start, end, net)

        points = self._compute_route_points(x0, y0, x1, y1, how, jog_start, jog_end)
        n_seg = len(points) - 1

        # Expand layers to per-segment based on direction
        if len(layers) == 2:
            if how[0] == '-':
                dir_layer = {'-': layers[0], '|': layers[1]}
            else:
                dir_layer = {'|': layers[0], '-': layers[1]}
            seg_layers = []
            for i in range(n_seg):
                px0, py0 = points[i]
                px1, py1 = points[i + 1]
                seg_layers.append(dir_layer['-'] if py0 == py1 else dir_layer['|'])
        elif len(layers) == n_seg:
            seg_layers = layers
        else:
            raise ValueError(
                f"layer must be 1, 2, or {n_seg} layers for {n_seg} segments (how={how!r})")

        hw = width // 2
        ext = hw if end_style == 'extend' else 0

        for i in range(n_seg):
            px0, py0 = points[i]
            px1, py1 = points[i + 1]
            ly = seg_layers[i]
            if py0 == py1:
                left = min(px0, px1) - ext
                right = max(px0, px1) + ext
                self.add_rect(ly, left, py0 - hw, right, py0 + hw, net=net)
            elif px0 == px1:
                bottom = min(py0, py1) - ext
                top = max(py0, py1) + ext
                self.add_rect(ly, px0 - hw, bottom, px0 + hw, top, net=net)
            else:
                raise ValueError(f"Diagonal segment: ({px0},{py0}) to ({px1},{py1})")

            # Insert 1×2 corner via at layer transitions
            if i + 1 < n_seg and seg_layers[i] != seg_layers[i + 1]:
                cx, cy = points[i + 1]
                via_stack = get_via_stack(seg_layers[i], seg_layers[i + 1])
                if via_stack:
                    cnx, cny = via_stack[0].corner_cuts()
                    self.add_via(seg_layers[i], seg_layers[i + 1], cx, cy,
                                 nx=cnx, ny=cny, net=net)

        return Route(points, seg_layers, width, net, end_style=end_style)

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
        cx, cy = ref.local_center
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
