"""
Abstract base classes for PADE backends.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pade.core import Cell
    from pade.statement import Statement


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
