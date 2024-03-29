from pade.utils import num2string
from pade import warn, fatal

class Corner:
    """
    For corner setup
    """
    def __init__(self, name, corner_string):
        self.name = name
        self.corner_string = corner_string

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def get_string(self) -> str:
        return self.corner_string



class Analysis:
    """
    Abstract analysis class
    An analysis is initialized by a name and a dictionary of paramaters.
    The analysis holds a netlist_string which is appended to the final spectre netlist.
    """
    def __init__(self, name, type=None, parameters={}):
        self.name = name
        self.parameters = parameters
        self.type = type if type is not None else name
        self.netlist_string = ""

    def get_netlist_string(self):
        # write netlist
        self.netlist_string = f"{self.name} {self.type} "
        for param in self.parameters:
            value = self.parameters[param]
            self.netlist_string += f"{param}={num2string(value)} "
        return self.netlist_string

class Option:
    """
    General option to append to netlist
    """
    def __init__(self, option_string):
        self.option_string = option_string

    def get_netlist_string(self):
        return self.option_string


class pss(Analysis):
    """
    Periodic Steady-State
    """
    def __init__(self, nodes=None, name='pss', parameters={}):
        self.nodes = nodes
        self.autonomous = (nodes is not None)
        super().__init__(name, type='pss', parameters=parameters)


    def get_netlist_string(self):
        # Overwrite function for writing netlist
        self.netlist_string = f"{self.name} "
        if self.nodes is not None:
            self.netlist_string += f"{self.nodes[0]} {self.nodes[0]} "
        self.netlist_string += f"{self.type} "
        for param in self.parameters:
            value = self.parameters[param]
            self.netlist_string += f"{param}={num2string(value)} "
        return self.netlist_string

class pnoise(Analysis):
    """
    Periodic noise
    """
    def __init__(self, nodes=None, name='pnoise', parameters={}):
        self.nodes = nodes
        self.autonomous = (nodes is not None)
        super().__init__(name, type='pnoise', parameters=parameters)


    def get_netlist_string(self):
        # Overwrite function for writing netlist
        self.netlist_string = f"{self.name} "
        if self.nodes is not None:
            self.netlist_string += f"{self.nodes[0]} {self.nodes[0]} "
        self.netlist_string += f"{self.type} "
        for param in self.parameters:
            value = self.parameters[param]
            self.netlist_string += f"{param}={num2string(value)} "
        return self.netlist_string


class tran(Analysis):
    """
    Transient analysis
    """
    def __init__(self, name='tran', parameters={}):
        default_params = {
            'cmin': 0,
            'method': 'gear2only',
            'annotate': 'status',
            'maxiters': 5,
            'save': 'selected'
        }
        p = default_params
        for param in parameters:
            if not parameters[param] is None:
                p[param] = parameters[param]
        super().__init__(name, type='tran', parameters=p)

class dc(Analysis):
    """
    DC analysis
    """
    def __init__(self, name='dc', parameters={}):
        default_params = {
            'maxiters': 150,
            'maxsteps': 10000,
            'write': '"spectre.dc"',
            'annotate': 'status',
        }
        p = default_params
        for param in parameters:
            p[param] = parameters[param]
        super().__init__(name, type='dc', parameters=parameters)


class dcOpInfo(Analysis):
    """
    DC Operating Point
    """
    # Append dcOpInfo
    def __init__(self, name='dcOpInfo', type='info', parameters={}):
        default_params = {
            'what': 'oppoint',
            'where': 'rawfile',
        }
        p = default_params
        for param in parameters:
            p[param] = parameters[param]
        super().__init__(name, type=type, parameters=p)


class initial_condition(Analysis):
    """
    Set initial condition
    Not really an analysis, but works with type=''
    """
    # Append dcOpInfo
    def __init__(self, name='ic', type='', parameters={}):
        super().__init__(name, type=type, parameters=parameters)


class ac(Analysis):
    """
    AC Analysis
    """
    def __init__(self, name='ac', parameters={}):
        default_params = {
            'start': 1,
            'stop': 10e9,
            'annotate': 'status',
        }
        p = default_params
        for param in parameters:
            p[param] = parameters[param]
        super().__init__(name, type='ac', parameters=p)


class noise(Analysis):
    """
    Noise Analysis
    """
    def __init__(self, name='noise', parameters={}):
        default_params = {
            'start': 1,
            'stop': 10e9,
            'annotate': 'status',
        }
        p = default_params
        for param in parameters:
            p[param] = parameters[param]
        super().__init__(name, type='noise', parameters=p)

class stb(Analysis):
    """
    Stability analysis
    Parameters:
        probe_instance_name: str
            Instance name of the probe to use for stb analysis
        mode: str
            Allowed values: S, C or D
            Single ended, common or differential
            If C or D, assuming the probe is a diffstbprobe cell
    """
    def __init__(self, probe_instance_name, mode, name='stb', parameters={}):
        mode = mode.upper()
        if mode == 'S':
            probe = probe_instance_name
        elif mode == 'C':
            probe = probe_instance_name + '.IPRB_CM'
        elif mode == 'D':
            probe = probe_instance_name + '.IPRB_DM'
        else:
            fatal(f'Invalid stb mode: {mode}')
        default_params = {
            'start': 1,
            'stop': 10e9,
            'annotate': 'status',
            'probe': probe
        }
        p = default_params
        for param in parameters:
            p[param] = parameters[param]
        super().__init__(name, type='stb', parameters=p)
