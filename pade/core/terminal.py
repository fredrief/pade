"""
Terminal - Connection point on a cell.
"""

from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.core.net import Net


class Terminal:
    """
    A terminal is a connection point on a cell.

    Attributes:
        name: Terminal name (e.g., 'drain', 'gate', 'vdd')
        cell: Cell that owns this terminal
        net: Net that this terminal is connected to (None if unconnected)
    """

    def __init__(self, name: str, cell: 'Cell') -> None:
        """
        Create a terminal.

        Args:
            name: Terminal name
            cell: Parent cell that owns this terminal
        """
        self.name = name
        self.cell = cell
        self.net: Optional['Net'] = None

    def __str__(self) -> str:
        net_name = self.net.name if self.net else "None"
        return f"Terminal {self.name} of cell {self.cell.get_name_from_top()}, connected to net: {net_name}"

    def __repr__(self) -> str:
        return self.__str__()

    def get_net(self) -> Optional['Net']:
        """Return the net this terminal is connected to."""
        return self.net

    def get_name_from_top(self) -> str:
        """Return hierarchical name like 'parent.cell.terminal'."""
        return f"{self.cell.get_name_from_top()}.{self.name}"

    def connect(self, net: 'Union[Net, str]') -> None:
        """
        Connect this terminal to a net.

        Args:
            net: Net object or net name (string)
        """
        from pade.core.net import Net

        if isinstance(net, Net):
            self.net = net
            net.connect([self])
        elif isinstance(net, str):
            # Get or create net in parent cell
            parent = self.cell.parent_cell
            if parent is None:
                raise ValueError(f"Cannot connect terminal {self.name} - cell has no parent")

            if parent.has_net(net):
                net_obj = parent.get_net(net)
            else:
                net_obj = Net(net, parent)

            self.net = net_obj
            net_obj.connect([self])
        else:
            raise ValueError(f'Cannot connect. {net} is not a Net or string')

    def disconnect(self) -> None:
        """Disconnect this terminal from its net."""
        if self.net is not None:
            self.net.disconnect(self)
            self.net = None
