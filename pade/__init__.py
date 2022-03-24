# Units
from pint import UnitRegistry
ureg = UnitRegistry(case_sensitive=True)
Q_ = ureg.Quantity

# Import Inform for all modules
from inform import warn, fatal, error, display, Color
green = Color('green')
info = green('Info:')

