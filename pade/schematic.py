from datetime import datetime
from scipy.linalg import hadamard
from pade.utils import num2string, get_kwarg
import sys
import os
from inform import warn, fatal
import re


class Design:
    """
    Design class
    """
    def __init__(self, cell_name, parameters={}, **kwargs):
        """
        Initialize design
        """
        # Dictionary to hold all child cells
        self.cells = {}
        # Dictionary of parameters
        self.parameters = parameters
        # Dictionary of nets. Always include gnd
        self.nets = {}
        self.add_net('0')
        # Design meta:
        self.cell_name = cell_name
        # Netlist string. Contains all design-related info. Is completed by simulator
        self.netlist_string = ""
        # Initial conditions
        self.ic = get_kwarg(kwargs, 'ic')
        self.netlist_filename = get_kwarg(kwargs, 'netlist_filename')


    def __str__(self):
        s = "# -------------------------------------------------------- #\n"
        s += "Design object for {}:\n".format(self.cell_name)
        s += "PARAMETERS: \n"
        for key in self.parameters:
            value = self.parameters[key]
            s += "{}: {}\n".format(key, value)
        s += "CELLS: ({})\n".format(len(self.cells))
        for cell_name in self.cells:
            s += self.cells[cell_name].__str__() + "\n"
        s += "# -------------------------------------------------------- #"
        return s

    def wire_up(self):
        """
        Defines the design. Implemented by subclass.
        """
        pass

    def add_net(self, net):
        """
        Add net to desing
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

    def has_net(self, net_name):
        """
        Check if net named net_name is already in design
        """
        return net_name in self.nets

    def get_net(self, net_name):
        """
        Return net of name net_name if exist else None
        """
        if net_name in self.nets:
            return self.nets[net_name]
        else:
            return None

    def get_subckts(self):
        """
        Returns a ordered list of all unique subckts in design
        """
        subckts = []
        for cell_name in self.cells:
            cell = self.cells[cell_name]
            subckts = cell.append_subckt_list(subckts)
        return subckts

    def add_parameters(self, parameters):
        """
        Add parameters to design

        Arguments
            parameters: Dictionary
        """
        # Copy parameters
        for key in parameters:
            if not key in self.parameters:
                self.parameters[key] = parameters[key]


    def add_cells(self, cells):
        """
        Add cell to design
        Arguments
            cells: list of Cell objects
        """
        for cell in cells:
            # Connect design and cell objects
            if(self.has_cell(cell.instance_name)):
                warn(f"WARNING: instance_name {cell.instance_name} is instantiated twice! This might result in errors in the netlist.")
            self.cells[cell.instance_name] = cell

    def get_cell(self, instance_name):
        """
        Return cell 'instance_name' if exists
        """
        if instance_name in self.cells:
            return self.cells[instance_name]
        else:
            raise ValueError(f'Cell with name {instance_name} does not exist')

    def remove_cell(self, instance_name):
        """
        Remove cell 'instance_name' from design if exists
        """
        if instance_name in self.cells:
            del self.cells[instance_name]
        else:
            raise ValueError(f'Cell with name {instance_name} does not exist')

    def has_cell(self, instance_name):
        return instance_name in self.cells


    def get_cell_meta(self):
        """
        Return commented cell meta text
        """
        s = "// Design cell name: {}\n".format(self.cell_name)
        return s

    def get_parameter_string(self):
        s = "parameters"
        for p, value in self.parameters.items():
            s += " {}={}".format(p, num2string(value))
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
        for cell_name in self.cells:
            cell = self.cells[cell_name]
            self.append_netlist_string(cell.get_instance_string())

    def append_netlist_string(self, lines):
        self.netlist_string += lines

    def get_netlist_string(self):
        self.rewrite_netlist()
        return self.netlist_string

class Cell:
    """
    Cell view
    """
    def __init__(self, cell_name, instance_name, design, **kwargs):
        """
        Initialize cell_view

        Arguments
            declare: bool
                Whether the cell should be declared in beginning of netlist or not. This should be set to false if the cell is a standard spectre component like cap or res
            parent_cell: Cell
                Specify if the cell is a subcell of another cell

        Keyword arguments:
            exclude_list:
                List of strings that are matched to exclude subcells in subckt definition. Only applicable if netlist_filename is provided. (default [])

        """
        # List of terminals

        self.terminals = []

        self.nets = {}
        self.cell_name = cell_name
        self.instance_name = instance_name
        # Parameters dict (Only parameters that is passed to spectre)
        self.parameters = {}
        # Connect cell and design/parent cell
        self.design = design
        self.parent_cell = get_kwarg(kwargs, 'parent_cell')
        if self.parent_cell:
            self.parent_cell.add_subcell(self)
        else:
            design.add_cells([self])

        self.subcells = {}
        # Generate parameters and terminals if netlist is available
        netlist_filename = get_kwarg(kwargs, 'netlist_filename')
        if netlist_filename:
            self.extract_data_from_file(netlist_filename, design, **kwargs)
        # Initialize subckt string
        self.declare_subckt = get_kwarg(kwargs, 'declare', default=True)
        # AHDL Filepath
        self.ahdl_filepath = ""
        # Include filepath
        self.include_filepath = ""


    def extract_data_from_file(self, file, design, **kwargs):
        """
        Read a spectre netlist and define parameters and terminals accordingly
            Supports line continuity for both parameters and terminals.

        """
        # Clean file by removing new line characters
        with open(file, "r") as raw:
            string_clean_lines = ""
            for line in raw:
                clean_line = line.rstrip().lstrip()
                if(clean_line.endswith('\\')):
                    clean_line = clean_line.rstrip('\\')
                else:
                    clean_line += '\n'
                string_clean_lines += clean_line

        for line in string_clean_lines.splitlines():
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
                if not self.cell_name == line.split()[1]:
                    fatal('Cannot instantiate component. Cell name does not equal subckt declaration in file.')

                for terminal in line.split()[2:]:
                    self.add_terminal(terminal)
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
                for i, nets in enumerate(line.split()[1:sc_first_param_location-1]):
                    sc_connected_nets.append(nets)
                    sc_terminals.append(str(i))
                for i, sc_param in enumerate(line.split()[sc_first_param_location:]):
                    sc_param_key, sc_param_value = sc_param.split('=')
                    sc_param_dict[sc_param_key] = sc_param_value
                exclude_list = kwargs['exclude_list'] if 'config_file' in kwargs else []
                skip_subcell = 0
                for exclusion in exclude_list:
                    if(exclusion in line):
                        skip_subcell = 1
                if(skip_subcell == 0):
                    subcell = Cell(sc_cell_name, sc_instance_name, design, declare=False, parent_cell=self)
                    subcell.add_multiple_terminals(sc_terminals)
                    subcell.quick_connect(sc_terminals, sc_connected_nets)
                    subcell.add_parameters(sc_param_dict)

    def add_parameters(self, parameters):
        """
        Add parameters to design

        Arguments
            parameters: Dictionary
        """
        # Copy parameters
        for key in parameters:
            if not key in self.parameters:
                self.parameters[key] = parameters[key]

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
        Add subcell
        """
        self.subcells[cell.instance_name] = cell

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
            s += 'include "{}"\n'.format(self.include_filepath)
        if self.ahdl_filepath != "":
            s += 'ahdl_include "{}"\n'.format(self.ahdl_filepath)
        return s

    def get_subckt_string(self):
        """
        Return sub circuit declaration string
        """
        # META
        s = ""
        s += f"// Cell name: {self.cell_name}\n"
        s += "// View name: schematic\n"
        s += f"subckt {self.cell_name} "
        # TERMINALS
        for t in self.terminals:
            s += t.name
            # Add space after all except the last
            if not t==self.terminals[-1]:
                s += " "
            # Add new line after last terminal
            else:
                s += "\n"
        # PARAMETERS
        if self.parameters:
            s += "parameters "
            for p in self.parameters:
                s += f"{p} "
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
        # The all terminals of cell must be connected to nets before instance string can be generated
        if any([t.net is None for t in self.terminals]):
            unconnected_terminals = []
            for t in self.terminals:
                if t.net is None:
                    unconnected_terminals.append(t.name)
            raise RuntimeError(f'Cell {self.instance_name} has unconnected terminals: {unconnected_terminals}')
        s  = "{} ".format(self.instance_name)
        for t in self.terminals:
            s += "{}".format(t.net.name)
            # Add space after all except the last
            if not t==self.terminals[-1]:
                s += " "
        s += " {} ".format(self.cell_name)
        # Add parameters that is not None
        params = self.parameters if self.parameters is not None else []
        for p in params:
            if p is not None:
                s += "{}={} ".format(p, params[p])
        s += "\n"
        return s

    def __str__(self):
        # Display name and instance name
        s  = "{}: {}\n".format(self.cell_name, self.instance_name)

        # Display terminals and connected nets
        s += "# Connections: "
        for i, x in enumerate(self.terminals):
            s+= f"({x.name} -> {x.net.name})"
            if(i < len(self.terminals)-1):
                s+= ", "

        return s+"\n"

    def add_terminal(self, name, iotype=None, pos=None):
        """
        Add terminal <name> if it does not already exist
        Added both as an attribute and as a member of list of terminals
        """
        if not hasattr(self,name) and isinstance(name, str):
            terminal = Terminal(name, self, self.design, iotype=iotype, pos=pos)
            setattr(self, name, terminal)
            self.terminals.append(terminal)
            # Connect terminal to net of same name
            net = Net(name, self)
            terminal.connect(net)
        else:
            raise ValueError('Terminal {} already exist/was not set for another reason'.format(name))

    def add_multiple_terminals(self, terminals):
        """
        Add multiple terminals
        """
        for t in terminals:
            self.add_terminal(t)

    def has_terminal(self, tname):
        if not isinstance(tname, str):
            raise ValueError('Terminal name must be a string')
        else:
            return hasattr(self, tname)

    def get_terminal(self, tname):
        """
        Returns object Terminal if it exists in cell
        """
        if not isinstance(tname, str):
            raise ValueError('Terminal name must be a string')
        elif not hasattr(self, tname):
            raise ValueError('No terminal named {} exist in cell {}'.format(tname, self.instance_name))
        else:
            return getattr(self,tname)

    def get_all_terminal_names(self):
        """
        Returns a list containing all terminals in cell
        """
        terminals = []
        for x in self.terminals:
            terminals.append(x.name)
        return terminals

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


    def connect(self, tname, net):
        """
        Connect terminal to a net

        Arguments
            tname: str
            net: Net or str
        """
        # Verify that terminal is member of cell and get Terminal object
        if not isinstance(tname, str):
            raise ValueError('Terminal name must be a string')
        terminal = self.get_terminal(tname)

        # If net is Net, connect directly
        if isinstance(net, Net):
            terminal.net=net
            net.connect([terminal])
        # If net is str, check if net exist, else create a Net with this name and connect
        elif isinstance(net, str):
            parent = self.parent_cell if self.parent_cell else self.design
            if net in parent.nets:
                net = parent.get_net(net)
            else:
                net = Net(net, parent)
            terminal.net=net
            net.connect([terminal])
        else:
            raise ValueError('Could not connect. {} is not a Net or a string'.format(net))

    def quick_connect(self, terminals, nets):
        """
        Connect list of terminals to a list of nets
        Arguments
            terminals: [str]
                Array of terminal names
            nets: [str] or [Terminal]
                Array of terminals
        """
        # Validate
        if not len(terminals) == len(nets):
            raise ValueError(f'Number of terminals ({len(terminals)}) is not equal to number of nets ({len(nets)})')
        for i in range(0, len(terminals)):
            self.connect(terminals[i], nets[i])

    def set_parameter(self, name, value):
        """
        Set value of parameter 'name' to 'value'
        """
        self.parameters[name] = num2string(value)


class Terminal:
    """
    Terminal
    A Terminal is owned by a Cell and connected to a net
    It contains a reference to its cell as well as the design

    """
    def __init__(self, name, cell, design, iotype=None, pos=None):
        """
        Arguments
            iotype: string
                Has to be either "In", "Out" or None
            pos:
                Used for schematic
        """
        self.name = name
        self.net = None
        self.cell = cell
        self.design = design
        self.pos=pos
        if not (iotype is None or "In" or "Out"):
            raise ValueError('Invalid terminal type: {}'.format(iotype))
        else:
            self.iotype = iotype

    def __str__(self):
        s  = "Terminal {} of cell {} in design {}\n".format(self.name, self.cell.instance_name, self.design.cell_name)
        s += "Connected to net: {}\n".format(self.net.name if self.net else "None")
        return s

    def __repr__(self):
        s  = "Terminal {} of cell {} in design {}\n".format(self.name, self.cell.instance_name, self.design.cell_name)
        s += "Connected to net: {}\n".format(self.net.name if self.net else "None")
        return s

    def get_net(self):
        return self.net

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
            parent = self.cell.parent_cell if self.cell.parent_cell else self.design
            if parent.has_net(net):
                net = parent.get_net(net)
            else:
                net = Net(net, self.design)
            self.net=net
            net.connect([self])
        else:
            raise ValueError('Could not connect. {} is not a Net or a string'.format(net))

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
        s  = "Net {}\nConnected to:\n".format(self.name)
        for c in self.connections:
            s += "- terminal {} of cell {}\n".format(c.name, c.cell.instance_name)
        return s

    def connect(self, terminals):
        """
        Connect net to a list of terminals
        """
        for t in terminals:
            if isinstance(t, Terminal):
                self.connections.append(t)
            else:
                raise ValueError('{} is not a Terminal'.format(t))
