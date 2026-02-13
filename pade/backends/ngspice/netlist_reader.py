"""
SPICE netlist reader for NGspice.

Parses .subckt definitions from SPICE netlist files.
"""

import re
from pathlib import Path
from typing import Optional

from pade.backends.base import NetlistReader
from pade.core.cell import Cell
from pade.core.parameter import Parameter


class NetlistCell(Cell):
    """
    A Cell created from an external SPICE netlist file.

    This represents a "black box" subcircuit whose implementation
    is defined in an external file. The file content can be inlined
    into the generated netlist.

    Attributes:
        source_path: Path to the source netlist file
    """

    def __init__(self, instance_name: Optional[str] = None, parent: Optional[Cell] = None,
                 cell_name: Optional[str] = None, source_path: Optional[str] = None,
                 terminals: list[str] = None):
        if terminals is None:
            raise ValueError("NetlistCell requires terminals")
        super().__init__(instance_name=instance_name, parent=parent, cell_name=cell_name)
        self.source_path = source_path

        for term_name in terminals:
            self.add_terminal(term_name)


def _make_subckt_class(subckt_name: str, source_path: str,
                       terminal_names: list[str],
                       param_defaults: dict[str, Parameter]) -> type[NetlistCell]:
    """
    Factory function to create a NetlistCell subclass for a specific subcircuit.

    Returns a class (not instance) that can be instantiated multiple times.
    """

    class _NetlistCell(NetlistCell):
        def __init__(self, instance_name=None, parent=None, **kwargs):
            super().__init__(
                instance_name=instance_name,
                parent=parent,
                cell_name=subckt_name,
                source_path=source_path,
                terminals=terminal_names,
            )
            mult = kwargs.pop('mult', None)
            for name, param in param_defaults.items():
                if name in kwargs:
                    self.set_parameter(name, str(kwargs[name]), default=param.default)
                else:
                    self.set_parameter(name, param.value, default=param.default)
            for name, value in kwargs.items():
                if name not in param_defaults:
                    self.set_parameter(name, str(value))
            if mult is not None:
                self.set_multiplier(mult)

        @classmethod
        def info(cls) -> str:
            terms_str = ', '.join(terminal_names)
            params_str = ', '.join(f'{k}={v.default}' for k, v in param_defaults.items())
            return f'{subckt_name}({terms_str}) parameters: {params_str}'

    _NetlistCell.__name__ = subckt_name
    _NetlistCell.__qualname__ = subckt_name
    return _NetlistCell


class SpiceNetlistReader(NetlistReader):
    """
    Reads SPICE format netlists and extracts subcircuit definitions.

    Supports standard SPICE .subckt syntax:
        .subckt name node1 node2 ... [param1=val1 param2=val2 ...]
        ...
        .ends [name]

    Example:
        reader = SpiceNetlistReader()
        MyCell = reader.read_subckt('/path/to/file.spice', 'MYCELL')
        inst = MyCell('X1', parent, param1='value')
    """

    # Regex patterns for parsing
    _SUBCKT_START = re.compile(
        r'^\s*\.subckt\s+(\w+)\s+(.*)', re.IGNORECASE
    )
    _ENDS = re.compile(r'^\s*\.ends\s*(\w+)?', re.IGNORECASE)
    _PARAM_VALUE = re.compile(r'(\w+)\s*=\s*([^\s]+)')

    def read_subckt(self, path: str, subckt_name: Optional[str] = None) -> type[Cell]:
        """
        Read a subcircuit from a SPICE netlist file.

        Args:
            path: Path to the netlist file
            subckt_name: Name of subcircuit to read (optional if file has only one)

        Returns:
            A Cell class (not instance) that can be instantiated
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Netlist file not found: {path}")

        subckts = self._parse_file(path)

        if not subckts:
            raise ValueError(f"No subcircuits found in {path}")

        if subckt_name is None:
            if len(subckts) > 1:
                names = list(subckts.keys())
                raise ValueError(
                    f"Multiple subcircuits found: {names}. Specify subckt_name."
                )
            subckt_name = list(subckts.keys())[0]

        if subckt_name not in subckts:
            available = list(subckts.keys())
            raise ValueError(
                f"Subcircuit '{subckt_name}' not found. Available: {available}"
            )

        data = subckts[subckt_name]
        return _make_subckt_class(
            subckt_name,
            str(path),
            data['terminals'],
            data['parameters']
        )

    def list_subckts(self, path: str) -> list[str]:
        """List all subcircuit names in a file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Netlist file not found: {path}")

        subckts = self._parse_file(path)
        return list(subckts.keys())

    def _parse_file(self, path: Path) -> dict:
        """
        Parse a SPICE file and extract all subcircuit definitions.

        Returns:
            Dict mapping subckt name to {'terminals': [...], 'parameters': {...}}
        """
        content = path.read_text()

        # Handle line continuations (+ at start of line)
        content = re.sub(r'\n\s*\+\s*', ' ', content)

        subckts = {}
        current_subckt = None
        current_data = None

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('*'):
                continue

            # Check for .subckt start
            match = self._SUBCKT_START.match(line)
            if match:
                subckt_name = match.group(1)
                rest = match.group(2)

                # Parse terminals and parameters from the rest of the line
                terminals, parameters = self._parse_subckt_line(rest)

                current_subckt = subckt_name
                current_data = {
                    'terminals': terminals,
                    'parameters': parameters
                }
                continue

            # Check for .ends
            match = self._ENDS.match(line)
            if match and current_subckt:
                subckts[current_subckt] = current_data
                current_subckt = None
                current_data = None
                continue

            # Check for .param inside subckt (additional parameters)
            if current_subckt and line.lower().startswith('.param'):
                param_part = line[6:].strip()
                for m in self._PARAM_VALUE.finditer(param_part):
                    name, value = m.group(1), m.group(2)
                    if name not in current_data['parameters']:
                        current_data['parameters'][name] = Parameter(name, value, default=value)

        return subckts

    def _parse_subckt_line(self, rest: str) -> tuple[list[str], dict[str, Parameter]]:
        """
        Parse the portion of .subckt line after the name.

        Handles: node1 node2 node3 [param1=val1 param2=val2]
        """
        terminals = []
        parameters = {}

        # Split by whitespace, but handle param=value pairs
        tokens = rest.split()
        for token in tokens:
            if '=' in token:
                # This is a parameter
                match = self._PARAM_VALUE.match(token)
                if match:
                    name, value = match.group(1), match.group(2)
                    parameters[name] = Parameter(name, value, default=value)
            else:
                # This is a terminal name
                terminals.append(token)

        return terminals, parameters


def load_subckt(path: str, subckt_name: Optional[str] = None) -> type[Cell]:
    """
    Convenience function to load a subcircuit from a SPICE file.

    Args:
        path: Path to the SPICE netlist file
        subckt_name: Name of subcircuit (optional if file has only one)

    Returns:
        A Cell class that can be instantiated

    Example:
        MyCell = load_subckt('/path/to/cell.spice')
        inst = MyCell('X1', parent, param='value')
    """
    reader = SpiceNetlistReader()
    return reader.read_subckt(path, subckt_name)
