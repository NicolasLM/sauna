from . import PsutilPlugin, STATUS_CRIT, STATUS_OK


class ProcessesPlugin(PsutilPlugin):

    def count(self, check_config):
        num_pids = len(self.psutil.pids())
        return (
            self._value_to_status_less(num_pids, check_config),
            '{} processes'.format(num_pids)
        )

    def running(self, check_config):
        process_exec = check_config['exec']
        required_args = check_config.get('args', '').split()

        for process in self.psutil.process_iter():
            try:
                if process.exe() != process_exec:
                    continue
                if self._required_args_are_in_cmdline(required_args,
                                                      process.cmdline()):
                    return (
                        STATUS_OK,
                        'Process {} is running'.format(process_exec)
                    )
            except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                # Zombies and processes that stopped throw NoSuchProcess
                pass
        return (
            STATUS_CRIT,
            'Process {} is not running'.format(process_exec)
        )

    def _required_args_are_in_cmdline(self, required_args, cmdline):
        for arg in required_args:
            if arg not in cmdline[1:]:
                return False
        return True

    @staticmethod
    def config_sample():
        return '''
        # Information about processes
        Processes:
          checks:
            # Number of processes in the system
            - type: count
              warn: 400
              crit: 500
            # Critical if process is not running
            - type: running
              name: docker_running
              exec: /usr/bin/docker
              args: daemon
        '''
