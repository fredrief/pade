"""
Cell - Core circuit component representing hierarchy and connectivity.
"""

from typing import Any, Optional, Union
from pade.core.terminal import Terminal
from pade.core.net import Net
from pade.core.parameter import Parameter
from pade.logging import logger


class Cell:
    """
    A cell represents a circuit component with hierarchy and connectivity.

    This is a pure data structure with no backend-specific logic.
    Netlist generation is handled by backend NetlistWriter classes.

    Attributes:
        cell_name: Type/definition name (e.g., 'nmos', 'amplifier')
        instance_name: Instance name (e.g., 'M1', 'dut')
        parent_cell: Parent cell in hierarchy (None for top-level)
        library: Library name (e.g., 'gpdk045', 'analogLib')
        terminals: Dictionary of terminals {name: Terminal}
        nets: Dictionary of nets {name: Net}
        subcells: Dictionary of subcells {instance_name: Cell}
        parameters: Dictionary of parameters {name: Parameter}
    """

    def __init__(self,
                 instance_name: str,
                 parent: Optional['Cell'] = None,
                 cell_name: Optional[str] = None,
                 library: Optional[str] = None,
                 **kwargs) -> None:
        """
        Create a cell.

        Args:
            instance_name: Instance name (unique within parent)
            parent: Parent cell in hierarchy
            cell_name: Type/definition name (defaults to class name)
            library: Library name
            **kwargs: Additional config options (stored in self.config)
        """
        self.cell_name = cell_name or type(self).__name__
        self.instance_name = instance_name
        self.parent_cell = parent
        self.library = library
        self.config = kwargs

        # Data structures
        self.terminals: dict[str, Terminal] = {}
        self.nets: dict[str, Net] = {}
        self.subcells: dict[str, Cell] = {}
        self.parameters: dict[str, Parameter] = {}

        # Add self to parent's subcells
        if self.parent_cell:
            self.parent_cell._add_subcell(self)

    def __str__(self) -> str:
        return f"Cell {self.instance_name} (type: {self.cell_name})"

    def __repr__(self) -> str:
        return self.__str__()

    def __getattr__(self, name: str):
        """
        Allow attribute access to subcells and terminals.

        Enables: self.m2 (subcell), self.m2.s (terminal of subcell)
        """
        subcells = self.__dict__.get('subcells', {})
        if name in subcells:
            return subcells[name]
        terminals = self.__dict__.get('terminals', {})
        if name in terminals:
            return terminals[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def add_terminal(self, names: Union[str, list[str]]) -> Union[Terminal, list[Terminal]]:
        """
        Add terminal(s) to this cell.

        Args:
            names: Terminal name or list of names

        Returns:
            Created Terminal(s)
        """
        if not isinstance(names, list):
            return self._add_single_terminal(names)

        return [self._add_single_terminal(name) for name in names]

    def _add_single_terminal(self, name: str) -> Terminal:
        """Add a single terminal."""
        if name in self.terminals:
            logger.warning(f'Terminal {name} already exists in {self.get_name_from_top()}')
            return self.terminals[name]

        terminal = Terminal(name, self)
        self.terminals[name] = terminal
        return terminal

    def get_terminal(self, name: str) -> Terminal:
        """
        Get terminal by name.

        Args:
            name: Terminal name

        Returns:
            Terminal object

        Raises:
            ValueError: If terminal doesn't exist
        """
        if name not in self.terminals:
            raise ValueError(f'No terminal named {name} in cell {self.get_name_from_top()}')
        return self.terminals[name]

    def get_all_terminals(self) -> list[Terminal]:
        """Return list of all terminals in definition order."""
        return list(self.terminals.values())

    def add_net(self, names: Union[Net, str, list[str]]) -> Union[Net, list[Net]]:
        """
        Add net(s) to this cell.

        Args:
            names: Net object, net name, or list of net names

        Returns:
            Net object(s)
        """
        if isinstance(names, Net):
            self.nets[names.name] = names
            return names
        elif isinstance(names, list):
            return [self._add_single_net(name) for name in names]
        else:
            return self._add_single_net(names)

    def _add_single_net(self, name: str) -> Net:
        """Add a single net by name."""
        if name in self.nets:
            return self.nets[name]
        net_obj = Net(name, self)
        self.nets[name] = net_obj
        return net_obj

    def get_net(self, name: str) -> Optional[Net]:
        """
        Get net by name.

        Args:
            name: Net name

        Returns:
            Net object or None if not found
        """
        return self.nets.get(name)

    def has_net(self, name: str) -> bool:
        """Check if net exists."""
        return name in self.nets

    def get_all_nets(self) -> list[Net]:
        """Return list of all nets."""
        return list(self.nets.values())

    def connect(self,
                terminals: Union[str, Terminal, list[Union[str, Terminal]]],
                nets: Union[str, Net, Terminal, list[Union[str, Net, Terminal]]]) -> None:
        """
        Connect terminal(s) to net(s).

        Flexible method supporting:
        - Single connection: connect('in', 'input_net')
        - Multiple connections: connect(['in', 'out'], ['inp', 'outp'])
        - Terminal-to-terminal: connect('vdd', other_cell.vdd)

        Args:
            terminals: Terminal name(s) or Terminal object(s)
            nets: Net name(s), Net object(s), or Terminal object(s)
        """
        # Convert to lists
        if not isinstance(terminals, list):
            terminals = [terminals]
            nets = [nets]

        if len(terminals) != len(nets):
            raise ValueError(
                f'Number of terminals ({len(terminals)}) != number of nets ({len(nets)})'
            )

        # Connect each pair
        for term, net in zip(terminals, nets):
            self._connect_single(term, net)

    def _connect_single(self,
                       terminal: Union[str, Terminal],
                       net: Union[str, Net] | Terminal) -> None:
        """
        Connect a single terminal to a net.

        Args:
            terminal: Terminal name or Terminal object
            net: Net name, Net object, or Terminal object
        """
        # Get Terminal object
        if isinstance(terminal, str):
            terminal_obj = self.get_terminal(terminal)
        elif isinstance(terminal, Terminal):
            if terminal.name not in self.terminals:
                raise ValueError(f'Terminal {terminal.name} does not exist in {self}')
            terminal_obj = terminal
        else:
            raise ValueError('Terminal must be a string or Terminal object')

        # Handle different net types
        if isinstance(net, (Net, str)):
            terminal_obj.connect(net)
        elif isinstance(net, Terminal):
            # Terminal-to-terminal connection
            self._connect_terminal_to_terminal(terminal_obj, net)
        else:
            raise ValueError(f'Cannot connect. {net} is not a Net, string, or Terminal')

    def _connect_terminal_to_terminal(self, term1: Terminal, term2: Terminal) -> None:
        """
        Connect two terminals together.

        Creates a net with appropriate name and connects both terminals.

        Args:
            term1: First terminal (belongs to self)
            term2: Second terminal
        """
        # term1 belongs to self, find where to create the net

        # Case 1: Connecting self's terminal to its subcell's terminal
        # e.g., DUT.vdd -> DUT.M1.s
        if term2.cell.parent_cell == self:
            # Create net inside self
            netname = term1.name
            if self.has_net(netname):
                net_obj = self.get_net(netname)
            else:
                net_obj = Net(netname, self)
            term1.connect(net_obj)
            term2.connect(net_obj)
            return

        # Case 2: Connecting two sibling cells or cell to parent
        # Both cells have same parent
        parent = self.parent_cell
        if parent is None:
            raise ValueError(f'Cannot connect terminals - {self} has no parent cell')

        if parent == term2.cell:
            # term2 belongs to parent cell
            netname = term2.name
        elif parent == term2.cell.parent_cell:
            # term2 belongs to sibling cell
            netname = term2.get_name_from_top().replace('.', '_')
        else:
            raise ValueError(f'Cannot connect {term1} to {term2} - incompatible hierarchy')

        # Get or create net in parent
        if parent.has_net(netname):
            net_obj = parent.get_net(netname)
        else:
            net_obj = Net(netname, parent)

        # Connect both terminals
        term1.connect(net_obj)
        if term2.net != net_obj:
            term2.connect(net_obj)

    def add_cell(self,
                 cell_class: type['Cell'],
                 instance_name: str,
                 **kwargs) -> 'Cell':
        """
        Create and add a subcell.

        Args:
            cell_class: Cell class to instantiate
            instance_name: Instance name
            **kwargs: Arguments passed to cell_class constructor

        Returns:
            The created Cell

        Example:
            self.add_cell(Resistor, 'R1', r=1e3)
            self.add_cell(VoltageSource, 'V1', dc=1.8)
        """
        return cell_class(instance_name, parent=self, **kwargs)

    def _add_subcell(self, cell: 'Cell') -> None:
        """Internal: Add a subcell to this cell."""
        if cell.instance_name in self.subcells:
            logger.warning(f'Cell {cell.get_name_from_top()} already exists in {self.get_name_from_top()}')
        self.subcells[cell.instance_name] = cell

    def _remove_subcell(self, cell: 'Cell') -> None:
        """Internal: Remove a subcell from this cell."""
        if cell.instance_name not in self.subcells:
            logger.warning(f'Cell {cell.get_name_from_top()} does not exist in {self.get_name_from_top()}')
            return
        del self.subcells[cell.instance_name]

    def get_subcells(self) -> list['Cell']:
        """Return list of all subcells."""
        return list(self.subcells.values())

    def disconnect(self) -> None:
        """Remove this cell from its parent."""
        if self.parent_cell:
            self.parent_cell._remove_subcell(self)

    def set_parameter(self,
                      names: Union[str, list[str]],
                      values: Union[Any, list[Any]],
                      **kwargs) -> None:
        """
        Set parameter(s).

        Args:
            names: Parameter name or list of names
            values: Parameter value or list of values
            **kwargs: Additional parameter options (default, unit) - applied to all
        """
        if not isinstance(names, list):
            names = [names]
            values = [values]

        if len(names) != len(values):
            raise ValueError(f'Number of names ({len(names)}) != values ({len(values)})')

        for name, value in zip(names, values):
            if isinstance(value, Parameter):
                self.parameters[name] = value
            else:
                self.parameters[name] = Parameter(name, value, **kwargs)

    def get_parameter(self, name: str) -> Any:
        """
        Get parameter value.

        Args:
            name: Parameter name

        Returns:
            Parameter value
        """
        if name not in self.parameters:
            raise ValueError(f'No parameter named {name} in cell {self.get_name_from_top()}')
        return self.parameters[name].value

    def get_name_from_top(self) -> str:
        """
        Get hierarchical name from top level.

        Returns:
            Hierarchical name like 'parent.subcell.instance_name'
        """
        name_string = self.instance_name
        pc = self.parent_cell

        # Walk up hierarchy until we reach top (where instance_name == cell_name)
        while pc and pc.instance_name != pc.cell_name:
            name_string = f'{pc.instance_name}.{name_string}'
            pc = pc.parent_cell

        return name_string
