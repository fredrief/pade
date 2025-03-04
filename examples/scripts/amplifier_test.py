"""
Demo script for analysis of a simple amplifier.

This example script is for illustration purpose only. The script could not be run directly, as several user-specific configurations is required for the simulator etc.
"""

from analysis import Corner, Typical, dcOpInfo, tran, dc, ac
from test import Test
from evaluation import Expression, Specification
from examples.testbenches.tb_amplifier import tb_amplifier
import numpy as np

# Some global settings
DEBUG = False
CACHE = True

# Cell name and output directory for simulation results
cell_name = 'tb_gm_ac'
html_dir =  f"/path/to/results/directory/{cell_name}"

# Create a list of corners to simulate
corners = [Typical(), Corner('fs_pre', name='FS_T27C'), Corner('sf_pre', name='SF_T27C'), Corner('ff_pre', temp=50, name='FF_T50C'), Corner('ff_pre', temp=10, name='FF_T10C'), Corner('ss_pre', temp=10, name='SS_T10C'), Corner('ss_pre', temp=50, name='SS_T50C')]

# Instantiate testbench
tstop = 30e-6
tb = tb_amplifier(cell_name=cell_name)


# Instantiate analyses
analyses = []
analyses.append(dc())
if DEBUG:
        analyses.append(dcOpInfo())
analyses.append(ac(parameters={'save': 'selected', 'log': '200', 'start': '1K'}))
analyses.append(tran(parameters={'stop': tstop, 'save': 'selected',}))


# List of expressions to save
output_selections=['vi', 'vo']

# Create an expression for evaluating DC-gain
A0 = Expression('A0', lambda vo, vi: np.max(np.abs(vo/vi)), ['outp', 'vi'], 'ac', unit='V/V', spec=Specification('>', 9.5))

# Initialize test object
main = Test(
        design=tb,
        analyses=analyses,
        expressions=[A0],
        html_dir=html_dir,
        corners=corners,
        output_selections=output_selections,
        at_remote=False,
        debug=DEBUG,
        )

# Run simulation, print summary and store results in HTML-table
main.run(cache=CACHE)
res = main.evaluate()
print(res)
main.to_html()
