import re

from sauna.plugins import PluginRegister
from sauna.plugins.base import PsutilPlugin

my_plugin = PluginRegister('Processes')


@my_plugin.plugin()
class Processes(PsutilPlugin):

    @my_plugin.check()
    def count(self, check_config):
        num_pids = len(self.psutil.pids())
        return (
            self._value_to_status_less(num_pids, check_config),
            '{} processes'.format(num_pids)
        )

    @my_plugin.check()
    def zombies(self, check_config):
        zombies = [p for p in self.psutil.process_iter()
                   if p.status() == 'zombie']
        num_zombies = len(zombies)
        return (
            self._value_to_status_less(num_zombies, check_config),
            '{} zombies'.format(num_zombies)
        )

    def _count_running_processes(self, check_config):
        """Count the number of times a process is running.

        Processes are identified by their first argument 'exec' and
        additional 'args'.
        :rtype int
        """
        process_exec = check_config['exec']
        required_args = check_config.get('args', '').split()
        instances = 0

        for process in self.psutil.process_iter():
            try:
                cmdline = process.cmdline()
            except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                # Zombies and processes that stopped throw NoSuchProcess
                continue

            # Often cmdline in an empty list
            if not cmdline:
                continue

            if cmdline[0] != process_exec:
                continue

            if self._required_args_are_in_cmdline(required_args, cmdline):
                instances += 1

        return instances

    @my_plugin.check()
    def running(self, check_config):
        process = check_config['exec']
        nb = check_config.get('nb')
        instances = self._count_running_processes(check_config)

        if instances == 0:
            return self.STATUS_CRIT, 'Process {} not running'.format(process)
        if nb is None:
            return self.STATUS_OK, 'Process {} is running'.format(process)
        if instances == nb:
            return self.STATUS_OK, 'Process {} is running'.format(process)
        return (self.STATUS_WARN,
                'Process {} is running {} times'.format(process, instances))

    @my_plugin.check()
    def file_descriptors(self, check_config):
        """Check that processes and system are not running out of fd."""
        check_config = self._strip_percent_sign_from_check_config(check_config)

        # Check fds of individuals processes
        names, worst_value = self._get_processes_exhausting_fds(check_config)
        if names:
            return (
                self._value_to_status_less(worst_value, check_config),
                'Processes running out of fd: {}'.format(', '.join(names))
            )

        # Check fds of whole system
        percent_used_fds = self._get_percent_system_used_fds()
        if (self._value_to_status_less(percent_used_fds, check_config) !=
                self.STATUS_OK):
            return (
                self._value_to_status_less(percent_used_fds, check_config),
                'System using {}% of file descriptors'.format(percent_used_fds)
            )

        return self.STATUS_OK, 'File descriptors under the limits'

    def _get_processes_exhausting_fds(self, check_config):
        processes_names = set()
        highest_percentage = 0
        for process in self.psutil.process_iter():
            try:
                open_fd = process.num_fds()
                limit_fd = self._get_process_fd_limit(process.pid)
                percentage = int(open_fd * 100 / limit_fd)
                if (self._value_to_status_less(percentage, check_config) !=
                        self.STATUS_OK):
                    processes_names.add(process.name())
                if percentage > highest_percentage:
                    highest_percentage = percentage
            except (self.psutil.NoSuchProcess, self.psutil.AccessDenied,
                    OSError):
                pass
        return processes_names, highest_percentage

    @classmethod
    def _get_process_fd_limit(cls, pid):
        """Retrieve the soft limit of usable fds for a process."""
        with open('/proc/{}/limits'.format(pid)) as f:
            limits = f.read()
        match = re.search(r'^Max open files\s+(\d+)\s+\d+\s+files',
                          limits, flags=re.MULTILINE)
        if not match:
            raise Exception('Cannot parse /proc/{}/limits'.format(pid))
        return int(match.group(1))

    @classmethod
    def _get_percent_system_used_fds(cls):
        """Percentage of opened file descriptors over the whole system.

        :rtype int
        """
        with open('/proc/sys/fs/file-nr') as f:
            # Weird behavior on Python 3.2 on Wheezy:
            # f.read() does not return the entire content of this
            # particular file while it should according to the docs.
            # As the file only contains a single line, f.readline()
            # does the job.
            file_nr = f.readline()
        match = re.match(r'^(\d+)\t\d+\t(\d+)$', file_nr)
        if not match:
            raise Exception('Cannot parse /proc/sys/fs/file-nr')
        system_opened_fds = int(match.group(1))
        system_max_fds = int(match.group(2))
        return int(system_opened_fds * 100 / system_max_fds)

    @classmethod
    def _required_args_are_in_cmdline(cls, required_args, cmdline):
        for arg in required_args:
            if arg not in cmdline[1:]:
                return False
        return True

    @staticmethod
    def config_sample():
        return '''
        # Information about processes
        - type: Processes
          checks:
            # Number of processes in the system
            - type: count
              warn: 400
              crit: 500
            # Number of zombies processes in the system
            - type: zombies
              warn: 1
              crit: 5
            # File descriptors
            - type: file_descriptors
              warn: 60%
              crit: 80%
            # Critical if process is not running
            - type: running
              name: docker_running
              exec: /usr/bin/docker
              args: daemon
        '''
