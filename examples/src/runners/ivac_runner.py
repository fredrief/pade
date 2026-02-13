"""Inverter AC gain simulation runner."""

from pathlib import Path
import numpy as np

from pade.statement import Statement, Analysis, Save
from pade.backends.ngspice.simulator import NgspiceSimulator
from pade.backends.ngspice.results_reader import read_raw
from pade.utils.parallel import run_parallel
from pdk.sky130.config import config
from src.testbenches.inverter import InverterACTB


class IVACRunner:
    """Runner for inverter small-signal AC gain.

    Instantiate with fixed sizing, then run single simulations or sweep VDD.

    Example:
        runner = IVACRunner(wn=1.5, wp=3, l=0.3)
        result = runner.run_and_evaluate(vdd=1.8)
        print(result['dc_gain_db'])

        # Sweep VDD in parallel
        sweep = runner.sweep_vdd(np.linspace(0.4, 1.8, 8))
    """

    def __init__(self, wn: float, wp: float, l: float, cl: float = 100e-15):
        self.wn = wn
        self.wp = wp
        self.l = l
        self.cl = cl
        self.simulator = NgspiceSimulator(
            output_dir=config.sim_data_dir / 'inv_dc_gain'
        )

    def _build_statements(self) -> list[Statement]:
        return [
            Statement(f'.lib "{config.sky130_lib}" tt'),
            Analysis('ac', start=1, stop=1e9, points=10),
            Save(['out']),
        ]

    def _build_tb(self, vdd: float) -> InverterACTB:
        return InverterACTB(vdd=vdd, wn=self.wn, wp=self.wp, l=self.l, cl=self.cl)

    def _identifier(self, vdd: float) -> str:
        return f'L{self.l}_VDD{vdd:.2f}'

    def run(self, vdd: float, **kwargs) -> Path:
        """Run single AC simulation. Returns path to raw file."""
        tb = self._build_tb(vdd)
        statements = self._build_statements()
        return self.simulator.simulate(
            tb, statements, self._identifier(vdd), show_output=False
        )

    def evaluate(self, raw_file: Path) -> dict:
        """Extract DC gain from AC raw file."""
        data = read_raw(raw_file)
        vout = data['v(out)']
        dc_gain = np.abs(vout[0])
        return {
            'dc_gain': dc_gain,
            'dc_gain_db': 20 * np.log10(dc_gain),
        }

    def run_and_evaluate(self, vdd: float, **kwargs) -> dict:
        """Run single simulation and extract DC gain."""
        raw_file = self.run(vdd, **kwargs)
        result = self.evaluate(raw_file)
        result['vdd'] = vdd
        result['raw_file'] = raw_file
        return result

    def sweep_vdd(self, vdd_values, max_workers: int = 4) -> dict:
        """Sweep VDD in parallel. Returns dict with arrays for plotting.

        Returns:
            {'vdd': np.array, 'dc_gain_db': np.array}
        """
        statements = self._build_statements()
        simulations = [
            (self._build_tb(float(vdd)), statements, self._identifier(float(vdd)))
            for vdd in vdd_values
        ]

        raw_files = run_parallel(self.simulator, simulations, max_workers=max_workers)

        gains_db = []
        for vdd in vdd_values:
            raw_file = raw_files.get(self._identifier(float(vdd)))
            if raw_file:
                result = self.evaluate(raw_file)
                gains_db.append(result['dc_gain_db'])
            else:
                gains_db.append(np.nan)

        return {
            'vdd': np.asarray(vdd_values),
            'dc_gain_db': np.asarray(gains_db),
        }
