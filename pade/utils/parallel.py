"""
Parallel simulation utilities.
"""

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.statement import Statement
    from pade.backends.base import Simulator


def _run_single(args: tuple) -> tuple[str, Optional[Path], Optional[str], float]:
    """
    Worker function for parallel simulation.

    Returns:
        (identifier, raw output path or None, error message or None, elapsed_time)
    """
    (simulator_class, simulator_kwargs, cell, statements, identifier) = args

    start_time = time.time()

    try:
        # Recreate simulator in worker process
        simulator = simulator_class(**simulator_kwargs)

        # Run simulation using simulator's own method
        results = simulator.simulate(
            cell, statements, identifier, show_output=False
        )
        elapsed = time.time() - start_time
        return (identifier, results, None, elapsed)
    except Exception as e:
        elapsed = time.time() - start_time
        return (identifier, None, str(e), elapsed)


def run_parallel(
    simulator: 'Simulator',
    simulations: list[tuple['Cell', list['Statement'], str]],
    max_workers: int = 4,
) -> dict[str, Optional[Path]]:
    """
    Run multiple simulations in parallel.

    Args:
        simulator: Simulator instance (with output_dir already set)
        simulations: List of (cell, statements, identifier) tuples
        max_workers: Maximum parallel processes

    Returns:
        Dict mapping identifier to raw output path (or None if failed)

    Example:
        simulator = SpectreSimulator(output_dir='./sim', ...)
        results = run_parallel(
            simulator,
            simulations=[
                (tb, statements_tt, 'corner_tt'),
                (tb, statements_ff, 'corner_ff'),
                (tb, statements_ss, 'corner_ss'),
            ],
            max_workers=4,
        )
    """
    import pade

    # Disable logging for clean output
    pade.set_log_level('SILENT')

    # Extract simulator kwargs for recreation in workers
    simulator_class = type(simulator)
    simulator_kwargs = _get_simulator_kwargs(simulator)

    num_sims = len(simulations)
    actual_workers = min(max_workers, num_sims)

    print(f'Running {num_sims} simulations with {actual_workers} workers...')

    # Prepare arguments
    args_list = []
    for cell, statements, identifier in simulations:
        args_list.append((
            simulator_class, simulator_kwargs, cell, statements, identifier
        ))

    results = {}
    completed = 0

    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = {executor.submit(_run_single, args): args[4] for args in args_list}

        for future in as_completed(futures):
            identifier, result_path, error, elapsed = future.result()
            results[identifier] = result_path
            completed += 1

            if error:
                print(f'  [{completed}/{num_sims}] {identifier}: FAILED ({elapsed:.1f}s) - {error}')
            else:
                print(f'  [{completed}/{num_sims}] {identifier}: OK ({elapsed:.1f}s)')

    failed = sum(1 for v in results.values() if v is None)
    print(f'Completed {num_sims - failed}/{num_sims} simulations')

    # Re-enable logging
    pade.set_log_level('INFO')

    return results


def _get_simulator_kwargs(simulator: 'Simulator') -> dict:
    """
    Extract kwargs needed to recreate simulator in worker process.

    Each backend's simulator should be reconstructable from these kwargs.
    """
    kwargs = {}

    # Common attributes that simulators may have
    for attr in ['output_dir', 'setup_script', 'command_options', 'format']:
        if hasattr(simulator, attr):
            kwargs[attr] = getattr(simulator, attr)

    # Handle nested attributes (like writer.global_nets for Spectre)
    if hasattr(simulator, 'writer') and hasattr(simulator.writer, 'global_nets'):
        kwargs['global_nets'] = simulator.writer.global_nets

    return kwargs
