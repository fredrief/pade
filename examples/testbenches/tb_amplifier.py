"""
This file demonstrate how to declare a new testbench
"""
from schematic import Design
from examples.comopnents.amplifiers import amp
from stdlib.analog_lib import vdc, vsin, res

class tb_amplifier(Design):
    """
    Amplifier testbench.
    """
    # Declare the class constructor
    # It is convenient to allow default values to be overwritten by optional keyword arguments
    def __init__(self, cell_name='tb_amplifier', **kwargs):

        self.vdd = 0.8 if not 'vdd' in kwargs else kwargs['vdd']
        self.R1 = 10e-15
        self.R2 = 100e-15
        self.RL = 10e-15
        self.vi = 10e-3
        self.fi = 5e6
        super().__init__(cell_name)

    # The wire_up() method is called by the super constructor. A bit confusing, will probably change this.
    # Instantiate supply, stimuli, load and DUT inside this method.
    def wire_up(self):
        # SUPPLY
        vsupply = vdc('VDD', self, self.vdd).quick_connect(['p', 'n'], ['vdd', '0'])

        # STIMULI
        vin = vsin('VIN', self, 0, self.vi, self.fi).quick_connect(['p', 'n'], ['vi', '0'])

        # DUT
        ammplifier = amp('A0', self, gain=1000).quick_connect(
            ['vdd', 'vss',  'vin',  'vip',  'vop',  'von'],
            ['vdd', '0',    '0',    'vx',   'vo',   '0'] )
        # Inverting amplifier with resistive feedback
        r1 = res('R1', self, self.R1).quick_connect(['p', 'n'], ['vi', 'vx'])
        r2 = res('R2', self, self.R2).quick_connect(['p', 'n'], ['vx', 'vo'])

        # LOAD
        rl = res('RL', self, self.RL).quick_connect(['p', 'n'], ['vo', '0'])

