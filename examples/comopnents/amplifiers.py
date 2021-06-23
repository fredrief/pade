"""
This file demonstrate how to declare a new component
"""

from schematic import Cell
from stdlib.analog_lib import vcvs

class amp(Cell):
    """
    Ideal amplifier
    Terminals: 'vdd', 'vss', 'vin', 'vip', 'vop', 'von'
    """
    def __init__(self, instance_name, design, gain=10e3, parent_cell=None):
        # Call super init
        cell_name = 'amp'
        super().__init__(cell_name, instance_name, design, parent_cell=parent_cell)

        # Add terminals. These will be stored as class attributes
        self.add_terminal("vdd")
        self.add_terminal("vss")
        # Multiple terminals can also be added at once using
        self.add_multiple_terminals(['vin', 'vip', 'vop', 'von'])

        # Instantiate internal cells of the amplifier. A simple voltage-controlled voltage source in this case
        A = vcvs('A', design, gain, parent_cell=self)
        # Connect its terminals to internal nets by calling cell.connect()
        A.connect('out_p', 'vop')
        A.connect('out_n', 'von')
        # Multiple terminals can also be connected at once using
        A.quick_connect(['in_p', 'in_n'],['vip',  'vin'])
