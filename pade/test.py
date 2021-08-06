from pade.psf_parser import PSFParser
from pade.analysis import tran, dc, noise, ac, Typical
from pade.spectre import Spectre as Simulator
from pade.signal import Signal
from pade.evaluation import Evaluation
from pade.ssh_utils import SSH_Utils
from pade import info, display, warn, error, fatal
import yaml

class Test:
    """
    Test class.
    A test has a design, a set of analyses, design variables and expressions for evaluation.
    Covers the functionality of the Explorer view in Cadence Virtuoso

    Currently only supporting Spectre simulator.
    TODO: Support SPICE

    Parameters
        design: Design
            Design to simulate
        analyses: [Analysis]
            Analyses to run
        expressions: [Expression]
            List of expressions to evaluate. If None, traces from parser is returned

    Keyword arguments:
        debug: bool (default: False)
            If True, the test will be run in debug mode.
            In debug mode, the user is supposed to use another tool for debugging, and the test is terminated after
            the simulation has finished. All traces will be saved.
        at_remote: bool (default: False)
            If True, the test will assume to be initialize at the remote server, meaning that no ssh connection
            is required to run the simulation.
        corners: [Corner]
            Corners to simulate
        command_options: ['str'] (default: ['-f', 'psfascii', '++aps', '+mt'])
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
    """
    def __init__(self, design, analyses, expressions=None, **kwargs):
        self.design = design
        self.debug = kwargs['debug'] if 'debug' in kwargs else False
        debug_currents = kwargs['debug_currents'] if 'debug_currents' in kwargs else False
        self.at_remote = kwargs['at_remote'] if 'at_remote' in kwargs else False
        self.mcoptions = kwargs['mcoptions'] if 'mcoptions' in kwargs else None
        # Initialize simulator
        command_options = kwargs['command_options'] if 'command_options' in kwargs else ['-f', 'psfascii', '++aps', '+mt']
        output_selections = kwargs['output_selections'] if 'output_selections' in kwargs else []
        if self.debug:
            output_selections = ['*'] if not debug_currents else ['*', '*:currents']
        self.corners = kwargs['corners'] if 'corners' in kwargs else [Typical()]
        self.append_netlist = kwargs['append_netlist'] if 'append_netlist' in kwargs else []
        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'

        # Init simulator
        sim = Simulator(design, analyses,
            command_options=command_options,
            output_selections=output_selections,
            corners=self.corners,
            at_remote=self.at_remote,
            global_nets=self.global_nets)
        for string in self.append_netlist:
            sim.append_netlist_line(string)
        self.simulator = sim

        # Parse config file
        results_dir = f"{sim.project_root_dir}/{design.cell_name}_results"

        # Evaluation
        self.expressions = expressions
        self.html_dir = kwargs['html_dir'] if 'html_dir' in kwargs else results_dir
        self.latex_dir = kwargs['latex_dir'] if 'latex_dir' in kwargs else results_dir

        # Hold simulation results
        self.signals = None # Parsed signals



    def run(self, cache=True, as_daemon=False, skip_run=False):
        """
        Run simulation
        Parameters:
            cache: bool
                If True, the simulation will not run if an identical netlist does already exist
            as_daemon: bool
                If True, use python-daemon to daemonize the simulation
                TODO: Move the daemonizing to test-object level. Will allow for running corners and MC simultaneously.
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
        parser = PSFParser(self.design.cell_name, simulations=simulations, at_remote=self.at_remote, mcoptions=mcoptions)
        fetch_all = False
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
                new_corner_runs = sim.run(cache=cache, as_daemon=as_daemon, from_remote=self.at_remote)
            else:
                new_corner_runs = simulations
            # Terminate if debugging
            if self.debug:
                display(info, 'Debug mode active: Terminating Program')
                quit()
            # Fetch and parse
            if not self.at_remote:
                parser.fetch_raw_data(new_runs=new_corner_runs, fetch_all=fetch_all)
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
                            fatal(f'Signal not available for evaluation: Name {signal}, Analysis {analysis}, Simulation {sim}')
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
