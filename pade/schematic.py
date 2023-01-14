from symbol import return_stmt
from pade.utils import num2string, get_kwarg, append_dict
import re
import json
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
            logger: Logger
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
        self.instance_name = instance_name
        self.lib_name = kwargs.get('lib_name')

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

        # For LPE netlist, do not parse, just return netlist
        # This will be used in the get subckt function
        self.lpe_netlist = kwargs.get('lpe_netlist')

        # Initialize subckt string
        self.declare_subckt = get_kwarg(kwargs, 'declare', default=True)
        # AHDL Filepath
        self.ahdl_filepath = ""
        # Include filepath (additional filepath to include)
        self.include_filepath = ""

    def __repr__(self) -> str:
        return f"Cell {self.instance_name}, type {self.cell_name}\n"


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

    def append_subckt_list(self, subckt_list):
        """
        Append self to subckt list in right order
        """
        # First append all subcells to the list
        for instance_name in self.subcells:
            cell = self.subcells[instance_name]
            subckt_list = cell.append_subckt_list(subckt_list)
        # append self to list if not already present
        if not any([self.cell_name == x.cell_name for x in subckt_list]):
            subckt_list.append(self)
        return subckt_list

    def add_subcell(self, cell):
        """
        Add subcell both in dict and as attribute
        """
        self.subcells[cell.instance_name] = cell

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

    def insert(self, ta1: Terminal , ta2: Terminal, t1: Terminal, t2: Terminal):
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

    def get_subckts(self):
        """
        Returns a ordered list of all unique subckts in Cell
        """
        subckts = []
        for cell_name in self.subcells:
            cell = self.subcells[cell_name]
            subckts = cell.append_subckt_list(subckts)
        return subckts

    def get_spiceIn_subckt_string(self):
        # SUBCKTS
        s = ""
        subckts = self.get_subckts()
        for cell in subckts:
            if cell.declare_subckt:
                s += cell.get_subckt_string() + "\n"
        s += self.get_subckt_string(remove_unconnected_terminals=False)
        return s

    def get_subckt_string(self, remove_unconnected_terminals=True):
        """
        Return sub circuit declaration string
        """
        # If lpe_netlist is set, return directly
        if self.lpe_netlist is not None:
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
                    # continue

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
            s += f"{c.get_instance_string()}"

        # END
        s += f"ends {self.cell_name}\n"
        return s


    def get_instance_string(self):
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
        s += " {} ".format(self.cell_name)
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
            # Give lib_name to cell
            cell.lib_name = self.lib_name
            # As cell to do the same for all subcells
            cell.set_library_on_all_cells()



class LayoutCell(Cell):
    """
    Extends Cell with functionality for generating Layout
    TODO: Support symbol
    """
    def __init__(self, cell_name, instance_name, parent_cell=None, **kwargs):
        super().__init__(cell_name, instance_name, parent_cell, **kwargs)
        self.cic_class = kwargs.get('cic_class', "Layout::LayoutDigitalCell")
        # Definition for json object file
        self.cell_definition = {
            "name": self.cell_name,
            "class": self.cic_class,
        }

        # Parameters for Spice netlist file
        self.layout_parameters = kwargs.get('layout_parameters', {})

    def add_layout_parameter(self, key, value):
        # Parameters for Spice netlist file
        self.layout_parameters[key] = value

    def _get_lay_cic_spice_subckt_string(self):
        """
        Return subcircuit definition for cic spice layout files
        """
        s = f".SUBCKT {self.cell_name}"
        # TERMINALS
        for t in self.get_sorted_terminal_list():
            s += f' {t.name}'
        s += "\n"
        # SUBCELLS
        for key in self.subcells:
            c = self.subcells[key]
            s += f"{c._get_lay_cic_spice_instance_string()}"
        # END
        s += f".ENDS {self.cell_name}\n\n"
        return s

    def _get_lay_cic_spice_instance_string(self):
        """
        Return instance string for cic spice layout files
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
        s += " {} ".format(self.cell_name)

        for p in self.layout_parameters:
            if self.layout_parameters[p] is not None:
                s += "{}={} ".format(p, num2string(self.layout_parameters[p]))
        s += "\n"
        return s

    def get_layout_cic_spice(self):
        netlist = ""
        # First append netlist from all subckts
        subckts = self.get_subckts()
        for cell in subckts:
            if isinstance(cell, LayoutCell):
                netlist += cell._get_lay_cic_spice_subckt_string()

        # Then append self
        netlist += self._get_lay_cic_spice_subckt_string()
        return netlist


    def write_object_definition_file(self, filename, header={}, options={}, include_json_list=[]):
        self.object_definition_dict = {}
        self.object_definition_dict['header'] = header
        self.object_definition_dict['options'] = options
        self.object_definition_dict['cells'] = []

        # json files to include
        cell_name_list = [] # List to keep track of cells in dict
        for json_file in include_json_list:
            with open(json_file, 'r') as f:
                d = json.load(f)
                for cell in d['cells']:
                    self.object_definition_dict['cells'].append(cell)
                    if 'name' in cell:
                        cell_name_list.append(cell['name'])

        # Append cell definition of all subcells
        subckts = self.get_subckts()
        for cell in subckts:
            # Do not add cell if already in dict
            if isinstance(cell, LayoutCell) and not cell.cell_name in cell_name_list:
                self.object_definition_dict['cells'].append(cell.cell_definition)
                cell_name_list.append(cell.cell_name)

        # Then append self
        self.object_definition_dict['cells'].append(self.cell_definition)

        with open(filename, 'w') as f:
            json.dump(self.object_definition_dict, f)

    def write_layout_cic_spice(self, filename, append_spi_file=None):
        netlist = self.get_layout_cic_spice()
        if append_spi_file:
            with open(append_spi_file, 'r') as fi:
                append_netl = fi.read()
                netlist += append_netl

        with open(filename, 'w') as f:
            f.write(netlist)

    def set_properties(self, properties):
        """
        Set layout properties to object definition
        """
        self.append_cell_dict(properties)
        # for key, value in properties.items():
        #     self.cell_definition[key] = value

    def has_property(self, p):
        return p in self.cell_definition

    def append_cell_dict(self, d):
        self.cell_definition = append_dict(self.cell_definition, d)

    def _get_port_name(self, port):
        """
        Helper function to get port_name from port to handle different types
        """
        if isinstance(port, Terminal):
            port_name = port.name
        elif isinstance(port, str):
            port_name = port
        else:
            raise ValueError(f'Invalid port: {port}, must be string or Terminal')
        return port_name

    def _get_net_name(self, net):
        """
        Helper function to get net_name from net to handle different types
        """
        if isinstance(net, Net):
            net_name = net.name
        elif isinstance(net, str):
            net_name = net
        elif isinstance(net, Terminal):
            net_name = net.name
            if not net_name in self.nets:
                raise ValueError(f'Net: {net}, does not exist in {self}')
        else:
            raise ValueError(f'Invalid net: {net}, must be string, Net Terminal')
        return net_name

    def add_port_on_rect(self, port, layer_name, rect=None):
        """
        Add port on rect after route
        Also add terminal
        """
        port_name = self._get_port_name(port)
        # Add port as terminal if not exist
        if not port_name in self.terminals:
            terminal = self.add_terminal(port_name)
        else:
            terminal = self.get_terminal(port_name)
        # Build port dict
        port_dict = {
            "afterRoute": {
                "addPortOnRects": [[
                    port_name,
                    layer_name,
                ]]
            }
        }
        if rect is not None:
            port_dict["afterRoute"]["addPortOnRects"][0].append(self.get_hierarchy_string(rect))

        self.append_cell_dict(port_dict)

        # Finally connect terminal to net in current hierchy
        if isinstance(rect, Terminal) and isinstance(port, Terminal):
            net = self.add_net(self._get_net_name(port.name))
            if rect.net is None:
                rect.connect(net)





    def add_directed_route(self, layer_name, net_name, route_command, options=[]):
        route_dict = {
            "beforeRoute": {
                'addDirectedRoutes':
                [[layer_name, net_name, route_command]]
            }
        }
        opt_string = ''
        for opt in options:
            opt_string += opt
            if not opt == options[-1]:
                opt_string += ','
        route_dict["beforeRoute"]["addDirectedRoutes"][0].append(opt_string)
        self.append_cell_dict(route_dict)

    def get_hierarchy_string(self, terminal):
        """
        Returns the string from self to port on the form (SC=sub circuit):
        SC1:SC2:TERMINAL
        """
        if isinstance(terminal, str):
            return terminal
        elif isinstance(terminal, Terminal):
            s = terminal.name
            parent_cell = terminal.cell
            while parent_cell is not self:
                s = f'{parent_cell.instance_name}:{s}'
                parent_cell = parent_cell.parent_cell
            return s
        else:
            raise ValueError(f'Invalid terminal {terminal}')

    def route(self, layer_name, net, from_port, to_port, route_type, options=[]):
        route_cmd = f'{self.get_hierarchy_string(from_port)}{route_type}{self.get_hierarchy_string(to_port)}'

        self.add_directed_route(layer_name, self._get_net_name(net), route_cmd, options=options)

        self._deep_connect(from_port, net)
        self._deep_connect(to_port, net)

    def _deep_connect(self, port, net):
        """
        Connect port to net, where the port is allowed to be deep in the hiearchy, and the connection is made within self
        """
        # Add connection from ports to net if not present
        net = self.add_net(self._get_net_name(net))
        while port.cell is not self and port.cell.parent_cell is not self:
            # Find the port in the right hiearchy level
            port = port.cell.parent_cell.get_terminal(port.net.name)
        if port.net is None:
            port.connect(net)
        elif not port.net.get_name_from_top() == net.get_name_from_top():
            raise RuntimeError(f'You tried to route {port.get_name_from_top()} to {net.get_name_from_top()}, but {port.get_name_from_top()} is already connected to {port.net.get_name_from_top()}')


    def add_via(self, start_layer, stop_layer, rect, horizontal_cuts, *args):
        """
        Add a via at an horizontal offset to a rectangle defined by a path regex

        [ "M3",          //Start layer
        "M4",          //Stop layer
        "MP1:D",       //Path regex to find rectangle
        2,             //Horizontal cuts
        1,             //Vertical cuts       [optional]
        8,             //Horizontal offset   [optional]
        "CUST_VREF"    //Custom name for via [optional]
        ]
        """
        via_dict = {
            "beforeRoute": {
                'addVias':
                    [[start_layer,
                    stop_layer,
                    self.get_hierarchy_string(rect),
                    horizontal_cuts
                    ]]
            }
        }
        for a in args:
            via_dict["beforeRoute"]["addVias"][0].append(a)

        self.append_cell_dict(via_dict)

    def add_vertical_rect(self, layer_name, rect, cuts=0):
        """
        Adds a custom rectangle for the height of the module
        ["M5",          //Layer
        "CUST_C16",    //Path regex
        1              //Cuts, default 0, if 0 then use rectangle width
        ]
        """
        vr_dict = {
            "beforeRoute": {
                'addVerticalRects':
                    [[layer_name,
                    self.get_hierarchy_string(rect),
                    cuts
                    ]]
            }
        }
        self.append_cell_dict(vr_dict)

class Design(Cell):
    """
    Top-level design class
    """
    def __init__(self, cell_name, **kwargs):
        super().__init__(cell_name, cell_name, **kwargs)
        self.add_net('0')
        # Initial conditions
        self.ic = get_kwarg(kwargs, 'ic')


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


class PatternCell(LayoutCell):
    """
    The basic unit cells
    """
    def __init__(self, cell_name, instance_name, parent_cell=None, **kwargs):
        cic_class = kwargs.get('cic_class', "Gds::GdsPatternTransistor")
        super().__init__(cell_name, instance_name, parent_cell, cic_class=cic_class,  **kwargs)

    # Overwrite/disable layout subckt
    def _get_lay_cic_spice_subckt_string(self):
        return ""



