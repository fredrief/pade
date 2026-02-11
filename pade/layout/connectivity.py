"""Compile-time layout connectivity checks.

Provides short-circuit detection by flattening the layout hierarchy,
resolving nets, and checking for overlapping shapes with different nets
on the same connectivity layer.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional

from pade.layout.cell import LayoutCell
from pade.layout.shape import Shape


@dataclass
class Short:
    """A detected short between two nets on the same layer."""
    layer: str
    net_a: str
    net_b: str
    source_a: str
    source_b: str
    bounds_a: tuple
    bounds_b: tuple

    def __str__(self):
        return (f"SHORT on {self.layer}: "
                f"'{self.net_a}' ({self.source_a}) vs "
                f"'{self.net_b}' ({self.source_b})")


@dataclass
class ShortCheckResult:
    """Result of a short-circuit check."""
    shorts: List[Short] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return len(self.shorts) == 0

    def summary(self) -> str:
        if self.clean:
            return "No shorts detected."
        lines = [f"{len(self.shorts)} short(s) detected:\n"]
        for s in self.shorts:
            lines.append(f"  {s}")
        return '\n'.join(lines)

    def __str__(self):
        return self.summary()

    def __repr__(self):
        return f"ShortCheckResult(shorts={len(self.shorts)})"


def check_shorts(cell: LayoutCell) -> ShortCheckResult:
    """Check a layout cell for short circuits.

    Flattens the layout with hierarchical net resolution, then checks
    for overlapping shapes on the same connectivity layer that have
    different resolved net names.

    Only layers with ``connectivity=True`` are checked.
    Shapes without a net are silently skipped.

    Args:
        cell: Top-level LayoutCell to check.

    Returns:
        ShortCheckResult with any detected shorts.
    """
    shapes = cell.get_all_shapes(resolve_nets=True)

    # Group shapes by connectivity layer
    by_layer: dict[str, list[Shape]] = defaultdict(list)
    for s in shapes:
        if s.layer.connectivity and s.net is not None:
            by_layer[s.layer.name].append(s)

    shorts: list[Short] = []
    seen_pairs: set = set()

    for layer_name, layer_shapes in by_layer.items():
        n = len(layer_shapes)
        for i in range(n):
            a = layer_shapes[i]
            for j in range(i + 1, n):
                b = layer_shapes[j]
                if a.net == b.net:
                    continue
                # Check geometric overlap (including touching)
                if a.geometry.intersects(b.geometry):
                    # Deduplicate by sorted net pair + layer
                    pair_key = (layer_name,
                                min(a.net, b.net),
                                max(a.net, b.net))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        shorts.append(Short(
                            layer=layer_name,
                            net_a=a.net,
                            net_b=b.net,
                            source_a=a.source or '?',
                            source_b=b.source or '?',
                            bounds_a=a.bounds,
                            bounds_b=b.bounds,
                        ))

    return ShortCheckResult(shorts=shorts)
