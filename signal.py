from pade.utils import num2string
from pade import ureg, Q_, info, display, warn, error, fatal
from shlib import ls, to_path, mkdir
from scipy.interpolate import interp1d
import numpy as np
import numpy.lib.mixins
from numbers import Number

HANDLED_FUNCTIONS = {}
def implements(np_function):
   "Register an __array_function__ implementation for Signal objects."
   def decorator(func):
       HANDLED_FUNCTIONS[np_function] = func
       return func
   return decorator

@implements(np.imag)
def imag(sig):
    "Implementation of np.imag for Signal objects"
    return Signal(np.imag(sig.trace), sig.unit, f'I({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)

@implements(np.real)
def real(sig):
    "Implementation of np.real for Signal objects"
    return Signal(np.real(sig.trace), sig.unit, f'R({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)

@implements(np.max)
def max(sig):
    "Implementation of np.max for Signal objects"
    return Signal(np.max(sig.trace), sig.unit, f'R({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)

@implements(np.min)
def min(sig):
    "Implementation of np.min for Signal objects"
    return Signal(np.min(sig.trace), sig.unit, f'R({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)

@implements(np.mean)
def mean(sig):
    "Implementation of np.mean for Signal objects"
    return Signal(np.mean(sig.trace), sig.unit, f'R({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)

@implements(np.angle)
def angle(sig):
    "Implementation of np.angle for Signal objects"
    return Signal(np.angle(sig.trace), sig.unit, f'/_({sig.name})', analysis=sig.analysis, simulation=sig.simulation, sweep=sig.sweep)


class Signal(numpy.lib.mixins.NDArrayOperatorsMixin):
    """
        Signal class
        Parameters:
            trace: Array like
                Array or scalar holding the signal value
            unit: str or Unit
                The unit
            name: str
                Signal name
            analysis: str
                Name of the simulation analysis from which the signal is generated
            simulation: str
                Name of the simulation (often the corner) from which the signal is generated
            sweep: bool
                Whether or not the signal is a sweep variable like frequency or time
            passed_spec: bool
                This might be set when the value of the signal is compared to a specification
    """
    def __init__(self, trace, unit, name=None, analysis=None, simulation=None, sweep=None, passed_spec=None):
        self.name = name
        try:
            if len(trace) == 1:
                self.trace = trace[0]
            else:
                self.trace = trace
        except:
            self.trace = trace
        if isinstance(unit, str):
            unit = Q_(1, unit).units
        self.unit = unit
        self.analysis = analysis
        self.simulation = simulation
        self.sweep = sweep # bool
        self.passed_spec = passed_spec

    def __getitem__(self, item):
        return self.__class__(self.trace[item], self.unit, f'{self.name}[{item}]',
         analysis=self.analysis, simulation=self.simulation, sweep=self.sweep)

    def __repr__(self):
        return "{:.2f~P}".format(self.to_quantity())

    def __len__(self):
        return len(self.trace)

    def __format__(self, format_spec):
        return self.to_quantity().__format__(format_spec)

    def __array__(self, *args):
        # Dont know why I must accept multiple arguments
        return np.array(self.trace)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if method == '__call__':
            quantities = [] # Pint Quantities, used for handling units
            traces = []
            namestr = ''
            analysis = None
            simulation = None
            sweep = None
            for input in inputs:
                if isinstance(input, Number) or isinstance(input, list):
                    input = float(input)
                    quantities.append(input)
                    traces.append(input)
                    namestr += num2string(input, decimals=1)
                elif isinstance(input, self.__class__):
                    quantities.append(input.trace * input.unit)
                    traces.append(input.trace)
                    namestr += input.name if input.name else ''
                    analysis = input.analysis if input.analysis else None
                    simulation = input.simulation if input.simulation else None
                    sweep = input.sweep if input.sweep else None
                else:
                    return NotImplemented
            res = ufunc(*traces, **kwargs)
            try:
                unit = ufunc(*quantities, **kwargs).units
            except:
                unit = ''
            return self.__class__(res, unit,
                                    namestr, analysis=analysis, simulation=simulation, sweep=sweep)
        else:
            return NotImplemented

    def __array_function__(self, func, types, args, kwargs):
        if func not in HANDLED_FUNCTIONS:
            return NotImplemented
        if not all(issubclass(t, self.__class__) for t in types):
            return NotImplemented
        return HANDLED_FUNCTIONS[func](*args, **kwargs)

    def set_name(self, name):
        self.name = name

    def set_unit(self, unit):
        """
            Override unit
        """
        self.unit = ureg.Quantity(self.trace, unit).units

    def get_unit(self):
        return self.unit

    def set_simulation(self, simulation):
        """
            Override simulation
        """
        self.simulation = simulation

    def at(self, x_sig, x_val, name=None):
        """
            Interpolate self as function of x_sig, at x_val
        """
        name = name if name else f'{self.name}[{x_val}]'
        x_sig = x_sig.trace if isinstance(x_sig, Signal) else x_sig

        try:
            trace = interp1d(x_sig, self.trace)(x_val)
        except ValueError:
            trace = np.nan
        try:
            trace = float(trace)
        except:
            pass
        return Signal(trace, self.unit, name, analysis=self.analysis, simulation=self.simulation, sweep=self.sweep)

    def iat(self, x_val):
        """
            Return index corresponding to value of self that is closest to xval
        """
        idx = (np.abs(self.trace - x_val)).argmin()
        return idx

    def grad(self, x, name=None):
        """
            Return gradient of self wrt x
        """
        name = name if name else f"d{self.name}/d{x.name}"
        trace = np.gradient(self.trace, x.trace)
        return Signal(trace, self.unit, name, analysis=self.analysis, simulation=self.simulation, sweep=self.sweep)

    def set_status(self, status):
        """
        Specify if signal passed spec
        """
        self.passed_spec = status

    def get_status(self):
        return self.passed_spec

    def to_quantity(self):
        """
            Returns a Pint Quantity representation of self
        """
        q = ureg.Quantity(self.trace, self.unit)
        # Try to convert to derived units
        derived_units = ['W', 'mho', 'F']
        for u in derived_units:
            try:
                q = q.to(u)
            except:
                pass
        return q.to_compact()
