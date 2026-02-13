"""SKY130 via definitions and layer stack.

Layer topology, cut-count helpers, and via-stack lookup.
All numeric rules come from sky130_rules (rules.py) — single source of truth.
"""

from dataclasses import dataclass
from pade.layout.shape import Layer
from pdk.sky130.layers import LI, M1, M2, M3, M4, M5, MCON, VIA1, VIA2, VIA3, VIA4
from pdk.sky130.rules import sky130_rules


@dataclass
class ViaDefinition:
    """Via between two adjacent routing layers.

    Enclosure rules follow the SKY130 directional pattern:
      - enc: minimum enclosure on all sides
      - enc_adj: enclosure required on at least one of two adjacent sides

    When drawing, enc_adj is applied in the x-direction and enc in the
    y-direction (satisfying the "one of two adjacent sides" rule).
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

    @classmethod
    def from_rules(cls, name: str, bot_layer: Layer, cut_layer: Layer,
                   top_layer: Layer, rules) -> 'ViaDefinition':
        """Construct from a DesignRules object (sky130_rules.MCON, etc.)."""
        return cls(
            name=name,
            bot_layer=bot_layer, cut_layer=cut_layer, top_layer=top_layer,
            cut_w=rules.W, cut_h=getattr(rules, 'H', rules.W),
            cut_space=rules.S,
            bot_enc=rules.ENC_BOT, bot_enc_adj=rules.ENC_BOT_ADJ,
            top_enc=rules.ENC_TOP, top_enc_adj=rules.ENC_TOP_ADJ,
        )

    def max_cuts(self, w: int, h: int) -> tuple[int, int]:
        """Max cuts (nx, ny) fitting in an area of w × h (nm)."""
        nx = max(1, (w + self.cut_space) // (self.cut_w + self.cut_space))
        ny = max(1, (h + self.cut_space) // (self.cut_h + self.cut_space))
        return nx, ny

    def array_extent(self, nx: int, ny: int) -> tuple[int, int]:
        """Total extent (w, h) of an nx × ny cut array, excluding enclosures."""
        w = nx * self.cut_w + max(0, nx - 1) * self.cut_space
        h = ny * self.cut_h + max(0, ny - 1) * self.cut_space
        return w, h

    def _metal_footprint(self, nx: int, ny: int) -> tuple[int, int]:
        """Max metal extent (w, h) across bot and top for nx×ny cuts.

        Uses the fixed convention: enc_adj in x, enc in y.
        """
        arr_w, arr_h = self.array_extent(nx, ny)
        bot_w = arr_w + 2 * self.bot_enc_adj
        bot_h = arr_h + 2 * self.bot_enc
        top_w = arr_w + 2 * self.top_enc_adj
        top_h = arr_h + 2 * self.top_enc
        return max(bot_w, top_w), max(bot_h, top_h)

    def corner_cuts(self) -> tuple[int, int]:
        """Optimal (nx, ny) for a 1×2 corner via minimizing footprint."""
        w_a, h_a = self._metal_footprint(1, 2)
        w_b, h_b = self._metal_footprint(2, 1)
        if max(w_a, h_a) <= max(w_b, h_b):
            return 1, 2
        return 2, 1

    def min_route_width(self) -> int:
        """Minimum route width for a corner 1×2 via to fit within the route."""
        nx, ny = self.corner_cuts()
        w, h = self._metal_footprint(nx, ny)
        return max(w, h)


MCON_DEF = ViaDefinition.from_rules('MCON', LI, MCON, M1, sky130_rules.MCON)
VIA1_DEF = ViaDefinition.from_rules('VIA1', M1, VIA1, M2, sky130_rules.VIA1)
VIA2_DEF = ViaDefinition.from_rules('VIA2', M2, VIA2, M3, sky130_rules.VIA2)
VIA3_DEF = ViaDefinition.from_rules('VIA3', M3, VIA3, M4, sky130_rules.VIA3)
VIA4_DEF = ViaDefinition.from_rules('VIA4', M4, VIA4, M5, sky130_rules.VIA4)


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
