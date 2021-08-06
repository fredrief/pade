from pade import ureg, info, display, warn, error, fatal
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
    def __init__(self, cell_name, simulations, mcoptions=None, at_remote=False, **kwargs):
        """
        Parameters:
            cell_name: str
                Name of testbench
            simulations: [str]
                List of simulation/corner runs to parse. The names in this list is assumed to be the names of
                the raw data directories, both local and remote.
        """
        # Parse config file
        config_file = kwargs['config_file'] if 'config_file' in kwargs else 'config/user_config.yaml'
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.local_info = config['local_info']
        self.cell_name = cell_name
        self.local_path = f"{self.local_info['local_project_root_dir']}/{self.cell_name}/{self.cell_name}_simulation_output"
        self.local_netlist_dir = f"{self.local_info['local_project_root_dir']}/{self.cell_name}/{self.cell_name}_netlists"

        # If MC analysis, add mcrun to simulation name
        self.simulations = []
        self.mcmode = False
        self.mccorner = None
        if not mcoptions is None:
            self.mcmode = True
            numruns = mcoptions['numruns']
            firstrun = mcoptions['firstrun'] if 'firstrun' in mcoptions else 1
            simulations = simulations.split(' ') if isinstance(simulations, str) else simulations
            if len(simulations) > 1:
                fatal('Can only run one corner in montecarlo mode')
            corner = simulations[0]
            self.mccorner = corner
            for run in range(firstrun, firstrun + numruns):
                self.simulations.append(f'{corner}({run})')
        else:
            self.simulations = simulations.split(' ') if isinstance(simulations, str) else simulations

        # Dictionary for holding signals
        # self.signals = {'simulation:analysis:name': Signal()}
        self.signals = {}
        # Remote stuff
        self.at_remote = at_remote
        if not at_remote:
            self.remote_info = config['remote_info']
            ssh = SSH_Utils(self.remote_info['server_address'])
            self.ssh = ssh
            self.remote_psf_dir = f"{self.remote_info['remote_raw_dir']}/{self.cell_name}_raw"

    def fetch_raw_data(self, new_runs=[], fetch_all=False):
        """
        Fetch raw data
        Parameters:
            new_runs: [str]
                List of simulation/corner runs that has changed since last simulation. In other words,
                only simulations in this list will be fetched and re-parsed. Other simulations will not be fetched,
                given that the raw data directory exist locally.
            fetch_all: bool
                Override new_runs, and fetch all simulations/corners

        """
        if self.mcmode:
            simulations_to_fetch = [self.mccorner]
        else:
            simulations_to_fetch = self.simulations
        for simulation in simulations_to_fetch:
            local_path =self.local_path
            simulation_raw_dir = to_path(local_path, simulation)
            if not simulation in new_runs and file_exist(simulation_raw_dir) and not fetch_all:
                display(info, f'Found cached raw data directory: {simulation_raw_dir}')
                continue
            remote_path = f"{to_path(self.remote_psf_dir, f'{simulation}')}"
            display(info, 'FETCHING RAW SIMULATION DATA')
            display('\t', f'From: {remote_path}')
            display('\t', f'To:   {simulation_raw_dir}')
            # Create path if it does not exist
            mkdir(local_path)
            # Remove old analysis files from folder if exist
            rm(ls(simulation_raw_dir))
            # Fetch all analysis of raw directory
            self.ssh.cp_from(remote_path, local_path)

    def parse(self, mcrun=None):
        """
        Parse psf file into traces

        Parameters:
            mcrun: int
                If running a montecarlo analysis, specify the run number. This will add to the parsed signal output
        """
        # Fetch psf raw dir if it does not exist
        local_raw_dir = self.local_path
        if not file_exist(self.local_path):
            self.fetch_raw_data()

        if not mcrun is None:
            simulations_to_parse = [self.mccorner]
        else:
            simulations_to_parse = self.simulations
        for simulation in simulations_to_parse:
            simulation_path = to_path(local_raw_dir, simulation)
            raw_files = ls(simulation_path)
            simulation = simulation_path.name
            # If MC analysis, add mcrun to simulation name
            if not mcrun is None:
                simulation += f'({mcrun})'

            for file in raw_files:
                filename = file.name
                # Only parse valid analysis files
                if not self.is_valid_analysis(filename):
                    continue
                analysis_name = filename.split('.')[0]
                display(info, f'PARSING PSF FILE: {simulation_path.name}/{filename}')
                # Parsing might fail
                try:
                    psf = PSF(file)
                except Exception as err:
                    # warn(f'Could not parse file {file}, error occurred: {err}')
                    continue
                for signal in psf.all_signals():
                    if isinstance(signal.ordinate, Quantity):
                        trace = np.array([signal.ordinate.real + 1j*signal.ordinate.imag])
                    else:
                        trace = signal.ordinate
                    unit = getattr(ureg, signal.units.replace('sqrt(Hz)', 'hertz**0.5')) if signal.units else None
                    q = ureg.Quantity(trace, unit)
                    s = Signal(trace, q.units, name=signal.name, analysis=analysis_name, simulation=simulation, sweep=False)
                    self.signals[f'{simulation}:{analysis_name}:{s.name}'] = s
                if psf.sweeps:
                    for sweep in psf.sweeps:
                        try:
                            unit = getattr(ureg, sweep.units)
                        except:
                            unit = ''
                        s = Signal(sweep.abscissa, unit, name=sweep.name, analysis=analysis_name, simulation=simulation, sweep=True)
                        self.signals[f'{simulation}:{analysis_name}:{s.name}'] = s

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


    def get_signal(self, name, analysis, simulation):
        identifier = f'{simulation}:{analysis}:{name}'
        if identifier in self.signals:
            return self.signals[identifier]
        else:
            raise RuntimeError(f'Signal does not exist: Name {name}, Analysis {analysis}, Simulation {simulation}')

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
