"""
NGspice simulator interface.
"""

from typing import Optional, Union

import subprocess
import time
from pathlib import Path
from pade.backends.base import Simulator
from pade.backends.ngspice.netlist_writer import SpiceNetlistWriter
from pade.core.cell import Cell
from pade.statement import Statement
from pade.logging import logger


class NgspiceSimulator(Simulator):
    """
    Runs NGspice simulations.

    Args:
        output_dir: Root directory for simulation outputs.
        command_options: Default command line options for ngspice.

    Example:
        simulator = NgspiceSimulator(output_dir='./sim')
        raw_path = simulator.simulate(tb, statements, 'run1')
    """

    def __init__(self,
                 output_dir: Union[str, Path],
                 command_options: Optional[list[str]] = None,
                 global_nets: str = '0',
                 ascii_output: bool = False):
        self.output_dir = Path(output_dir)
        self.command_options = command_options or []
        self.writer = SpiceNetlistWriter(global_nets=global_nets, ascii_output=ascii_output)

    def prepare(self, cell: Cell, statements: list[Statement],
                identifier: str) -> tuple[Path, Path, Path]:
        """Write netlist and prepare output paths."""
        sim_dir = self.output_dir / identifier
        sim_dir.mkdir(parents=True, exist_ok=True)
        netlist_path = self.writer.write_netlist(cell, sim_dir, statements)
        logger.info(f'Netlist written to {netlist_path}')
        raw_file = sim_dir / 'output.raw'
        stdout_file = sim_dir / 'ngspice.out'
        return netlist_path, raw_file, stdout_file

    def simulate(self,
                 cell: Cell,
                 statements: list[Statement],
                 identifier: str,
                 extra_options: Optional[list[str]] = None,
                 show_output: bool = True) -> Path:
        """Run NGspice simulation. Returns path to raw output file."""
        netlist_path, raw_file, stdout_file = self.prepare(cell, statements, identifier)
        success = self.run(netlist_path, raw_file, stdout_file=stdout_file,
                          extra_options=extra_options, show_output=show_output)
        if success:
            return raw_file
        raise RuntimeError('NGspice simulation failed')

    def run(self,
            netlist_path: Union[str, Path],
            raw_file: Union[str, Path],
            stdout_file: Union[str, Optional[Path]] = None,
            extra_options: Optional[list[str]] = None,
            show_output: bool = True) -> bool:
        """
        Run NGspice on existing netlist.

        Args:
            netlist_path: Path to netlist file
            raw_file: Path to raw output file
            stdout_file: File to write stdout
            extra_options: Additional CLI options
            show_output: Show live output

        Returns:
            True if successful
        """
        netlist_path = Path(netlist_path)
        raw_file = Path(raw_file)
        raw_file.parent.mkdir(parents=True, exist_ok=True)

        # Build ngspice command
        # -b: batch mode
        # -r: raw output file
        cmd = ['ngspice', '-b', str(netlist_path), '-r', str(raw_file)]
        cmd.extend(self.command_options)
        if extra_options:
            cmd.extend(extra_options)

        logger.info(f'Running: {" ".join(cmd)}')

        start_time = time.time()

        # Run simulation
        stdout_file = Path(stdout_file) if stdout_file else None
        f_out = open(stdout_file, 'w') if stdout_file else None

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            current_line = ''
            while True:
                char = process.stdout.read(1)
                if not char:
                    break

                # Write to file
                if f_out:
                    f_out.write(char)
                    f_out.flush()

                # Update display
                if show_output:
                    if char == '\n':
                        print('\r' + ' ' * min(len(current_line), 80) + '\r', end='', flush=True)
                        current_line = ''
                    elif char == '\r':
                        current_line = ''
                        print('\r', end='', flush=True)
                    else:
                        current_line += char
                        display = current_line[-80:] if len(current_line) > 80 else current_line
                        print(f'\r{display}', end='', flush=True)

            process.wait()
            returncode = process.returncode

            # Clear the status line
            if show_output and current_line:
                print('\r' + ' ' * min(len(current_line), 80) + '\r', end='', flush=True)

        finally:
            if f_out:
                f_out.close()

        elapsed = time.time() - start_time

        if returncode != 0:
            logger.error(f'NGspice failed after {elapsed:.1f}s')
            if stdout_file and stdout_file.exists():
                logger.error(f'See {stdout_file} for details')
            return False

        logger.info(f'NGspice complete in {elapsed:.1f}s')
        return True
