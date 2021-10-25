from pade.analysis import Analysis, Corner, Typical
from pade.ssh_utils import SSH_Utils
from shlib import mkdir, ls, to_path, rm
from pade.utils import get_kwarg, num2string, cat, writef
import re
import numpy as np
import logging
import yaml
import subprocess
from tqdm import tqdm

class Spectre(object):
    """
    For spectre simulations on remote server
    """
    def __init__(self, netlist_dir, output_dir, log_dir, logger, design, analyses, sim_name, output_selections=[], command_options=['-format', 'psfascii', '++aps', '+mt', '-log'], **kwargs):

        # Parse config file
        config_file = get_kwarg(kwargs, 'config_file','config/user_config.yaml')
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.local_info = config['local_info']
        spectre_setup = get_kwarg(kwargs, 'spectre_setup','config/spectre_setup.yaml')
        with open(spectre_setup, 'r') as f:
            self.spectre_options = yaml.safe_load(f)

        # Set command options that will append to the spectre command
        self.command_options = command_options
        self.output_selections = output_selections
        # paths and names
        self.design = design # Netlist/design cell name
        self.netlist_dir = netlist_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        # Initialization
        self.logger = logger
        self.analyses = analyses # []
        self.design = design
        self.montecarlo_settings = None
        self.netlist_string = None
        self.lines_to_append_netlist = []

        self.global_nets = get_kwarg(kwargs, 'global_nets', '0')
        # corner:
        self.corner = get_kwarg(kwargs, 'corner', Typical())
        self.sim_name=sim_name
        self.tqdm_pos = get_kwarg(kwargs, 'tqdm_pos', 0)

    def _get_analyses_string(self):
        """
        Return the analyses' contribution to the netlist
        """
        # analyses
        astr = ""
        astr += "\n"
        if self.montecarlo_settings:
            # MC analyses
            astr += 'montecarlo montecarlo numruns=1 '
            for param, value in self.montecarlo_settings.items():
                # An attempt to set a higher number of runs will be ignored
                if not param == 'numruns':
                    astr += f'{param}={num2string(value)} '
            astr += " { \n"
            for a in self.analyses:
                # Only include analyes inside mc brackets, not options and info
                if not a.type in ['options', 'info']:
                    astr += a.get_netlist_string() + "\n"
            astr += "} \n"
            for a in self.analyses:
                # Append options and info statements
                if a.type in ['options', 'info']:
                    astr += a.get_netlist_string() + "\n"
        else:
            for a in self.analyses:
                astr += a.get_netlist_string() + "\n"
            astr += "\n"
        return astr

    def set_mc_settings(self, settings):
        """
        Set montecarlo settings
        Parameters:
            settings: dict
                MC settings
        """
        self.montecarlo_settings = settings

    def set_mc_param(self, param, value,):
        """
        Set parameter of the mc analyses
        """
        if self.montecarlo_settings:
            self.montecarlo_settings[param] = value
        else:
            self.logger.warn('Cannot set parameter because montecarlo settings does not exist')

    def init_netlist(self):
        """
        Initialize netlist
        [MODELFILE] will be replaced by model file in simulation
        """
        self.netlist_string = "// Generated for: spectre\n"
        self.netlist_string += "// Design cell name: {}\n".format(self.design.cell_name)
        self.netlist_string += 'simulator lang=spectre\n'
        self.netlist_string += f"global {self.global_nets}\n"
        self.netlist_string += f"include \"{self.local_info['spectre_model_path']}\" section=[MODELFILE]\n"

        # Schematic
        self.netlist_string += self.design.get_netlist_string()

        # Analyses
        self.netlist_string += self._get_analyses_string()

        # Initial conditions
        if self.design.ic is not None:
            self.netlist_string += 'ic '
            ic_dict = self.design.ic
            for net, value in ic_dict.items():
                self.netlist_string += f'{net}={value} '
            self.netlist_string += '\n'

        # Spectre settings
        for name in self.spectre_options:
            statement = self.spectre_options[name]['statement']
            parameters = self.spectre_options[name]['parameters']
            self.netlist_string += name + ' ' + statement
            for param_name in parameters:
                self.netlist_string += f" {param_name}={parameters[param_name]}"
            self.netlist_string += '\n'
        # Save outputs
        self.netlist_string += "save "
        for signal in self.output_selections:
            self.netlist_string += f"{signal} "
        self.netlist_string += "\n"
        # Extra lines
        for line in self.lines_to_append_netlist:
            self.netlist_string += line + '\n'

    def append_netlist_line(self, string):
        """
        Append line to netlist string
        This function must be called before netlist initialization
        """
        self.lines_to_append_netlist.append(string)

    def _generate_netlist_string(self, corner):
        """
        Adds corner-specific options to the netlist template
        Parameters:
            corner: Corner
        """
        # Always re-initialize netlist string
        self.init_netlist()
        # Append temperature info
        self.netlist_string += f'TempOp options temp={corner.temp}\n'
        return self.netlist_string.replace('[MODELFILE]', corner.model_file)

    def write_netlist(self, corner):
        """
        Write netlist string to files
        One Netlist file per corner
        """
        netlist_path = to_path(self.netlist_dir, corner.name + '.txt')
        writef(self._generate_netlist_string(corner), netlist_path)


    def run(self, cache=True):
        """ Run simulation """
        corner = self.corner
        netlist_filename = f'{corner.name}.txt'
        netlist_path = to_path(self.netlist_dir, netlist_filename)
        simulation_raw_dir = self.output_dir
        # Check cache
        if cache:
            prev_netlist = cat(netlist_path)
            new_netlist = self._generate_netlist_string(corner)
            if (new_netlist == prev_netlist):
                self.logger.info(f'Netlist unchanged, skip simulation. Corner: {corner}')
                return

        self.logger.info('Writing netlist')
        # Write netlist to file
        self.write_netlist(corner)

        self.logger.info('Starting spectre simulation')
        # Spectre commands
        popen_cmd = f"source {self.local_info['spectre_setup_script']} ; " + \
            f"spectre {netlist_path} " + \
            f"-raw {simulation_raw_dir} "
        for cmd in self.command_options:
            popen_cmd += f"{cmd} "

        # Run sim
        self.logger.info(f'Simulating: {corner.name}')
        log_file = to_path(self.log_dir, 'spectre_sim.log')
        # Progress bar
        self.tq = tqdm(total=100, desc=f'{self.sim_name}', leave=False, position=self.tqdm_pos)
        with open(log_file, 'wb') as f:
            process = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            p0 = 0
            for line in iter(process.stdout.readline, b''):
                f.write(line)
                line_s = line.decode('ascii')
                # Only write time info to console
                progress_line = re.search('\(.* %\)', line_s)
                if progress_line:
                    progress = float(line_s.split(' %')[0].split('(')[1])
                    analyses = line_s.split(':')[0].strip()
                    if not analyses in ['ac', 'tran', 'montecarlo_tran', 'noise', 'stb', 'dc']:
                        continue
                    self.tq.update(progress-p0)
                    p0 = progress
                    # Close tq
            self.tq.close()
            status_list = line_s.split(' ')
            err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
            errors = int(status_list[err_idx])
            if errors:
                raise SpectreError(log_file)

        self.logger.info("SPECTRE SIMULATION COMPLETE")
        self.logger.info(f"Raw data directory: {simulation_raw_dir}")


class SpectreError(Exception):
    """
    Exception raised when spectre has error
    """
    def __init__(self, log_file):
        self.message = f'Errors occurred during spectre simulation. See {log_file} for details'
        super().__init__(self.message)

    def __str__(self):
        return self.message
