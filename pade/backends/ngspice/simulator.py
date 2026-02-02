"""
NGspice simulator interface.
"""

from typing import Optional, Union

import subprocess
import time
from pathlib import Path
from pade.backends.base import Simulator
from pade.backends.ngspice.netlist_writer import SpiceNetlistWriter
from pade.core import Cell
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

    def simulate(self,
                 cell: Cell,
                 statements: list[Statement],
                 identifier: str,
                 extra_options: Optional[list[str]] = None,
                 show_output: bool = True) -> Path:
        """
        Run NGspice simulation.

        Args:
            cell: Top-level cell (testbench)
            statements: List of statements (analyses, options, etc.)
            identifier: Simulation identifier (creates subdirectory)
            extra_options: Additional CLI options for this run only
            show_output: Show live output from ngspice

        Returns:
            Path to raw output directory
        """
        sim_dir = self.output_dir / identifier
        sim_dir.mkdir(parents=True, exist_ok=True)

        # Generate netlist
        netlist_path = sim_dir / f'{cell.cell_name}.spice'
        self.writer.write_netlist(cell, netlist_path, statements)
        logger.info(f'Netlist written to {netlist_path}')

        # Run simulation
        raw_dir = sim_dir / 'raw'
        raw_dir.mkdir(parents=True, exist_ok=True)
        stdout_file = sim_dir / 'ngspice.out'

        success = self.run(netlist_path, raw_dir, stdout_file=stdout_file,
                          extra_options=extra_options, show_output=show_output)

        if success:
            return raw_dir
        else:
            raise RuntimeError('NGspice simulation failed')

    def run(self,
            netlist_path: Union[str, Path],
            output_dir: Union[str, Path],
            stdout_file: Union[str, Optional[Path]] = None,
            extra_options: Optional[list[str]] = None,
            show_output: bool = True) -> bool:
        """
        Run NGspice on existing netlist.

        Args:
            netlist_path: Path to netlist file
            output_dir: Directory for raw output
            stdout_file: File to write stdout
            extra_options: Additional CLI options
            show_output: Show live output

        Returns:
            True if successful
        """
        netlist_path = Path(netlist_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        raw_file = output_dir / 'output.raw'

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
