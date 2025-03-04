from pade.utils import num2string, append_dict
import re
from inform import warn, debug

class Terminal:
    """
    Terminal
    A Terminal is owned by a Cell and connected to a net
    It contains a reference to its cell.
    It knows in which order it appears in the netlist definition.

    """
    def __init__(self, name: str, cell):
        self.name = name
        self.net = None
        self.cell = cell
        # Index of self in definition of cell
        self.index = len(cell.terminals) + 1

    def __str__(self):
        s  = f"Terminal {self.name} of cell {self.cell.instance_name}\n"
        s += "Connected to net: {}\n".format(self.net.name if self.net else "None")
        return s

    def __repr__(self):
        s  = "Terminal {} of cell {}\n".format(self.name, self.cell.instance_name)
        s += "Connected to net: {}\n".format(self.net.name if self.net else "None")
        return s

    def get_net(self):
        return self.net

    def get_name_from_top(self):
        return f"{self.cell.get_name_from_top()}.{self.name}"

    def connect(self, net):
        """
        Connect terminal to a net

        Arguments
            net: Net or str
        """
        # If net is Net, connect directly
        if isinstance(net, Net):
            self.net=net
            net.connect([self])
        # If net is str, check if net exist, else create a Net with this name and connect
        elif isinstance(net, str):
            parent = self.cell.parent_cell
            if parent.has_net(net):
                net = parent.get_net(net)
            else:
                net = Net(net, self.design)
            self.net=net
            net.connect([self])
        else:
            raise ValueError('Could not connect. {} is not a Net or a string'.format(net))

    def disconnect(self):
        """
        Disconnect self from net
        """
        if self.net is not None:
            self.net.disconnect(self)
            self.net = None


class Net:
    """
    Net
    A net is owned by a design/cell and connected to one or more terminals
    Contains reference to its design and connected terminals
    """
    def __init__(self, name, cell):
        """
        Arguments:
            name: String
            cell: Cell
        """
        self.name = name
        self.cell = cell
        cell.add_net(self)
        self.connections = []

    def __str__(self):
        s  = f"Net {self.name} in Cell {self.cell.instance_name}\nConnected to:\n"
        for c in self.connections:
            s += "- terminal {} of cell {}\n".format(c.name, c.cell.instance_name)
        return s

    def __repr__(self):
        s  = f"Net {self.name} in Cell {self.cell.instance_name}\nConnected to:\n"
        for c in self.connections:
            s += "- terminal {} of cell {}\n".format(c.name, c.cell.instance_name)
        return s

    def get_name_from_top(self):
        return f"{self.cell.get_name_from_top()}:{self.name}"


    def connect(self, terminals):
        """
        Connect net to a list of terminals
        """
        for t in terminals:
            if isinstance(t, Terminal):
                self.connections.append(t)
            else:
                raise ValueError('{} is not a Terminal'.format(t))

    def disconnect(self, terminal: Terminal):
        """
        Remove terminal from list of connections
        """
        if terminal in self.connections:
            self.connections.remove(terminal)
        else:
            warn(f'Terminal {terminal.get_name_from_top()} was never connected to {self}')


class Parameter:
    """
    Parameter class
    """
    def __init__(self, name, value, default=None, CDF=False) -> None:
        self.name = name
        self.value = value
        self.default = default
        self.is_CDF = CDF # Indicate whether or not the parameter is a CDF parameter

    def get_value_str(self):
        return f'{self.name}={num2string(self.value)}'

    def get_default_str(self):
        return f'{self.name}={num2string(self.default)}' if self.default is not None else self.name

class Cell:
    """
    Cell view
    """
    def __init__(self, cell_name, instance_name, parent_cell=None, **kwargs):
        """
        Initialize cell_view

        Arguments
            cell_name: str
            instance_name: str
        Keyword arguments:
            exclude_list:
                List of strings that are matched to exclude subcells in subckt definition. Only applicable if netlist_filename is provided. (default [])
            declare: bool
                Whether the cell should be declared in beginning of netlist or not. This should be set to false if the cell is a standard spectre component like cap or res
            parent_cell: Cell
                Specify if the cell is a subcell of another cell

        """
        self.terminals = {}
        self.nets = {}
        self.subcells = {}
        # Parameters dict (Only parameters that is passed to spectre)
        self.parameters = {}
        self.cell_name = cell_name
        self.model_name = kwargs.get('model_name', self.cell_name)
        self.instance_name = instance_name
        self.lib_name = kwargs.get('lib_name')
        self.cdl_subtype = kwargs.get('cdl_subtype')

        # Connect cell and design/parent cell
        self.parent_cell = parent_cell
        if self.parent_cell:
            self.parent_cell.add_subcell(self)

        # Generate parameters and terminals if netlist is available
        netlist_filename = kwargs.get('netlist_filename')
        if netlist_filename:
            try:
                self.extract_data_from_file(netlist_filename, **kwargs)
                # debug(f'Extracted cell {self.cell_name} from file {netlist_filename}')
            except Exception as e:
                warn(f'Could not extract Cell {self.cell_name} from netlist.')
        spice_filename = kwargs.get('spice_filename')
        if spice_filename:
            try:
                self.parse_spice(spice_filename, **kwargs)
                # debug(f'Extracted cell {self.cell_name} from file {netlist_filename}')
            except Exception as e:
                warn(f'Could not extract Cell {self.cell_name} from netlist.')


        # For LPE netlist, do not parse given netlist, just return directly
        # This will be used in the get subckt function
        self.lpe_netlist = None

        # Initialize subckt string
        self.declare_subckt = kwargs.get('declare', True)
        # AHDL Filepath
        self.ahdl_filepath = ""
        # Include filepath (additional filepath to include)
        self.include_filepath = ""

    def __repr__(self) -> str:
        return f"Cell {self.instance_name}, type {self.cell_name}\n"


    def parse_spice(self, file, **kwargs):
        # Dictionary of known spice components
        prefix_map = {
            'C': {
                'name': 'capacitor',
                'parameter': 'c'
            },
            'R': {
                'name': 'resistor',
                'parameter': 'r'
            },
            'L': {
                'name': 'inductor',
                'parameter': 'l'
            },
        }

        # Clean file by removing new line characters
        with open(file, "r") as raw_f:
            string_clean_lines = ""
            for line in raw_f.readlines():
                clean_line = line.rstrip().lstrip()
                if(clean_line.endswith('\\')):
                    clean_line = clean_line.rstrip('\\')
                else:
                    clean_line += '\n'
                string_clean_lines += clean_line

        for line in string_clean_lines.splitlines():
            if line.startswith('*'): # Ignore comments
                continue

            # everything is separated by space. Find elements on line
            content = line.split(' ')
            if content[0].lower() == '.subckt':
                # self.cell_name = content[1]
                # The rest is terminals
                for terminal in content[2:]:
                    t = self.add_terminal(terminal)
                    # Add terminal ass attribute
                    setattr(self, t.name, t)

            # Check if this is a known component
            instance_name = content[0]
            prefix = instance_name[0]
            known_prefix_list = list(prefix_map.keys())
            if prefix in known_prefix_list:
                cell_name = prefix_map[prefix]['name']
                p_name = prefix_map[prefix]['parameter']
                t1 = content[1]
                t2 = content[2]
                val = content[3]
                # Instantiate
                cell = Cell(cell_name, instance_name, self, declare=False)
                cell.add_terminal(t1)
                cell.add_terminal(t2)
                cell.add_parameters({p_name: val})
                cell.quick_connect([t1, t2], [t1, t2])


    def extract_data_from_file(self, file, **kwargs):
        """
        Read a spectre netlist and define parameters and terminals accordingly
            Supports line continuity for both parameters and terminals.

        """
        # Clean file by removing new line characters
        with open(file, "r") as raw_f:
            string_clean_lines = ""
            for line in raw_f.readlines():
                clean_line = line.rstrip().lstrip()
                if(clean_line.endswith('\\')):
                    clean_line = clean_line.rstrip('\\')
                else:
                    clean_line += '\n'
                string_clean_lines += clean_line

        for line in string_clean_lines.splitlines():
            if line.startswith('//'):
                continue
            #Add parameters
            if (line.startswith('ends') or line == '\n' or line == ''):
                pass
            elif line.startswith('parameters'):
                parameters_dict = {}
                # Add parameters in form a=b (no whitespace)
                for param in line.split()[1:]:
                    search_param = re.search(".=.", param)
                    if search_param != None:
                        parameter = search_param.string.split("=")
                        parameters_dict[parameter[0]] = parameter[1]
                # Find all parameters in format a = b (with whitespaces)
                for i, param in enumerate(line.split()):
                    if(param == '='):
                        parameters_dict[line.split()[i-1]] = line.split()[i+1]
                self.add_parameters(parameters_dict)

            # Define terminals
            elif line.startswith('subckt'):
                # Accept that the cell_name in the netlist is different from the specified cell name

                # if not self.cell_name == line.split()[1]:
                #     raise ValueError('Cannot instantiate component. Cell name does not equal subckt declaration in file.')
                for terminal in line.split()[2:]:
                    t = self.add_terminal(terminal)
                    # Add terminal ass attribute
                    setattr(self, t.name, t)
            # Define subcells in subckt
            else:
                sc_connected_nets   = []
                sc_terminals        = []
                sc_param_dict = {}
                # Find out where parameters are declared (used for location of instance name, terminals etc.)
                for i, x in enumerate(line.split()):
                    if(re.search('.=.', x) != None):
                        sc_first_param_location = i
                        break
                sc_cell_name        = line.split()[sc_first_param_location-1]
                sc_instance_name    = line.split()[0]
                for i, net in enumerate(line.split()[1:sc_first_param_location-1]):
                    sc_connected_nets.append(net.strip("(").strip(")"))
                    sc_terminals.append(str(i))
                for i, sc_param in enumerate(line.split()[sc_first_param_location:]):
                    sc_param_key, sc_param_value = sc_param.split('=')
                    sc_param_dict[sc_param_key] = sc_param_value
                exclude_list = kwargs.get('exclude_list', [])
                skip_subcell = 0
                for exclusion in exclude_list:
                    if(exclusion in line):
                        skip_subcell = 1
                if(skip_subcell == 0):
                    subcell = Cell(sc_cell_name, sc_instance_name, declare=False, parent_cell=self)
                    subcell.add_multiple_terminals(sc_terminals)
                    subcell.quick_connect(sc_terminals, sc_connected_nets)
                    subcell.add_parameters(sc_param_dict)

    def get_subcell_by_iname(self, target_iname):
        """
        Return subcell with specified iname
        """
        for iname, cell in self.subcells.items():
            if iname == target_iname:
                return cell

    def set_parameter(self, name, value, CDF=False):
        """
        Set value of parameter 'name' to 'value'
        Value can be a numerical value or a Parameter
        """
        if isinstance(value, Parameter):
            self.parameters[name] = value
        else:
            # Create Parameter object if value us numerical
            param = Parameter(name, value, CDF=CDF)
            self.parameters[name] = param


    def get_parameter(self, name):
        """
        Return numerical value of parameter
        """
        return self.parameters[name].value

    def add_parameters(self, parameters):
        """
        Add parameters to design
        Arguments
            parameters: Dictionary
        """
        for name, value in parameters.items():
            self.set_parameter(name, value)

    def append_subckt_list(self, subckt_list, unique=True):
        """
        Append self to subckt list in right order
        """
        if self.lpe_netlist is None:
            # First append all subcells to the list
            for instance_name in self.subcells:
                cell = self.subcells[instance_name]
                subckt_list = cell.append_subckt_list(subckt_list, unique=unique)
        # append self to list if not already present
        if not unique:
            subckt_list.append(self)
        elif not any([self.cell_name == x.cell_name for x in subckt_list]):
            subckt_list.append(self)
        return subckt_list

    def add_subcell(self, cell):
        """
        Add subcell both in dict and as attribute
        """
        if cell.instance_name in self.subcells:
            warn(f'Cell {cell.instance_name} already exist in {self.instance_name}, will be overwritten!')
        self.subcells[cell.instance_name] = cell

    def remove_subcell(self, cell):
        """
        Remove cell from subcells
        """
        if not cell.instance_name in self.subcells:
            warn(f'Cell {cell.instance_name} does not exist in {self.instance_name}, cannot be removed!')
        self.subcells.pop(cell.instance_name, None)

    def disconnect(self):
        self.parent_cell.remove_subcell(self)


    #TODO:  I think this overlaps with get_subckts
    def get_subcells(self):
        """
        Returns a list of all unique subcells of this cell
        """
        subcells = []
        for instance_name in self.subcells:
            cell = self.subcells[instance_name]
            if not any([cell.cell_name == x.cell_name for x in subcells]):
                subcells.append(cell)
        return subcells

    def get_include_statements(self):
        """
        Returns include string if applicable
        """
        s = ""
        if self.include_filepath != "":
            s += f'include "{self.include_filepath}"\n'
        if self.ahdl_filepath != "":
            s += f'ahdl_include "{self.ahdl_filepath}"\n'
        return s

    def get_sorted_terminal_list(self):
        """
        Return a list of terminals, sorted by index
        """
        t_list = self.terminals.values()
        return sorted(t_list, key=lambda t: t.index)

    def add_terminal(self, name):
        """
        Add terminal <name> if it does not already exist
        Added as a member of dict of terminals
        """
        if not name in self.terminals and isinstance(name, str):
            terminal = Terminal(name, self)
            self.terminals[name] = terminal
            return terminal
        else:
            warn(f'Terminal {name} already exist in cell {self.get_name_from_top()}')
            return self.terminals[name]

    def delete_terminal(self, terminal: Terminal):
        """
        Delete terminal
        """
        del self.terminals[terminal.name]
        del terminal

    def add_multiple_terminals(self, terminals):
        """
        Add multiple terminals
        """
        t_list = []
        for t in terminals:
            t_list.append(self.add_terminal(t))
        return t_list

    def get_terminal(self, terminal):
        """
        Returns object Terminal if it exists in cell
        """
        if not isinstance(terminal, str):
            raise ValueError('Terminal name must be a string')
        elif not terminal in self.terminals:
            raise ValueError('No terminal named {} exist in cell {}'.format(terminal, self.instance_name))
        else:
            return self.terminals[terminal]

    def get_all_terminals(self):
        """
        Return a list of all terminal objects
        """
        return list(self.terminals.values())

    def get_unconnected_terminals(self):
        """
        Return a list of all unconnected terminal objects
        """
        return [t for t in self.terminals.values() if t.net is None]

    def get_all_nets(self):
        """
        Return a list of all net objects
        """
        return list(self.nets.values())

    def get_net(self, net_name):
        """
        Return net of name net_name if exist else None
        """
        if net_name in self.nets:
            return self.nets[net_name]
        else:
            return None

    def add_net(self, net):
        """
        Add net to cell
        Arguments:
            net: Net
        """
        # If net is Net, connect directly
        if isinstance(net, Net):
            self.nets[net.name] = net
        # If net is str, assume create a Net with this name and connect
        elif isinstance(net, str):
            net = Net(net, self)
            self.nets[net.name] = net
        else:
            raise ValueError('Could not add ned. Must be a Net or a string')
        return net


    def connect(self, terminal, net):
        """
        Connect terminal to a net

        Arguments
            tname: Terminal or str
            net: Net or str
        """
        # Verify that terminal is member of cell and get Terminal object
        if isinstance(terminal, str):
            terminal = self.get_terminal(terminal)
        elif not isinstance(terminal, Terminal):
            raise ValueError('Terminal must be a Terminal object or a string with terminal name')
        elif not terminal.name in self.terminals:
            raise ValueError(f'Could not connect because {terminal.name} does not exist in {self}')

        # If net is Net, connect directly
        if isinstance(net, Net):
            terminal.connect(net)
        # If net is str, check if net exist, else create a Net with this name and connect
        elif isinstance(net, str):
            parent = self.parent_cell
            if net in parent.nets:
                net = parent.get_net(net)
            else:
                net = Net(net, parent)
            terminal.connect(net)
        # If net is terminal, create a net with the same name as the terminal and connect
        elif isinstance(net, Terminal):
            t2 = net # The other terminal
            parent = self.parent_cell
            if parent == t2.cell:
                # If the parent of the terminal is the same as self.parent, connect to a net with the name of the terminal.
                # This assumes that terminal is the terminal of a subcell and that t2 is a terminal of self
                netname = t2.name
                if netname in parent.nets:
                    net = parent.get_net(netname)
                else:
                    net = Net(netname, parent)
                terminal.connect(net)

            elif parent == t2.cell.parent_cell:
                # In this case t2 is the terminal of a subcell. Create a net with a unique name, and connect both terminals to the same net.
                netname = t2.get_name_from_top().replace('.', '')
                if netname in parent.nets:
                    net = parent.get_net(netname)
                else:
                    net = Net(netname, parent)
                terminal.connect(net)
                t2.connect(net)

            else:
                raise ValueError(f'Could not connect {terminal} to {net}')
        else:
            raise ValueError(f'Could not connect. {net} is not a Net, string or a Terminal')

    def quick_connect(self, terminals, nets):
        """
        Connect list of terminals to a list of nets
        Arguments
            terminals: [str] or [Terminal]
                Array of terminal names
            nets: [str] or [Net] or [Terminal]
                Array of terminals
        """
        # Validate
        if not len(terminals) == len(nets):
            raise ValueError(f'Number of terminals ({len(terminals)}) is not equal to number of nets ({len(nets)})')
        for i in range(0, len(terminals)):
            self.connect(terminals[i], nets[i])

    def insert(self, ta1: Terminal, ta2: Terminal, t1: Terminal, t2: Terminal):
        """
        Connect self.t1 and self.t2 between Terminals ta1 and ta2
        """
        # Verify that ta1 and ta2 are both connected to the same net
        if ta1.net is None or ta2.net is None:
            raise ValueError(f'Cannot insert between terminals {ta1} and {ta2} because one of them are not connected to a net')
        elif ta1.net is not ta2.net:
            raise ValueError(f'Cannot insert between terminals {ta1} and {ta2} because they are not connected to the same net.')

        net2 = ta2.net
        # Disconnect all other terminals connected to net1. Add to pending list. Disconnect later
        pending_terminal_list = []
        for t in net2.connections:
            if not t is ta2:
                pending_terminal_list.append(t)
        # Connect t2 to net2
        t2.connect(net2)
        # Create a new net and connect t2 and all pending terminals
        net1 = Net(ta1.get_name_from_top().replace('.', ''), self.parent_cell)
        t1.connect(net1)
        for t in pending_terminal_list:
            t.disconnect()
            t.connect(net1)

    def get_iname(self, base='X', new_col=False):
        """
        Return a valid instance name with given base.
        If X1 and X2 already exist in cell, then the next valid name is X3

        If new_col=True then a char will be appended before numerical index

        If stack_v: append numeric value to stack vertically. Else, append alphabetic to stack horisontally
        """
        # First determine base depending on col
        current_col = 'A' # Alphabetical index, gives col
        for iname, c in self.subcells.items():
            # Check for alphabetical index
            split_base = iname.split(base)
            if len(split_base) > 1:
                # If the instance name of subcell contains base, assume the next char is the alphabetic col index
                # Ex: If base=MN and iname is MNB3, then the next col char should be C
                col = split_base[1][0]
                if ord(col) > ord(current_col):
                    current_col = col
        if new_col:
            current_col = chr(ord(current_col) + 1)
        colbase = f'{base}{current_col}'
        current_index = -1 # Numerical index, gives horisontal stacking
        for iname, c in self.subcells.items():
            # Get numerical index of subcell
            ibase, index = re.split(r'(^[^\d]+)', iname)[1:]
            if ibase == colbase:
                current_index = int(index)
        current_index = current_index + 1
        return f'{base}{current_col}{current_index}'

    def get_subckts(self, unique=True):
        """
        Returns a ordered list of all unique subckts in Cell
        """
        subckts = []
        for cell_name in self.subcells:
            cell = self.subcells[cell_name]
            subckts = cell.append_subckt_list(subckts, unique=unique)
        return subckts



    def get_spiceIn_subckt_string(self):
        # SUBCKTS
        s = ""
        subckts = self.get_subckts()
        for cell in subckts:
            if cell.declare_subckt:
                s += cell.get_subckt_string(remove_unconnected_terminals=False, spice_in=True) + "\n"
        s += self.get_subckt_string(remove_unconnected_terminals=False, spice_in=True)
        return s

    def get_subckt_string(self, remove_unconnected_terminals=True, use_model_name=True, spice_in=False):
        """
        Return sub circuit declaration string
        """
        # If lpe_netlist is set, return directly
        if self.lpe_netlist is not None and not spice_in:
            s = ""
            with open(self.lpe_netlist, 'r') as f:
                for line in f.readlines():
                    s += line
            return s
        # Check if Cell as unconnected terminals
        ut_list = list(self.terminals.keys())
        for key in self.subcells:
            c = self.subcells[key]
            for t in c.get_sorted_terminal_list():
                if t.net is None:
                    raise RuntimeError(f'Terminal {t.get_name_from_top()} is not connected to a net')
                    # warn(f'Terminal {t.get_name_from_top()} is not connected to a net. Will be removed.')
                    # c.delete_terminal(t)
                    continue

                if t.net.name in ut_list:
                    ut_list.remove(t.net.name)
        if len(ut_list):
            warn(f'Cell {self.get_name_from_top()} has internally unconnected terminals: {ut_list}')


        # META
        s = ""
        s += f"// Cell name: {self.cell_name}\n"
        s += "// View name: schematic\n"
        s += f"subckt {self.cell_name}"
        # TERMINALS
        for t in self.get_sorted_terminal_list():
            if t.net is None and remove_unconnected_terminals:
                warn(f'Terminal {t.get_name_from_top()} is not connected to a net. Will be removed.')
                self.delete_terminal(t)
                continue
            s += f' {t.name}'
        s += "\n"
        # PARAMETERS
        if self.parameters:
            s += "parameters "
            for name, param in self.parameters.items():
                s += f"{param.get_default_str()} "
            s += "\n"

        # SUBCELLS
        for key in self.subcells:
            c = self.subcells[key]
            s += f"{c.get_instance_string(use_model_name=use_model_name)}"

        # END
        s += f"ends {self.cell_name}\n"
        return s

    def get_instance_string(self, use_model_name=True):
        """
        Return instance string for netlist
        """
        # All terminals of cell must be connected to nets before instance string can be generated
        if any([t.net is None for t in self.terminals.values()]):
            unconnected_terminals = []
            for t in self.terminals.values():
                if t.net is None:
                    unconnected_terminals.append(t.name)
            raise RuntimeError(f'Cell {self.instance_name} has unconnected terminals: {unconnected_terminals}')
        s  = f"{self.instance_name}"
        t_list = self.get_sorted_terminal_list()
        for t in t_list:
            s += f" {t.net.name}"
        if use_model_name:
            s += " {} ".format(self.model_name)
        else:
            s += " {} ".format(self.cell_name)
        # Add CDL subtype if set
        if not self.cdl_subtype is None:
            s += f'$[{self.cdl_subtype}] '
        # Add parameters that is not None
        for name, param in self.parameters.items():
            s += f"{param.get_value_str()} "
        s += "\n"
        return s

    def get_name_from_top(self):
        """
        Returns the instance name on the form
        P1.P2.self.instance_name
        """
        name_string = self.instance_name
        pc = self.parent_cell
        # Design has cell_name = instance_name. Stop when we have reached Design
        while pc and pc.instance_name != pc.cell_name:
            name_string = f'{pc.instance_name}.{name_string}'
            pc = pc.parent_cell
        return name_string


    def get_terminal_from_net(self, net):
        """
        Return the terminal of self that is connected to netname
        """
        if isinstance(net, str):
            net = self.parent_cell.get_net(net)
        elif isinstance(net, Net):
            pass
        else:
            raise ValueError(f'{net} is not a Net')
        for t in self.terminals.values():
            if t.net == net:
                return t

    def set_library_on_all_cells(self):
        """
        Set the library of all subcells to self.lib_name
        """
        for iname, cell in self.subcells.items():
            if cell.declare_subckt:
                # Give lib_name to cell
                cell.lib_name = self.lib_name
                # As cell to do the same for all subcells
                cell.set_library_on_all_cells()

class Design(Cell):
    """
    Top-level design class
    """
    def __init__(self, cell_name, **kwargs):
        super().__init__(cell_name, cell_name, **kwargs)
        self.add_net('0')
        # Initial conditions (DEPRICATED)
        self.ic = kwargs.get('ic', {})


    def get_cell_meta(self):
        """
        Return commented cell meta text
        """
        s = "// Design cell name: {}\n".format(self.cell_name)
        return s

    def get_parameter_string(self):
        # s = "parameters"
        # for p, value in self.parameters.items():
        #     s += " {}={}".format(p, num2string(value))
        s = "parameters "
        for name, param in self.parameters.items():
            s += f"{param.get_value_str()} "
        return s

    def rewrite_netlist(self):
        self.netlist_string = ""
        self.write_netlist()


    def write_netlist(self, netlist_filename=None):
        """
        This function writes the netlist for the design, to the local variable self.netlist_string.
        The netlist will be completed by the simulator

        The netlist format is:
            - PARAMETERS
            - SUBCKTS
            - ACTUAL DESIGN (TB)
            - SIMULATOR OPTIONS
            - OTHER OPTIONS - completed by simulator
            - INCLUDE - completed by simulator
        """
        ### Return netlist from file if exists
        if netlist_filename:
            with open(netlist_filename, 'r') as f:
                for line in f.readline():
                    self.append_netlist_string(line)
            return
        ### Else build netlist from cells

        # PARAMETERS
        if len(self.parameters) > 0:
            self.append_netlist_string(self.get_parameter_string() + "\n\n")
        else:
            self.append_netlist_string("\n\n")

        # SUBCKTS
        subckts = self.get_subckts()
        for cell in subckts:
            if cell.declare_subckt:
                self.append_netlist_string(cell.get_subckt_string() + "\n")
            self.append_netlist_string(cell.get_include_statements())

        # ACTUAL DESIGN
        # Write metatext and all components of design
        self.append_netlist_string(self.get_cell_meta())
        for cell_name in self.subcells:
            cell = self.subcells[cell_name]
            self.append_netlist_string(cell.get_instance_string())

    def append_netlist_string(self, lines):
        self.netlist_string += lines

    def get_netlist_string(self):
        self.rewrite_netlist()
        return self.netlist_string


