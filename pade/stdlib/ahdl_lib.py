import os
from pade.schematic import Cell
from pade.utils import num2string
from shlib import to_path
class ahdl_cell(Cell):
    """
    Use prewritten verilog-a model from Cadence library
    """
    def __init__(self, cell_name, instance_name, design, ahdl_lib_path, parent_cell=None, parameters={}):

        # model library directory
        modlibpath = to_path(ahdl_lib_path,cell_name,f'veriloga/veriloga.va')
        if not modlibpath.is_readable():
            raise ValueError(f'AHDL model {cell_name} does not exist')

        super().__init__(cell_name, instance_name, design, library_name="ahdl_lib", parent_cell=parent_cell, declare=False)
        self.add_multiple_terminals(parse_model(cell_name, modlibpath))
        self.ahdl_filepath=modlibpath
        self.add_parameters(parameters)


def parse_model(cell_name, path):
    """
    Parse prewritten verilog-a model from Cadence library
    """
    terminals = []
    with open(path, 'r') as fi:
        for line in fi.readlines():
            #Find declaration
            if f'module {cell_name}' in line:
                l = line.split('(')[1].split(')')[0]
                terminals = l.split(', ')
                return terminals

