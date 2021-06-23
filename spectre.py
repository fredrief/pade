from pade.analysis import Analysis, Corner, Typical
from pade.ssh_utils import SSH_Utils
from shlib import mkdir, ls, to_path, rm
from pade import info, display, warn, error, fatal
from pade.utils import num2string
import subprocess
import sys
import os
import re
import numpy as np
import logging
import daemon
from daemon import pidfile
import yaml


class Spectre(object):
    """
    For spectre simulations on remote server
    """
    def __init__(self, design, analysis, output_selections=[], command_options=['-format', 'psfascii'], at_remote=False, **kwargs):
        """
        Parameters:
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
        config_file = kwargs['config_file'] if 'config_file' in kwargs else 'pade/config/user_config.yaml'
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.local_info = config['local_info']
        spectre_setup = kwargs['spectre_setup'] if 'spectre_setup' in kwargs else 'pade/config/spectre_setup.yaml'
        with open(spectre_setup, 'r') as f:
            self.spectre_options = yaml.safe_load(f)

        # Set command options that will append to the spectre command
        self.command_options = command_options
        self.output_selections = output_selections
        # paths and names
        self.cell_name = design.cell_name # Netlist/design cell name
        self.local_netlist_dir = f"{self.local_info['local_root_dir']}/{self.local_info['local_netlist_dir']}/{self.cell_name}"
        mkdir(self.local_netlist_dir)

        # Initialization
        self.analysis = analysis # []
        self.design = design
        self.montecarlo_settings = None
        self.netlist_string = None
        self.lines_to_append_netlist = []

        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'
        # Corners:
        self.corners = kwargs['corners'] if 'corners' in kwargs else [Typical()]

        # Remote stuff
        self.at_remote = at_remote
        if not at_remote:
            self.remote_info = config['remote_info']
            ssh = SSH_Utils(self.remote_info['server_address'])
            self.ssh = ssh
            self.remote_netlist_dir = f"{self.remote_info['remote_netlist_dir']}/{self.cell_name}_netlist"
            if not ssh.path_exist(self.remote_netlist_dir):
                ssh.mkdir(self.remote_netlist_dir)
            self.remote_psf_dir = f"{self.remote_info['remote_raw_dir']}/{self.cell_name}_raw"
            # Create remote raw directory if it does not exist
            path = self.remote_psf_dir
            ssh.mkdir(path)

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
                fatal('I don\'t want to run montecarlo with multiple corners, too much output will be generated. Please select only one corner in combination with montecarlo analysis.')
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
        self.netlist_string += "// Design library name: {}\n".format(self.design.library_name)
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
        with open(local_netlist_path, 'w') as f:
            f.writelines(self._generate_netlist_string(corner))

    def run_remote(self, cache=True, daemon_logf=None):
        """
        Run simulation(s) on remote server
        """
        disp_func = lambda *s: display(info, *s)
        if daemon_logf is not None:
            logger = self.init_logger(daemon_logf)
            disp_func = logger.info

        mcrun = ''
        if self.montecarlo_settings is not None:
            mcrun += f"({self.montecarlo_settings['firstrun']})"

        disp_func("START SPECTRE SIMULATION")
        disp_func(f"Corners: {self.corners}{mcrun}")
        new_corner_runs = []
        for corner in self.corners:
            # Check cache
            if cache:
                remote_netlist = self.ssh.cat(to_path(self.remote_netlist_dir, f'{corner.name}.txt'))
                local_netlist = self._generate_netlist_string(corner)
                if (local_netlist == remote_netlist):
                    disp_func(f'Netlist unchanged, skip simulation. Corner: {corner}')
                    continue

            # Write netlist and coy to remote
            netlist_filename = f'{corner.name}.txt'
            local_netlist_path = to_path(self.local_netlist_dir, netlist_filename)
            remote_netlist_path = to_path(self.remote_netlist_dir, netlist_filename)
            new_corner_runs.append(corner.name)
            self.write_netlist(corner)
            self.ssh.cp_to(local_netlist_path, remote_netlist_path)

            # Clean up remote raw file directory before starting new simulation
            # This is to avoid fetching unwanted analysis later
            remote_raw_dir = to_path(self.remote_psf_dir, corner.name)
            self.ssh.clean_up(remote_raw_dir)

            # Remote connection commands
            popen_cmd = [
                f"{self.remote_info['start_up_commands']}",
                "spectre", f"{remote_netlist_path}",
                "-raw", f"{remote_raw_dir}"
                ]
            # Spectre commands
            for cmd in self.command_options:
                popen_cmd.append(cmd)

            # Run sim
            disp_func('\t', f'Simulating: {corner.name}')
            with open(f"{self.local_info['local_root_dir']}/{self.local_info['local_log_dir']}/spectre_sim.log", 'wb') as f:
                process = self.ssh.execute(popen_cmd)
                if daemon_logf is None:
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
                        fatal('Errors occurred during spectre simulation. See spectre_related_data/logs/spectre_sim.log for details')
                else:
                    for line in iter(process.stdout.readline, b''):
                        f.write(line)
                        line_s = line.decode('ascii')
                        disp_func(line_s)

        disp_func("SPECTRE SIMULATION COMPLETE")
        disp_func('\t', f"Raw data directory: {self.remote_info['server_address']}:{self.remote_psf_dir}")
        return new_corner_runs

    def init_logger(self, logf):
        """
        Initialize and return logger for daemon simulations
        """
        logger = logging.getLogger('spectre')
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(logf, 'w')
        fh.setLevel(logging.DEBUG)
        formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(formatstr)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger

    def simulate_local_netlist(self, local_netlist_path, simulation_name=None):
        """
        Simulate complete netlist from a local file
        This functionality could be outside the Spectre object, but is kept inside for now
        because of easy access to remote server address etc.
        """
        display(info, "START SPECTRE SIMULATION")
        display('\t', f"With local netlist file: {local_netlist_path}")
        # Create PosixPath object to get name
        local_netlist_path = to_path(local_netlist_path)
        netlist_name = local_netlist_path.name
        simulation_name = simulation_name if simulation_name else local_netlist_path.sans_ext().name
        remote_netlist_path = to_path(self.remote_netlist_dir, netlist_name)
        self.ssh.cp_to(local_netlist_path, remote_netlist_path)

        # Clean up remote raw file directory before starting new simulation
        # This is to avoid fetching unwanted analysis later
        remote_raw_dir = to_path(self.remote_psf_dir, simulation_name)
        self.ssh.clean_up(remote_raw_dir)

        # Remote connection commands
        popen_cmd = [
            f"{self.remote_info['start_up_commands']}",
            "spectre", f"{remote_netlist_path}",
            "-raw", f"{remote_raw_dir}"
            ]
        # Spectre commands
        for cmd in self.command_options:
            popen_cmd.append(cmd)

        # Run sim
        display('\t', f'Simulating: {netlist_name}')
        with open(f"{self.local_info['local_root_dir']}/{self.local_info['local_log_dir']}/spectre_sim.log", 'wb') as f:
            process = self.ssh.execute(popen_cmd)
            for line in iter(process.stdout.readline, b''):
                f.write(line)
                line_s = line.decode('ascii')
                # Only write time info to console
                progress_line = re.search('\(\d* %\)', line_s)
                if progress_line:
                    progress = progress_line.group(0).strip('(').strip(')')
                    print(f'Progress: {progress} \r', end="", flush=True)
            status_list = line_s.split(' ')
            err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
            errors = int(status_list[err_idx])
            if errors:
                fatal('Errors occurred during spectre simulation. See spectre_related_data/logs/spectre_sim.log for details')

        display(info, "SPECTRE SIMULATION COMPLETE")
        display('\t', f"Raw data directory: {self.host}:{self.remote_psf_dir}")
        return [simulation_name]

    def run_locally(self, cache=False):
        """
        Run simulation(s) locally on the computer initializing the simulation.
        """
        display(info, "START SPECTRE SIMULATION")
        display(info, f"Corners: {self.model_files}")
        new_corner_runs = []
        for corner in self.corners:
            # Cache currently not supported
            # Write netlist and coy to remote
            netlist_filename = f'{corner.name}.txt'
            local_netlist_path = to_path(self.local_netlist_dir, netlist_filename)
            new_corner_runs.append(corner.name)
            self.write_netlist(corner)

            # Spectre commands
            local_raw_dir = to_path(self.local_info['local_raw_dir'], self.cell_name, corner.name)
            # Create cell raw dir if it does not exist
            mkdir(to_path(self.local_info['local_raw_dir'], self.cell_name))
            popen_cmd = [
                "spectre", f"{local_netlist_path}",
                "-raw", f"{local_raw_dir}"
                ]
            for cmd in self.command_options:
                popen_cmd.append(cmd)

            # Run sim
            display('\t', f'Simulating: {corner}')
            with open(f"{self.local_info['local_root_dir']}/{self.local_info['local_log_dir']}/spectre_sim.log", 'wb') as f:
                process = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE)
                for line in iter(process.stdout.readline, b''):
                    f.write(line)
                    line_s = line.decode('ascii')
                    # Only write time info to console
                    progress_line = re.search('\(\d* %\)', line_s)
                    if progress_line:
                        progress = progress_line.group(0).strip('(').strip(')')
                        print(f'Progress: {progress} \r', end="", flush=True)
                status_list = line_s.split(' ')
                err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
                errors = int(status_list[err_idx])
                if errors:
                    fatal('Errors occurred during spectre simulation. See spectre_related_data/logs/spectre_sim.log for details')

        display(info, "SPECTRE SIMULATION COMPLETE")
        display('\t', f"Raw data directory: {self.local_info['local_raw_dir']}")
        return new_corner_runs

    def run(self, cache=True, as_daemon=False, from_remote=False):
        """
        Parameters:
            cache: bool
                If True, the simulation will not run if an identical netlist does already exist
            as_daemon: bool
                If True, use python-daemon to daemonize the simulation
            from_remote: bool
                Set to True if the simulation is executed from remote server, i.e. do not copy netlist
        """
        # Run simulation
        if as_daemon:
            daemon_dir = f"{self.local_info['local_root_dir']}/{self.local_info['local_daemon_dir']}/{self.cell_name}"
            logf = f'{daemon_dir}/spectre_sim.log'
            pidf = f'{daemon_dir}/spectre_sim.pid'
            if os.path.exists(pidf):
                fatal('Cannot start simulation because a simulation with the same cell name is already running')
            display(info, 'DAEMONIZING SIMULATION')
            display('\t', f'Daemon directory: {daemon_dir}')
            mkdir(daemon_dir)
            with daemon.DaemonContext(working_directory=f'{daemon_dir}',umask=0o002,pidfile=pidfile.TimeoutPIDLockFile(pidf),) as context:
                self.run_remote(cache=cache, daemon_logf=logf)
        elif not self.at_remote:
            return self.run_remote(cache=cache)
        else:
            return self.run_locally(cache=cache)


