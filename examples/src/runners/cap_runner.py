"""Capacitor simulation runner."""

from pathlib import Path
import ltspice
import numpy as np

from pade.statement import Statement, Analysis, Save
from pade.backends.ngspice.simulator import NgspiceSimulator
from pdk.sky130.config import config
from src.testbenches.cap_ac import CapacitorAC


class CapRunner:
    """Runner for capacitor AC impedance simulations.

    Example:
        runner = CapRunner(w=10, l=10)
        raw = runner.run('prelayout')
        result = runner.evaluate(raw)

        # With PEX
        raw_pex = runner.run('postlayout', pex={'C1': 'rc'})
    """

    def __init__(self, **kwargs):
        self.simulator = NgspiceSimulator(output_dir=config.sim_data_dir)
        self.default_kwargs = kwargs


    def _build_statements(self, **kwargs) -> list[Statement]:
        return [
            Statement(f'.lib {config.sky130_lib} tt'),
            Analysis('ac', variation='dec',
                     points=kwargs.get('points', 10), start=kwargs.get('fstart', '1k'), stop=kwargs.get('fstop', '1G')),
            Save(['inp', 'i(Vac)']),
        ]

    def run(self, identifier: str, **kwargs) -> Path:
        """Run simulation with merged kwargs. Returns raw file path."""
        merged = {**self.default_kwargs, **kwargs}
        tb = CapacitorAC(**merged)
        statements = self._build_statements(**merged)
        return self.simulator.simulate(tb, statements, identifier)

    def evaluate(self, raw_file: Path) -> dict:
        """Parse results and compute capacitance."""
        l = ltspice.Ltspice(str(raw_file))
        l.parse()

        freq = l.get_frequency()
        v_inp = l.get_data('v(inp)')
        i_vac = l.get_data('i(vac)')
        Z = np.abs(v_inp / i_vac)

        # Capacitance at 1MHz
        idx_1M = np.argmin(np.abs(freq - 1e6))
        C = 1 / (2 * np.pi * freq[idx_1M] * Z[idx_1M])

        return {
            'freq': freq,
            'Z': Z,
            'C_1MHz': C,
        }

    def run_and_evaluate(self, identifier: str, **kwargs) -> dict:
        """Run simulation and evaluate results."""
        raw = self.run(identifier, **kwargs)
        result = self.evaluate(raw)
        result['raw_file'] = raw
        return result
