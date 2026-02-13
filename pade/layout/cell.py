"""
LayoutCell - Base class for hierarchical layout.
"""

from typing import Optional, List, Tuple, Union
from pade.layout.transform import Transform
from pade.layout.shape import Shape, Layer
from pade.layout.ref import Ref, Pin, Point
from pade.layout.route import Route, RouteSegment
from pade.layout.instance_list import LayoutInstanceList


class LayoutCell:
    """
    Base class for layout cells.

    Contains shapes, refs, pins, and subcells. All coordinates in nanometers.
    """

    def __init__(self,
                 instance_name: Optional[str] = None,
                 parent: Optional['LayoutCell'] = None,
                 cell_name: Optional[str] = None,
                 schematic=None,
                 layout_params: Optional[dict] = None,
                 **kwargs):
        """
        Create a layout cell.

        Args:
            instance_name: Instance name (unique within parent). If None and parent
                is set, the name is taken from the parent attribute on assignment.
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
        self.refs: dict[str, Ref] = {}
        self.pins: dict[str, Pin] = {}
        self.subcells: dict[str, 'LayoutCell'] = {}

        # Connectivity checklist (built lazily from schematic)
        self._conn_checklist: Optional[dict] = None  # (inst, term) → net
        self._conn_covered: set = set()               # checked-off (inst, term) pairs
        self._conn_external_required: Optional[dict] = None  # (schem_inst, term) → net for mult>1
        self._conn_external_covered: set = set()      # (schem_inst, term) with external connection

        if parent is not None and self.instance_name is not None:
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

    @classmethod
    def instantiate(cls, parent, schematic=None, **kwargs) -> LayoutInstanceList:
        """Create one or more layout instances from schematic (mult from schematic.set_multiplier)."""
        mult = max(1, int(getattr(schematic, '_mult', 1)))
        cells = [cls(parent=parent, schematic=schematic, **kwargs) for _ in range(mult)]
        return LayoutInstanceList(cells)

    def __setattr__(self, name: str, value) -> None:
        if name != 'parent' and isinstance(value, LayoutCell):
            p = getattr(value, 'parent', None)
            if p is None:
                object.__setattr__(value, 'parent', self)
                if getattr(value, 'instance_name', None) is None:
                    object.__setattr__(value, 'instance_name', name)
                self._add_subcell(value)
            elif p is self and getattr(value, 'instance_name', None) is None:
                value.instance_name = name
                self._add_subcell(value)
        elif isinstance(value, (list, LayoutInstanceList)):
            cells = value._cells if isinstance(value, LayoutInstanceList) else value
            if cells and all(
                    isinstance(c, LayoutCell) and getattr(c, 'parent', None) in (None, self)
                    and getattr(c, 'instance_name', None) is None
                    for c in cells):
                for i, cell in enumerate(cells):
                    if getattr(cell, 'parent', None) is None:
                        object.__setattr__(cell, 'parent', self)
                    cell.instance_name = name if len(cells) == 1 else f'{name}_{i}'
                    self._add_subcell(cell)
        object.__setattr__(self, name, value)

    def __getattr__(self, name: str):
        """
        Allow attribute access to refs and subcells.

        Enables: self.M1 (subcell), self.M1.D (ref of subcell)
        """
        # Check subcells
        if 'subcells' in self.__dict__ and name in self.__dict__['subcells']:
            return self.__dict__['subcells'][name]
        # Check refs (includes pins, since pins are also registered as refs)
        if 'refs' in self.__dict__ and name in self.__dict__['refs']:
            return self.__dict__['refs'][name]
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

    def add_ref(self, name: str, target) -> Ref:
        """Add a named reference point to this cell.

        A Ref is a routing/placement anchor with no LVS significance.
        Accessible as ``self.<name>`` via ``__getattr__``.

        Args:
            name: Access key (e.g., 'D', 'DBOT', 'SBUS')
            target: A :class:`Shape` or a :class:`Ref` from a subcell.
                When a subcell Ref is given its shape is transformed
                into this cell's coordinate system.

        Returns:
            The created Ref
        """
        shape = self._resolve_target_shape(target)
        ref = Ref(name=name, cell=self, shape=shape)
        self.refs[name] = ref
        return ref

    def add_pin(self, name: str, target) -> Pin:
        """Add a cell-interface pin (LVS terminal).

        A Pin is a Ref that additionally represents a schematic terminal.
        The GDS writer generates labels from pins.  Also registered as a
        Ref, so ``self.<name>`` works for routing.

        Args:
            name: Terminal / access name (e.g., 'OUT', 'VDD')
            target: A :class:`Shape`, :class:`Ref`, or subcell Ref.

        Returns:
            The created Pin
        """
        shape = self._resolve_target_shape(target)
        pin = Pin(name=name, cell=self, shape=shape, terminal=name)
        self.pins[name] = pin
        self.refs[name] = pin  # also accessible as a ref
        # Pin declares this terminal is connected (no route needed)
        if isinstance(target, Ref):
            self._check_off_ref(target, name)
        return pin

    def _resolve_target_shape(self, target) -> Shape:
        """Resolve a Ref or Shape target to a Shape in this cell's coordinates.

        If *target* is a Ref from a subcell, its shape bounds are
        transformed into this cell's local coordinate system and a new
        Shape is returned.  If *target* is already a Shape it is
        returned as-is.
        """
        if isinstance(target, Shape):
            return target
        if isinstance(target, Ref):
            # Transform bounds into self's coordinate system
            x0, y0, x1, y1 = self._transform_ref_bounds(target)
            return Shape.rect(target.layer, x0, y0, x1, y1, net=target.net)
        if isinstance(target, Point):
            layer = target.layer
            net = target.net
            if layer is None and target.ref is not None:
                layer = target.ref.layer
            if net is None and target.ref is not None:
                net = target.ref.net
            if layer is None:
                raise ValueError("Point must carry a layer (or originate from a Ref)")
            x, y = int(target[0]), int(target[1])
            return Shape.rect(layer, x, y, x, y, net=net)
        raise TypeError(f"target must be a Shape, Ref, or Point, got {type(target).__name__}")

    def get_ref(self, name: str) -> Ref:
        """Get ref by name."""
        if name not in self.refs:
            raise ValueError(f"No ref named '{name}' in {self}")
        return self.refs[name]

    # ------------------------------------------------------------------
    # Connectivity checklist
    # ------------------------------------------------------------------

    def _build_checklist(self) -> dict:
        """Build ``{(instance_name, terminal_name): net_name}`` from schematic.

        Only direct subcells are included (one level deep).  When a subcell
        has mult > 1, layout instance names are expanded to inst_0, inst_1, ...
        Terminal names are stored **lower-case** so that the look-up from layout
        refs/pins (which are often upper-case) is case-insensitive.
        """
        checklist = {}
        if self.schematic is None:
            return checklist
        for inst_name, subcell in self.schematic.subcells.items():
            mult = max(1, int(getattr(subcell, '_mult', 1)))
            for term_name, terminal in subcell.terminals.items():
                if terminal.net is None:
                    continue
                net = terminal.net.name
                term_lower = term_name.lower()
                for i in range(mult):
                    layout_inst = inst_name if mult == 1 else f'{inst_name}_{i}'
                    checklist[(layout_inst, term_lower)] = net
        return checklist

    def _build_external_required(self) -> dict:
        """Build {(schem_inst_name, term): net} for subcells with mult > 1.

        Each entry means: at least one of inst_0, inst_1, ... must be connected
        to something outside the group (port or another instance).
        """
        out = {}
        if self.schematic is None:
            return out
        for inst_name, subcell in self.schematic.subcells.items():
            mult = max(1, int(getattr(subcell, '_mult', 1)))
            if mult <= 1:
                continue
            for term_name, terminal in subcell.terminals.items():
                if terminal.net is None:
                    continue
                out[(inst_name, term_name.lower())] = terminal.net.name
        return out

    def _get_checklist(self) -> dict:
        """Lazy accessor for the connectivity checklist."""
        if self._conn_checklist is None:
            self._conn_checklist = self._build_checklist()
            self._conn_external_required = self._build_external_required()
        return self._conn_checklist

    def _get_external_required(self) -> dict:
        """Lazy accessor for external-connection requirements (mult > 1)."""
        self._get_checklist()
        return self._conn_external_required or {}

    def _check_off_ref(self, point, net: Optional[str]) -> None:
        """Mark a route endpoint as covered in the connectivity checklist.

        *point* is a Ref, ref-name string, Point, or coordinate tuple.
        Handles both direct-child refs (e.g. ``self.MN1A.D``) and
        deeper refs (e.g. ``self.I0.MN.G``).  For deep refs the
        local net is resolved upward through the intermediate schematic
        hierarchy to find the terminal on the direct child, which is
        then looked up in the checklist.

        :class:`Point` instances that carry a back-reference to the
        originating Ref (e.g. ``cap.TOP.north + offset``) are also
        resolved.
        """
        ref = self._origin_ref(point)
        if ref is None or net is None:
            return

        # Walk up from ref.cell to find the direct child of self,
        # collecting the hierarchy chain.
        chain = []  # list of LayoutCells from ref.cell up to (but not including) self
        cell = ref.cell
        while cell is not None and cell is not self:
            chain.append(cell)
            cell = cell.parent
        if cell is not self or not chain:
            return

        direct_child = chain[-1]  # the immediate subcell of self
        direct_schem = direct_child.schematic
        if direct_schem is None:
            return

        if len(chain) == 1:
            # Ref belongs to a direct subcell — simple case.
            # Use Pin.terminal when available, so add_pin('VDD', ...) checks off (I0, 'vdd').
            if isinstance(ref, Pin):
                local_net = ref.terminal
            else:
                local_net = ref.net
        else:
            # Ref is deeper (e.g. I0.MN.G).  Resolve upward through
            # intermediate schematics to get the terminal name on the
            # direct child.
            local_net = ref.net  # starts as e.g. 'G'
            # chain is [MN, I0] (innermost first, direct_child last)
            for layout_cell in chain[:-1]:
                schem = layout_cell.schematic
                if schem is None:
                    return
                # Find which terminal of this schematic has local_net
                term_name = next(
                    (t for t in schem.terminals
                     if t.lower() == local_net.lower()),
                    None
                )
                if term_name is None or schem.terminals[term_name].net is None:
                    return
                # Resolve to the parent-level net name
                local_net = schem.terminals[term_name].net.name

        if local_net is None:
            return
        term_key = local_net.lower()

        key = (direct_child.instance_name, term_key)
        checklist = self._get_checklist()
        if key in checklist:
            expected_net = checklist[key]
            if expected_net.lower() != net.lower():
                from pade.logging import logger
                logger.warning(
                    f"Connectivity: route net '{net}' does not match "
                    f"schematic net '{expected_net}' for "
                    f"{direct_child.instance_name}.{local_net}")
            self._conn_covered.add(key)

    def _resolve_ref_to_schematic_endpoint(self, point) -> Optional[Union[str, tuple]]:
        """Resolve a route endpoint to 'port' or (schem_inst_name, term) or None.

        Returns 'port' if point is this cell's pin; (schem_inst, term) for a
        direct subcell ref (schem_inst is base name, e.g. MP1A for MP1A_0);
        None for tuple coords or refs we can't resolve.
        """
        ref = self._origin_ref(point)
        if ref is None:
            return None
        if ref.cell is self and ref.name in self.pins:
            return 'port'
        chain = []
        cell = ref.cell
        while cell is not None and cell is not self:
            chain.append(cell)
            cell = cell.parent
        if cell is not self or not chain:
            return None
        direct_child = chain[-1]
        if direct_child.schematic is None or self.schematic is None:
            return None
        if len(chain) == 1:
            if isinstance(ref, Pin):
                local_net = ref.terminal
            else:
                local_net = ref.net
        else:
            local_net = ref.net
            for layout_cell in chain[:-1]:
                schem = layout_cell.schematic
                if schem is None:
                    return None
                term_name = next(
                    (t for t in schem.terminals if t.lower() == (local_net or '').lower()),
                    None
                )
                if term_name is None or schem.terminals[term_name].net is None:
                    return None
                local_net = schem.terminals[term_name].net.name
        if local_net is None:
            return None
        term_key = local_net.lower()
        schem_inst = next(
            (k for k, v in self.schematic.subcells.items() if v is direct_child.schematic),
            None
        )
        if schem_inst is None:
            return None
        return (schem_inst, term_key)

    def _check_off_external(self, start, end, net: Optional[str]) -> None:
        """If this route connects a mult group to something outside the group, mark external as covered."""
        if net is None:
            return
        ext_req = self._get_external_required()
        if not ext_req:
            return
        A = self._resolve_ref_to_schematic_endpoint(start)
        B = self._resolve_ref_to_schematic_endpoint(end)
        if A is None or B is None:
            return
        if A == B:
            return
        def outside_group(key, other):
            if key == 'port' or not isinstance(key, tuple):
                return False
            if other == 'port':
                return True
            if isinstance(other, tuple) and other[0] != key[0]:
                return True
            return False
        for key in (A, B):
            other = B if key is A else A
            if isinstance(key, tuple) and key in ext_req and outside_group(key, other):
                self._conn_external_covered.add(key)

    def check_off_net(self, net: str) -> None:
        """Mark all schematic connections for *net* as covered in the checklist.

        Use when a net is connected implicitly (e.g. power via tap overlap)
        so that every (instance, terminal) on that net is checked off.
        Also satisfies external requirements for mult groups on that net.

        Args:
            net: Net name (e.g. 'AVSS', 'AVDD')
        """
        checklist = self._get_checklist()
        net_lower = net.lower()
        for (inst, term), checklist_net in checklist.items():
            if checklist_net.lower() == net_lower:
                self._conn_covered.add((inst, term))
        for (schem_inst, term), ext_net in self._get_external_required().items():
            if ext_net.lower() == net_lower:
                self._conn_external_covered.add((schem_inst, term))

    def check_connectivity(self) -> list:
        """Report schematic connections not yet covered by ``route()`` calls.

        Returns a list of dicts with keys *instance*, *terminal*, *net*
        for every uncovered connection.  For mult>1, also requires at least
        one instance in the group to be connected to something outside the group.
        An empty list means all connections are accounted for.
        """
        checklist = self._get_checklist()
        ext_req = self._get_external_required()
        missing = []
        for (inst, term), net in sorted(checklist.items()):
            if (inst, term) not in self._conn_covered:
                missing.append({'instance': inst, 'terminal': term, 'net': net})
        for (schem_inst, term), net in sorted(ext_req.items()):
            if (schem_inst, term) not in self._conn_external_covered:
                missing.append({'instance': schem_inst, 'terminal': term, 'net': net})
        return missing

    def print_connectivity_report(self) -> None:
        """Print a human-readable connectivity report."""
        missing = self.check_connectivity()
        checklist = self._get_checklist()
        ext_req = self._get_external_required()
        total = len(checklist) + len(ext_req)
        covered = len(self._conn_covered) + len(self._conn_external_covered)
        print(f"Connectivity: {covered}/{total} connections covered")
        if not missing:
            print("  All connections covered.")
            return
        # Group by net for readability
        by_net: dict = {}
        for m in missing:
            by_net.setdefault(m['net'], []).append(f"{m['instance']}.{m['terminal']}")
        for net, pins in sorted(by_net.items()):
            print(f"  Missing net '{net}': {', '.join(pins)}")

    def check_shorts(self):
        """Check for short circuits in this cell's layout.

        Flattens the layout with hierarchical net resolution, then
        checks for overlapping shapes with different nets on
        connectivity layers.

        Returns:
            ShortCheckResult with any detected shorts.
        """
        from pade.layout.connectivity import check_shorts
        return check_shorts(self)

    def _transform_ref_bounds(self, ref: Ref) -> tuple:
        """Transform ref bounds from source cell to self's coordinate system."""
        corners = [
            (ref.x0, ref.y0), (ref.x1, ref.y0),
            (ref.x0, ref.y1), (ref.x1, ref.y1),
        ]
        transformed = []
        for cx, cy in corners:
            x, y = cx, cy
            cell = ref.cell
            while cell is not None and cell is not self:
                x, y = cell.transform.apply_point(x, y)
                cell = cell.parent
            if cell is not self:
                raise ValueError(
                    f"Ref '{ref.name}' on '{ref.cell}' is not a subcell of '{self}'")
            transformed.append((x, y))
        xs = [t[0] for t in transformed]
        ys = [t[1] for t in transformed]
        return min(xs), min(ys), max(xs), max(ys)

    def route(self, start: Union[Tuple[int, int], Ref, str],
              end: Union[Tuple[int, int], Ref, str],
              layer: Layer, width: int,
              how: str = '-|',
              jog_start: int = 0,
              jog_end: int = 0,
              track: int = 0,
              track_end: int = 0,
              net: Optional[str] = None,
              end_style: str = 'extend') -> Route:
        """
        Create and draw a route between two points.
        
        Args:
            start: Starting point - (x, y) tuple, Ref, or ref name string
            end: Ending point - (x, y) tuple, Ref, or ref name string
            layer: Layer for the route
            width: Route width in nm
            how: Route pattern:
                 '-'  : horizontal (straight in x, ignores end y)
                 '|'  : vertical (straight in y, ignores end x)
                 '-|' : horizontal first, then vertical
                 '|-' : vertical first, then horizontal
            jog_start: Perpendicular offset at start (nm). Sign determines direction.
            jog_end: Perpendicular offset at end (nm). Sign determines direction.
            track: Integer track offset at start.  Offset is measured from
                the outer edge of the start ref shape (not its center).
                For ``track=1`` the offset is
                ``ref_extent/2 + min_spacing + width/2``, each additional
                track adds ``width + min_spacing``.  Positive = +Y for '-',
                +X for '|'.  When *start* is not a Ref the offset falls
                back to centre-based (ref extent = 0).
            track_end: Integer track offset at end (same convention as *track*
                but relative to *end* ref).
            net: Net name. Auto-detected from Ref if not specified.
            end_style: ``'extend'`` (default) overshoots segment endpoints
                by width/2 to fill corners.  ``'flush'`` ends exactly at
                the waypoint coordinates.
        
        Returns:
            The drawn Route object
        """
        # Convert track offsets to jog values
        if track != 0 or track_end != 0:
            min_s = self._get_layer_min_spacing(layer, width)
            pitch = width + min_s
            if track != 0:
                jog_start += self._track_to_jog(
                    track, start, how[0], width, min_s, pitch)
            if track_end != 0:
                # Last segment direction
                last_dir = how[-1] if len(how) > 1 else how[0]
                jog_end += self._track_to_jog(
                    track_end, end, last_dir, width, min_s, pitch)

        # Resolve start point
        x0, y0, net0 = self._resolve_route_point(start)
        x1, y1, net1 = self._resolve_route_point(end)
        
        # Auto-detect net from refs
        if net is None:
            net = net0 or net1

        # Check off connectivity
        self._check_off_ref(start, net)
        self._check_off_ref(end, net)
        self._check_off_external(start, end, net)

        # Compute waypoints
        points = self._compute_route_points(x0, y0, x1, y1, how, jog_start, jog_end)
        
        # Create and draw route
        route = Route(points, layer, width, net, end_style=end_style)
        route.draw(self)
        return route

    def _track_to_jog(self, track: int, point, seg_dir: str,
                      width: int, min_s: int, pitch: int) -> int:
        """Convert a track number to a jog offset in nm.

        The first track clears the ref shape edge:
            ``ref_extent/2 + min_spacing + width/2``
        Each additional track adds one *pitch* (``width + min_spacing``).

        Args:
            track: signed track number (0 means no offset)
            point: the route endpoint (Ref, str, or tuple)
            seg_dir: first/last segment direction char ('-' or '|')
            width: route width
            min_s: minimum spacing for the layer
            pitch: width + min_s
        """
        ref = self._as_ref(point)
        if ref is not None:
            if seg_dir == '-':
                extent = ref.height
            else:
                extent = ref.width
            # Ensure we clear a via at the ref (via top metal often larger than pin)
            extent = max(extent, 2 * min_s + width)
        else:
            extent = 0
        sign = 1 if track > 0 else -1
        n = abs(track)
        # First track: from ref edge to route centre
        offset = extent // 2 + min_s + width // 2
        # Additional tracks: each one full pitch further
        offset += (n - 1) * pitch
        return sign * offset
    
    def _get_layer_min_spacing(self, layer: Layer, width: int) -> int:
        """Get minimum spacing for a layer.  Override in PDK subclass."""
        return width  # conservative fallback: pitch = 2 * width

    def _as_ref(self, point) -> Optional[Ref]:
        """Return the Ref if *point* is a Ref or ref-name, else None."""
        if isinstance(point, Ref):
            return point
        if isinstance(point, str) and point in self.refs:
            return self.refs[point]
        return None

    def _origin_ref(self, point) -> Optional[Ref]:
        """Return the Ref this point logically originates from.

        Like :meth:`_as_ref` but also resolves ``Point.ref``, so that
        compass points (``ref.north``, ``ref.south + offset``, etc.)
        trace back to their originating Ref.  Used for connectivity
        bookkeeping where provenance matters but geometry does not.
        """
        ref = self._as_ref(point)
        if ref is not None:
            return ref
        back_ref = getattr(point, 'ref', None)
        if isinstance(back_ref, Ref):
            return back_ref
        return None

    def _resolve_route_point(self, point: Union[Tuple[int, int], Ref, str]
                             ) -> Tuple[int, int, Optional[str]]:
        """
        Resolve a route point to (x, y, net).

        Handles subcell refs by transforming coordinates to self's system.
        RouteSegment is resolved to its center.
        
        Args:
            point: (x, y) tuple, Ref, ref name string, or RouteSegment
        
        Returns:
            (x, y, net) where net may be None
        """
        if isinstance(point, RouteSegment):
            cx, cy = point.center
            return cx, cy, point.net
        if isinstance(point, Ref):
            cx, cy = point.local_center
            # Transform through hierarchy if ref belongs to a subcell
            cell = point.cell
            while cell is not None and cell is not self:
                cx, cy = cell.transform.apply_point(cx, cy)
                cell = cell.parent
            return cx, cy, point.net
        if isinstance(point, str):
            ref = self.get_ref(point)
            cx, cy = ref.local_center
            return cx, cy, ref.net
        # Point (tuple subclass with optional .net) or plain tuple
        net = getattr(point, 'net', None)
        return point[0], point[1], net
    
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

        # Main routing pattern
        if how == '-':
            # Horizontal: straight in x at start y, ignore end y
            points.append((x1, y0))
        elif how == '|':
            # Vertical: straight in y at start x, ignore end x
            points.append((x0, y1))
        elif how == '-|':
            # Horizontal first, then vertical
            if jog_end != 0:
                # Shift the vertical leg, then return to destination
                x_jog = x1 + jog_end
                points.append((x_jog, y0))  # horizontal to jogged x
                points.append((x_jog, y1))  # vertical at jogged x
                points.append((x1, y1))     # horizontal back to x1
            else:
                points.append((x1, y0))  # horizontal to x1
                points.append((x1, y1))  # vertical to y1
        elif how == '|-':
            # Vertical first, then horizontal
            if jog_end != 0:
                # Shift the horizontal leg, then return to destination
                y_jog = y1 + jog_end
                points.append((x0, y_jog))  # vertical to jogged y
                points.append((x1, y_jog))  # horizontal at jogged y
                points.append((x1, y1))     # vertical back to y1
            else:
                points.append((x0, y1))  # vertical to y1
                points.append((x1, y1))  # horizontal to x1
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

    def place(self, at: Union[Tuple[int, int], Ref],
              anchor: Union[Tuple[int, int], Ref]) -> 'LayoutCell':
        """Place self so that *anchor* lands exactly on *at*.

        Both arguments are resolved to the parent's coordinate system,
        then self is shifted by the difference.

        Example::

            MN1.place(at=MN0.DTOP, anchor=MN1.DBOT)
            # MN1's bottom dummy poly overlaps MN0's top dummy poly

        Args:
            at: Target position — Ref (on a sibling or its sub-cell)
                or ``(x, y)`` tuple in parent coordinates.
            anchor: Reference point on self — Ref (on self or a sub-cell)
                or ``(x, y)`` tuple in parent coordinates.

        Returns:
            self for chaining.
        """
        at_x, at_y = self._resolve_point_in_parent(at)
        anchor_x, anchor_y = self._resolve_point_in_parent(anchor)
        self.move(dx=at_x - anchor_x, dy=at_y - anchor_y)
        return self

    def _resolve_point_in_parent(self, point: Union[Tuple[int, int], Ref]
                                 ) -> Tuple[int, int]:
        """Resolve a Ref or ``(x, y)`` to parent-cell coordinates.

        For a Ref, walks the cell hierarchy from the ref's owning cell
        up to (but not including) ``self.parent``, applying transforms.
        """
        if isinstance(point, Ref):
            cx, cy = point.local_center
            cell = point.cell
            while cell is not None and cell is not self.parent:
                cx, cy = cell.transform.apply_point(cx, cy)
                cell = cell.parent
            return cx, cy
        return point[0], point[1]

    def align(self, direction: str, other: Union['LayoutCell', LayoutInstanceList], margin: int = 0,
              match: bool = False) -> 'LayoutCell':
        """
        Align self relative to other cell (both must share the same parent).

        Directions:
            'right': self's left edge at other's right edge + margin
            'left':  self's right edge at other's left edge - margin
            'above': self's bottom edge at other's top edge + margin
            'below': self's top edge at other's bottom edge - margin

        If match=True, also align the perpendicular axis: same x for above/below (left edges),
        same y for right/left (bottom edges).

        Returns self for chaining.
        """
        other_cell = other[0] if isinstance(other, LayoutInstanceList) else other
        sb = self.transformed_bbox()
        ob = other_cell.transformed_bbox()

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

        if match:
            sb = self.transformed_bbox()
            if direction in ('above', 'below'):
                self.move(dx=ob[0] - sb[0])
            else:
                self.move(dy=ob[1] - sb[1])
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

    def get_all_shapes(self, transform: Optional[Transform] = None,
                       resolve_nets: bool = False,
                       _net_map: Optional[dict] = None,
                       _path: Optional[str] = None) -> List[Shape]:
        """
        Get all shapes flattened with transforms applied.

        Args:
            transform: Additional transform to apply (for hierarchy).
            resolve_nets: If True, resolve local net names to hierarchical
                net names using schematic connectivity, and populate
                each shape's ``source`` with the instance hierarchy path.
            _net_map: (internal) mapping from local net name to parent net
                name, passed during recursion.  Caller should not set this.
            _path: (internal) instance hierarchy path built during recursion.

        Returns:
            List of Shape objects in absolute coordinates
        """
        if transform is None:
            transform = Transform()
        if _path is None:
            _path = self.instance_name or self.cell_name or '<top>'

        result = []

        # Own shapes
        for shape in self.shapes:
            s = shape.transformed(transform)
            if resolve_nets:
                local_net = s.net
                s.source = f'{_path} net={local_net}' if local_net else _path
                if _net_map and s.net:
                    s.net = _net_map.get(s.net.lower(), s.net)
            result.append(s)

        # Subcell shapes (recursively)
        for subcell in self.subcells.values():
            sub_transform = subcell.transform.compose(transform)
            sub_path = f'{_path}.{subcell.instance_name}'

            # Build net map for this subcell from schematic connectivity
            sub_net_map = None
            if resolve_nets:
                sub_net_map = self._build_net_map(subcell, _net_map)

            result.extend(subcell.get_all_shapes(
                sub_transform,
                resolve_nets=resolve_nets,
                _net_map=sub_net_map,
                _path=sub_path))

        return result

    @staticmethod
    def _build_net_map(subcell: 'LayoutCell',
                       parent_net_map: Optional[dict]) -> dict:
        """Build a local→hierarchical net mapping for a subcell.

        Uses the subcell's schematic terminal connections to map local
        net names (e.g. 'd', 's') to the parent-level net names (e.g.
        'P', 'TAIL').  If the parent itself has a net_map (i.e. it is
        also a subcell), the mapping is chained so that leaf-level names
        resolve all the way to the top.

        Returns:
            dict mapping lowercase local-net → resolved parent-net.
        """
        net_map: dict = {}
        schem = getattr(subcell, 'schematic', None)
        if schem is None:
            return net_map

        for term_name, terminal in schem.terminals.items():
            if terminal.net is not None:
                parent_net = terminal.net.name
                # Chain through parent's map if available
                if parent_net_map:
                    parent_net = parent_net_map.get(
                        parent_net.lower(), parent_net)
                net_map[term_name.lower()] = parent_net

        return net_map

    def get_hierarchy_name(self) -> str:
        """Get hierarchical name from top level."""
        parts = [self.instance_name]
        cell = self.parent
        while cell is not None:
            parts.insert(0, cell.instance_name)
            cell = cell.parent
        return '.'.join(parts)
