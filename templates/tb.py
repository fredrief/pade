from pade.schematic import Design
from pade.stdlib.analog_lib import vdc
from techlib.techlib import nch_slvt
from navn_components import *

class navn_tb(Design):

    def __init__(self, **kwargs):
        cell_name = "navn"
        super().__init__(cell_name, parameters={'vds': 0.3}, **kwargs)
        self.vgs = 0.3 if not 'vgs' in kwargs else kwargs['vgs']

        # Wire up
        vgs = vdc('VGS', self, self.vgs).quick_connect(['p', 'n'], ['g', '0'])
        vds = vdc('VDS', self, 'vds').quick_connect(['p', 'n'], ['d', '0'])
        mn = nch_slvt('MN', self).quick_connect(['d', 'g', 's', 'b'], ['d', 'g', '0', '0'])
