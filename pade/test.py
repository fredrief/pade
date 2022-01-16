from typing import List
from pade.psf_parser import PSFParser
from pade.analysis import tran, dc, noise, ac, Typical
from pade.spectre import Spectre as Simulator
from pade.evaluation import Evaluation, Expression
from pade.utils import get_kwarg, get_logger
from pade import fatal
from shlib.shlib import lsf, rm, to_path, mkdir
import matplotlib.pyplot as plt

class Test:
    """
    Equovalent to Cadence Explorer
    Run a single test
    """
    def __init__(self, project_root_dir, design, analyses, expressions=None, **kwargs):
        self.parse_kwargs(**kwargs)
        self.project_root_dir = project_root_dir
        self.design = design
        self.project_name = project_root_dir.name
        # Output selection
        # if self.debug:
        #     self.output_selections = ['*'] if not self.debug_currents else ['*', '*:currents']
        self.expressions = expressions
        self.output_selections = self.get_output_selections(self.output_selections, expressions)

        # keep all paths and directories at the same place
        self.sim_data_dir = to_path(self.project_root_dir, f"{self.project_name}_sim_data", self.dir_name)
        self.log_dir = to_path(self.sim_data_dir,"logs")
        self.netlist_dir = to_path(self.sim_data_dir,"netlists")
        self.res_dir = to_path(self.sim_data_dir,"results")
        self.output_dir = to_path(self.sim_data_dir,"simulation_output")
        self.html_dir = kwargs['html_dir'] if 'html_dir' in kwargs else self.res_dir
        self.latex_dir = kwargs['latex_dir'] if 'latex_dir' in kwargs else self.res_dir
        self.figure_dir = to_path(self.project_root_dir, f"{self.project_name}_figures")
        # Logger
        main_logf = to_path(self.log_dir, 'main.log')
        # Make all directories at init
        mkdir(self.log_dir, self.netlist_dir, self.output_dir, self.log_dir, self.html_dir, self.latex_dir, self.res_dir, self.log_dir)

        self.logger = get_kwarg(kwargs, 'logger')
        if self.logger is None:
            self.logger = get_logger(logf=main_logf, name=self.sim_name)

        # Init simulator
        sim = Simulator(
            self.netlist_dir,
            self.output_dir,
            self.log_dir,
            self.logger,
            design,
            analyses,
            self.sim_name,
            command_options=self.command_options,
            output_selections=self.output_selections,
            corner=self.corner,
            global_nets=self.global_nets,
            tqdm_pos=self.tqdm_pos)
        # Eventually set mcoptions in simulator
        if self.mcoptions is not None:
            sim.set_mc_settings(self.mcoptions)
        # Eventually append netlist
        for string in self.append_netlist:
            sim.append_netlist_line(string)
        self.simulator = sim

        # Hold simulation results
        self.signals = None # Parsed signals



    def run(self, cache=True):
        """
        Run simulation
        Parameters:
            cache: bool
                If True, the simulation will not run if an identical netlist does already exist
        """
        sim = self.simulator
        parser = PSFParser(self.logger, self.output_dir, self.sim_name)
        sim.run(cache=cache)
        # Terminate if debugging
        if self.debug:
            self.logger.info('Debug mode active: Terminating Program')
            quit()
        parser.parse()

        # Store signals
        self.signals = parser.signals
        self.parser = parser
        return parser.signals

    def evaluate(self, expressions=None):
        expressions = self.expressions if expressions is None else expressions
        parser = self.parser
        # Verify that signals in expression exist in parser
        e_names = [e.name for e in expressions]
        for e in expressions:
            signal_names = e.signal_names
            analysis = e.analysis_name
            for signal in signal_names:
                if not signal in e_names:
                    try:
                        parser.get_signal(signal, analysis)
                    except:
                        fatal(f'Signal not available for evaluation: Name {signal}, Analysis {analysis}, Simulation {self.sim_name}')
        # EVALUATE
        self.evaluation = Evaluation(parser, expressions,
                            html_dir=self.html_dir, latex_dir=self.latex_dir)
        self.evaluation.evaluate()
        return self.evaluation.results

    def to_html(self):
        try:
            self.evaluation.to_html()
        except Exception as e:
            self.logger.info(f'Failed writing results to HTML table: {e}')

    def to_latex(self):
        try:
            self.evaluation.to_latex()
        except Exception as e:
            self.logger.info(f'Failed writing results to Latex table: {e}')

    def save_plot(self, expressions, name='plot.png'):
        figure_path = to_path(self.figure_dir, name)
        signals = self.evaluate(expressions).to_numpy()
        N = signals.shape[0]
        for n in range(N):
            sig = signals[n][0]
            sweep = self.parser.get_sweep(sig.analysis)
            plt.subplot(N+1, 1, n+1)

            # plt.yticks([])
            if not n==N-1:
                plt.xticks([])
            # Plotting against sweep fails if dimensions are not equal
            try:
                plt.plot(sweep.trace, sig.trace, label=sig.name)
            except ValueError:
                plt.plot(sig.trace, label=sig.name)
            plt.legend(loc='upper right')
            # plt.ylabel(f'[{sig.unit}]')
        plt.savefig(figure_path)


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
        rm(self.log_dir, self.netlist_dir, self.output_dir, self.log_dir, self.res_dir)


    def parse_kwargs(self, **kwargs):
        self.corner = get_kwarg(kwargs, 'corner', Typical())
        self.sim_name = get_kwarg(kwargs, 'sim_name', self.corner.name)
        self.dir_name = get_kwarg(kwargs, 'dir_name', self.sim_name)
        self.run_index = get_kwarg(kwargs, 'run_index', 0)
        self.tqdm_pos = get_kwarg(kwargs, 'tqdm_pos', self.run_index)
        self.debug = kwargs['debug'] if 'debug' in kwargs else False
        self.debug_currents = kwargs['debug_currents'] if 'debug_currents' in kwargs else False
        self.mcoptions = kwargs['mcoptions'] if 'mcoptions' in kwargs else None
        # Initialize simulator
        self.mt = get_kwarg(kwargs, 'mt', 2)
        # command options
        self.command_options = ['-f', 'psfascii', '++aps', f'+mt={self.mt}', '-log']
        if 'command_options' in kwargs:
            for opt in kwargs['command_options']:
                self.command_options.append(opt)
        self.output_selections = kwargs['output_selections'] if 'output_selections' in kwargs else []
        # Add all signal names from expressions
        self.append_netlist = kwargs['append_netlist'] if 'append_netlist' in kwargs else []
        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'

