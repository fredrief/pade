from pade import ureg
from pade.signal import Signal
from pade.ssh_utils import SSH_Utils
from pade.utils import file_exist
from psf_utils import PSF, Quantity
from shlib import ls, to_path, mkdir, rm
from numbers import Number
import pandas as pd
import numpy as np
import subprocess
import os
import yaml

class PSFParser(object):
    """
    Helper class for parsing psfascii files
    """
    def __init__(self, logger, output_dir, sim_name, **kwargs):
        """
        """
        self.logger = logger
        self.output_dir = output_dir
        self.sim_name = sim_name
        # Dictionary for holding signals
        # self.signals = {'sim_name:analysis:name': Signal()}
        self.signals = {}

    def parse(self):
        """
        Parse psf file into traces

        Parameters:
            logger: Logger
                Logger object
            mcrun: int
                If running a montecarlo analysis, specify the run number. This will add to the parsed signal output
        """
        raw_files = ls(self.output_dir)

        for file in raw_files:
            filename = file.name
            # Only parse valid analysis files
            if not self.is_valid_analysis(filename):
                continue
            analysis_name = filename.split('.')[0]
            self.logger.info(f'PARSING PSF FILE: {self.sim_name}/{filename}')
            # Parsing might fail
            try:
                psf = PSF(file)
            except Exception as err:
                self.logger.warning(f'Could not parse file {file}, error occurred: {err}')
                continue
            for signal in psf.all_signals():
                if isinstance(signal.ordinate, Quantity):
                    trace = np.array([signal.ordinate.real + 1j*signal.ordinate.imag])
                else:
                    trace = signal.ordinate
                unit = getattr(ureg, signal.units.replace('sqrt(Hz)', 'hertz**0.5')) if signal.units else None
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
        valid_types = ['tran', 'ac', 'dc', 'info', 'stb', 'noise']
        # logFile etc..
        if len(filename.split('.')) < 2:
            res = False
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
            raise RuntimeError(f'Signal does not exist: Name {name}, Analysis {analysis}')

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
