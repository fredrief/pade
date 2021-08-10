from pade.utils import get_logger
import numpy as np
from navn_tb import navn_tb
from pade.analysis import Fast, Mc, Slow, Typical, dc
from pade.evaluation import Expression, Specification
from pade.test import Test
import time
logger = get_logger()

# Some global settings
DEBUG = False
CACHE = False
MC = False

# Create a list of corners to simulate
corners = [Typical()]

# Instantiate testbench
tstop = 30e-6

tb = navn_tb(vgs=0.3)

# Monte carlo options
mcoptions = {
    'numruns': 4,
    'seed': 6,
    'variations': 'all',
    'donominal': 'no',
    'sampling': 'lhs',
}
mcoptions = mcoptions if MC else None
# Instantiate analyses
analyses = []
analyses.append(dc(start=0, param='vds', stop=0.5, lin=100))
# Analyses names
dc_name = 'montecarlo_dc' if MC else 'dc'

# List of expressions to save
output_selections=['g', 'd', 'VDS:p']

# Create an expression for evaluating DC-gain
expr = [
    Expression('Id_max', lambda id: np.max(np.abs(id)), ['VDS:p'], dc_name, unit='A', spec=Specification('>', 0))
]

# Initialize test object
main = Test(
    logger=logger,
    design=tb,
    analyses=analyses,
    expressions=expr,
    corners=corners,
    output_selections=output_selections,
    debug=DEBUG,
    debug_currents=True,
    mcoptions=mcoptions,
    )

# Run simulation, print summary and store results in HTML-table
main.run(cache=CACHE)
res = main.evaluate()
logger.info(res)
main.to_html()
