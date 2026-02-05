"""PEX support for SKY130 cells."""

import re
from pathlib import Path
from pade.logging import logger


def _parse_pex_terminals(pex_path: Path, cell_name: str) -> list[str]:
    """Parse terminal order from PEX subckt definition."""
    content = pex_path.read_text()
    pattern = rf'^\.subckt\s+{re.escape(cell_name)}\s+(.+)$'
    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).split()
    return []


def pex_enabled(cls):
    """Decorator to add PEX netlist switching to a cell class.
    
    When PEX is enabled for an instance:
    - Switches source_path to PEX netlist
    - Reorders terminals to match PEX subckt definition
    - Clears parameters (PEX has fixed geometry)
    
    Example:
        CapMimM4 = pex_enabled(load_subckt('cap_mim_m4.spice'))
        
        # Then in testbench:
        cap = CapMimM4('C1', parent, w=10, pex={'C1': 'rc'})
    """
    from pdk.sky130.config import config
    
    original_init = cls.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        pex_cfg = kwargs.get('pex', {})
        if not pex_cfg:
            return
            
        hier_name = self.get_name_from_top()
        pex_type = pex_cfg.get(hier_name)
        
        if pex_type:
            pex_path = config.cell_pex_dir(self.cell_name) / f'pex_{pex_type}.spice'
            if pex_path.exists():
                self.source_path = pex_path
                
                # Reorder terminals to match PEX subckt definition
                pex_terminals = _parse_pex_terminals(pex_path, self.cell_name)
                if pex_terminals:
                    self.terminals = {name: self.terminals[name] for name in pex_terminals}
                
                # Clear parameters (PEX netlist has fixed geometry)
                self.parameters.clear()
                
                logger.info(f'PEX: {hier_name} -> {pex_path.name}')
            else:
                logger.warning(f'PEX: {pex_path} not found')
    
    cls.__init__ = new_init
    return cls
