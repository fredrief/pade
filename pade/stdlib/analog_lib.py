from pade.schematic import Cell
from pade.utils import get_kwarg, num2string
from shlib import to_path
import os

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
        self.add_parameters({
            'vt1': num2string(vt1),
            'vt2': num2string(vt2),
            'ropen': num2string(ropen),
            'rclosed': num2string(rclosed),
        })
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
            self.set_parameter(key, parameters[key])

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
        self.d = self.add_terminal("d")
        self.c = self.add_terminal("c")
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
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
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'r': num2string(R)})

class cap(Cell):
    """
    Capacitor
    terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, C):
        # Call super init
        super().__init__('capacitor', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'c': num2string(C)})

class inductor(Cell):
    """
    Capacitor
    terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, L):
        # Call super init
        super().__init__('inductor', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'l': num2string(L)})

class idc(Cell):
    """
    DC Current source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, idc):
        # Call super init
        super().__init__('isource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'dc': num2string(idc), 'type': 'dc'})

class vsin(Cell):
    """
    Sine voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, vdc, ampl, freq, **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'type': 'sine', 'sinedc': num2string(vdc), 'ampl': num2string(ampl), 'freq': num2string(freq), 'mag': '1'})
        for key in kwargs:
            self.set_parameter(key, kwargs[key])

class vbit(Cell):
    """
    Digital bit stream
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, val0, val1, period, datastr, rise='1n', fall='1n', **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        datastr = f'"{datastr}"'
        self.add_parameters({'type': 'bit', 'val0': val0, 'val1': val1, 'period': period, 'data': datastr, 'rise': rise, 'fall': fall})
        for key in kwargs:
            self.set_parameter(key, kwargs[key])

class isin(Cell):
    """
    AC Current source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, idc, ampl, freq, **kwargs):
        # Call super init
        super().__init__('isource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'type': 'sine', 'sinedc': num2string(idc), 'ampl': num2string(ampl), 'freq': num2string(freq), 'mag': '1'})
        for key in kwargs:
            self.set_parameter(key, kwargs[key])


class ipulse(Cell):
    """
    Current pulse source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, i1, i2, per, parameters={}):
        # Call super init
        super().__init__('isource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'val0': num2string(i1), 'val1': num2string(i2), 'period': num2string(per), 'type': 'pulse'})
        for p in parameters:
            self.set_parameter(p, parameters[p])

class vdc(Cell):
    """
    DC Voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, vdc, **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'dc': num2string(vdc), 'type': 'dc'})
        for key in kwargs:
            self.set_parameter(keym, kwargs[key])


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
        self.add_parameters({'type': 'vccs', 'gm': num2string(gm)})

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
        self.add_parameters({'gain': num2string(gain)})

class vpulse(Cell):
    """
    DC Voltage source
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, val0, val1, period, delay=None, rise=None, fall=None, width=None):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        # Add properties
        self.add_parameters({'type': 'pulse', 'val0': num2string(val0), 'val1': num2string(val1), 'period': num2string(period), 'mag': 1})
        # Add optional properties
        if delay is not None:
            self.set_parameter('delay', num2string(delay))
        if rise is not None:
            self.set_parameter('rise', num2string(rise))
        if fall is not None:
            self.set_parameter('fall', num2string(fall))
        if width is not None:
            self.set_parameter('width', num2string(width))


class vpwl(Cell):
    """
    Arguments:
        wave: List
            List of time/value points
    Terminals: p, n
    """
    def __init__(self, instance_name, parent_cell, wave, **kwargs):
        # Call super init
        super().__init__('vsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.p = self.add_terminal("p")
        self.n = self.add_terminal("n")
        wave_str_list = [num2string(w) for w in wave]
        # Add properties
        wave_str = "[" + ' '.join(wave_str_list) + ']'
        self.add_parameters({'type': 'pwl', 'wave': wave_str})
        # Add optional properties
        # V0 (net2 net1) vsource type=pwl wave=[ 0 0 1u 1 2u 2 ]
        for key, value in kwargs.items():
            self.set_parameter(key, value)



class bsource(Cell):
    """
    Behavioral Source Use Model
    Terminals: 'p', 'n'
    """
    def __init__(self, instance_name, parent_cell, output, expression, parameters={}):
        # Call super init
        super().__init__('bsource', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.n = self.add_terminal("n")
        self.p = self.add_terminal("p")
        # Add properties
        self.set_parameter(f'{output}', f'{expression}')
        for key in parameters:
            self.set_parameter(key, parameters[key])

class diffstbprobe(Cell):
    """
    Differential stb probe
    Terminals: 'in1', 'in2', 'out1', 'out2'
    """
    def __init__(self, instance_name, parent_cell, filepath, parameters={}):
        # Call super init
        super().__init__('diffstbprobe', instance_name, parent_cell, declare=False, library_name="analog_lib")
        # Add terminals
        self.in1, self.in2, self.out1, self.out2 = self.add_multiple_terminals(['in1', 'in2', 'out1', 'out2'])
        self.include_filepath = filepath
        # Add properties
        for key in parameters:
            self.set_parameter(key, parameters[key])
