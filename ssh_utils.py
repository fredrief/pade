import subprocess
import os
from pade import info, display, warn, error, fatal

class SSH_Utils:
    """
        Helper class for handling ssh connection to remote server
    """
    def __init__(self, server_address):
        """
        Parameters:
            server_address: str
                Eks: johndoe@server.domain.com
        """

        self.host = server_address

    def path_exist(self, path):
        """
        Check if path exist at remote server
        """
        return subprocess.call(['ssh', self.host, 'test', '-e', path]) == 0

    def pull(self, directory):
        """
        Run git pull
        TODO: This is currently not working
        """
        return subprocess.call(['ssh', self.host, f'cd {directory} ; git pull'], stdout=subprocess.PIPE, shell=True)

    def cat(self, path):
        """
        Read content of file
        """
        if self.path_exist(path):
            return self.check_output(['cat', path])
        return f'Path {path} does not exist'

    def check_output(self, cmd):
        try:
            res = subprocess.check_output(['ssh', self.host, *cmd])
            return res.decode('ascii')
        except:
            pass
        return 'No output generated'

    def mkdir(self, path):
        """
        Make directory
        """
        if not self.path_exist(path):
            failed = subprocess.call(['ssh', self.host, 'mkdir', path])
            if failed:
                warn(f'Failed to create directory {path} at {self.host}')
            else:
                display('\t', f'Created remote directory {path} at {self.host}')

    def clean_up(self, path):
        """
        Remove all files in directory, without deleting directory
        """
        host = self.host
        if self.path_exist(path):
            path = str(path)  + '/*'
            status = subprocess.call(['ssh', self.host, 'rm', '-r', path])

    def cp_to(self, local_path, remote_path):
        """
        Copy file to remote server
        """
        # Copy to remote
        if not os.path.exists(local_path):
            fatal(f'Failed copying to remote server. File not found: {local_path}')
        try:
            process = subprocess.Popen(["scp", '-r', local_path, f"{self.host}:{remote_path}"], stdout=subprocess.PIPE)
            sts = os.waitpid(process.pid, 0)

        except:
            fatal('Failed copying to remote server')

    def cp_from(self, remote_path, local_path):
        """
        Copy file from remote server
        """
        # Copy from remote
        if not self.path_exist(remote_path):
            fatal(f'Cannot copy from remote server. File not found: {remote_path}')
        try:
            process = subprocess.Popen(["scp", '-r', f"{self.host}:{remote_path}", local_path], stdout=subprocess.PIPE)
            sts = os.waitpid(process.pid, 0)

        except:
            err('Failed copying from remote server')

    def execute(self, commands, stdout=subprocess.PIPE):
        """
        Execute commands at remote server

        Returns:
            Process
        """
        # Remote connection commands
        popen_cmd = [
            "ssh", f"{self.host}"]
        # User commands
        for cmd in commands:
            popen_cmd.append(cmd)
        return subprocess.Popen(popen_cmd, stdout=subprocess.PIPE)


