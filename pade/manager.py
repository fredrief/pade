from pade.psf_parser import PSFParser
from pade.analysis import Corner, tran, dc, noise, ac, Typical
from pade.spectre import Spectre as Simulator
from pade.signal import Signal
from pade.evaluation import Evaluation, Expression
from pade.test import Test
from pade.utils import get_kwarg, get_logger
import pandas as pd
from shlib.shlib import lsf, rm, to_path, mkdir
from mpire import WorkerPool

class Manager:
    """
    Similar to Cadence Assembler
    Contains one or more tests
    """
    def __init__(self, project_root_dir, analyses, expressions=None, **kwargs) -> None:
        self.parse_kwargs(**kwargs)
        self.project_root_dir = project_root_dir
        self.analyses = analyses
        self.expressions = expressions

    def run_multiple_designs(self, designs, cache=True):
        # Create list of corners
        arguments = []
        idx=0
        for d in designs:
            arguments.append((d, idx, cache))
            idx += 1
        with WorkerPool(n_jobs=self.workers, pass_worker_id=True, use_dill=True) as pool:
            res = pd.concat(pool.map(self.run_single_design, arguments), axis=1)
        return res

    def run_corners(self, model_files, temperatures=[27], cache=True):
        # Create list of corners
        arguments = []
        idx=0
        for p in model_files:
            for t in temperatures:
                corner = Corner(p, t,f'{p}_{t}C')
                arguments.append((corner, idx, cache))
                idx += 1
        with WorkerPool(n_jobs=self.workers, use_dill=False) as pool:
            res = pd.concat(pool.map(self.run_single_corner, arguments), axis=1)
        return res

    def run_single_design(self, wid, design, rid, cache=True):
        test = Test(
            self.project_root_dir,
            design,
            self.analyses,
            self.expressions,
            corner=self.corner,
            sim_name=f'#{rid}',
            dir_name=f'wid_{wid}',
            run_index=rid,
            tqdm_pos=wid,
            output_selections=self.output_selections,
        )
        test.run(cache=cache)
        res = test.evaluate()
        return res

    def run_single_corner(self, corner, idx, cache=True):
        test = Test(
            self.project_root_dir,
            self.design,
            self.analyses,
            self.expressions,
            corner=corner,
            run_index=idx,
            output_selections=self.output_selections,
        )
        test.run(cache=cache)
        return test.evaluate()

    def run_test(self, test: Test, cache=True):
        test.run(cache=cache)
        return test.evaluate()

    def parse_kwargs(self, **kwargs):
        # Initialize simulator
        self.output_selections = kwargs['output_selections'] if 'output_selections' in kwargs else []
        # Add all signal names from expressions
        self.append_netlist = kwargs['append_netlist'] if 'append_netlist' in kwargs else []
        # Logger
        self.logger = get_kwarg(kwargs, 'logger', get_logger())
        self.workers = get_kwarg(kwargs, 'workers', 5)
        self.corner = get_kwarg(kwargs, 'corner', Typical())
        self.design = get_kwarg(kwargs, 'design', None)

