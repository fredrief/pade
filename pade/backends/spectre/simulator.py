"""
Spectre simulator interface.
"""

from typing import Optional, Union

import subprocess
import time
from pathlib import Path
from pade.backends.base import Simulator
from pade.backends.spectre.netlist_writer import SpectreNetlistWriter
from pade.core.cell import Cell
from pade.statement import Statement
from pade.logging import logger


class SpectreSimulator(Simulator):
    """
    Runs Spectre simulations.

    Args:
        output_dir: Root directory for simulation outputs.
        setup_script: Path to shell script that sets up Cadence environment.
                      Sourced before running spectre (required for Jupyter).
        command_options: Default command line options for spectre.
        format: Output format ('psfascii' or 'psfbin').
        global_nets: Global nets declaration.

    Example:
        simulator = SpectreSimulator(
            output_dir='./sim',
            setup_script='/tools/cadence/setup.sh',
            command_options=['+mt', '++aps'],
        )
        results = simulator.simulate(tb, statements, 'run1')
    """

    def __init__(self,
                 output_dir: Union[str, Path],
                 setup_script: Union[str, Optional[Path]] = None,
                 command_options: Optional[list[str]] = None,
                 format: str = 'psfascii',
                 global_nets: str = '0'):
        self.output_dir = Path(output_dir)
        self.setup_script = Path(setup_script) if setup_script else None
        self.command_options = command_options or []
        self.format = format
        self.writer = SpectreNetlistWriter(global_nets=global_nets)

    def simulate(self,
                 cell: Cell,
                 statements: list[Statement],
                 identifier: str,
                 extra_options: Optional[list[str]] = None,
                 show_output: bool = True) -> Path:
        """
        Run Spectre simulation.

        Args:
            cell: Top-level cell (testbench)
            statements: List of statements (analyses, options, etc.)
            identifier: Simulation identifier (creates subdirectory)
            extra_options: Additional CLI options for this run only
            show_output: Show live output from spectre

        Returns:
            Path to raw output directory (contains per-analysis PSF files)
        """
        sim_dir = self.output_dir / identifier
        sim_dir.mkdir(parents=True, exist_ok=True)

        # Generate netlist
        netlist_path = self.writer.write_netlist(cell, sim_dir, statements)
        logger.info(f'Netlist written to {netlist_path}')

        # Run simulation
        # Note: Spectre creates multiple files in raw_dir (one per analysis)
        raw_dir = sim_dir / 'raw'
        stdout_file = sim_dir / 'spectre.out'
        success = self.run(netlist_path, raw_dir, stdout_file=stdout_file,
                          extra_options=extra_options, show_output=show_output)

        if success:
            return raw_dir
        else:
            raise RuntimeError('Spectre simulation failed')

    def run(self,
            netlist_path: Union[str, Path],
            output_dir: Union[str, Path],
            stdout_file: Union[str, Optional[Path]] = None,
            extra_options: Optional[list[str]] = None,
            show_output: bool = True) -> bool:
        """
        Run Spectre on existing netlist.

        Args:
            netlist_path: Path to netlist file
            output_dir: Directory for raw output
            stdout_file: File to write stdout (for checking progress)
            extra_options: Additional CLI options for this run
            show_output: Continuously print last line of output

        Returns:
            True if successful
        """
        netlist_path = Path(netlist_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Simulation directory (parent of raw output)
        sim_dir = output_dir.parent

        # Build spectre command
        spectre_cmd = ['spectre', str(netlist_path)]
        spectre_cmd.extend(['-raw', str(output_dir)])
        spectre_cmd.extend(['-format', self.format])

        # Note: spectre creates log file and ahdlSimDB in cwd (sim_dir)

        spectre_cmd.extend(self.command_options)
        if extra_options:
            spectre_cmd.extend(extra_options)

        # Wrap with setup script if provided
        if self.setup_script:
            cmd = ['bash', '-c', f'source {self.setup_script} && {" ".join(spectre_cmd)}']
        else:
            cmd = spectre_cmd

        logger.info(f'Running: {" ".join(cmd)}')

        start_time = time.time()

        # Run with live output display
        # Run from sim_dir so any other output files go there
        stdout_file = Path(stdout_file) if stdout_file else None
        f_out = open(stdout_file, 'w') if stdout_file else None

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(sim_dir),  # Run from sim_dir
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
                        # Clear and move to next line
                        print('\r' + ' ' * min(len(current_line), 80) + '\r', end='', flush=True)
                        current_line = ''
                    elif char == '\r':
                        # Carriage return - reset current line display
                        current_line = ''
                        print('\r', end='', flush=True)
                    else:
                        current_line += char
                        # Print current line (truncated to 80 chars)
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
            logger.error(f'Spectre failed after {elapsed:.1f}s')
            if stdout_file and stdout_file.exists():
                logger.error(f'See {stdout_file} for details')
            return False

        logger.info(f'Spectre complete in {elapsed:.1f}s')
        return True
