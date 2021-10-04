from typing import List
from pade.psf_parser import PSFParser
from pade.analysis import tran, dc, noise, ac, Typical
from pade.spectre import Spectre as Simulator
from pade.signal import Signal
from pade.evaluation import Evaluation, Expression
from pade.ssh_utils import SSH_Utils
from pade.utils import get_kwarg, get_logger
from shlib.shlib import lsf, rm, to_path, mkdir
from tqdm.std import tqdm
import yaml

class Test:
    """
    Test class.
    A test has a design, a set of analyses, design variables and expressions for evaluation.
    Covers the functionality of the Explorer view in Cadence Virtuoso

    Currently only supporting Spectre simulator.
    TODO: Support SPICE

    Parameters
        project_root_dir: Path
            Project root
        design: Design
            Design to simulate
        analyses: [Analysis]
            Analyses to run
        expressions: [Expression]
            List of expressions to evaluate. If None, traces from parser is returned

    Keyword arguments:
        logf: str
            Logfile. None -> stdout
        debug: bool (default: False)
            If True, the test will be run in debug mode.
            In debug mode, the user is supposed to use another tool for debugging, and the test is terminated after
            the simulation has finished. All traces will be saved.
        corners: [Corner]
            Corners to simulate
        command_options: ['str'] (default: ['-f', 'psfascii', '++aps', '+mt', '-log'])
            Commands to add to the simulator command line call.
        output_selections: ['str'] (default: [''])
            Traces to save
        append_netlist: ['str'] (default: [''])
            Extra lines to append to the netlist. E.g: ['ic vcm=500m', simNoise options noiseon_type=[thermal, flicker] ]
        latex_dir: str
            Path to directory where latex tables are saved
        html_dir: str
            Path to directory where html tables are saved
        mcoptions: Dictionary
            Montecarlo options. Montecarlo disabled if this is not specified
        run_index: int
            Index used to handle multiprocessing
    """
    def __init__(self, project_root_dir, design, analyses, expressions=None, **kwargs):
        # Sim name and index
        self.run_index = get_kwarg(kwargs, 'run_index', 0)
        self.sim_name = get_kwarg(kwargs, 'sim_name', None)
        if self.sim_name is None:
            self.sim_name = str(self.run_index)

        self.project_root_dir = project_root_dir
        self.design = design
        self.debug = kwargs['debug'] if 'debug' in kwargs else False
        debug_currents = kwargs['debug_currents'] if 'debug_currents' in kwargs else False
        self.mcoptions = kwargs['mcoptions'] if 'mcoptions' in kwargs else None
        # Initialize simulator
        command_options = kwargs['command_options'] if 'command_options' in kwargs else ['-f', 'psfascii', '++aps', '+mt', '-log']
        output_selections = kwargs['output_selections'] if 'output_selections' in kwargs else []
        if self.debug:
            output_selections = ['*'] if not debug_currents else ['*', '*:currents']
        self.expressions = expressions
        # Add all signal names from expressions
        output_selections = self.get_output_selections(output_selections, expressions)
        self.corners = kwargs['corners'] if 'corners' in kwargs else [Typical()]
        self.append_netlist = kwargs['append_netlist'] if 'append_netlist' in kwargs else []
        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'

        # keep all paths and directories at the same place
        dir_suffix = f'_{self.sim_name}'
        self.log_dir = to_path(self.project_root_dir,f"{self.design.cell_name}_logs" + dir_suffix)
        self.netlist_dir = to_path(self.project_root_dir,f"{self.design.cell_name}_netlists" + dir_suffix)
        self.res_dir = to_path(self.project_root_dir,f"{self.design.cell_name}_results" + dir_suffix)
        self.output_dir = to_path(self.project_root_dir,f"{self.design.cell_name}_simulation_output" + dir_suffix)

        # Make all directories at init
        mkdir(self.log_dir, self.netlist_dir, self.output_dir, self.log_dir)

        # Logger
        logf = get_kwarg(kwargs, 'logf', None)
        self.logger = get_logger(logf)
        # Prgoress bar
        self.tq = tqdm(total=100, position=self.run_index, desc=f'{self.sim_name}', leave=False)

        # Init simulator
        sim = Simulator(
            self.netlist_dir,
            self.output_dir,
            self.log_dir,
            self.logger,
            design,
            analyses,
            self.tq,
            command_options=command_options,
            output_selections=output_selections,
            corners=self.corners,
            global_nets=self.global_nets,)
        for string in self.append_netlist:
            sim.append_netlist_line(string)
        self.simulator = sim

        # Parse config file
        results_dir = f"{project_root_dir}/{design.cell_name}_results"
        # Evaluation
        self.html_dir = kwargs['html_dir'] if 'html_dir' in kwargs else results_dir
        self.latex_dir = kwargs['latex_dir'] if 'latex_dir' in kwargs else results_dir

        # Hold simulation results
        self.signals = None # Parsed signals



    def run(self, cache=True, skip_run=False):
        """
        Run simulation
        Parameters:
            cache: bool
                If True, the simulation will not run if an identical netlist does already exist
        """
        numruns = 1
        firstrun = 1
        # Montecarlo
        mcruns = None
        mcoptions = self.mcoptions
        if mcoptions is not None:
            mcruns = mcoptions['numruns'] if 'numruns' in mcoptions else 1
            numruns = mcruns
            firstrun = mcoptions['firstrun'] if 'firstrun' in mcoptions else 1

        sim = self.simulator
        simulations = [corner.name for corner in self.corners]
        parser = PSFParser(self.project_root_dir, self.logger, self.design.cell_name, simulations=simulations, mcoptions=mcoptions)
        parser_mcrun = None
        for run in range(firstrun, firstrun + numruns):
            # Increment mc run if mcoptions is set
            if mcoptions is not None:
                mcoptions['firstrun'] = run
                sim.set_mc_settings(mcoptions)
                fetch_all = True
                parser_mcrun = run
            # Run spectre simulation
            if not skip_run:
                new_corner_runs = sim.run(cache=cache)
            else:
                new_corner_runs = simulations
            # Terminate if debugging
            if self.debug:
                self.logger.info('Debug mode active: Terminating Program')
                quit()
            parser.parse(mcrun=parser_mcrun)

        # Store signals
        self.signals = parser.signals
        self.parser = parser
        return parser.signals

    def evaluate(self, expressions=None):
        expressions = self.expressions if expressions is None else expressions
        parser = self.parser
        # Verify that signals in expression exist in parser
        simulations = parser.simulations
        e_names = [e.name for e in expressions]
        for e in expressions:
            signal_names = e.signal_names
            analysis = e.analysis_name
            for sim in simulations:
                for signal in signal_names:
                    if not signal in e_names:
                        try:
                            parser.get_signal(signal, analysis, sim)
                        except:
                            self.logger.critical(f'Signal not available for evaluation: Name {signal}, Analysis {analysis}, Simulation {sim}')
        # EVALUATE
        self.evaluation = Evaluation(parser, expressions,
                            html_dir=self.html_dir, latex_dir=self.latex_dir )
        self.evaluation.evaluate()
        if self.mcoptions is not None:
            self.evaluation.create_summary()
        return self.evaluation.results

    def to_html(self):
        self.evaluation.to_html()

    def to_latex(self):
        self.evaluation.to_latex()

    def get_output_selections(self, outputs: List, expressions: Expression):
        """
        Append all signal names of expressions to output selections
        Return sorted list for convenience
        """
        output_set = set(outputs)
        if expressions is not None:
            for e in expressions:
                signal_names = e.signal_names
                for name in signal_names:
                    if not name in output_set:
                        output_set.add(name)
        l = list(output_set)
        l.sort()
        return l


    def clean_up(self):
        """
        Clean up all directories
        """
        # Logs
        rm(self.log_dir, self.netlist_dir, self.output_dir, self.log_dir)
