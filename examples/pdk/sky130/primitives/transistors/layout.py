"""SKY130 Transistor Layout Primitives.

Transistor layout with horizontal poly orientation:
- Poly runs horizontally (left-right)
- Source/Drain stacked vertically
- Tap on left (NFET) or right (PFET) by default
- Poly contact follows tap side
- Origin at lower-left corner
"""

from pdk.sky130.layout import SKY130LayoutCell
from pdk.sky130.layers import (
    POLY, DIFF, TAP, NWELL, PWELL, NSDM, PSDM, LI, LICON, MCON, NPC, M1
)


class MOSFET_Layout(SKY130LayoutCell):
    """
    Base MOSFET layout generator for SKY130.

    Parameters (all dimensions in um):
        w: Gate width (default 1.0 um)
        l: Gate length (default 0.15 um)
        nf: Number of fingers
        tap: 'left', 'right', 'both', or None
        poly_contact: 'left', 'right', 'both', or None (default follows tap)
        schematic: Optional schematic Cell instance (extracts w, l, nf)
    """

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = None
    TAP_TYPE = TAP
    TAP_IMPLANT = None
    SUB_TYPE = None
    DEFAULT_TAP = 'left'

    def __init__(self,
                 instance_name: str,
                 parent: SKY130LayoutCell = None,
                 schematic=None,
                 w: float = 1.0,
                 l: float = 0.15,
                 nf: int = 1,
                 tap: str = None,
                 poly_contact: str = None,
                 cell_name: str = None):
        """
        Create MOSFET layout.

        Args:
            instance_name: Instance name
            parent: Parent layout cell
            schematic: Schematic Cell instance (w, l, nf extracted from it)
            w: Gate width in um (default 1.0)
            l: Gate length in um (default 0.15)
            nf: Number of fingers (default 1)
            tap: Tap position ('left', 'right', 'both', None). Default: class default
            poly_contact: Poly contact position. Default: follows tap
            cell_name: Base cell name (used as prefix for encoded name)
        """
        # Resolve tap/poly_contact before passing as kwargs
        tap = tap if tap is not None else self.DEFAULT_TAP
        poly_contact = poly_contact if poly_contact is not None else tap
        if poly_contact is None:
            poly_contact = 'left'

        # Extract schematic parameters if provided
        if schematic is not None:
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
        """Check parameters against design rules (rules are in nm)."""
        r = self.rules.MOS
        l_nm = self.to_nm(self.l)
        w_nm = self.to_nm(self.w)
        if l_nm < r.MIN_L:
            raise ValueError(f"Gate length {l_nm}nm < minimum {r.MIN_L}nm")
        if w_nm < r.MIN_W:
            raise ValueError(f"Gate width {w_nm}nm < minimum {r.MIN_W}nm")
        if self.tap not in ('left', 'right', 'both', None):
            raise ValueError(f"Invalid tap position: {self.tap}")
        if self.poly_contact not in ('left', 'right', 'both', None):
            raise ValueError(f"Invalid poly_contact position: {self.poly_contact}")
    
    def _draw(self):
        """Draw the transistor."""
        if self.nf == 1:
            self._draw_single_finger()
        else:
            self._draw_multi_finger()
    
    def _draw_single_finger(self):
        """Draw a single-finger transistor with horizontal poly.
        
        Layout structure (vertical stacking):
            - Dummy poly (top)
            - Drain contact region
            - Active poly gate
            - Source contact region  
            - Dummy poly (bottom)
            
        Gate contacts at left/right ends of poly, past diffusion.
        """
        r = self.rules.MOS
        licon = self.rules.LICON
        mcon = self.rules.MCON
        m1 = self.rules.M1

        gate_w = self.to_nm(self.w)
        gate_l = self.to_nm(self.l)
        
        licon_size = licon.W  # LICON size (170nm)
        licon_space = licon.S  # LICON spacing (170nm)
        mcon_size = mcon.W  # MCON size (170nm)
        mcon_space = mcon.S  # MCON spacing (190nm)
        
        # S/D contact region height (diffusion extension beyond gate)
        sd_region = r.DIFF_EXT
        
        # Gate contact dimensions: 2 LICONs/MCONs arranged horizontally
        poly_enc_cont = licon.ENC_POLY
        licon_array_w = 2 * licon_size + licon_space  # 510nm
        mcon_array_w = 2 * mcon_size + mcon_space  # 530nm
        
        # Gate contact height (single row of vias)
        gate_cont_h = licon_size + 2 * poly_enc_cont
        
        # Gate contact M1 width (2 MCONs + enclosure)
        gate_m1_w = mcon_array_w + 2 * mcon.ENC_TOP  # ~650nm
        
        # Gate contact poly width
        gate_poly_w = licon_array_w + 2 * poly_enc_cont  # ~710nm
        
        # Poly extension beyond diffusion:
        # Need space for: gate M1 + S bus routing + spacing to S/D M1
        # Layout: gate_M1 | S_bus | gap | S/D_M1 | diffusion
        s_bus_w = m1.MIN_W
        poly_ext = gate_m1_w + m1.MIN_S + s_bus_w + m1.MIN_S
        
        # Tap dimensions - add spacing for S bus routing
        tap_spacing = m1.MIN_W + m1.MIN_S  # Space between tap M1 and S bus
        base_tap_width = self._calc_tap_width() if self.tap else 0
        tap_width = base_tap_width + tap_spacing if self.tap else 0
        tap_left = self.tap in ('left', 'both')
        tap_right = self.tap in ('right', 'both')
        
        # X positions
        dev_x0 = tap_width if tap_left else 0
        diff_x0 = dev_x0 + poly_ext
        diff_x1 = diff_x0 + gate_w
        poly_x0 = dev_x0
        poly_x1 = diff_x1 + poly_ext
        
        # Y positions (from bottom: dummy, source, gate, drain, dummy)
        # Dummy height matches gate contact height for proper stacking overlap
        dummy_h = max(gate_l, gate_cont_h)
        
        y_dummy_bot = 0
        y_src = dummy_h
        y_gate = y_src + sd_region
        y_drn = y_gate + gate_l
        y_dummy_top = y_drn + sd_region
        total_height = y_dummy_top + dummy_h
        
        # Diffusion spans from source region to drain region
        diff_y0 = y_src
        diff_y1 = y_drn + sd_region
        
        total_width = poly_x1 + (tap_width if tap_right else 0)
        
        # === Draw diffusion ===
        self.add_rect(self.DIFF_TYPE, diff_x0, diff_y0, diff_x1, diff_y1, net='diff')
        
        # === Draw poly gates (active + dummies) ===
        # Bottom dummy
        self.add_rect(POLY, poly_x0, y_dummy_bot, poly_x1, y_dummy_bot + dummy_h)
        # Active gate
        self.add_rect(POLY, poly_x0, y_gate, poly_x1, y_gate + gate_l, net='G')
        # Top dummy
        self.add_rect(POLY, poly_x0, y_dummy_top, poly_x1, y_dummy_top + dummy_h)
        
        # === Draw diffusion implant ===
        impl_ext = 125
        self.add_rect(self.DIFF_IMPLANT,
                      diff_x0 - impl_ext, diff_y0 - impl_ext,
                      diff_x1 + impl_ext, diff_y1 + impl_ext)
        
        # === Draw S/D contacts ===
        sd_cx = (diff_x0 + diff_x1) // 2
        src_cy = y_src + sd_region // 2
        drn_cy = y_drn + sd_region // 2
        
        self._draw_sd_contact(sd_cx, src_cy, gate_w, 'S')
        self._draw_sd_contact(sd_cx, drn_cy, gate_w, 'D')
        
        # === Draw gate contacts (at outer ends of poly, leaving room for routing) ===
        gate_cy = y_gate + gate_l // 2
        # Gate contact center at half the gate M1 width from poly edge
        gc_offset = gate_m1_w // 2  # Contact center from poly edge
        if self.poly_contact in ('left', 'both'):
            gc_cx = dev_x0 + gc_offset
            self._draw_gate_contact(gc_cx, gate_cy, 'G')
        if self.poly_contact in ('right', 'both'):
            gc_cx = poly_x1 - gc_offset
            self._draw_gate_contact(gc_cx, gate_cy, 'G')
        
        # === Draw tap ===
        if tap_left:
            self._draw_tap(0, 0, tap_width, total_height, 'left')
        if tap_right:
            self._draw_tap(total_width - tap_width, 0, tap_width, total_height, 'right')
        
        # === Draw well (NWELL for PFET) ===
        if self.SUB_TYPE is not None:
            well_enc = r.SUB_ENC_DIFF
            self.add_rect(self.SUB_TYPE,
                          -well_enc, -well_enc,
                          total_width + well_enc, total_height + well_enc)
        
        # === Add ports ===
        self.add_port('S', M1, sd_cx, src_cy)
        self.add_port('D', M1, sd_cx, drn_cy)
        if self.poly_contact in ('left', 'both'):
            self.add_port('G', M1, dev_x0 + gc_offset, gate_cy)
        elif self.poly_contact == 'right':
            self.add_port('G', M1, poly_x1 - gc_offset, gate_cy)
        
        if tap_left:
            self.add_port('B', M1, base_tap_width // 2, total_height // 2)
        elif tap_right:
            self.add_port('B', M1, total_width - base_tap_width // 2, total_height // 2)
    
    def _calc_tap_width(self) -> int:
        """Calculate tap region width."""
        r = self.rules.MOS
        contact_size = r.CONTACT_SIZE
        # Tap needs: enclosure + contact + enclosure + spacing to diff
        tap_enc = 60  # Tap enclosure of contact
        tap_to_diff = 200  # Spacing from tap to diffusion
        return tap_enc + contact_size + tap_enc + tap_to_diff
    
    def _calc_via_count(self, available: int, via_size: int, via_space: int) -> int:
        """Calculate number of vias that fit in available space."""
        if available < via_size:
            return 0
        return max(1, (available + via_space) // (via_size + via_space))

    def _draw_sd_contact(self, cx: int, cy: int, width: int, net: str):
        """
        Draw source/drain contact stack: LICON -> LI -> MCON -> M1.
        
        Via count scales with width. LI and M1 sized to enclose vias only.
        """
        licon = self.rules.LICON
        mcon = self.rules.MCON
        
        cs = licon.W
        cs_space = licon.S
        li_enc = licon.ENC_LI
        m1_enc = mcon.ENC_TOP
        
        # Calculate number of LICON/MCON based on width
        # Available width for vias (with enclosure margin)
        avail = width - 2 * licon.ENC_DIFF
        n_via = self._calc_via_count(avail, cs, cs_space)
        
        # Total width of via array
        via_array_w = n_via * cs + (n_via - 1) * cs_space if n_via > 1 else cs
        
        # LI and M1 dimensions (just enclose the vias)
        li_w = via_array_w + 2 * li_enc
        li_h = cs + 2 * li_enc
        m1_w = via_array_w + 2 * m1_enc
        m1_h = cs + 2 * m1_enc
        
        # Draw LICON array
        via_x0 = cx - via_array_w // 2
        for i in range(n_via):
            vx = via_x0 + i * (cs + cs_space)
            self.add_rect(LICON, vx, cy - cs // 2, vx + cs, cy + cs // 2, net=net)
        
        # LI
        self.add_rect(LI, cx - li_w // 2, cy - li_h // 2,
                      cx + li_w // 2, cy + li_h // 2, net=net)
        
        # MCON array (same positions as LICON)
        mcon_size = mcon.W
        mcon_space = mcon.S
        n_mcon = self._calc_via_count(via_array_w, mcon_size, mcon_space)
        mcon_array_w = n_mcon * mcon_size + (n_mcon - 1) * mcon_space if n_mcon > 1 else mcon_size
        
        mcon_x0 = cx - mcon_array_w // 2
        for i in range(n_mcon):
            mx = mcon_x0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, mx, cy - mcon_size // 2, mx + mcon_size, cy + mcon_size // 2, net=net)
        
        # M1
        self.add_rect(M1, cx - m1_w // 2, cy - m1_h // 2,
                      cx + m1_w // 2, cy + m1_h // 2, net=net)

    def _draw_gate_contact(self, cx: int, cy: int, net: str):
        """
        Draw gate contact at end of poly with M1 access.
        
        Stack: POLY -> 2x LICON (horizontal) -> LI -> 2x MCON (horizontal) -> M1
        """
        licon = self.rules.LICON
        mcon = self.rules.MCON
        
        licon_size = licon.W  # 170
        licon_space = licon.S  # 170
        li_enc = licon.ENC_LI
        m1_enc = mcon.ENC_TOP
        poly_enc = licon.ENC_POLY
        mcon_size = mcon.W  # 170
        mcon_space = mcon.S  # 190
        
        # 2 LICONs arranged horizontally
        n_via = 2
        licon_array_w = n_via * licon_size + (n_via - 1) * licon_space  # 510nm
        
        # Poly extension to cover LICONs (horizontal)
        poly_w = licon_array_w + 2 * poly_enc
        poly_h = licon_size + 2 * poly_enc
        self.add_rect(POLY, cx - poly_w // 2, cy - poly_h // 2,
                      cx + poly_w // 2, cy + poly_h // 2, net=net)
        
        # Draw 2 LICONs (horizontal row)
        licon_x0 = cx - licon_array_w // 2
        for i in range(n_via):
            vx = licon_x0 + i * (licon_size + licon_space)
            self.add_rect(LICON, vx, cy - licon_size // 2, vx + licon_size, cy + licon_size // 2, net=net)
        
        # LI (encloses LICONs)
        li_w = licon_array_w + 2 * li_enc
        li_h = licon_size + 2 * li_enc
        self.add_rect(LI, cx - li_w // 2, cy - li_h // 2,
                      cx + li_w // 2, cy + li_h // 2, net=net)
        
        # 2 MCONs arranged horizontally
        mcon_array_w = n_via * mcon_size + (n_via - 1) * mcon_space  # 530nm
        mcon_x0 = cx - mcon_array_w // 2
        for i in range(n_via):
            mx = mcon_x0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, mx, cy - mcon_size // 2, mx + mcon_size, cy + mcon_size // 2, net=net)
        
        # M1 (encloses MCONs)
        m1_w = mcon_array_w + 2 * m1_enc
        m1_h = mcon_size + 2 * m1_enc
        self.add_rect(M1, cx - m1_w // 2, cy - m1_h // 2,
                      cx + m1_w // 2, cy + m1_h // 2, net=net)
        
        # NPC (enclosure around poly contact area)
        npc_enc = 100
        self.add_rect(NPC, cx - licon_array_w // 2 - npc_enc, cy - licon_size // 2 - npc_enc,
                      cx + licon_array_w // 2 + npc_enc, cy + licon_size // 2 + npc_enc)
    
    def _draw_tap(self, x0: int, y0: int, width: int, height: int, side: str):
        """
        Draw substrate tap region.
        
        Args:
            x0, y0: Lower-left corner of tap region
            width, height: Tap region size
            side: 'left' or 'right'
        """
        licon = self.rules.LICON
        cs = licon.W
        cs_space = licon.S
        li_enc = licon.ENC_LI
        tap_enc = 60  # Tap enclosure of contact
        
        # Tap diffusion (fill region minus spacing to active diff)
        tap_margin = 50
        diff_space = 130  # Space between tap and active diffusion
        if side == 'left':
            tap_x0 = x0 + tap_margin
            tap_x1 = x0 + width - diff_space
        else:
            tap_x0 = x0 + diff_space
            tap_x1 = x0 + width - tap_margin
        
        tap_y0 = y0 + tap_margin
        tap_y1 = y0 + height - tap_margin
        
        # TAP layer
        self.add_rect(self.TAP_TYPE, tap_x0, tap_y0, tap_x1, tap_y1, net='B')
        
        # Tap implant
        impl_ext = 125
        self.add_rect(self.TAP_IMPLANT,
                      tap_x0 - impl_ext, tap_y0 - impl_ext,
                      tap_x1 + impl_ext, tap_y1 + impl_ext)
        
        # Via array (vertical column)
        tap_cx = (tap_x0 + tap_x1) // 2
        tap_cy = (tap_y0 + tap_y1) // 2
        
        # MCON array
        mcon = self.rules.MCON
        mcon_size = mcon.W
        mcon_space = mcon.S
        mcon_enc = mcon.ENC_TOP
        
        # Leave margin at top/bottom for dummy poly overlap when stacking
        # Margin = dummy height + S/D region to avoid contact overlap
        licon_size = self.rules.LICON.W
        poly_enc_cont = self.rules.LICON.ENC_POLY
        gate_cont_h = licon_size + 2 * poly_enc_cont
        sd_region = self.rules.MOS.DIFF_EXT
        via_margin = gate_cont_h + sd_region
        
        # Calculate MCON array with margin
        via_region_y0 = tap_y0 + via_margin
        via_region_y1 = tap_y1 - via_margin
        avail_mcon_h = via_region_y1 - via_region_y0 - 2 * mcon_enc
        n_mcon = max(1, self._calc_via_count(avail_mcon_h, mcon_size, mcon_space))
        mcon_array_h = n_mcon * mcon_size + (n_mcon - 1) * mcon_space if n_mcon > 1 else mcon_size
        via_cy = (via_region_y0 + via_region_y1) // 2
        mcon_y0 = via_cy - mcon_array_h // 2
        
        for i in range(n_mcon):
            my = mcon_y0 + i * (mcon_size + mcon_space)
            self.add_rect(MCON, tap_cx - mcon_size // 2, my,
                          tap_cx + mcon_size // 2, my + mcon_size, net='B')
        
        # LICON array - match MCON count and region
        n_licon = n_mcon
        licon_array_h = n_licon * cs + (n_licon - 1) * cs_space if n_licon > 1 else cs
        licon_y0 = via_cy - licon_array_h // 2
        
        for i in range(n_licon):
            vy = licon_y0 + i * (cs + cs_space)
            self.add_rect(LICON, tap_cx - cs // 2, vy, tap_cx + cs // 2, vy + cs, net='B')
        
        # LI (covers full tap height for stacking)
        li_w = cs + 2 * li_enc
        self.add_rect(LI, tap_cx - li_w // 2, tap_y0,
                      tap_cx + li_w // 2, tap_y1, net='B')
        
        # M1 (covers full tap region for stacking overlap)
        m1_w = mcon_size + 2 * mcon_enc
        self.add_rect(M1, tap_cx - m1_w // 2, tap_y0,
                      tap_cx + m1_w // 2, tap_y1, net='B')
    
    def _draw_multi_finger(self):
        """
        Draw multi-finger transistor with dummy poly.
        
        Structure (from bottom to top):
            - Bottom dummy poly
            - Source contact region
            - Gate 1
            - Drain contact region
            - Gate 2
            - Source contact region
            - ... (alternating)
            - Top dummy poly
        """
        r = self.rules.MOS
        licon = self.rules.LICON
        mcon = self.rules.MCON
        m1 = self.rules.M1

        gate_w = self.to_nm(self.w)
        gate_l = self.to_nm(self.l)
        sd_region = r.DIFF_EXT
        
        licon_size = licon.W
        licon_space = licon.S
        mcon_size = mcon.W
        mcon_space = mcon.S
        
        # Gate contact dimensions: 2 LICONs/MCONs arranged horizontally
        poly_enc_cont = licon.ENC_POLY
        licon_array_w = 2 * licon_size + licon_space  # 510nm
        mcon_array_w = 2 * mcon_size + mcon_space  # 530nm
        
        # Gate contact height (single row of vias)
        gate_cont_h = licon_size + 2 * poly_enc_cont
        
        # Gate contact M1 width (2 MCONs + enclosure)
        gate_m1_w = mcon_array_w + 2 * mcon.ENC_TOP
        
        # Gate contact poly width
        gate_poly_w = licon_array_w + 2 * poly_enc_cont
        
        # Poly extension beyond diffusion:
        # Need space for: gate M1 + S bus routing + spacing to S/D M1
        s_bus_w = m1.MIN_W
        poly_ext = gate_m1_w + m1.MIN_S + s_bus_w + m1.MIN_S
        
        # Gate contact center offset from poly edge
        gc_offset = gate_m1_w // 2
        
        # Tap dimensions - add spacing for S bus routing
        tap_spacing = m1.MIN_W + m1.MIN_S
        base_tap_width = self._calc_tap_width() if self.tap else 0
        tap_width = base_tap_width + tap_spacing if self.tap else 0
        tap_left = self.tap in ('left', 'both')
        tap_right = self.tap in ('right', 'both')
        
        # X positions
        dev_x0 = tap_width if tap_left else 0
        diff_x0 = dev_x0 + poly_ext
        diff_x1 = diff_x0 + gate_w
        poly_x0 = dev_x0
        poly_x1 = diff_x1 + poly_ext
        
        # Y positions - dummy height matches gate contact height for stacking
        dummy_h = max(gate_l, gate_cont_h)
        y_dummy_bot = 0
        y_first_sd = dummy_h  # First S/D region starts after bottom dummy
        
        # Total height: dummy + nf*(sd + gate) + sd + dummy
        # = 2*dummy + (nf+1)*sd + nf*gate
        total_height = 2 * dummy_h + (self.nf + 1) * sd_region + self.nf * gate_l
        
        # Diffusion spans all S/D regions and gates
        diff_y0 = y_first_sd
        diff_y1 = total_height - dummy_h
        
        total_width = poly_x1 + (tap_width if tap_right else 0)
        
        # === Draw diffusion ===
        self.add_rect(self.DIFF_TYPE, diff_x0, diff_y0, diff_x1, diff_y1, net='diff')
        
        # === Draw diffusion implant ===
        impl_ext = 125
        self.add_rect(self.DIFF_IMPLANT,
                      diff_x0 - impl_ext, diff_y0 - impl_ext,
                      diff_x1 + impl_ext, diff_y1 + impl_ext)
        
        # === Draw dummy poly (bottom and top) ===
        self.add_rect(POLY, poly_x0, y_dummy_bot, poly_x1, y_dummy_bot + dummy_h)
        y_dummy_top = total_height - dummy_h
        self.add_rect(POLY, poly_x0, y_dummy_top, poly_x1, y_dummy_top + dummy_h)
        
        # === Draw active gates and contacts ===
        sd_cx = (diff_x0 + diff_x1) // 2
        gate_cy_list = []
        src_cy_list = []
        drn_cy_list = []
        
        for i in range(self.nf):
            # S/D region before this gate
            sd_y = y_first_sd + i * (sd_region + gate_l)
            sd_cy = sd_y + sd_region // 2
            if i % 2 == 0:
                src_cy_list.append(sd_cy)
                self._draw_sd_contact(sd_cx, sd_cy, gate_w, 'S')
            else:
                drn_cy_list.append(sd_cy)
                self._draw_sd_contact(sd_cx, sd_cy, gate_w, 'D')
            
            # Gate
            gate_y = sd_y + sd_region
            self.add_rect(POLY, poly_x0, gate_y, poly_x1, gate_y + gate_l, net='G')
            gate_cy_list.append(gate_y + gate_l // 2)
        
        # Final S/D region after last gate
        final_sd_y = y_first_sd + self.nf * (sd_region + gate_l)
        final_sd_cy = final_sd_y + sd_region // 2
        if self.nf % 2 == 0:
            src_cy_list.append(final_sd_cy)
            self._draw_sd_contact(sd_cx, final_sd_cy, gate_w, 'S')
        else:
            drn_cy_list.append(final_sd_cy)
            self._draw_sd_contact(sd_cx, final_sd_cy, gate_w, 'D')
        
        # === Connect S/D regions using M1 vertical straps ===
        # S bus between tap and gate contact, D bus between diffusion and right gate contact
        m1_w = m1.MIN_W
        
        # Gate contact X positions
        gc_left_x = dev_x0 + gc_offset
        gc_right_x = poly_x1 - gc_offset
        
        # S bus: between tap and left gate contact (or at left edge if no tap)
        # D bus: between diffusion and right gate contact
        s_bus_x = gc_left_x + gate_m1_w // 2 + m1.MIN_S + m1_w // 2
        d_bus_x = diff_x1 + m1.MIN_S + m1_w // 2
        
        if len(src_cy_list) > 1:
            # Vertical S bus
            s_y0 = min(src_cy_list) - m1_w // 2
            s_y1 = max(src_cy_list) + m1_w // 2
            self.add_rect(M1, s_bus_x - m1_w // 2, s_y0, s_bus_x + m1_w // 2, s_y1, net='S')
            # Horizontal M1 routes from each S contact to the bus
            for src_cy in src_cy_list:
                self.route((sd_cx, src_cy), (s_bus_x, src_cy), M1, m1_w, how='-', net='S')
        
        if len(drn_cy_list) > 1:
            # Vertical D bus
            d_y0 = min(drn_cy_list) - m1_w // 2
            d_y1 = max(drn_cy_list) + m1_w // 2
            self.add_rect(M1, d_bus_x - m1_w // 2, d_y0, d_bus_x + m1_w // 2, d_y1, net='D')
            # Horizontal M1 routes from each D contact to the bus
            for drn_cy in drn_cy_list:
                self.route((sd_cx, drn_cy), (d_bus_x, drn_cy), M1, m1_w, how='-', net='D')
        
        # === Route gate connections using M1 ===
        # Vertical M1 strap connecting all gate contacts
        if self.nf > 1:
            if self.poly_contact in ('left', 'both'):
                g_y0 = min(gate_cy_list) - gate_m1_w // 2
                g_y1 = max(gate_cy_list) + gate_m1_w // 2
                self.add_rect(M1, gc_left_x - gate_m1_w // 2, g_y0,
                              gc_left_x + gate_m1_w // 2, g_y1, net='G')
            if self.poly_contact in ('right', 'both'):
                g_y0 = min(gate_cy_list) - gate_m1_w // 2
                g_y1 = max(gate_cy_list) + gate_m1_w // 2
                self.add_rect(M1, gc_right_x - gate_m1_w // 2, g_y0,
                              gc_right_x + gate_m1_w // 2, g_y1, net='G')
        
        # === Draw gate contacts ===
        if self.poly_contact in ('left', 'both'):
            for gc_cy in gate_cy_list:
                self._draw_gate_contact(gc_left_x, gc_cy, 'G')
        if self.poly_contact in ('right', 'both'):
            for gc_cy in gate_cy_list:
                self._draw_gate_contact(gc_right_x, gc_cy, 'G')
        
        # === Draw taps ===
        if tap_left:
            self._draw_tap(0, 0, tap_width, total_height, 'left')
        if tap_right:
            self._draw_tap(total_width - tap_width, 0, tap_width, total_height, 'right')
        
        # === Draw well (NWELL for PFET) ===
        if self.SUB_TYPE is not None:
            well_enc = r.SUB_ENC_DIFF
            self.add_rect(self.SUB_TYPE,
                          -well_enc, -well_enc,
                          total_width + well_enc, total_height + well_enc)
        
        # === Add ports ===
        # Source at first S region
        self.add_port('S', M1, sd_cx, src_cy_list[0])
        # Drain at first D region
        self.add_port('D', M1, sd_cx, drn_cy_list[0])
        # Gate (on M1)
        if self.poly_contact in ('left', 'both'):
            self.add_port('G', M1, gc_left_x, gate_cy_list[0])
        elif self.poly_contact == 'right':
            self.add_port('G', M1, gc_right_x, gate_cy_list[0])
        # Bulk (on M1)
        if tap_left:
            self.add_port('B', M1, base_tap_width // 2, total_height // 2)
        elif tap_right:
            self.add_port('B', M1, total_width - base_tap_width // 2, total_height // 2)


class NFET_01V8_Layout(MOSFET_Layout):
    """SKY130 1.8V NMOS transistor layout."""

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = NSDM
    TAP_TYPE = TAP
    TAP_IMPLANT = PSDM
    SUB_TYPE = None
    DEFAULT_TAP = 'left'

    def __init__(self, instance_name: str, parent: SKY130LayoutCell = None,
                 schematic=None, w: float = 1.0, l: float = 0.15, nf: int = 1,
                 tap: str = None, poly_contact: str = None):
        super().__init__(instance_name, parent, schematic=schematic,
                         w=w, l=l, nf=nf, tap=tap, poly_contact=poly_contact,
                         cell_name='nfet_01v8')


class PFET_01V8_Layout(MOSFET_Layout):
    """SKY130 1.8V PMOS transistor layout."""

    DIFF_TYPE = DIFF
    DIFF_IMPLANT = PSDM
    TAP_TYPE = TAP
    TAP_IMPLANT = NSDM
    SUB_TYPE = NWELL
    DEFAULT_TAP = 'right'

    def __init__(self, instance_name: str, parent: SKY130LayoutCell = None,
                 schematic=None, w: float = 1.0, l: float = 0.15, nf: int = 1,
                 tap: str = None, poly_contact: str = None):
        super().__init__(instance_name, parent, schematic=schematic,
                         w=w, l=l, nf=nf, tap=tap, poly_contact=poly_contact,
                         cell_name='pfet_01v8')
