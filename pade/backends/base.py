"""
Abstract base classes for PADE backends.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.statement import Statement
    from pade.layout.cell import LayoutCell


class NetlistReader(ABC):
    """
    Abstract base class for netlist reading/parsing.

    Each backend implements this to parse subcircuit definitions
    from external netlist files (Spectre .scs, SPICE .spice, etc.).
    """

    @abstractmethod
    def read_subckt(self, path: str | Path, subckt_name: str | None = None) -> 'Cell':
        """
        Read a subcircuit from a netlist file.

        Args:
            path: Path to netlist file
            subckt_name: Name of subcircuit to read (if None, reads first/only subckt)

        Returns:
            Cell representing the subcircuit (can be instantiated in other cells)
        """
        pass

    @abstractmethod
    def list_subckts(self, path: str | Path) -> list[str]:
        """
        List all subcircuit names in a netlist file.

        Args:
            path: Path to netlist file

        Returns:
            List of subcircuit names
        """
        pass


class NetlistWriter(ABC):
    """
    Abstract base class for netlist generation.

    Each backend implements this to convert Cell hierarchy
    to its specific netlist format (Spectre, SPICE, etc.).
    """

    @abstractmethod
    def write_netlist(self, cell: 'Cell', path: str | Path,
                      statements: list['Statement'] | None = None) -> None:
        """Write netlist to file."""
        pass

    @abstractmethod
    def generate_netlist(self, cell: 'Cell',
                         statements: list['Statement'] | None = None) -> str:
        """Generate netlist string."""
        pass


class LayoutWriter(ABC):
    """
    Abstract base class for layout generation.

    Each backend implements this to write layout to its specific
    format (Magic .mag, GDSII, etc.).
    """

    @abstractmethod
    def write(self, cell: 'LayoutCell', path: str | Path) -> None:
        """
        Write layout cell to file.

        Args:
            cell: Top-level LayoutCell
            path: Output file path
        """
        pass

    @abstractmethod
    def write_hierarchy(self, cell: 'LayoutCell', output_dir: str | Path) -> None:
        """
        Write cell and all subcells to separate files.

        Args:
            cell: Top-level LayoutCell
            output_dir: Directory for output files
        """
        pass

    def _collect_labels(self, cell: 'LayoutCell') -> list:
        """Collect LVS labels for a cell.

        If the cell has a linked schematic, generates labels on ALL shapes
        whose net matches a terminal name. Falls back to ports if no
        schematic is linked.

        Returns:
            List of (net_name, layer, x0, y0, x1, y1) tuples
        """
        if cell.schematic is not None:
            return self._labels_from_schematic(cell)
        return self._labels_from_ports(cell)

    def _labels_from_schematic(self, cell: 'LayoutCell') -> list:
        """Generate labels from schematic terminals on all matching shapes.

        Places a label on every shape whose net matches a terminal name.
        Multiple labels on the same net are fine for all LVS tools.
        """
        terminal_names = {t.lower(): t for t in cell.schematic.terminals}
        labels = []
        for shape in cell.shapes:
            if shape.net is not None and shape.net.lower() in terminal_names:
                term_name = terminal_names[shape.net.lower()]
                b = shape.bounds
                labels.append((term_name, shape.layer, b[0], b[1], b[2], b[3]))
        return labels

    def _labels_from_ports(self, cell: 'LayoutCell') -> list:
        """Fallback: generate labels from ports (for cells without schematic)."""
        labels = []
        for port in cell.ports.values():
            labels.append((port.net, port.layer,
                           port.x0, port.y0, port.x1, port.y1))
        return labels


class Simulator(ABC):
    """
    Abstract base class for circuit simulation.

    Each backend implements this to run simulations.
    """

    @abstractmethod
    def simulate(self, cell: 'Cell', statements: list['Statement'],
                 identifier: str, **kwargs) -> Path:
        """
        Run simulation.

        Args:
            cell: Top-level cell (testbench)
            statements: Simulation statements
            identifier: Simulation identifier (creates subdirectory)

        Returns:
            Path to results directory
        """
        pass

    @abstractmethod
    def run(self, netlist_path: str | Path, output_dir: str | Path, **kwargs) -> bool:
        """
        Run simulation on existing netlist.

        Args:
            netlist_path: Path to netlist file
            output_dir: Directory for outputs

        Returns:
            True if successful
        """
        pass
