"""Icarus Verilog simulation wrapper."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'


@dataclass
class SimulationResult:
    """Result of an Icarus Verilog simulation run."""
    success: bool
    vcd_path: Path | None
    log_path: Path

    def __str__(self) -> str:
        if self.success:
            lines = [f"{GREEN}Simulation successful{RESET}"]
            if self.vcd_path and self.vcd_path.exists():
                lines.append(f"VCD: {self.vcd_path}")
            return '\n'.join(lines)
        else:
            return f"{RED}Simulation failed{RESET}\nSee log: {self.log_path}"

    def __repr__(self) -> str:
        return f"SimulationResult(success={self.success}, vcd_path='{self.vcd_path}')"


class IcarusSimulator:
    """Run Verilog simulation using Icarus Verilog (iverilog + vvp).

    Example:
        from utils.iverilog import IcarusSimulator
        sim = IcarusSimulator()
        result = sim.simulate(
            verilog_files=['cic_filter.v', 'cic_filter_tb.v'],
            top_module='cic_filter_tb',
            output_dir=Path('work/cic_sim'),
        )
        print(result)
    """

    def simulate(
        self,
        verilog_files: list[str | Path],
        top_module: str,
        output_dir: str | Path,
        vcd_filename: str | None = None,
    ) -> SimulationResult:
        """Compile and run a Verilog simulation.

        Args:
            verilog_files: List of Verilog source files.
            top_module: Top-level testbench module name.
            output_dir: Directory for simulation outputs.
            vcd_filename: Expected VCD filename (as set by $dumpfile in the
                testbench). If None, defaults to '<top_module>.vcd'.

        Returns:
            SimulationResult with VCD path and log.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        binary_path = output_dir / f'{top_module}.vvp'
        log_path = output_dir / 'iverilog.log'
        vcd_filename = vcd_filename or f'{top_module}.vcd'
        vcd_path = output_dir / vcd_filename

        # Resolve all source files to absolute paths
        abs_files = [str(Path(f).resolve()) for f in verilog_files]

        # Compile with iverilog
        compile_result = subprocess.run(
            ['iverilog', '-o', str(binary_path), '-s', top_module] + abs_files,
            capture_output=True,
            text=True,
        )

        with open(log_path, 'w') as f:
            f.write('=== COMPILE ===\n')
            f.write(compile_result.stdout)
            if compile_result.stderr:
                f.write(compile_result.stderr)

        if compile_result.returncode != 0:
            return SimulationResult(
                success=False, vcd_path=None, log_path=log_path
            )

        # Run simulation with vvp (cwd = output_dir so VCD lands there)
        sim_result = subprocess.run(
            ['vvp', str(binary_path.resolve())],
            capture_output=True,
            text=True,
            cwd=output_dir,
        )

        with open(log_path, 'a') as f:
            f.write('\n=== SIMULATION ===\n')
            f.write(sim_result.stdout)
            if sim_result.stderr:
                f.write(sim_result.stderr)

        success = sim_result.returncode == 0

        return SimulationResult(
            success=success,
            vcd_path=vcd_path if success and vcd_path.exists() else None,
            log_path=log_path,
        )
