"""SKY130 Transistor Layout Primitives.

Transistor layout with horizontal poly orientation:
- Poly runs horizontally (left-right)
- Source/Drain stacked vertically
- Tap on left (NFET) or right (PFET) by default
- Poly contact follows tap side
- Origin at lower-left corner
"""

from types import SimpleNamespace
from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import (
    POLY, DIFF, TAP, NWELL, NSDM, PSDM, LI, LICON, MCON, NPC, M1
)


class MOSFET_Layout(SKY130LayoutCell):
    """
    Base MOSFET layout generator for SKY130.

    Parameters (all dimensions in um):
        w: Gate width
        l: Gate length
        nf: Number of fingers
        tap: 'left', 'right', 'both', or None
        poly_contact: 'left', 'right', 'both', or None (default follows tap)
        schematic: Schematic Cell instance (extracts w, l, nf)
    """

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = None
    TAP_TYPE = TAP
    TAP_IMPLANT = None
    SUB_TYPE = None
    DEFAULT_TAP = 'left'

    def __init__(self, instance_name, parent, schematic,
                 tap=None, poly_contact=None, cell_name=None):
        tap = tap if tap is not None else self.DEFAULT_TAP
        poly_contact = poly_contact if poly_contact is not None else tap
        if poly_contact is None:
            poly_contact = 'left'

        w = float(schematic.get_parameter('w'))
        l = float(schematic.get_parameter('l'))
        nf = int(schematic.get_parameter('nf'))

        super().__init__(instance_name, parent, cell_name=cell_name,
                         schematic=schematic,
                         layout_params={'tap': tap, 'poly_contact': poly_contact})

        self.w = w
        self.l = l
        self.nf = nf
        self.tap = tap
        self.poly_contact = poly_contact

        self._validate_parameters()
        self._draw()

    def _validate_parameters(self):
        r = self.rules.MOS
        if self.to_nm(self.l) < r.MIN_L:
            raise ValueError(f"Gate length {self.to_nm(self.l)}nm < minimum {r.MIN_L}nm")
        if self.to_nm(self.w) < r.MIN_W:
            raise ValueError(f"Gate width {self.to_nm(self.w)}nm < minimum {r.MIN_W}nm")
        if self.nf < 1:
            raise ValueError(f"Number of fingers must be >= 1, got {self.nf}")
        if self.tap not in ('left', 'right', 'both', None):
            raise ValueError(f"Invalid tap position: {self.tap}")
        if self.poly_contact not in ('left', 'right', 'both', None):
            raise ValueError(f"Invalid poly_contact position: {self.poly_contact}")

    # --- Main draw flow ---

    def _draw(self):
        g = self._compute_geometry()
        self._draw_diffusion(g)
        self._draw_poly(g)
        self._draw_implants(g)
        self._draw_sd_contacts(g)
        self._draw_gate_contacts(g)
        self._draw_m1_routing(g)
        self._draw_taps(g)
        self._draw_well(g)
        self._add_refs(g)

    # --- Geometry computation ---

    def _compute_geometry(self):
        """Compute all layout coordinates and dimensions."""
        g = SimpleNamespace()
        r = self.rules.MOS
        licon = self.rules.LICON
        mcon = self.rules.MCON
        m1 = self.rules.M1
        impl = self.rules.IMPL

        g.gate_w = self.to_nm(self.w)
        g.gate_l = self.to_nm(self.l)
        g.nf = self.nf
        g.is_ptype_sd = (self.DIFF_IMPLANT.name == 'PSDM')
        g.impl_enc = impl.ENC_DIFF
        g.poly_to_diff = r.DIFF_POLY_SPACE

        # LI height for contacts
        li_enc = licon.ENC_LI
        li_spacing = self.rules.LI.MIN_S
        g.li_h = licon.W + 2 * li_enc

        # S/D region: ensure LI spacing between adjacent S/D and gate contacts
        # Derived from: sd_region/2 + li_h/2 + li_spacing <= sd_region + gate_l/2 - li_h/2
        sd_region_for_li = 2 * (g.li_h + li_spacing) - g.gate_l
        g.sd_region = max(r.DIFF_EXT, sd_region_for_li)

        # Gate contact array (2 LICONs horizontal)
        licon_array_w = 2 * licon.W + licon.S
        mcon_array_w = 2 * mcon.W + mcon.S
        g.gate_cont_h = licon.W + 2 * licon.ENC_POLY
        g.gate_m1_w = mcon_array_w + 2 * mcon.ENC_TOP
        g.gate_m1_h = mcon.W + 2 * mcon.ENC_TOP
        li_gc_w = licon_array_w + 2 * li_enc

        # Gate contact X offset from device edge
        licon_to_impl = licon.S_IMPL
        gc_offset_default = g.gate_m1_w // 2
        gc_offset_for_tap = (licon_to_impl + licon_array_w // 2
                             - (g.impl_enc - r.TAP_DIFF_SPACE))

        g.tap_left = self.tap in ('left', 'both')
        g.tap_right = self.tap in ('right', 'both')

        g.gc_offset_left = (gc_offset_for_tap
                            if (g.tap_left and self.poly_contact in ('left', 'both'))
                            else gc_offset_default)
        g.gc_offset_right = (gc_offset_for_tap
                             if (g.tap_right and self.poly_contact in ('right', 'both'))
                             else gc_offset_default)

        # S/D M1 width (needed for multi-finger bus routing clearance)
        sd_avail = g.gate_w - 2 * licon.ENC_DIFF
        sd_n_licon = self._calc_via_count(sd_avail, licon.W, licon.S)
        sd_licon_arr = sd_n_licon * licon.W + (sd_n_licon - 1) * licon.S if sd_n_licon > 1 else licon.W
        sd_n_mcon = self._calc_via_count(sd_licon_arr, mcon.W, mcon.S)
        sd_mcon_arr = sd_n_mcon * mcon.W + (sd_n_mcon - 1) * mcon.S if sd_n_mcon > 1 else mcon.W
        g.sd_m1_w = sd_mcon_arr + 2 * mcon.ENC_TOP

        # Poly extensions
        poly_ext_for_li = gc_offset_default + li_gc_w // 2 + li_spacing + li_enc
        # Per-side: LICON-to-P-diff spacing (uses actual gc_offset for each side)
        poly_ext_for_impl_left = (g.gc_offset_left + licon_array_w // 2
                                  + licon_to_impl + g.impl_enc)
        poly_ext_for_impl_right = (g.gc_offset_right + licon_array_w // 2
                                   + licon_to_impl + g.impl_enc)

        # Bus routing clearance: gc_M1 | spacing | bus_M1 | spacing | sd_M1
        # Always reserve space (even for nf=1) so that gate contact and
        # tap X positions are consistent across all finger counts.
        has_left_contact = self.poly_contact in ('left', 'both')
        has_right_contact = self.poly_contact in ('right', 'both')
        poly_ext_for_bus_left = (g.gc_offset_left + g.gate_m1_w // 2
                                 + 2 * m1.MIN_S + m1.MIN_W
                                 + max(0, g.sd_m1_w // 2 - g.gate_w // 2)
                                 ) if has_left_contact else 0
        poly_ext_for_bus_right = (g.gc_offset_right + g.gate_m1_w // 2
                                  + 2 * m1.MIN_S + m1.MIN_W
                                  + max(0, g.sd_m1_w // 2 - g.gate_w // 2)
                                  ) if has_right_contact else 0

        g.poly_ext_left = self._calc_poly_ext(
            r.GATE_EXT, g.gc_offset_left, g.gate_m1_w, m1.MIN_S,
            poly_ext_for_li, poly_ext_for_impl_left, g.is_ptype_sd,
            has_left_contact, poly_ext_for_bus_left)
        g.poly_ext_right = self._calc_poly_ext(
            r.GATE_EXT, g.gc_offset_right, g.gate_m1_w, m1.MIN_S,
            poly_ext_for_li, poly_ext_for_impl_right, g.is_ptype_sd,
            has_right_contact, poly_ext_for_bus_right)

        # Tap width
        base_tap_width = self._calc_tap_width() if self.tap else 0
        g.tap_width = base_tap_width + (m1.MIN_W + m1.MIN_S) if self.tap else 0

        # When a bus is placed outside the diff on the tap side (no gate contact
        # on that side), poly_ext must ensure:
        #   1. diff/tap.3 spacing: poly_ext + TAP_DIFF_SPACE >= DIFF_TAP_S
        #   2. M1 spacing: bus M1 to tap M1 >= M1.MIN_S
        if self.tap and base_tap_width > 0:
            # Compute tap M1 inner edge distance from device edge
            tap_cx_offset = (r.TAP_MARGIN
                             + g.tap_width - r.TAP_DIFF_SPACE) // 2
            tap_m1_hw = (mcon.W + 2 * mcon.ENC_TOP) // 2
            tap_m1_margin = g.tap_width - tap_cx_offset - tap_m1_hw

            min_ext_diff_tap = r.DIFF_TAP_S - r.TAP_DIFF_SPACE
            min_ext_m1_tap = 2 * m1.MIN_S + m1.MIN_W - tap_m1_margin
            min_ext_with_tap = max(min_ext_diff_tap, min_ext_m1_tap)

            # S bus outside diff on left: when no left contact
            s_bus_outside_left = not has_left_contact
            # D bus outside diff on right: when no right contact
            d_bus_outside_right = not has_right_contact

            if g.tap_left and s_bus_outside_left:
                g.poly_ext_left = max(g.poly_ext_left, min_ext_with_tap)
            if g.tap_right and d_bus_outside_right:
                g.poly_ext_right = max(g.poly_ext_right, min_ext_with_tap)

        # X positions
        g.dev_x0 = g.tap_width if g.tap_left else 0
        g.diff_x0 = g.dev_x0 + g.poly_ext_left
        g.diff_x1 = g.diff_x0 + g.gate_w
        g.poly_x0 = g.dev_x0
        g.poly_x1 = g.diff_x1 + g.poly_ext_right

        # Edge height (above/below diffusion for dummy poly)
        edge_for_dummy = g.gate_l + g.poly_to_diff
        g.edge_h = edge_for_dummy

        # Y positions
        g.y_first_sd = g.edge_h
        g.total_height = 2 * g.edge_h + (g.nf + 1) * g.sd_region + g.nf * g.gate_l
        g.diff_y0 = g.y_first_sd
        g.diff_y1 = g.total_height - g.edge_h
        g.total_width = g.poly_x1 + (g.tap_width if g.tap_right else 0)

        # Compute S/D and gate Y positions
        g.sd_cx = (g.diff_x0 + g.diff_x1) // 2
        g.gate_y_list = []
        g.src_cy_list = []
        g.drn_cy_list = []

        for i in range(g.nf):
            sd_y = g.y_first_sd + i * (g.sd_region + g.gate_l)
            sd_cy = sd_y + g.sd_region // 2
            if i % 2 == 0:
                g.src_cy_list.append(sd_cy)
            else:
                g.drn_cy_list.append(sd_cy)
            g.gate_y_list.append(sd_y + g.sd_region)

        final_sd_y = g.y_first_sd + g.nf * (g.sd_region + g.gate_l)
        final_sd_cy = final_sd_y + g.sd_region // 2
        if g.nf % 2 == 0:
            g.src_cy_list.append(final_sd_cy)
        else:
            g.drn_cy_list.append(final_sd_cy)

        # Gate contact X positions
        g.gc_left_x = g.dev_x0 + g.gc_offset_left
        g.gc_right_x = g.poly_x1 - g.gc_offset_right

        # Poly stripe X extents: active gates end at contact pad, dummies at GATE_EXT
        gc_pad_w = 2 * licon.W + licon.S + 2 * licon.ENC_POLY
        g.gate_poly_x0 = (g.gc_left_x - gc_pad_w // 2
                          if has_left_contact else g.diff_x0 - r.GATE_EXT)
        g.gate_poly_x1 = (g.gc_right_x + gc_pad_w // 2
                          if has_right_contact else g.diff_x1 + r.GATE_EXT)
        g.dummy_poly_x0 = g.diff_x0 - r.GATE_EXT
        g.dummy_poly_x1 = g.diff_x1 + r.GATE_EXT

        # S/D contact Y range (used for tap via placement)
        all_sd_cy = g.src_cy_list + g.drn_cy_list
        g.sd_cy_min = min(all_sd_cy)
        g.sd_cy_max = max(all_sd_cy)

        return g

    @staticmethod
    def _calc_poly_ext(ext_min, gc_offset, gate_m1_w, m1_min_s,
                       ext_for_li, ext_for_impl, is_ptype, has_contact,
                       ext_for_bus=0):
        """Compute poly extension for one side."""
        if not has_contact:
            return ext_min
        ext = max(ext_min, gc_offset + gate_m1_w // 2 + m1_min_s,
                  ext_for_li, ext_for_bus)
        if is_ptype:
            ext = max(ext, ext_for_impl)
        return ext

    # --- Drawing methods ---

    def _draw_diffusion(self, g):
        self.add_rect(self.DIFF_TYPE, g.diff_x0, g.diff_y0, g.diff_x1, g.diff_y1, net='diff')

    def _draw_poly(self, g):
        self._draw_poly_stripes(g)

    def _draw_poly_stripes(self, g):
        """Draw dummy and active poly gates as horizontal stripes."""
        # Bottom dummy (no net — not electrically connected)
        bot_y = (g.edge_h - g.poly_to_diff - g.gate_l) // 2
        g.dummy_bot = self.add_rect(POLY, g.gate_poly_x0, bot_y,
                                    g.gate_poly_x1, bot_y + g.gate_l)
        # Active gates
        for gy in g.gate_y_list:
            self.add_rect(POLY, g.gate_poly_x0, gy,
                          g.gate_poly_x1, gy + g.gate_l, net='G')
        # Top dummy (no net — not electrically connected)
        top_base = g.total_height - g.edge_h
        top_y = top_base + (g.edge_h + g.poly_to_diff - g.gate_l) // 2
        g.dummy_top = self.add_rect(POLY, g.gate_poly_x0, top_y,
                                    g.gate_poly_x1, top_y + g.gate_l)

    def _draw_implants(self, g):
        self.add_rect(self.DIFF_IMPLANT,
                      g.diff_x0 - g.impl_enc, g.diff_y0 - g.impl_enc,
                      g.diff_x1 + g.impl_enc, g.diff_y1 + g.impl_enc)

    def _draw_sd_contacts(self, g):
        """Draw S/D contact stacks, storing all M1 shapes for refs."""
        g.src_m1_list = []
        g.drn_m1_list = []
        for cy in g.src_cy_list:
            shape = self._draw_sd_contact(g.sd_cx, cy, g.gate_w, 'S')
            g.src_m1_list.append(shape)
        for cy in g.drn_cy_list:
            shape = self._draw_sd_contact(g.sd_cx, cy, g.gate_w, 'D')
            g.drn_m1_list.append(shape)

    def _draw_gate_contacts(self, g):
        """Draw gate contact stacks at each gate level."""
        g.gate_m1_list = []
        if self.poly_contact in ('left', 'both'):
            for gy in g.gate_y_list:
                shape = self._draw_gate_contact(g.gc_left_x, gy + g.gate_l // 2, 'G')
                g.gate_m1_list.append(shape)
        if self.poly_contact in ('right', 'both'):
            for gy in g.gate_y_list:
                shape = self._draw_gate_contact(g.gc_right_x, gy + g.gate_l // 2, 'G')
                g.gate_m1_list.append(shape)

    def _draw_m1_routing(self, g):
        """Draw M1 bus routing for multi-finger S/D and gate connections.

        S bus is placed on the gate contact side (same side as tap by default).
        D bus is placed on the opposite side, facing outward.
        For poly_contact='both': NFET S bus left, PFET S bus right.
        """
        m1_r = self.rules.M1
        m1_w = m1_r.MIN_W
        g.src_bus_m1 = None
        g.drn_bus_m1 = None
        g.gate_bus_m1 = None

        # Bus X positions per side
        has_left_gc = self.poly_contact in ('left', 'both')
        has_right_gc = self.poly_contact in ('right', 'both')
        left_bus_x = (g.gc_left_x + g.gate_m1_w // 2 + m1_r.MIN_S + m1_w // 2
                      if has_left_gc
                      else g.diff_x0 - m1_r.MIN_S - m1_w // 2)
        right_bus_x = (g.gc_right_x - g.gate_m1_w // 2 - m1_r.MIN_S - m1_w // 2
                       if has_right_gc
                       else g.diff_x1 + m1_r.MIN_S + m1_w // 2)

        # S bus on gate contact side; for 'both', use default tap side
        if self.poly_contact == 'both':
            s_bus_left = (self.DEFAULT_TAP == 'left')
        else:
            s_bus_left = (self.poly_contact == 'left')

        if s_bus_left:
            s_bus_x, d_bus_x = left_bus_x, right_bus_x
        else:
            s_bus_x, d_bus_x = right_bus_x, left_bus_x

        if len(g.src_cy_list) > 1:
            y0 = min(g.src_cy_list) - m1_w // 2
            y1 = max(g.src_cy_list) + m1_w // 2
            g.src_bus_m1 = self.add_rect(M1, s_bus_x - m1_w // 2, y0,
                                         s_bus_x + m1_w // 2, y1, net='S')
            for cy in g.src_cy_list:
                self.route((g.sd_cx, cy), (s_bus_x, cy), M1, m1_w, how='-', net='S')

        if len(g.drn_cy_list) > 1:
            y0 = min(g.drn_cy_list) - m1_w // 2
            y1 = max(g.drn_cy_list) + m1_w // 2
            g.drn_bus_m1 = self.add_rect(M1, d_bus_x - m1_w // 2, y0,
                                         d_bus_x + m1_w // 2, y1, net='D')
            for cy in g.drn_cy_list:
                self.route((g.sd_cx, cy), (d_bus_x, cy), M1, m1_w, how='-', net='D')

        # Gate M1 strap (multi-finger: connects all gate contacts)
        if g.nf > 1:
            gate_cy_list = [gy + g.gate_l // 2 for gy in g.gate_y_list]
            if has_left_gc:
                y0 = min(gate_cy_list) - g.gate_m1_h // 2
                y1 = max(gate_cy_list) + g.gate_m1_h // 2
                g.gate_bus_m1 = self.add_rect(
                    M1, g.gc_left_x - g.gate_m1_w // 2, y0,
                    g.gc_left_x + g.gate_m1_w // 2, y1, net='G')
            if has_right_gc:
                y0 = min(gate_cy_list) - g.gate_m1_h // 2
                y1 = max(gate_cy_list) + g.gate_m1_h // 2
                shape = self.add_rect(
                    M1, g.gc_right_x - g.gate_m1_w // 2, y0,
                    g.gc_right_x + g.gate_m1_w // 2, y1, net='G')
                if g.gate_bus_m1 is None:
                    g.gate_bus_m1 = shape

    def _draw_taps(self, g):
        g.tap_m1 = None
        if g.tap_left:
            g.tap_m1 = self._draw_tap(0, 0, g.tap_width, g.total_height,
                                      'left', g.sd_cy_min, g.sd_cy_max)
        if g.tap_right:
            shape = self._draw_tap(g.total_width - g.tap_width, 0,
                                   g.tap_width, g.total_height,
                                   'right', g.sd_cy_min, g.sd_cy_max)
            if g.tap_m1 is None:
                g.tap_m1 = shape

    def _draw_well(self, g):
        if self.SUB_TYPE is not None:
            enc = self.rules.MOS.SUB_ENC_DIFF
            self.add_rect(self.SUB_TYPE,
                          -enc, -enc,
                          g.total_width + enc, g.total_height + enc)

    def _add_refs(self, g):
        # Aggregate refs (first contact as default routing target)
        if g.src_m1_list:
            self.add_pin('S', g.src_m1_list[0])
        if g.drn_m1_list:
            self.add_pin('D', g.drn_m1_list[0])
        if g.gate_m1_list:
            self.add_pin('G', g.gate_m1_list[0])
        if g.tap_m1 is not None:
            self.add_pin('B', g.tap_m1)

        # Indexed refs (per-finger routing targets)
        for i, shape in enumerate(g.src_m1_list):
            self.add_ref(f'S{i}', shape)
        for i, shape in enumerate(g.drn_m1_list):
            self.add_ref(f'D{i}', shape)
        for i, shape in enumerate(g.gate_m1_list):
            self.add_ref(f'G{i}', shape)

        # Dummy poly refs
        self.add_ref('DBOT', g.dummy_bot)
        self.add_ref('DTOP', g.dummy_top)

        # Bus refs (multi-finger only)
        if g.src_bus_m1 is not None:
            self.add_ref('SBUS', g.src_bus_m1)
        if g.drn_bus_m1 is not None:
            self.add_ref('DBUS', g.drn_bus_m1)
        if g.gate_bus_m1 is not None:
            self.add_ref('GBUS', g.gate_bus_m1)

    # --- Component helpers ---

    def _calc_tap_width(self):
        """Calculate base tap region width (excluding M1 routing space)."""
        r = self.rules.MOS
        licon = self.rules.LICON
        return (r.TAP_MARGIN + 2 * licon.ENC_DIFF
                + r.CONTACT_SIZE + r.TAP_DIFF_SPACE)

    def _calc_via_count(self, available, via_size, via_space):
        """Calculate number of vias that fit in available space."""
        if available < via_size:
            return 0
        return max(1, (available + via_space) // (via_size + via_space))

    def _draw_sd_contact(self, cx, cy, width, net):
        """Draw source/drain contact stack: LICON -> LI -> MCON -> M1."""
        licon = self.rules.LICON
        mcon = self.rules.MCON
        cs = licon.W
        cs_space = licon.S
        li_enc = licon.ENC_LI
        m1_enc = mcon.ENC_TOP

        avail = width - 2 * licon.ENC_DIFF
        n_via = self._calc_via_count(avail, cs, cs_space)
        via_array_w = n_via * cs + (n_via - 1) * cs_space if n_via > 1 else cs

        li_w = via_array_w + 2 * li_enc
        li_h = cs + 2 * li_enc

        # LICON array
        via_x0 = cx - via_array_w // 2
        for i in range(n_via):
            vx = via_x0 + i * (cs + cs_space)
            self.add_rect(LICON, vx, cy - cs // 2, vx + cs, cy + cs // 2, net=net)

        # LI
        self.add_rect(LI, cx - li_w // 2, cy - li_h // 2,
                      cx + li_w // 2, cy + li_h // 2, net=net)

        # MCON array
        mcon_size = mcon.W
        mcon_space = mcon.S
        n_mcon = self._calc_via_count(via_array_w, mcon_size, mcon_space)
        mcon_array_w = n_mcon * mcon_size + (n_mcon - 1) * mcon_space if n_mcon > 1 else mcon_size

        mcon_x0 = cx - mcon_array_w // 2
        for i in range(n_mcon):
            mx = mcon_x0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, mx, cy - mcon_size // 2,
                          mx + mcon_size, cy + mcon_size // 2, net=net)

        # M1 (encloses MCON array, not LICON array)
        m1_w = mcon_array_w + 2 * m1_enc
        m1_h = mcon_size + 2 * m1_enc
        return self.add_rect(M1, cx - m1_w // 2, cy - m1_h // 2,
                             cx + m1_w // 2, cy + m1_h // 2, net=net)

    def _draw_gate_contact(self, cx, cy, net):
        """Draw gate contact: POLY -> 2x LICON -> LI -> 2x MCON -> M1 + NPC."""
        licon = self.rules.LICON
        mcon = self.rules.MCON
        npc = self.rules.NPC

        licon_size = licon.W
        licon_space = licon.S
        li_enc = licon.ENC_LI
        m1_enc = mcon.ENC_TOP
        poly_enc = licon.ENC_POLY
        mcon_size = mcon.W
        mcon_space = mcon.S

        n_via = 2
        licon_array_w = n_via * licon_size + (n_via - 1) * licon_space

        # Poly pad
        poly_w = licon_array_w + 2 * poly_enc
        poly_h = licon_size + 2 * poly_enc
        self.add_rect(POLY, cx - poly_w // 2, cy - poly_h // 2,
                      cx + poly_w // 2, cy + poly_h // 2, net=net)

        # LICONs
        licon_x0 = cx - licon_array_w // 2
        for i in range(n_via):
            vx = licon_x0 + i * (licon_size + licon_space)
            self.add_rect(LICON, vx, cy - licon_size // 2,
                          vx + licon_size, cy + licon_size // 2, net=net)

        # LI
        li_w = licon_array_w + 2 * li_enc
        li_h = licon_size + 2 * li_enc
        self.add_rect(LI, cx - li_w // 2, cy - li_h // 2,
                      cx + li_w // 2, cy + li_h // 2, net=net)

        # MCONs
        mcon_array_w = n_via * mcon_size + (n_via - 1) * mcon_space
        mcon_x0 = cx - mcon_array_w // 2
        for i in range(n_via):
            mx = mcon_x0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, mx, cy - mcon_size // 2,
                          mx + mcon_size, cy + mcon_size // 2, net=net)

        # M1
        m1_w = mcon_array_w + 2 * m1_enc
        m1_h = mcon_size + 2 * m1_enc
        m1_shape = self.add_rect(M1, cx - m1_w // 2, cy - m1_h // 2,
                                 cx + m1_w // 2, cy + m1_h // 2, net=net)

        # NPC
        npc_enc = npc.ENC
        self.add_rect(NPC, cx - licon_array_w // 2 - npc_enc,
                      cy - licon_size // 2 - npc_enc,
                      cx + licon_array_w // 2 + npc_enc,
                      cy + licon_size // 2 + npc_enc)

        return m1_shape

    def _draw_tap(self, x0, y0, width, height, side, via_y0, via_y1):
        """Draw substrate tap region.

        Vias (LICON/MCON) are placed only within the via_y0..via_y1 range
        (S/D contact Y range) so that stacked cells don't have via conflicts
        in the overlap region. TAP diffusion, implant, LI, and M1 span the
        full tap height.
        """
        r = self.rules.MOS
        licon = self.rules.LICON
        mcon = self.rules.MCON
        impl = self.rules.IMPL

        cs = licon.W
        cs_space = licon.S
        li_enc = licon.ENC_LI
        tap_margin = r.TAP_MARGIN
        tap_diff_space = r.TAP_DIFF_SPACE
        impl_enc = impl.ENC_DIFF

        if side == 'left':
            tap_x0 = x0 + tap_margin
            tap_x1 = x0 + width - tap_diff_space
        else:
            tap_x0 = x0 + tap_diff_space
            tap_x1 = x0 + width - tap_margin

        tap_y0 = y0 + tap_margin
        tap_y1 = y0 + height - tap_margin

        # TAP diffusion
        self.add_rect(self.TAP_TYPE, tap_x0, tap_y0, tap_x1, tap_y1, net='B')

        # Tap implant
        self.add_rect(self.TAP_IMPLANT,
                      tap_x0 - impl_enc, tap_y0 - impl_enc,
                      tap_x1 + impl_enc, tap_y1 + impl_enc)

        # Via arrays (vertical column, centered in tap diffusion)
        # Vias restricted to via_y0..via_y1 (S/D contact Y range)
        tap_cx = (tap_x0 + tap_x1) // 2
        mcon_size = mcon.W
        mcon_space = mcon.S
        mcon_enc = mcon.ENC_TOP

        avail_h = (via_y1 - via_y0)
        n_mcon = max(1, self._calc_via_count(avail_h, mcon_size, mcon_space))
        mcon_array_h = n_mcon * mcon_size + (n_mcon - 1) * mcon_space if n_mcon > 1 else mcon_size
        via_cy = (via_y0 + via_y1) // 2

        mcon_y0 = via_cy - mcon_array_h // 2
        for i in range(n_mcon):
            my = mcon_y0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, tap_cx - mcon_size // 2, my,
                          tap_cx + mcon_size // 2, my + mcon_size, net='B')

        # LICON array (match MCON count)
        n_licon = n_mcon
        licon_array_h = n_licon * cs + (n_licon - 1) * cs_space if n_licon > 1 else cs
        licon_y0 = via_cy - licon_array_h // 2
        for i in range(n_licon):
            vy = licon_y0 + i * (cs + cs_space)
            self.add_rect(LICON, tap_cx - cs // 2, vy,
                          tap_cx + cs // 2, vy + cs, net='B')

        # LI (full tap height)
        li_w = cs + 2 * li_enc
        self.add_rect(LI, tap_cx - li_w // 2, tap_y0,
                      tap_cx + li_w // 2, tap_y1, net='B')

        # M1 (full tap height)
        m1_w = mcon_size + 2 * mcon_enc
        return self.add_rect(M1, tap_cx - m1_w // 2, tap_y0,
                             tap_cx + m1_w // 2, tap_y1, net='B')


class NFET_01V8_Layout(MOSFET_Layout):
    """SKY130 1.8V NMOS transistor layout."""

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = NSDM
    TAP_TYPE = TAP
    TAP_IMPLANT = PSDM
    SUB_TYPE = None
    DEFAULT_TAP = 'left'

    def __init__(self, instance_name, parent, schematic,
                 tap=None, poly_contact=None):
        super().__init__(instance_name, parent, schematic=schematic,
                         tap=tap, poly_contact=poly_contact,
                         cell_name='nfet_01v8')


class PFET_01V8_Layout(MOSFET_Layout):
    """SKY130 1.8V PMOS transistor layout."""

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = PSDM
    TAP_TYPE = TAP
    TAP_IMPLANT = NSDM
    SUB_TYPE = NWELL
    DEFAULT_TAP = 'right'

    def __init__(self, instance_name, parent, schematic,
                 tap=None, poly_contact=None):
        super().__init__(instance_name, parent, schematic=schematic,
                         tap=tap, poly_contact=poly_contact,
                         cell_name='pfet_01v8')
