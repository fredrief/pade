import numpy as np
import numpy.linalg as nla
import os
import sys
import logging
from pade import info, display, warn, error, fatal
from shlib.shlib import to_path, mkdir



def num2string(val, asint=False, decimals=8):
    # Some special cases
    if isinstance(val, str):
        return val
    if val == 0:
        return '0'
    # Find base and prefix
    exp = 0
    while np.abs(val) < 1:
        val = val * 1000
        exp -= 3
    while np.abs(val) >= 1000:
        val = val / 1000
        exp += 3
    prefix = ''
    if exp == -3:
        prefix = 'm'
    elif exp == -6:
        prefix = 'u'
    elif exp == -9:
        prefix = 'n'
    elif exp == -12:
        prefix = 'p'
    elif exp == -15:
        prefix = 'f'
    elif exp == -18:
        prefix = 'a'
    elif exp == 3:
        prefix = 'k'
    elif exp == 6:
        prefix = 'M'
    elif exp == 9:
        prefix = 'G'
    elif exp == 12:
        prefix = 'T'
    elif exp == 15:
        prefix = 'P'

    # Format
    numstring = ""
    if asint or decimals < 1 or isinstance(val, int):
        numstring = f'{int(val)}' + prefix
    else:
        value_str = str(val)
        base_len = len(value_str.split('.')[0])
        precision = base_len + decimals
        width = 0
        numstring = f'{val:{width}.{precision}}' + prefix
    return numstring

def get_kwarg(dict, key, default=None):
    """ Returns dict[key] if exist else None """
    return dict[key] if key in dict else default

def get_logger(logf=None, name='cbadc'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logf is not None:
        handler = logging.FileHandler(logf, 'w')
        handler.setLevel(logging.INFO)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
    formatstr = '%(asctime)s - %(levelname)s\n%(message)s\n'
    formatter = logging.Formatter(formatstr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# File handling

def file_exist(filename):
    return os.path.exists(filename)

def cat(filename):
    """ Get content of file """

    try:
        with open(filename) as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return None

def writef(lines, filename):
    """ Write lines to file filename """
    with open(filename, "w") as f:
        f.writelines(lines)


# Print results
html_formatter = lambda s: '{:.4f~P}'.format(s)
