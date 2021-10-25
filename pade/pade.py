import click
import os
from shlib.shlib import ls, lsd, lsf, rm, to_path, cp, mkdir, touch, mv

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
    mkdir(f'{path_base}_sim_data')
    mkdir(f'{path_base}_notebooks')
    mkdir(f'{path_base}_verilog')

    # Write script template
    with open("/home/fredrief/projects/pade/templates/main.py", 'r') as fin:
        with open(f'{path_base}.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)

    # Write testbench template
    with open("/home/fredrief/projects/pade/templates/tb.py", 'r') as fin:
        with open(f'{path_base}_tb.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)

    # Write components template
    with open("/home/fredrief/projects/pade/templates/components.py", 'r') as fin:
        with open(f'{path_base}_components.py', 'w') as fout:
            for line in fin.readlines():
                line = line.replace('navn', name)
                fout.write(line)


@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.argument('oldname', type=str)
@click.argument('newname', type=str)
def rename(root, oldname, newname):
    """ Rename project in root directory 'root' with name 'oldname' to 'newname' """
    old_project_path = to_path(root, oldname)
    new_project_path = to_path(root, newname)
    mkdir(new_project_path)
    # In case newname hase parent dirs, get only name
    newname = newname.split("/")[-1]

    # Rename directories
    dirs = lsd(old_project_path)
    for dir in dirs:
        newdirname = dir.name.replace(oldname, newname)
        newpath = to_path(new_project_path, newdirname)
        mv(dir, newpath)

    # Rename files
    files = lsf(old_project_path)
    for file in files:
        newfilename = file.name.replace(oldname, newname)
        newpath = to_path(new_project_path, newfilename)
        touch(newpath)
        with open(file, 'r') as fin:
            with open(newpath, 'w') as fout:
                for line in fin.readlines():
                    line = line.replace(oldname, newname)
                    fout.write(line)
        rm(file)
    rm(old_project_path)


@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.argument('oldname', type=str)
@click.argument('newname', type=str)
def copy(root, oldname, newname):
    """ Copy project in root directory 'root' with name 'oldname' to 'newname' """
    old_project_path = to_path(root, oldname)
    new_project_path = to_path(root, newname)
    mkdir(new_project_path)
    # In case newname hase parent dirs, get only name
    newname = newname.split("/")[-1]

    # Rename directories and delete files within dirs
    # Ignore simulation data
    dirs = lsd(old_project_path)
    for dir in dirs:
        if not 'sim_data' in dir.name:
            newdirname = dir.name.replace(oldname, newname)
            newpath = to_path(new_project_path, newdirname)
            cp(dir, newpath)
            files = ls(newpath)
            rm(files)

    # Rename files
    files = lsf(old_project_path)
    for file in files:
        newfilename = file.name.replace(oldname, newname)
        newpath = to_path(new_project_path, newfilename)
        touch(newpath)
        with open(file, 'r') as fin:
            with open(newpath, 'w') as fout:
                for line in fin.readlines():
                    line = line.replace(oldname, newname)
                    fout.write(line)

