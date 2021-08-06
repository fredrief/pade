import numpy as np
import numpy.linalg as nla
import os


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

def get_kwarg(dict, key):
    """ Returns dict[key] if exist else None """
    return dict[key] if key in dict else None


def file_exist(filename):
    return os.path.exists(filename)
