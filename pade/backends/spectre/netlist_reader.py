"""
Spectre netlist reader - parses .scs/.txt subcircuit definitions.
"""

import re
from pathlib import Path
from typing import Optional

from pade.backends.base import NetlistReader
from pade.core.cell import Cell
from pade.core.parameter import Parameter


class NetlistCell(Cell):
    """
    A cell representing a subcircuit imported from an external netlist file.

    Unlike regular Cells that are defined in Python, NetlistCell is a "black box"
    that references an existing subcircuit definition from a netlist file.
    The netlist writer will inline the subcircuit content.

    Attributes:
        source_path: Path to the netlist file containing the subcircuit

    Example:
        # In components/devices.py
        from pade.backends.spectre import load_subckt

        NCH = load_subckt('/path/to/NCH.txt')
        PCH = load_subckt('/path/to/PCH.txt')

        # In testbench
        from components.devices import NCH, PCH

        mn = NCH('MN', self, wf='1u', l='200n')
        mn.connect(['D', 'G', 'S', 'B'], ['out', 'inp', '0', '0'])
    """

    def __init__(self,
                 instance_name: str,
                 parent: Optional[Cell] = None,
                 cell_name: Optional[str] = None,
                 source_path: Optional[str | Path] = None,
                 terminals: list[str] = None,
                 parameters: Optional[dict[str, Parameter]] = None,
                 **kwargs):
        """
        Create a netlist cell instance.

        Args:
            instance_name: Instance name (e.g., 'MN', 'MP')
            parent: Parent cell
            cell_name: Subcircuit name (e.g., 'NCH', 'PCH')
            source_path: Path to source netlist file
            terminals: List of terminal names (required)
            parameters: Dict of parameters with defaults
            **kwargs: Parameter values to override defaults
        """
        if terminals is None:
            raise ValueError("NetlistCell requires terminals")

        super().__init__(instance_name, parent, cell_name=cell_name)
        self.source_path = Path(source_path) if source_path else None

        # Add terminals (required)
        self.add_terminal(terminals)

        # Set parameters with defaults, allow overrides via kwargs
        if parameters:
            for name, param in parameters.items():
                if name in kwargs:
                    # User provided override
                    self.set_parameter(name, kwargs[name], default=param.default)
                else:
                    # Use default value
                    self.set_parameter(name, param.value, default=param.default)

    @classmethod
    def info(cls) -> str:
        """Return info string showing terminals and parameters."""
        # This will be overridden by the factory function
        return f"{cls.__name__}()"


def _make_netlist_cell_class(subckt_name: str,
                              source_path: Path,
                              terminal_names: list[str],
                              param_defaults: dict[str, Parameter]) -> type[NetlistCell]:
    """
    Create a NetlistCell subclass for a specific subcircuit.

    This allows creating instances like: NCH('M1', parent, wf='2u', l='300n')
    """
    class _NetlistCell(NetlistCell):
        def __init__(self,
                     instance_name: str,
                     parent: Optional[Cell] = None,
                     **kwargs):
            super().__init__(
                instance_name,
                parent,
                cell_name=subckt_name,
                source_path=source_path,
                terminals=terminal_names,
                parameters=param_defaults,
                **kwargs
            )

        @classmethod
        def info(cls) -> str:
            """Return info string showing terminals and parameters."""
            terms = ', '.join(terminal_names)
            params = ', '.join(f'{n}={p.default}' for n, p in param_defaults.items())
            return f"{subckt_name}({terms}) parameters: {params}"

    _NetlistCell.__name__ = subckt_name
    _NetlistCell.__qualname__ = subckt_name
    _NetlistCell.__doc__ = f"NetlistCell for {subckt_name} from {source_path}"
    return _NetlistCell


def load_subckt(path: str | Path, subckt_name: str | None = None) -> type[NetlistCell]:
    """
    Load a subcircuit from a Spectre netlist file.

    This is the recommended way to import external subcircuits for use in PADE.

    Args:
        path: Path to netlist file (.scs, .txt)
        subckt_name: Name of subcircuit to load (if None, loads first/only subckt)

    Returns:
        NetlistCell class that can be instantiated like any other Cell

    Example:
        # In components/devices.py
        from pade.backends.spectre import load_subckt

        NCH = load_subckt('/path/to/NCH.txt')
        PCH = load_subckt('/path/to/PCH.txt')

        # In testbench
        from components.devices import NCH, PCH

        mn = NCH('MN', self, wf='1u', l='200n')
        mp = PCH('MP', self, wf='2u', l='200n')
    """
    reader = SpectreNetlistReader()
    return reader.read_subckt(path, subckt_name)


class SpectreNetlistReader(NetlistReader):
    """
    Reads Spectre format netlist files (.scs, .txt).

    Parses subcircuit definitions and returns Cell classes that can be
    instantiated in other cells.

    For simple usage, prefer the `load_subckt()` function instead.
    """

    # Regex patterns for parsing
    _SUBCKT_START = re.compile(r'^\s*subckt\s+(\w+)\s+(.+)', re.IGNORECASE)
    _PARAMETERS = re.compile(r'^\s*parameters\s+(.+)', re.IGNORECASE)
    _ENDS = re.compile(r'^\s*ends\s+(\w+)?', re.IGNORECASE)
    _PARAM_VALUE = re.compile(r'(\w+)\s*=\s*([^\s]+)')

    def read_subckt(self, path: str | Path, subckt_name: str | None = None) -> type[NetlistCell]:
        """
        Read a subcircuit from a Spectre netlist file.

        Args:
            path: Path to netlist file
            subckt_name: Name of subcircuit to read (if None, reads first subckt)

        Returns:
            NetlistCell class that can be instantiated
        """
        path = Path(path)
        subckts = self._parse_file(path)

        if not subckts:
            raise ValueError(f"No subcircuits found in {path}")

        if subckt_name is None:
            # Return first subcircuit
            name, data = next(iter(subckts.items()))
        else:
            if subckt_name not in subckts:
                available = ', '.join(subckts.keys())
                raise ValueError(
                    f"Subcircuit '{subckt_name}' not found in {path}. "
                    f"Available: {available}"
                )
            name = subckt_name
            data = subckts[subckt_name]

        return _make_netlist_cell_class(
            subckt_name=name,
            source_path=path,
            terminal_names=data['terminals'],
            param_defaults=data['parameters']
        )

    def list_subckts(self, path: str | Path) -> list[str]:
        """List all subcircuit names in a netlist file."""
        path = Path(path)
        subckts = self._parse_file(path)
        return list(subckts.keys())

    def _parse_file(self, path: Path) -> dict[str, dict]:
        """
        Parse a Spectre netlist file.

        Returns:
            Dict mapping subckt name to {'terminals': [...], 'parameters': {...}}
        """
        content = path.read_text()

        # Handle line continuations (backslash at end of line)
        content = re.sub(r'\\\s*\n\s*', ' ', content)

        subckts = {}
        current_subckt = None
        current_terminals = []
        current_params = {}

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('//') or line.startswith('*'):
                continue

            # Check for subckt start
            match = self._SUBCKT_START.match(line)
            if match:
                current_subckt = match.group(1)
                # Parse terminals - they follow the subckt name
                terminals_str = match.group(2).strip()
                # Terminals can be space or parenthesis separated
                terminals_str = terminals_str.replace('(', ' ').replace(')', ' ')
                current_terminals = terminals_str.split()
                current_params = {}
                continue

            # Check for parameters line
            if current_subckt:
                match = self._PARAMETERS.match(line)
                if match:
                    params_str = match.group(1)
                    for param_match in self._PARAM_VALUE.finditer(params_str):
                        name = param_match.group(1)
                        value = param_match.group(2)
                        current_params[name] = Parameter(name, value, default=value)
                    continue

            # Check for ends
            match = self._ENDS.match(line)
            if match and current_subckt:
                subckts[current_subckt] = {
                    'terminals': current_terminals,
                    'parameters': current_params
                }
                current_subckt = None
                current_terminals = []
                current_params = {}

        return subckts
