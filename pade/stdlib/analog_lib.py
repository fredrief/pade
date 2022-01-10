from pade.schematic import Cell
from pade.utils import get_kwarg, num2string

class switch(Cell):
    """
    Switch
    Terminals: 'Np', 'Nm', 'NCp', 'NCm'
    """
    def __init__(self, instance_name, parent_cell, ropen='1T', rclosed='10.0', vt1=0.45, vt2=0.55):
        # Call super init
        super().__init__('switch', instance_name, parent_cell, library_name="analog_lib", declare=True)
        # Add terminals
        self.add_multiple_terminals(['Np', 'Nm', 'NCp', 'NCm'])
        self.parameters = {
            'vt1': num2string(vt1),
            'vt2': num2string(vt2),
            'ropen': num2string(ropen),
            'rclosed': num2string(rclosed),
        }
        sw_params = {
            'vt1': 'vt1',
            'vt2': 'vt2',
            'ropen': 'ropen',
            'rclosed': 'rclosed',
        }
        sw = relay('SW', parent_cell=self, parameters=sw_params).quick_connect(
            ['N+', 'N-', 'NC+', 'NC-'],
            ['Np', 'Nm', 'NCp', 'NCm'])

class relay(Cell):
    """
    Relay / ideal switch
    Terminals: 'N+', 'N-', 'NC+', 'NC-'
    """
    def __init__(self, instance_name, parent_cell, ropen='1T', rclosed='1000.0', parameters={}):
        # Call super init
        super().__init__('relay', instance_name, parent_cell, library_name="analog_lib", declare=False)
        # Add terminals
        self.add_multiple_terminals(['N+', 'N-', 'NC+', 'NC-'])
        # Add parameters
        self.set_parameter('ropen', ropen)
        self.set_parameter('rclosed', rclosed)

        self.set_parameter('vt1', get_kwarg(parameters, 'vt1', 0.3))
        self.set_parameter('vt2', get_kwarg(parameters, 'vt1', 0.7))

        for key in parameters:
            self.parameters[key] = parameters[key]

class transformer(Cell):
    """
    Transformer
    """
    def __init__(self, instance_name, parent_cell, n1):
        # Call super init
        super().__init__('transformer', instance_name, parent_cell, library_name="analog_lib", declare=False)
        # Add terminals
        self.add_terminal('pp')
        self.add_terminal('pn')
        self.add_terminal('sp')
        self.add_terminal('sn')
        # Add parameters
        self.set_parameter('n1', n1)


class ideal_balun(Cell):
    """
    Ideal Balun
    Terminals: 'd', 'c', 'p', 'n'
    """
    def __init__(self, instance_name, parent_cell):
        # Call super init
        super().__init__('ideal_balun', instance_name, parent_cell, library_name="analog_lib")
        # Add terminals
        self.add_terminal("d")
        self.add_terminal("c")
        self.add_terminal("p")
        self.add_terminal("n")
        # Add subcells
        k0 = transformer('K0', self, 2).quick_connect(['pp', 'pn', 'sp', 'sn'], ['d', '0', 'p', 'c'])
        k1 = transformer('K1', self, 2).quick_connect(['pp', 'pn', 'sp', 'sn'], ['d', '0', 'c', 'n'])


class res(Cell):
    """
    Resistor
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, R):
        # Call super init
        super().__init__('resistor', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'r': num2string(R)}

class cap(Cell):
    """
    Capacitor
    terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, C):
        # Call super init
        super().__init__('capacitor', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'c': num2string(C)}

class idc(Cell):
    """
    DC Current source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, idc):
        # Call super init
        super().__init__('isource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'dc': num2string(idc), 'type': 'dc'}

class ipulse(Cell):
    """
    Current pulse source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, i1, i2, per, parameters={}):
        # Call super init
        super().__init__('isource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'val0': num2string(i1), 'val1': num2string(i2), 'period': num2string(per), 'type': 'pulse'}
        for p in parameters:
            self.parameters[p] = parameters[p]

class vdc(Cell):
    """
    DC Voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, vdc, **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'dc': num2string(vdc), 'type': 'dc'}
        for key in kwargs:
            self.parameters[key] = kwargs[key]

class vsin(Cell):
    """
    DC Voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, vdc, ampl, freq, **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'type': 'sine', 'sinedc': num2string(vdc), 'ampl': num2string(ampl), 'freq': num2string(freq), 'mag': '1'}
        for key in kwargs:
            self.parameters[key] = kwargs[key]

class vccs(Cell):
    """
    Voltage Controlled Current Source (Ideal Transconductor)
    Terminals: 'out_n', 'out_p', 'in_p', 'in_n'
    """
    def __init__(self, instance_name, parent_cell, gm):
        # Call super init
        super().__init__('vccs', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("out_n")
        self.add_terminal("out_p")
        self.add_terminal("in_p")
        self.add_terminal("in_n")
        # Add properties
        self.parameters = {'type': 'vccs', 'gm': num2string(gm)}

class vcvs(Cell):
    """
    Voltage Controlled Voltage Source (Ideal Voltage Amplifier)
    Terminals: 'out_p', 'out_n', 'in_p', 'in_n'
    """
    def __init__(self, instance_name, parent_cell, gain):
        # Call super init
        super().__init__('vcvs', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("out_p")
        self.add_terminal("out_n")
        self.add_terminal("in_p")
        self.add_terminal("in_n")
        # Add properties
        self.parameters = {'gain': num2string(gain)}

class vpulse(Cell):
    """
    DC Voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, val0, val1, period, delay=None, rise=None, fall=None, width=None):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Add properties
        self.parameters = {'type': 'pulse', 'val0': num2string(val0), 'val1': num2string(val1), 'period': num2string(period)}
        # Add optional properties
        if delay is not None:
            self.parameters['delay'] = num2string(delay)
        if rise is not None:
            self.parameters['rise'] = num2string(rise)
        if fall is not None:
            self.parameters['fall'] = num2string(fall)
        if width is not None:
            self.parameters['width'] = num2string(width)

class bsource(Cell):
    """
    Behavioral Source Use Model
    Terminals: 'p', 'n'
    """
    def __init__(self, instance_name, parent_cell, output, expression, parameters={}):
        # Call super init
        super().__init__('bsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.add_terminal("n")
        self.add_terminal("p")
        # Add properties
        self.parameters[f'{output}'] = f'{expression}'
        for key in parameters:
            self.parameters[key] = parameters[key]

