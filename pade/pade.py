import click
import os
from shlib.shlib import to_path, cp, mkdir, touch

@click.group()
def cli():
    """ Python based Analog Design Environment """
    pass

@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.argument('name', type=str)
def setup(root, name):
    """ Setup new project in root directory 'root' with name 'name' """
    project_path = to_path(root, name)
    exist_project = os.path.exists(project_path)
    if exist_project:
        click.echo(f'Project does already exist!')
        return

    click.echo(f'Creating directories for project {name} in {root}')

    # Make root directory
    mkdir(project_path)
    path_base = f'{project_path}/{name}'

    # Make other directories
    mkdir(f'{path_base}_results')
    mkdir(f'{path_base}_daemon')
    mkdir(f'{path_base}_netlists')
    mkdir(f'{path_base}_simulation_output')
    mkdir(f'{path_base}_logs')

    # Write script template
    with open("/home/fredrief/projects/pade/templates/main.txt", 'r') as fin:
        with open(f'{path_base}.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)

    # Write testbench template
    with open("/home/fredrief/projects/pade/templates/tb.txt", 'r') as fin:
        with open(f'{path_base}_tb.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)
