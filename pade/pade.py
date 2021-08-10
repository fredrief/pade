import click
import os
from shlib.shlib import rm, to_path, cp, mkdir, touch, mv

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
    mkdir(f'{path_base}_figures')
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

    # Write components template
    with open("/home/fredrief/projects/pade/templates/components.txt", 'r') as fin:
        with open(f'{path_base}_components.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)


@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.argument('oldname', type=click.Path(exists=True))
@click.argument('newname', type=str)
def rename(root, oldname, newname):
    """ Rename project in root directory 'root' with name 'oldname' to 'newname' """
    old_project_path = to_path(root, oldname)
    old_path_base = f'{old_project_path}/{oldname}'
    new_project_path = to_path(root, newname)
    new_path_base = f'{new_project_path}/{newname}'
    mkdir(new_project_path)

    # Rename directories
    mv(f'{old_path_base}_results', f'{new_path_base}_results')
    mv(f'{old_path_base}_figures', f'{new_path_base}_figures')
    mv(f'{old_path_base}_netlists', f'{new_path_base}_netlists')
    mv(f'{old_path_base}_simulation_output', f'{new_path_base}_simulation_output')
    mv(f'{old_path_base}_logs', f'{new_path_base}_logs')

    # Rename files
    ## Main
    touch(f'{new_path_base}.py')
    touch(f'{new_path_base}_tb.py')
    touch(f'{new_path_base}_components.py')
    with open(f'{old_path_base}.py', 'r') as fin:
        with open(f'{new_path_base}.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace(oldname, newname)
                fout.write(line)
    rm(f'{old_path_base}.py')
    ## tb
    with open(f'{old_path_base}_tb.py', 'r') as fin:
        with open(f'{new_path_base}_tb.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace(oldname, newname)
                fout.write(line)
    rm(f'{old_path_base}_tb.py')
    ## components
    with open(f'{old_path_base}_components.py', 'r') as fin:
        with open(f'{new_path_base}_components.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace(oldname, newname)
                fout.write(line)
    rm(f'{old_path_base}_components.py')
    rm(old_project_path)
