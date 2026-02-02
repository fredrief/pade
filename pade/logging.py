"""
PADE logging configuration.

Usage:
    from pade.logging import logger

    logger.info('Running simulation')
    logger.warning('Terminal already exists')
    logger.error('Simulation failed')

To disable all logging:
    import pade
    pade.set_log_level('SILENT')

    # Or use standard logging levels:
    pade.set_log_level('WARNING')  # Only warnings and errors
    pade.set_log_level('ERROR')    # Only errors
"""

import logging

# Create PADE logger
logger = logging.getLogger('pade')
logger.setLevel(logging.INFO)

# Create handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def set_log_level(level: str | int) -> None:
    """
    Set PADE logging level.

    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SILENT',
               or numeric level (logging.DEBUG, etc.)

    Examples:
        pade.set_log_level('SILENT')   # Disable all logging
        pade.set_log_level('WARNING')  # Only warnings and above
        pade.set_log_level('DEBUG')    # Verbose output
    """
    if isinstance(level, str):
        level = level.upper()
        if level == 'SILENT':
            logger.setLevel(logging.CRITICAL + 1)  # Above all levels
        else:
            logger.setLevel(getattr(logging, level))
    else:
        logger.setLevel(level)
