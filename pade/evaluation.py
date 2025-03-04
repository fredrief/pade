from pade.signal import Signal
from pade import *
import numpy as np
import pandas as pd
from shlib import to_path, mkdir
class Specification:
    """
    Helper class for handling specifications
    Currently only supporting scalar expressions

    Parameters:
        log_func: str
            A string reffering to a logical function, e.g. "<"
            For a < signal < b, use log_func="< <"
        values: float
            Specification values
            Numbers of values must equal number of logical operators

    """
    def __init__(self, log_func, *values):

        if isinstance(log_func, str):
            log_func = log_func.strip()
            if not len(values) == len(log_func.split(' ')):
                fatal('Number of operators must equal number of values')
            try:
                if len(log_func.split(' ')) == 1:
                    log_func = eval(f'lambda x,y: x {log_func} y')
                elif len(log_func.split(' ')) == 2:
                    f1 = log_func.split(' ')[0]
                    f2 = log_func.split(' ')[1]
                    log_func = eval(f'lambda x,y,z: y {f1} x {f2} z')
            except SyntaxError:
                fatal(f'Invalid logic function: {log_func}')
        else:
            fatal(f'Logic function: {log_func} is not a string')
        self.log_func = log_func
        self.values = values

    def evaluate(self, signal):
        return self.log_func(signal.trace, *self.values)


class Expression:
    """
    Expression evaluated on simulation results
    Parameters
        name: str
            Expression name
        func: callable
            Function to evaluate on signals
        signal_names: [str]
            List of names of signals to evaluate.
            Currently this only support signals that exists in netlist
        analysis_name: 'str'
            Name of the analysis to evaluate the signals from
        spec: Specification
            Specification object holding the specifications for this expression

        Keyword arguments:
            unit: str
                Specify unit to override the automatically calculated unit by Pint.
    """
    def __init__(self, name, func, signal_names, analysis_name, func_kwargs={}, spec=None, **kwargs):
        self.name = name
        self.func = func
        self.func_kwargs = func_kwargs
        self.signal_names = signal_names
        self.analysis_name = analysis_name
        self.spec = spec
        # Keyword arguments
        unit = kwargs['unit'] if 'unit' in kwargs else None
        if isinstance(unit, str):
            unit = Q_(1, unit).units
        self.unit = unit


    def evaluate(self, signals):
        """
        Evaluate expression. The signals must be provided as a list of Signal object.
        Parameters:
            signals: [Signal]
                List of Signal objects to evaluate
        Returns:
            A new Signal object with evaluated result
        """
        # The result is assumed to be a Signal object
        result = self.func(*signals, **self.func_kwargs)
        # Try Signal-specific things.
        try:
            # We give the signal the name of the expression
            result.set_name(self.name)
            # Override unit if specified
            if self.unit:
                result.set_unit(self.unit)
            if self.spec:
                result.set_status(self.spec.evaluate(result))
        except:
            pass
        # Return result as Signal
        return result


class Evaluation:
    """
        Helper class for evaluating simulation results
    """
    def __init__(self, parser, expressions, **kwargs):
        """
        """
        self.parser = parser
        self.expressions = expressions
        # After evaluation
        self.results = None
        self.summary = None
        self.summary_statistics = {'Min': np.min, 'Max': np.max, 'Mean': np.mean, 'Std': np.std,
                                    'Yield': lambda arr: sum(arr)/len(arr) }
        # Kwargs
        self.html_dir = kwargs['html_dir'] if 'html_dir' in kwargs else None
        self.latex_dir = kwargs['latex_dir'] if 'latex_dir' in kwargs else None


    def evaluate(self):
        """
        Do evaluation
        """
        expressions = self.expressions
        sim = self.parser.sim_name # This is typically the corner names
        # Declear empty results dict
        results_dict = {'Parameter': []}
        results_dict[sim] = []
        for e in expressions:
            results_dict['Parameter'].append(e.name)
            signal_list = []
            for signal_name in e.signal_names:
                try:
                    signal_list.append(self.parser.get_signal(signal_name, e.analysis_name))
                except:
                    # If the signal is not in the parser, try to find it in previously evaluated expressions
                    sidx = [i for i in range(len(results_dict[sim])) if results_dict[sim][i].name == signal_name]
                    signal_list.append(results_dict[sim][sidx[0]])
            results_dict[sim].append(e.evaluate(signal_list))
        self.results = pd.DataFrame.from_dict(results_dict)
        self.results = self.results.set_index('Parameter')


    def create_summary(self):
        """
        Create statistical summary of results.
        For each expression, max, min, mean, std and yield will be displayed
        """
        if self.results is None:
            self.evaluate()
        res = self.results
        # Statistics to evaluate. Dictionary of name and callable
        statistics = self.summary_statistics
        # Declear empty summary dict
        summary_dict = {'Parameter': []}
        for stat in statistics:
            summary_dict[stat] = []
        for e in self.expressions:
            summary_dict['Parameter'].append(e.name)
            # Result values
            res_val_arr = res.loc[e.name].apply(np.asarray).to_numpy()
            # Result passed (if results are Signal objects)
            try:
                res_stat_arr = res.loc[e.name].apply(lambda s: s.get_status()).to_numpy()
                # Unit
                unit_arr = res.loc[e.name].apply(lambda s: s.get_unit())
                unit = e.unit if e.unit is not None else unit_arr[0]
            except:
                unit = None
            for name, func in statistics.items():
                if not name=='Yield':
                    eval_res = Signal(func(res_val_arr), unit, name=e.name, analysis=e.analysis_name)
                else:
                    # This will only work if results are Signal objects
                    try:
                        # Convert None to np.nan to avoid yield function from crashing
                        res_stat_arr = [np.nan if res_stat_arr[i] is None else res_stat_arr[i] for i in range(len(res_stat_arr))]
                        eval_res = Signal(func(res_stat_arr), '', name=e.name, analysis=e.analysis_name)
                    except:
                        pass

                summary_dict[name].append(eval_res)
        self.summary = pd.DataFrame(summary_dict)
