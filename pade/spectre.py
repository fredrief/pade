from shlib import mkdir, ls, to_path, rm
from pade.utils import num2string, cat, writef
import re
import subprocess
from tqdm import tqdm
from pade import display, succeed, fatal, warn
from datetime import datetime

class Spectre(object):
    """
    For spectre simulations on remote server
    """
    def __init__(self, netlist_dir, output_dir, log_dir, design, analyses, sim_name, output_selections=[], command_options=['-format', 'psfascii', '++aps', '+mt', '-log'], **kwargs):

        # Set command options that will append to the spectre command
        self.command_options = command_options
        self.output_selections = output_selections
        # paths and names
        self.design = design # Netlist/design cell name
        self.netlist_dir = netlist_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        # Initialization
        self.analyses = analyses # []
        self.design = design
        self.montecarlo_settings = None
        self.netlist_string = None
        self.lines_to_append_netlist = []

        self.global_nets = kwargs.get('global_nets', '0')

        self.corner = kwargs.get('corner')
        self.sim_name = sim_name
        self.tqdm_pos = kwargs.get('tqdm_pos', 0)

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
                # Only include analyes inside mc brackets, not options
                if not a.type in ['options']:
                    astr += a.get_netlist_string() + "\n"
            astr += "} \n"
            for a in self.analyses:
                # Append optionsstatements
                if a.type in ['options']:
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
            warn('Cannot set parameter because montecarlo settings does not exist')

    def init_netlist(self):
        """
        Initialize netlist
        [MODELFILE] will be replaced by model file in simulation
        """
        self.netlist_string = "// Generated for: spectre\n"
        self.netlist_string += "// Design cell name: {}\n".format(self.design.cell_name)
        self.netlist_string += f"// Timestamp: {datetime.now()}\n"
        self.netlist_string += 'simulator lang=spectre\n'
        self.netlist_string += f"global {self.global_nets}\n"
        self.netlist_string += self.corner.get_string()

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
        return self.netlist_string

    def write_netlist(self, corner):
        """
        Write netlist string to files
        One Netlist file per corner
        """
        netlist_path = to_path(self.netlist_dir, corner.name + '.txt')
        writef(self._generate_netlist_string(corner), netlist_path)


    def run(self, cache=True):
        """
        Run simulation
        Returns true if cache is used
        """
        corner = self.corner
        netlist_filename = f'{corner.name}.txt'
        netlist_path = to_path(self.netlist_dir, netlist_filename)
        simulation_raw_dir = self.output_dir
        # Check cache
        if cache:
            prev_netlist = cat(netlist_path)
            new_netlist = self._generate_netlist_string(corner)
            try:
                prev_netlist_ = re.sub('// Timestamp: .*\n', '', prev_netlist)
                new_netlist_ = re.sub('// Timestamp: .*\n', '', new_netlist)
            except:
                prev_netlist_ = prev_netlist
                new_netlist_ = new_netlist

            if (new_netlist_ == prev_netlist_):
                display(f'Netlist unchanged, skip simulation. Corner: {corner}')
                return True

        display('Writing netlist')
        # Write netlist to file
        self.write_netlist(corner)

        # Spectre commands
        popen_cmd = f"spectre {netlist_path} " + \
            f"-raw {simulation_raw_dir} "
        for cmd in self.command_options:
            popen_cmd += f"{cmd} "

        display(f'Starting spectre simulation.\nCommand: {popen_cmd}')

        # Run sim
        display(f'Simulating: {self.sim_name}')
        log_file = to_path(self.log_dir, 'spectre_sim.log')
        # Progress bar
        self.tq = tqdm(total=100, leave=False, position=self.tqdm_pos)
        with open(log_file, 'wb') as f:
            process = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            p0 = 0
            line_s = None
            for line in iter(process.stdout.readline, b''):
                f.write(line)
                try:
                    line_s = line.decode('ascii')
                except:
                    pass
                # Only write time info to console
                progress_line = re.search('\(.* %\)', line_s)
                if progress_line:
                    progress = float(line_s.split(' %')[0].split('(')[1])
                    analysis = line_s.split(':')[0].strip()
                    if not analysis in ['ac', 'tran', 'noise', 'stb', 'dc', 'montecarlo_ac', 'montecarlo_tran', 'montecarlo_noise', 'montecarlo_stb', 'montecarlo_dc']:
                        continue
                    self.tq.update(progress-p0)
                    self.tq.set_description(f'{self.sim_name} {analysis} {corner.name}')
                    p0 = progress
                    # Close tq
            self.tq.close()
            if line_s is None:
                fatal('Spectre simulation did not return any output')
            try:
                status_list = line_s.split(' ')
                err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
                errors = int(status_list[err_idx])
            except:
                errors = True
            if errors:
                raise SpectreError(log_file)

        display("SPECTRE SIMULATION COMPLETE")
        display(f"Raw data directory: {simulation_raw_dir}")


class SpectreError(Exception):
    """
    Exception raised when spectre has error
    """
    def __init__(self, log_file):
        self.message = f'Errors occurred during spectre simulation. See {log_file} for details'
        super().__init__(self.message)

    def __str__(self):
        return self.message

def run_spectre_parse_progress(netlist_path, sim_name, log_dir, simulation_raw_dir, corner, command_options=[], tqdm_pos=0, **kwargs):
        # Build spectre command
        popen_cmd = f"spectre {netlist_path} -raw {simulation_raw_dir} -f psfascii -log -ahdllibdir {simulation_raw_dir} "
        for cmd in command_options:
            popen_cmd += f"{cmd} "

        display(f'Starting spectre simulation.\nCommand: {popen_cmd}')
        log_file = to_path(log_dir, 'spectre_sim.log')
        # Progress bar
        tq = tqdm(total=100, leave=False, position=tqdm_pos)
        with open(log_file, 'wb') as f:
            process = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            p0 = 0
            line_s = None
            for line in iter(process.stdout.readline, b''):
                f.write(line)
                try:
                    line_s = line.decode('ascii')
                except:
                    pass
                # Only write time info to console
                progress_line = re.search('\(.* %\)', line_s)
                if progress_line:
                    progress = float(line_s.split(' %')[0].split('(')[1])
                    analysis = line_s.split(':')[0].strip()
                    if not analysis in ['ac', 'tran', 'noise', 'stb', 'dc', 'montecarlo_ac', 'montecarlo_tran', 'montecarlo_noise', 'montecarlo_stb', 'montecarlo_dc']:
                        continue
                    tq.update(progress-p0)
                    tq.set_description(f'{sim_name} {analysis} {corner.name}')
                    p0 = progress
                    # Close tq
            tq.close()
            if line_s is None:
                fatal('Spectre simulation did not return any output')
            try:
                status_list = line_s.split(' ')
                err_idx = int([i for i in range(0, len(status_list)) if "error" in status_list[i]][0])-1
                errors = int(status_list[err_idx])
            except:
                errors = True
            if errors:
                raise SpectreError(log_file)

        display("SPECTRE SIMULATION COMPLETE")
        display(f"Raw data directory: {simulation_raw_dir}")

def run_spectre(netlist_path, log_dir, simulation_raw_dir, command_options=[], **kwargs):
        # Build spectre command
        log_file = to_path(log_dir, 'spectre_sim.log')
        popen_cmd = f"spectre {netlist_path} -raw {simulation_raw_dir} -f psfascii =log {log_file} -ahdllibdir {simulation_raw_dir} "
        for cmd in command_options:
            popen_cmd += f"{cmd} "

        display(f'Starting spectre simulation.\nCommand: {popen_cmd}')
        display(f'Log file: {log_file}')
        process = subprocess.Popen(popen_cmd, shell=True)
