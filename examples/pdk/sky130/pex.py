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


def _parameterized_cell_name(cell) -> str:
    """Build the parameterized cell name matching LayoutCell._generate_cell_name.

    Encodes schematic parameters into the name so PEX directory lookup
    matches the layout cell name used during extraction.
    """
    parts = [cell.cell_name]
    for name, param in cell.parameters.items():
        val = param.value
        name_str = name.upper()
        if isinstance(val, float):
            val_str = f'{val:g}'.replace('.', 'p').replace('-', 'm')
        elif isinstance(val, str):
            val_str = val.replace('.', 'p').replace('-', 'm').upper()
        else:
            val_str = str(val)
        parts.append(f'{name_str}{val_str}')
    return '_'.join(parts) if len(parts) > 1 else cell.cell_name


def pex_enabled(cls):
    """Decorator to add PEX netlist switching to a cell class.

    When PEX is enabled for an instance:
    - Switches source_path to PEX netlist
    - Reorders terminals to match PEX subckt definition
    - Clears subcells and parameters (PEX replaces the full hierarchy)

    PEX switching is deferred until the cell is registered as a subcell
    (via ``Cell.__setattr__``), at which point ``instance_name`` is available
    for matching against the PEX config.

    Example:
        @pex_enabled
        class CapMim(Cell):
            ...

        # Pre-layout (normal subcircuit)
        self.C1 = CapMim(w=10, l=10)

        # Post-layout (swap to PEX netlist via kwarg)
        self.C1 = CapMim(w=10, l=10, pex={'C1': 'rc'})
    """
    from pdk.sky130.config import config

    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        pex_cfg = kwargs.get('pex', {})
        if pex_cfg:
            self._pex_cfg = pex_cfg

    def _post_register(self):
        """Apply PEX switching after instance_name is set by parent."""
        pex_cfg = getattr(self, '_pex_cfg', None)
        if not pex_cfg:
            return

        hier_name = self.get_name_from_top()
        pex_type = pex_cfg.get(hier_name)

        if pex_type:
            full_name = _parameterized_cell_name(self)
            pex_path = config.cell_pex_dir(full_name) / f'pex_{pex_type}.spice'
            if pex_path.exists():
                self.source_path = pex_path
                self.cell_name = full_name

                pex_terminals = _parse_pex_terminals(pex_path, full_name)
                if pex_terminals:
                    self.terminals = {name: self.terminals[name] for name in pex_terminals}

                self.subcells.clear()
                self.parameters.clear()

                logger.info(f'PEX: {hier_name} -> {pex_path.name}')
            else:
                logger.warning(f'PEX: {pex_path} not found')

    cls.__init__ = new_init
    cls._post_register = _post_register
    return cls
