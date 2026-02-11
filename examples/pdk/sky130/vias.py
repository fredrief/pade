"""SKY130 via definitions and layer stack.

All dimensions in nm. Rules from SKY130 DRC manual (Table F3c, S8D flow).
"""

from dataclasses import dataclass
from pade.layout.shape import Layer
from pdk.sky130.layers import LI, M1, M2, M3, M4, M5, MCON, VIA1, VIA2, VIA3, VIA4


@dataclass
class ViaDefinition:
    """Rules for building a via between two adjacent routing layers.

    Enclosure rules follow the SKY130 directional pattern:
      - enc: minimum enclosure on all sides
      - enc_adj: enclosure required on at least one of two adjacent sides

    When drawing, enc_adj is applied in the x-direction and enc in the
    y-direction (satisfying the "one of two adjacent sides" rule).

    Attributes:
        name: Human-readable name (e.g. 'MCON')
        bot_layer: Bottom routing layer
        cut_layer: Via cut layer
        top_layer: Top routing layer
        cut_w: Cut width (nm)
        cut_h: Cut height (nm)
        cut_space: Min cut-to-cut spacing (nm)
        bot_enc: Bottom metal min enclosure, all sides (nm)
        bot_enc_adj: Bottom metal directional enclosure (nm)
        top_enc: Top metal min enclosure, all sides (nm)
        top_enc_adj: Top metal directional enclosure (nm)
    """
    name: str
    bot_layer: Layer
    cut_layer: Layer
    top_layer: Layer
    cut_w: int
    cut_h: int
    cut_space: int
    bot_enc: int
    bot_enc_adj: int
    top_enc: int
    top_enc_adj: int

    def max_cuts(self, w: int, h: int) -> tuple[int, int]:
        """Max cuts (nx, ny) fitting in an area of w × h (nm).

        The area is the region available for the cut array (no enclosure
        included — caller subtracts enclosures before calling if needed).
        """
        nx = max(1, (w + self.cut_space) // (self.cut_w + self.cut_space))
        ny = max(1, (h + self.cut_space) // (self.cut_h + self.cut_space))
        return nx, ny

    def array_extent(self, nx: int, ny: int) -> tuple[int, int]:
        """Total extent (w, h) of an nx × ny cut array, excluding enclosures."""
        w = nx * self.cut_w + max(0, nx - 1) * self.cut_space
        h = ny * self.cut_h + max(0, ny - 1) * self.cut_space
        return w, h


# ---------------------------------------------------------------------------
# SKY130 via definitions (from Table F3c / periphery rules)
# ---------------------------------------------------------------------------

#                                                    cut  cut  cut   bot   bot    top   top
#                                                    w    h    space enc   enc_a  enc   enc_a
MCON_DEF = ViaDefinition('MCON', LI, MCON, M1,
                         cut_w=170, cut_h=170, cut_space=190,
                         bot_enc=0,  bot_enc_adj=0,     # ct.4: LI enc >= 0
                         top_enc=30, top_enc_adj=60)     # met1.4/met1.5

VIA1_DEF = ViaDefinition('VIA1', M1, VIA1, M2,
                         cut_w=150, cut_h=150, cut_space=170,
                         bot_enc=55, bot_enc_adj=85,     # via.4a/via.5a
                         top_enc=55, top_enc_adj=85)     # met2.4/met2.5

VIA2_DEF = ViaDefinition('VIA2', M2, VIA2, M3,
                         cut_w=200, cut_h=200, cut_space=200,
                         bot_enc=40, bot_enc_adj=55,     # via2.4/via2.4a (generous for grid)
                         top_enc=55, top_enc_adj=75)     # met3.3/met3.4 (generous for grid + MIN_W)

VIA3_DEF = ViaDefinition('VIA3', M3, VIA3, M4,
                         cut_w=200, cut_h=200, cut_space=200,
                         bot_enc=60, bot_enc_adj=60,     # no directional rule found
                         top_enc=60, top_enc_adj=60)     # no directional rule found

VIA4_DEF = ViaDefinition('VIA4', M4, VIA4, M5,
                         cut_w=800, cut_h=800, cut_space=800,
                         bot_enc=190, bot_enc_adj=190,   # no directional rule found
                         top_enc=310, top_enc_adj=310)   # no directional rule found


# ---------------------------------------------------------------------------
# Layer stack and lookup
# ---------------------------------------------------------------------------

LAYER_STACK = [LI, M1, M2, M3, M4, M5]

# Map (bot_layer, top_layer) -> ViaDefinition for adjacent pairs
VIA_MAP = {
    (LI, M1): MCON_DEF,
    (M1, M2): VIA1_DEF,
    (M2, M3): VIA2_DEF,
    (M3, M4): VIA3_DEF,
    (M4, M5): VIA4_DEF,
}


def layer_in_stack(layer: Layer) -> bool:
    """Return True if *layer* is part of the routing layer stack."""
    return any(l == layer for l in LAYER_STACK)


def _layer_index(layer: Layer) -> int:
    """Return index of a layer in the stack. Handles alias names."""
    for i, l in enumerate(LAYER_STACK):
        if l == layer:
            return i
    raise ValueError(f"Layer {layer} not in LAYER_STACK")


def get_via_stack(bot_layer: Layer, top_layer: Layer) -> list[ViaDefinition]:
    """Return ordered list of ViaDefinitions needed between two layers.

    Works for non-adjacent layers (e.g. LI → M3 returns [MCON, VIA1, VIA2]).
    Order is always bottom-up regardless of argument order.
    """
    bot_idx = _layer_index(bot_layer)
    top_idx = _layer_index(top_layer)
    if bot_idx == top_idx:
        return []
    if bot_idx > top_idx:
        bot_idx, top_idx = top_idx, bot_idx
    stack = []
    for i in range(bot_idx, top_idx):
        pair = (LAYER_STACK[i], LAYER_STACK[i + 1])
        stack.append(VIA_MAP[pair])
    return stack
