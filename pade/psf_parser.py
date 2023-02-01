from pade import *
from pade.signal import Signal
from pade.utils import get_unit
from psf_utils import PSF, Quantity
from shlib import ls, to_path, mkdir, rm
from numbers import Number
import pandas as pd
import numpy as np
import re

class PSFParser(object):
    """
    Helper class for parsing psfascii files
    """
    def __init__(self, output_dir, sim_name, **kwargs):
        """
        """
        self.output_dir = output_dir
        self.sim_name = sim_name
        # Dictionary for holding signals
        # self.signals = {'sim_name:analysis:name': Signal()}
        self.signals = {}

    def parse(self):
        """
        Parse psf file into traces

        Parameters:
            mcrun: int
                If running a montecarlo analysis, specify the run number. This will add to the parsed signal output
            sim_name:
                unique identifier for simulation
        """
        raw_files = ls(self.output_dir)

        for file in raw_files:
            filename = file.name
            # Only parse valid analysis files
            if not self.is_valid_analysis(filename):
                continue
            analysis_name = filename.split('.')[0]
            display(f'PARSING PSF FILE: {filename} ({self.sim_name})')

            # The parsing of DcOpInfo will chrash if the file contains "inf"
            # Modify the file to replace inf by nan
            if 'dcOpInfo' in filename:
                tmp = ""
                with open(file, 'r') as f:
                    for line in f.readlines():
                        tmp += line.replace('inf', 'nan')

                with open(file, 'w') as f:
                    f.writelines(tmp)

            # Parsing might fail
            try:
                psf = PSF(file)
            except Exception as err:
                warn(f'Could not parse file {file}, error occurred: {err}')
                continue
            for signal in psf.all_signals():
                if isinstance(signal.ordinate, Quantity):
                    trace = np.array([signal.ordinate.real + 1j*signal.ordinate.imag])
                else:
                    trace = signal.ordinate

                unit = get_unit(signal)
                q = ureg.Quantity(trace, unit)
                s = Signal(trace, q.units, name=signal.name, analysis=analysis_name, simulation=self.sim_name, sweep=False)
                self.signals[f'{self.sim_name}:{analysis_name}:{s.name}'] = s
            if psf.sweeps:
                for sweep in psf.sweeps:
                    try:
                        unit = getattr(ureg, sweep.units)
                    except:
                        unit = ''
                    s = Signal(sweep.abscissa, unit, name=sweep.name, analysis=analysis_name, simulation=self.sim_name, sweep=True)
                    self.signals[f'{self.sim_name}:{analysis_name}:{s.name}'] = s

    def is_valid_analysis(self, filename):
        """
        Check if analysis (filename) is a valid result file
        """
        res = True
        valid_types = ['tran', 'ac', 'dc', 'info', 'stb', 'noise', 'pss', 'pnoise']
        # logFile etc..
        if len(filename.split('.')) < 2:
            res = False
        elif 'margin.stb' in filename:
            res = False # stb.margin not supported
        else:
            t = filename.split('.')[-1]
            res = t in valid_types
        return res

    def get_signals_from_same_sim(self, name_list, analysis):
        signals = []
        for name in name_list:
            signals.append(self.get_signal(name, analysis))
        return signals


    def get_signal(self, name, analysis):
        identifier = f'{self.sim_name}:{analysis}:{name}'
        if identifier in self.signals:
            return self.signals[identifier]
        else:
            warn(f'Signal {name} from analysis {analysis} not available. Returning NaN')
            return np.nan

    def get_signal_list(self, sig_name_regex, analysis):
        identifier = f'{self.sim_name}:{analysis}:{sig_name_regex}'
        sig_list = []
        for name, sig in self.signals.items():
            if re.match(identifier, name):
                sig_list.append(sig)
        return sig_list


    def add_signal(self, signal):
        if isinstance(signal, Signal):
            identifier = f'{signal.simulation}:{signal.analysis}:{signal.name}'
            if identifier in self.signals:
                error(f'Signal {identifier} not added because it already exist')
            else:
                self.signals[identifier] = signal
                info(f'Added signal {identifier}')
        else:
            error(f'Signal not added because it is not a Signal object')

    def get_dataframe(self, analysis):
        """
        Return all data from given analysis as dataframe
        """
        df_dict = {}
        for identifier in self.signals:
            if analysis in identifier:
                df_dict[identifier.replace(analysis + ':', '')] = self.signals[identifier].trace
        return pd.DataFrame(df_dict)

    def get_sweep(self, analysis):
        for key, signal in self.signals.items():
            if signal.analysis == analysis and signal.sweep:
                return signal
