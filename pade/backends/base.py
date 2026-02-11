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
        """Collect LVS labels from the cell's pins.

        Each Pin maps to a schematic terminal and carries a layer and
        location.  One label is generated per pin.

        Returns:
            List of (terminal_name, layer, x0, y0, x1, y1) tuples
        """
        labels = []
        for pin in cell.pins.values():
            b = pin.bounds
            labels.append((pin.terminal, pin.layer, b[0], b[1], b[2], b[3]))
        return labels


class Simulator(ABC):
    """
    Abstract base class for circuit simulation.

    Each backend implements this to run simulations.
    """

    @abstractmethod
    def prepare(self, cell: 'Cell', statements: list['Statement'],
                identifier: str) -> tuple[Path, Path, Path]:
        """Write netlist and prepare output paths.

        Args:
            cell: Top-level cell (testbench)
            statements: Simulation statements
            identifier: Simulation identifier (creates subdirectory)

        Returns:
            (netlist_path, output_path, stdout_file)
        """
        pass

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
            Path to results
        """
        pass

    @abstractmethod
    def run(self, netlist_path: str | Path, output_path: str | Path, **kwargs) -> bool:
        """
        Run simulation on existing netlist.

        Args:
            netlist_path: Path to netlist file
            output_path: Path to output file/directory

        Returns:
            True if successful
        """
        pass
