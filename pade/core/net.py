"""
Net - Electrical connection between terminals.
"""

from typing import TYPE_CHECKING
from pade.logging import logger

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.core.terminal import Terminal


class Net:
    """
    A net represents an electrical connection between terminals.

    Attributes:
        name: Net name
        cell: Cell that owns this net
        connections: List of terminals connected to this net
    """

    def __init__(self, name: str, cell: 'Cell') -> None:
        """
        Create a net.

        Args:
            name: Net name
            cell: Parent cell that owns this net
        """
        self.name = name
        self.cell = cell
        cell.add_net(self)
        self.connections: list['Terminal'] = []

    def __str__(self) -> str:
        s = f"Net {self.name} in Cell {self.cell.get_name_from_top()}\nConnected to:\n"
        for c in self.connections:
            s += f"- terminal {c.name} of cell {c.cell.get_name_from_top()}\n"
        return s

    def __repr__(self) -> str:
        return self.__str__()

    def get_name_from_top(self) -> str:
        """Return hierarchical name like 'parent.cell:net'."""
        return f"{self.cell.get_name_from_top()}:{self.name}"

    def connect(self, terminals: list['Terminal']) -> None:
        """
        Connect a list of terminals to this net.

        Args:
            terminals: List of Terminal objects to connect
        """
        from pade.core.terminal import Terminal

        for t in terminals:
            if isinstance(t, Terminal):
                if t not in self.connections:
                    self.connections.append(t)
            else:
                raise ValueError(f'{t} is not a Terminal')

    def disconnect(self, terminal: 'Terminal') -> None:
        """
        Remove a terminal from this net's connections.

        Args:
            terminal: Terminal to disconnect
        """
        if terminal in self.connections:
            self.connections.remove(terminal)
        else:
            logger.warning(f'Terminal {terminal.get_name_from_top()} was not connected to {self}')
