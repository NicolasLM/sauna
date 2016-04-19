import socket
import re
import subprocess

from sauna.plugins import Plugin
from sauna.plugins import PluginRegister

my_plugin = PluginRegister('Postfix')


@my_plugin.plugin()
class Postfix(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 4280),
            'timeout': config.get('timeout', 5),
            'method': config.get('method', 'mailq')
        }
        self._mailq_output = None

    @my_plugin.check()
    def queue_size(self, check_config):
        queue_size = self._get_queue_size()
        return (self._value_to_status_less(queue_size, check_config),
                '{} mail(s) in queue'.format(queue_size))

    @property
    def mailq_output(self):
        if not self._mailq_output:
            if self.config['method'] == 'tcp':
                self._mailq_output = self._fetch_showq()
            else:
                self._mailq_output = self._exec_mailq_command()
        return self._mailq_output

    def _get_queue_size(self):
        if 'Mail queue is empty' in self.mailq_output:
            return 0
        if 'mail system is down' in self.mailq_output:
            raise Exception('Cannot get queue size: {}'.
                            format(self.mailq_output))
        match = re.search(
            r'^-- \d+ [GMK]bytes in (\d+) Requests?\.$',
            self.mailq_output,
            re.MULTILINE
        )
        if not match:
            raise Exception('Cannot parse mailq')
        return int(match.group(1))

    def _fetch_showq(self):
        """Connect to Postfix showq inet daemon and retrieve queue.

        This method is faster than executing mailq because it doesn't fork
        processes.
        It requires to have showq inet daemon activated which is not the case
        by default. To make showq listen on the loopback interface on port
        4280, add to your master.cf:
        127.0.0.1:4280     inet  n       -       -       -       -       showq
        """
        showq = bytes()
        with socket.create_connection((self.config['host'],
                                       self.config['port']),
                                      timeout=self.config['timeout']) as s:
            while True:
                buffer = bytearray(4096)
                bytes_received = s.recv_into(buffer)
                if bytes_received == 0:
                    break
                showq += buffer
        return showq.decode(encoding='utf-8')

    def _exec_mailq_command(self):
        """Execute mailq command to communicate with showq daemon.

        mailq invokes postqueue with a setuid bit that grant it access to the
        Unix socket of showq daemon.
        """
        p = subprocess.Popen(
            'mailq',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        stdout, _ = p.communicate(timeout=self.config['timeout'])
        return stdout

    @staticmethod
    def config_sample():
        return '''
        # Postfix queue
        Postfix:
          checks:
            - type: queue_size
              warn: 5
              crit: 10
        '''
