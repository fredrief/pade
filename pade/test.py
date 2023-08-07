from distutils.command.config import config
from typing import List
from pade.psf_parser import PSFParser
from pade.spectre import Spectre as Simulator
from pade.evaluation import Evaluation, Expression
from pade.utils import get_kwarg
from pade import *
from shlib.shlib import lsf, rm, to_path, mkdir
import matplotlib.pyplot as plt

class Test:
    """
    Equivalent to Cadence Explorer
    Run a single test
    """
    def __init__(self, project_root_dir, design, analyses, expressions=None, **kwargs):
        self.project_root_dir = project_root_dir
        self.design = design
        self.project_name = project_root_dir.name
        self.expressions = expressions
        self.corner = get_kwarg(kwargs, 'corner')
        self.sim_name = get_kwarg(kwargs, 'sim_name', self.corner.name)
        self.run_index = get_kwarg(kwargs, 'run_index', 0)
        self.tqdm_pos = get_kwarg(kwargs, 'tqdm_pos', self.run_index)
        self.debug = kwargs['debug'] if 'debug' in kwargs else False
        self.mcoptions = kwargs['mcoptions'] if 'mcoptions' in kwargs else None
        self.output_selections = kwargs['output_selections'] if 'output_selections' in kwargs else []
        self.skip_sim = kwargs.get('skip_sim', False)
        self.skip_parse = kwargs.get('skip_parse', False)
        # Add all signal names from expressions
        self.append_netlist = kwargs['append_netlist'] if 'append_netlist' in kwargs else []
        self.global_nets = kwargs['global_nets'] if 'global_nets' in kwargs else '0'

        self.output_selections = self.get_output_selections(self.output_selections, expressions)

        # keep all paths and directories at the same place
        self.sim_data_dir = to_path(self.project_root_dir, f"sim_data", self.sim_name, self.corner.name)
        self.log_dir = to_path(self.sim_data_dir,"logs")
        self.netlist_dir = to_path(self.sim_data_dir,"netlists")
        self.res_dir = to_path(self.sim_data_dir,"results")
        self.output_dir = to_path(self.sim_data_dir,"simulation_output")
        self.html_dir = kwargs['html_dir'] if 'html_dir' in kwargs else self.res_dir
        self.latex_dir = kwargs['latex_dir'] if 'latex_dir' in kwargs else self.res_dir

        # Skill plot object
        self.SkillPlot = kwargs.get('SkillPlot')
        # Skill script dir. Let it be equal to res if no skill scripts are specified
        self.skill_dir = to_path(self.sim_data_dir, "skill") if self.SkillPlot else self.res_dir
        # Make all directories at init
        mkdir(self.log_dir, self.netlist_dir, self.output_dir, self.log_dir, self.html_dir, self.latex_dir, self.res_dir, self.log_dir, self.skill_dir)

        # command options
        self.command_options = [
            '-f', 'psfascii', '-log', '-ahdllibdir', self.sim_data_dir]
        if 'command_options' in kwargs:
            for opt in kwargs['command_options']:
                self.command_options.append(opt)

        # Log file
        main_logf = to_path(self.log_dir, 'main.log')
        informer.set_logfile(main_logf)

        # Init simulator
        sim = Simulator(
            self.netlist_dir,
            self.output_dir,
            self.log_dir,
            design,
            analyses,
            self.sim_name,
            command_options=self.command_options,
            output_selections=self.output_selections,
            corner=self.corner,
            global_nets=self.global_nets,
            tqdm_pos=self.tqdm_pos,
            )

        self.used_cache = None # This will be set to true if the simulator used cache

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
        parser = PSFParser(self.output_dir, f'{self.sim_name}_{self.corner.name}')
        if not self.skip_sim:
            self.used_cache = sim.run(cache=cache)
        # Plot using skill
        if self.SkillPlot:
            self.SkillPlot.plot(self.skill_dir, self.output_dir)
        # Terminate if debugging
        if self.debug:
            display('Debug mode active: Terminating Program')
            quit()
        if not self.skip_parse:
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
                        fatal(f'Signal not available for evaluation: Name {signal}, Analysis {analysis}, Simulation {self.sim_name} Corner {self.corner.name}')
        # EVALUATE
        self.evaluation = Evaluation(parser, expressions,
                            html_dir=self.html_dir, latex_dir=self.latex_dir)
        self.evaluation.evaluate()
        return self.evaluation.results

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
        try:
            rm(self.sim_data_dir)
        except:
            rm(self.output_dir)
            pass
