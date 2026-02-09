"""SKY130 LayoutCell with config support."""

from typing import Optional, Tuple, Union
from pade.layout.cell import LayoutCell
from pade.layout.shape import Layer
from pade.layout.port import Port
from pade.layout.route import Route
from pdk.sky130.rules import sky130_rules

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

    def route(self, start: Union[Tuple[int, int], Port, str],
              end: Union[Tuple[int, int], Port, str],
              layer: Layer,
              width: Optional[int] = None,
              how: str = '-|',
              jog_start: int = 0,
              jog_end: int = 0,
              net: Optional[str] = None) -> Route:
        """
        Create and draw a route. Width defaults to layer minimum.
        
        Args:
            start: Starting point - (x, y) tuple, Port, or port name string
            end: Ending point - (x, y) tuple, Port, or port name string
            layer: Layer for the route
            width: Route width in nm (default: layer minimum from rules)
            how: Route pattern: '-', '-|', '|-'
            jog_start: Perpendicular offset at start (nm)
            jog_end: Perpendicular offset at end (nm)
            net: Net name (auto-detected from Port if not specified)
        
        Returns:
            The drawn Route object
        """
        if width is None:
            width = self._get_layer_min_width(layer)
        
        return super().route(start, end, layer, width, how, jog_start, jog_end, net)
    
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
