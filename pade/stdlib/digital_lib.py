from pade.schematic import Cell
from pade.utils import get_kwarg, num2string
from techlib.techlib import pch_slvt, nch_slvt

class Not(Cell):
    """
    Inverter
    Terminals: 'vdd', 'gnd', 'vin', 'vout'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        # Call super init
        cell_name = 'Not'
        super().__init__(cell_name, instance_name, design, parent_cell=parent_cell)
        # Add terminals
        self.add_multiple_terminals(['vdd', 'gnd', 'vin', 'vout'])
        # Add parameters
        self.set_parameter('wg', get_kwarg(kwargs, 'wg', 150e-9))
        self.set_parameter('lg', get_kwarg(kwargs, 'lg', 20e-9))
        self.set_parameter('mfac', get_kwarg(kwargs, 'mfac', 1))
        # Connect
        mp = pch_slvt('mp', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['vdd', 'vout', 'vin', 'vdd'])
        mn = nch_slvt('mn', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin', 'gnd'])

class Nor(Cell):
    """
    Nor gate
    Terminals: 'vin1', 'vin2', 'vout', 'vdd', 'gnd'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        super().__init__("Nor", instance_name, design, parent_cell=parent_cell, declare=True, **kwargs)
        self.add_multiple_terminals(['vin1', 'vin2', 'vout', 'vdd', 'gnd'])
        # Add parameters
        self.set_parameter('wg', get_kwarg(kwargs, 'wg', 150e-9))
        self.set_parameter('lg', get_kwarg(kwargs, 'lg', 20e-9))
        self.set_parameter('mfac', get_kwarg(kwargs, 'mfac', 1))
        mp1 = pch_slvt('MP1', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['vdd', 'a', 'vin1', 'vdd'])
        mp2 = pch_slvt('MP2', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['vdd', 'vout', 'vin2', 'a'])
        mn1 = nch_slvt('MN1', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin1', 'gnd'])
        mn2 = nch_slvt('MN2', design, parent_cell=self, wg='wg', lg='lg', mfac='mfac').quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin2', 'gnd'])

class Or(Cell):
    """
    Or gate
    Terminals: 'vin1', 'vin2', 'vout', 'vdd', 'gnd'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        super().__init__("Or", instance_name, design, parent_cell=parent_cell, declare=True, **kwargs)
        self.add_multiple_terminals(['vin1', 'vin2', 'vout', 'vdd', 'gnd'])
        n0 = Nor('N0', design, parent_cell=self).quick_connect(
            ['vin1', 'vin2', 'vout', 'vdd', 'gnd'], ['vin1', 'vin2', 'a', 'vdd', 'gnd'])
        n1 = Not('N1', design, parent_cell=self).quick_connect(
            ['vdd', 'gnd', 'vin', 'vout'], ['vdd', 'gnd', 'a', 'vout'])

class Nand(Cell):
    """
    Nand gate
    Terminals: 'vin1', 'vin2', 'vout', 'vdd', 'gnd'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        super().__init__("Nand", instance_name, design, parent_cell=parent_cell, declare=True, **kwargs)
        self.add_multiple_terminals(['vin1', 'vin2', 'vout', 'vdd', 'gnd'])
        mp1 = pch_slvt('MP1', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['vdd', 'vout', 'vin1', 'vdd'])
        mp2 = pch_slvt('MP2', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['vdd', 'vout', 'vin2', 'vdd'])
        mn1 = nch_slvt('MN1', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin1', 'a'])
        mn2 = nch_slvt('MN2', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['gnd', 'a', 'vin2', 'gnd'])


class And(Cell):
    """
    Nand gate
    Terminals: 'vin1', 'vin2', 'vout', 'vdd', 'gnd'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        super().__init__("And", instance_name, design, parent_cell=parent_cell, declare=True, **kwargs)
        self.add_multiple_terminals(['vin1', 'vin2', 'vout', 'vdd', 'gnd'])
        nand = Nand('N0', design, parent_cell=self).quick_connect(
            ['vin1', 'vin2', 'vout', 'vdd', 'gnd'], ['vin1', 'vin2', 'a', 'vdd', 'gnd'])
        n1 = Not('N1', design, parent_cell=self).quick_connect(
            ['vdd', 'gnd', 'vin', 'vout'], ['vdd', 'gnd', 'a', 'vout'])


class Nor3(Cell):
    """
    Nor gate with three inputs
    Terminals: 'vin1', 'vin2', 'vin3', 'vout', 'vdd', 'gnd'
    """
    def __init__(self, instance_name, design, parent_cell=None, **kwargs):
        super().__init__("Nor3", instance_name, design, parent_cell=parent_cell, declare=True, **kwargs)
        self.add_multiple_terminals(['vin1', 'vin2', 'vin3', 'vout', 'vdd', 'gnd'])
        mp1 = pch_slvt('MP1', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['vdd', 'a', 'vin1', 'vdd'])
        mp2 = pch_slvt('MP2', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['vdd', 'b', 'vin2', 'a'])
        mp3 = pch_slvt('MP3', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['vdd', 'vout', 'vin3', 'b'])
        mn1 = nch_slvt('MN1', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin1', 'gnd'])
        mn2 = nch_slvt('MN2', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin2', 'gnd'])
        mn3 = nch_slvt('MN3', design, parent_cell=self, wg=150e-9, lg=20e-9, mfac=1).quick_connect(['b', 'd', 'g', 's'], ['gnd', 'vout', 'vin3', 'gnd'])





class vdigcode(Cell):
    """
    Voltage source, providing digital code stimulus
    Terminals: p, n
    Arguments:
        code: str
            0s and 1s that should be used as stimuli. Example: '1101001'
        period: float
            The period of the signals (inverse of frequency)
        v_high: str
            The voltage for each bit that is 1
        v_low: str
            The voltage for each bit that is 0
        rise_time: str
            The rise time for the signal
        fall_time: str
            The fall time for the signal
        delay: str
            The delay before the code generation starts.
            The first voltage is given by the first bit in the code

    """
    # TODO: Support string period, rise_time and fall_time
    def __init__(self, instance_name, design, code, period, v_high, v_low=0, rise_time=1e-12, fall_time=1e-12, delay=None, parent_cell=None):
        # Call super init
        super().__init__('vsource', instance_name, design, declare=False, library_name="digital_lib", parent_cell=parent_cell)
        # Add terminals
        self.add_terminal("p")
        self.add_terminal("n")
        # Generate wave based on code
        wave = self.generate_wave(code, period, v_high, v_low, rise_time, fall_time)

        self.parameters = {'type': 'pwl', 'wave': wave}
        # Add optional properties
        if delay is not None:
            self.parameters['delay'] = num2string(delay)

    def generate_wave(self, code, period, v_high, v_low, rise_time, fall_time):
        wave = '[ '
        if(code[0]) == '1':
            volt = v_high
        else:
            volt = v_low

        for i, bit in enumerate(code):
            time = i*period
            if(bit == '1'):
                volt = v_high
                delayed_time = time+rise_time
            else:
                volt = v_low
                delayed_time = time+fall_time
            wave += num2string(time) + ' '
            wave += num2string(volt) + ' '
            wave += num2string(delayed_time) + ' '
            wave += num2string(volt) + ' '
            wave += num2string(time + period - 1e-12) + ' '
            wave += num2string(volt) + ' '
        wave += ']'
        return wave

class vdigcode_multiple(Cell):
    """
    Instansiates a multiple vdigcode cells, given multiple codes. Allows for single cell to drive multiple pins
    Terminals: p_{x}, n, where x is the positive
    Arguments:
        codes: [str]
            0s and 1s that should be used as stimuli. Example: ['1101001', '0010110', 0100101']
        period: float
            The period of the signals (inverse of frequency)
        v_high: str
            The voltage for each bit that is 1
        v_low: str
            The voltage for each bit that is 0
        rise_time: str
            The rise time for the signal
        fall_time: str
            The fall time for the signal
        delay: str
            The delay before the code generation starts.
            The first voltage is given by the first bit in the code
    """
    def __init__(self, instance_name, design, codes, period, v_high, v_low=0, rise_time=1e-12, fall_time=1e-12, delay=None, declare=True, parent_cell=None):
        # Call super init
        super().__init__('v1', instance_name, design, library_name="digital_lib", parent_cell=parent_cell)

        # Add terminals and subcells
        self.add_terminal("n")
        for i, code in enumerate(codes):
            self.add_terminal(f'p_{i}')
            subcell = vdigcode(f'{instance_name}_{i}', design, code, period, v_high, v_low=v_low, rise_time=rise_time, fall_time=fall_time, delay=delay, parent_cell=self)
            subcell.quick_connect(['p', 'n'], [f'p_{i}', 'n'])







