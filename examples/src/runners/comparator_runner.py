"""Comparator transient simulation runner."""

from pathlib import Path
import ltspice
import numpy as np

from pade.statement import Statement, Analysis, Save
from pade.backends.ngspice.simulator import NgspiceSimulator
from pdk.sky130.config import config
from src.testbenches.comparator import ComparatorTranTB


class ComparatorRunner:
    """Runner for NSALCMP transient simulation.

    Example:
        runner = ComparatorRunner()
        result = runner.run_and_evaluate(vdiff=10e-3)
    """

    def __init__(self, vdd: float = 1.8, vcm: float = 0.9,
                 fclk: float = 1e9, cl: float = 50e-15):
        self.vdd = vdd
        self.vcm = vcm
        self.fclk = fclk
        self.cl = cl
        self.simulator = NgspiceSimulator(
            output_dir=config.sim_data_dir / 'comparator'
        )

    def _build_statements(self, n_cycles: int = 10) -> list[Statement]:
        period = 1.0 / self.fclk
        tstop = n_cycles * period
        return [
            Statement(f'.lib "{config.sky130_lib}" tt'),
            Analysis('tran', stop=tstop),
            Save(['outp', 'outn', 'clk', 'inp', 'inn']),
        ]

    def _build_tb(self, vdiff: float) -> ComparatorTranTB:
        return ComparatorTranTB(
            vdd=self.vdd, vcm=self.vcm, vdiff=vdiff,
            fclk=self.fclk, cl=self.cl)

    def _identifier(self, vdiff: float) -> str:
        return f'vdiff_{vdiff*1e3:.1f}mV'

    def run(self, vdiff: float, n_cycles: int = 10) -> Path:
        """Run single transient simulation. Returns path to raw file."""
        tb = self._build_tb(vdiff)
        statements = self._build_statements(n_cycles)
        return self.simulator.simulate(
            tb, statements, self._identifier(vdiff), show_output=False)

    def evaluate(self, raw_file: Path) -> dict:
        """Extract output waveforms from raw file."""
        raw = ltspice.Ltspice(str(raw_file))
        raw.parse()
        return {
            'time': raw.get_data('time'),
            'outp': raw.get_data('v(outp)'),
            'outn': raw.get_data('v(outn)'),
            'clk': raw.get_data('v(clk)'),
        }

    def run_and_evaluate(self, vdiff: float, n_cycles: int = 10) -> dict:
        """Run simulation and extract waveforms."""
        raw_file = self.run(vdiff, n_cycles)
        result = self.evaluate(raw_file)
        result['vdiff'] = vdiff
        result['raw_file'] = raw_file
        return result
