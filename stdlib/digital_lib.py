from pade.schematic import Cell
from pade.utils import num2string

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

            

           
        


    