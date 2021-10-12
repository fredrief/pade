from pade.schematic import Cell
from pade.stdlib.analog_lib import vccs
from techlib.techlib import nch_slvt

class Gm(Cell):
    """ Ideal, fully differential transconductor """
    def __init__(self, instance_name, design, Gm, **kwargs):
        cell_name = "Gm"
        super().__init__(cell_name, instance_name, design, **kwargs)

        self.add_multiple_terminals(['in_p', 'in_n', 'out_p', 'out_n'])
        self.set_parameter('Gm', Gm)

        # Wire up
        Gm = vccs('Gm', design, Gm, parent_cell=self).quick_connect(
            ['out_n', 'out_p', 'in_p', 'in_n'],
            ['out_n', 'out_p', 'in_p', 'in_n'])
