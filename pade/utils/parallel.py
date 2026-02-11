"""
Parallel simulation utilities.

Netlists are written in the main process (avoids pickling Cell objects).
Only simulator execution is parallelized — the Simulator object is pickled
to workers, which call its run() method with pre-written netlist paths.
"""

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.statement import Statement
    from pade.backends.base import Simulator


def _run_sim(args: tuple) -> tuple[str, Optional[str], Optional[str], float]:
    """Worker: run simulator on a pre-written netlist.

    Returns:
        (identifier, output_path or None, error message or None, elapsed_time)
    """
    from pade.logging import set_log_level
    set_log_level('SILENT')

    simulator, identifier, netlist_path, output_path, stdout_file = args
    start_time = time.time()

    try:
        success = simulator.run(
            netlist_path, output_path,
            stdout_file=stdout_file, show_output=False
        )
        elapsed = time.time() - start_time
        if success:
            return (identifier, output_path, None, elapsed)
        return (identifier, None, 'simulation failed', elapsed)
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

    Phase 1: Write all netlists in the main process (fast, no pickling of Cells).
    Phase 2: Run simulator in parallel workers (Simulator object is pickled,
             only file paths are passed).

    Args:
        simulator: Simulator instance (any backend)
        simulations: List of (cell, statements, identifier) tuples
        max_workers: Maximum parallel processes

    Returns:
        Dict mapping identifier to output path (or None if failed)

    Example:
        results = run_parallel(
            simulator,
            simulations=[
                (tb_tt, statements, 'corner_tt'),
                (tb_ff, statements, 'corner_ff'),
            ],
            max_workers=4,
        )
    """
    from pade.logging import set_log_level
    set_log_level('SILENT')

    num_sims = len(simulations)
    actual_workers = min(max_workers, num_sims)

    # Phase 1: Write netlists in main process
    sim_configs = []
    for cell, statements, identifier in simulations:
        netlist_path, output_path, stdout_file = simulator.prepare(
            cell, statements, identifier
        )
        sim_configs.append((
            simulator, identifier,
            str(netlist_path), str(output_path), str(stdout_file),
        ))

    print(f'Running {num_sims} simulations with {actual_workers} workers...')

    # Phase 2: Run simulations in parallel
    results = {}
    completed = 0

    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = {
            executor.submit(_run_sim, cfg): cfg[1]
            for cfg in sim_configs
        }

        for future in as_completed(futures):
            identifier, output_path, error, elapsed = future.result()
            results[identifier] = Path(output_path) if output_path else None
            completed += 1

            if error:
                print(f'  [{completed}/{num_sims}] {identifier}: FAILED ({elapsed:.1f}s) - {error}')
            else:
                print(f'  [{completed}/{num_sims}] {identifier}: OK ({elapsed:.1f}s)')

    failed = sum(1 for v in results.values() if v is None)
    print(f'Completed {num_sims - failed}/{num_sims} simulations')

    set_log_level('INFO')

    return results
