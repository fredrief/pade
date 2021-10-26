import click
import os
from shlib.shlib import ls, lsd, lsf, rm, to_path, cp, mkdir, touch, mv

def _rename_files(old_path, new_path, oldname, newname, delete_old_files=False):
    # Rename files
    files = lsf(old_path)
    for file in files:
        try:
            newfilename = file.name.replace(oldname, newname)
            newpath = to_path(new_path, newfilename)
            with open(file, 'r') as fin:
                with open(newpath, 'w') as fout:
                    for line in fin.readlines():
                        line = line.replace(oldname, newname)
                        fout.write(line)
        except UnicodeDecodeError:
            # Delete corrupt file
            rm(newpath)
            click.echo(f'Could not read file: {newpath}')
        if delete_old_files:
            rm(file)

def _rename_dirs(old_project_path, new_project_path, delete_files=True, ignore=['sim_data', 'pycache']):
    oldname = old_project_path.name
    newname = new_project_path.name
    # Ignore simulation data
    dirs = lsd(old_project_path)
    for dir in dirs:
        if not any(ignore[i] in dir.name for i in range(len(ignore))):
            newdirname = dir.name.replace(oldname, newname)
            newpath = to_path(new_project_path, newdirname)
            cp(dir, newpath)
            if delete_files:
                files = ls(newpath)
                rm(files)
            else:
                _rename_files(dir, newpath, oldname, newname)


@click.group()
def cli():
    """ Python based Analog Design Environment """
    pass


@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.argument('oldname', type=str)
@click.argument('newname', type=str)
def rename(root, oldname, newname):
    """ Rename project in root directory 'root' with name 'oldname' to 'newname' """
    old_project_path = to_path(root, oldname)
    new_project_path = to_path(root, newname)
    mkdir(new_project_path)

    _rename_dirs(old_project_path, new_project_path, delete_files=False, ignore=['sim_data', 'pycache'])
    _rename_files(old_project_path, new_project_path, oldname, newname, delete_old_files=True)

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

    # Rename directories and delete files within dirs
    _rename_dirs(old_project_path, new_project_path, delete_files=False, ignore=['sim_data', 'pycache'])

    _rename_files(old_project_path, new_project_path, oldname, newname)
