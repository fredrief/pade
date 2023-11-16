# Units
from pint import UnitRegistry
ureg = UnitRegistry(case_sensitive=True)
Q_ = ureg.Quantity

# Import Inform for all modules
from inform import Inform, warn, fatal, error, display, comment, log, output, InformantFactory, debug
succeed = InformantFactory(message_color='green')
informer = Inform()
