from pade.analysis import Analysis, Corner, Typical
from pade.ssh_utils import SSH_Utils
from shlib import mkdir, ls, to_path, rm
from pade.utils import num2string, cat, writef
import re
import numpy as np
import logging
import daemon
from daemon import pidfile
import yaml
import subprocess

class Spectre(object):
    """
    For spectre simulations on remote server
    """
    def __init__(self, logger, design, analysis, output_selections=[], command_options=['-format', 'psfascii', '++aps', '+mt', '-log'], at_remote=False, **kwargs):
        """
        Parameters:
            logger: Logger
                Logger object
            design: Design
                Design/testbench to simulate
            analysis: [Analysis]
                List of analysis to simulate
            output_selections: [str]
                List of traces to save
            command_options: [str]
                options to append to the spectre command line call
            at_remote: bool
                Specify if the Spectre object is instantiated at the remote server or not.

        Keyword arguments:
            config_file:
                Path for alternative configuration file. (default pade/config/user_config.yaml)
            spectre_setup:
               Path for alternative spectre setup file. (default pade/config/spectre_setup.yaml)
            global_nets:
                Global nets used in spectre netlist (default: 0)
            corners: [Corner]
                List of Corners to simulate. Default: Typical
                The corner name will also give the name to the resulting raw data directories

        """
        # Parse config file
        config_file = kwargs['config_file'] if 'config_file' in kwargs else 'config/user_config.yaml'
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.local_info = config['local_info']
        spectre_setup = kwargs['spectre_setup'] if 'spectre_setup' in kwargs else 'config/spectre_setup.yaml'
        with open(spectre_setup, 'r') as f:
            self.spectre_options = yaml.safe_load(f)

        # Set command options that will append to the spectre command
        self.command_options = command_options
        self.output_selections = output_selections
        # paths and names
        self.cell_name = design.cell_name # Netlist/design cell name
        self.project_root_dir = f"{self.local_info['local_project_root_dir']}/{self.cell_name}"
        self.local_netlist_dir = f"{self.project_root_dir}/{self.cell_name}_netlists"

        # Initialization
        self.logger = logger
        self.analysis = analysis # []
        self.design = design
        self.montecarlo_settings = None
        self.netlist_string = None
        self.lines_to_append_netlist = []

        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'
        # Corners:
        self.corners = kwargs['corners'] if 'corners' in kwargs else [Typical()]

    def _get_analysis_string(self):
        """
        Return the analyses' contribution to the netlist
        """
        # Analysis
        astr = ""
        astr += "\n"
        if self.montecarlo_settings:
            # If Montecarlo, only one corner is allowed
            if len(self.corners) > 1:
                self.logger.error('I don\'t want to run montecarlo with multiple corners, too much output will be generated. Please select only one corner in combination with montecarlo analysis.')
                quit()
            # MC analysis
            astr += 'montecarlo montecarlo numruns=1 '
            for param, value in self.montecarlo_settings.items():
                # An attempt to set a higher number of runs will be ignored
                if not param == 'numruns':
                    astr += f'{param}={num2string(value)} '
            astr += " { \n"
            for a in self.analysis:
                # Only include analyes inside mc brackets, not options and info
                if not a.type in ['options', 'info']:
                    astr += a.get_netlist_string() + "\n"
            astr += "} \n"
            for a in self.analysis:
                # Append options and info statements
                if a.type in ['options', 'info']:
                    astr += a.get_netlist_string() + "\n"
        else:
            for a in self.analysis:
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
        Set parameter of the mc analysis
        """
        if self.montecarlo_settings:
            self.montecarlo_settings[param] = value
        else:
            warn('Cannot set parameter because montecarlo settings does not exist')

    def init_netlist(self):
        """
        Initialize netlist
        [MODELFILE] will be replaced by model file in simulation
        """
        self.netlist_string = "// Generated for: spectre\n"
        self.netlist_string += "// Design cell name: {}\n".format(self.cell_name)
        self.netlist_string += 'simulator lang=spectre\n'
        self.netlist_string += f"global {self.global_nets}\n"
        self.netlist_string += "include \"$SPECTRE_MODEL_PATH/design_wrapper.lib.scs\" section=[MODELFILE]\n"

        # Schematic
        self.netlist_string += self.design.get_netlist_string()

        # Analyses
        self.netlist_string += self._get_analysis_string()

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
        local_netlist_path = to_path(self.local_netlist_dir, corner.name + '.txt')
        writef(self._generate_netlist_string(corner), local_netlist_path)


    def run(self, cache=True, as_daemon=False):
        """ Run simulation """

        # Set first MC run
        mcrun = ''
        if self.montecarlo_settings is not None:
            mcrun += f"({self.montecarlo_settings['firstrun']})"

        self.logger.info("START SPECTRE SIMULATION")
        self.logger.info(f"Corners: {self.corners}{mcrun}")
        new_corner_runs = []

        for corner in self.corners:
            netlist_filename = f'{corner.name}.txt'
            local_netlist_path = to_path(self.local_netlist_dir, netlist_filename)
            simulation_raw_dir = to_path(self.project_root_dir, f"{self.cell_name}_simulation_output", corner.name )
            # Check cache
            if cache:
                prev_netlist = cat(local_netlist_path)
                new_netlist = self._generate_netlist_string(corner)
                if (new_netlist == prev_netlist):
                    self.logger.info(f'Netlist unchanged, skip simulation. Corner: {corner}')
                    continue

            # Write netlist to file
            new_corner_runs.append(corner.name)
            self.write_netlist(corner)

            # Spectre commands
            popen_cmd = f"source {self.local_info['spectre_setup_script']} ; " + \
                f"spectre {local_netlist_path} " + \
                f"-raw {simulation_raw_dir} "
            for cmd in self.command_options:
                popen_cmd += f"{cmd} "

            # Run sim
            self.logger.info(f'Simulating: {corner.name}')
            log_file =f"{self.project_root_dir}/{self.cell_name}_logs/spectre_sim.log"
            with open(log_file, 'wb') as f:
                process = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, shell=True)
                for line in iter(process.stdout.readline, b''):
                    f.write(line)
                    line_s = line.decode('ascii')
                    # Only write time info to console
                    progress_line = re.search('\(.* %\)', line_s)
                    if progress_line:
                        progress = line_s.split(')')[0].split('(')[1]
                        analysis = line_s.split(':')[0].strip()
                        if not analysis in ['ac', 'tran', 'noise', 'stb', 'dc']:
                            continue
                        print(f'{analysis}: {progress} \r', end="", flush=True)
                print('')
                status_list = line_s.split(' ')
                err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
                errors = int(status_list[err_idx])
                if errors:
                    self.logger.error(f'Errors occurred during spectre simulation. See {log_file} for details')
                    quit()

        self.logger.info("SPECTRE SIMULATION COMPLETE")
        self.logger.info(f"Raw data directory: {simulation_raw_dir}")
        return new_corner_runs
