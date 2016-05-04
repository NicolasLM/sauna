import re
import socket

from sauna.plugins import (Plugin, bytes_to_human, human_to_bytes,
                           PluginRegister)

my_plugin = PluginRegister('Memcached')


@my_plugin.plugin()
class Memcached(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 11211),
            'timeout': config.get('timeout', 5)
        }
        self._stats = None

    @my_plugin.check()
    def accepting_connections(self, check_config):
        try:
            accept_connections = self.stats['accepting_conns'] == 1
        except OSError as e:
            return (Plugin.STATUS_CRIT,
                    'Memcached is not accepting connections: {}'.format(e))
        if accept_connections:
            return Plugin.STATUS_OK, 'Memcached is accepting connections'
        else:
            return Plugin.STATUS_CRIT, 'Memcached is not accepting connections'

    @my_plugin.check()
    def bytes(self, check_config):
        status = self._value_to_status_less(self.stats['bytes'], check_config,
                                            human_to_bytes)
        output = 'Memcached memory: {}'.format(
            bytes_to_human(self.stats['bytes'])
        )
        return status, output

    @my_plugin.check()
    def used_percent(self, check_config):
        used_percent = int(
            self.stats['bytes'] * 100 / self.stats['limit_maxbytes']
        )
        status = self._value_to_status_less(used_percent, check_config,
                                            self._strip_percent_sign)
        output = 'Memcached memory used: {}% of {}'.format(
            used_percent, bytes_to_human(self.stats['limit_maxbytes'])
        )
        return status, output

    @my_plugin.check()
    def current_items(self, check_config):
        status = self._value_to_status_less(self.stats['curr_items'],
                                            check_config)
        output = 'Memcached holds {} items'.format(self.stats['curr_items'])
        return status, output

    @property
    def stats(self):
        if not self._stats:
            self._stats = self._raw_stats_to_dict(
                self._fetch_memcached_stats()
            )
        return self._stats

    @classmethod
    def _raw_stats_to_dict(cls, stats_data):
        """Convert raw memcached output to a dict of stats."""
        stats_string = stats_data.decode('ascii')
        stats_string = stats_string.replace('\r\n', '\n')
        matches = re.findall(r'^STAT (\w+) (\d+)$', stats_string,
                             flags=re.MULTILINE)
        return {match[0]: int(match[1]) for match in matches}

    def _fetch_memcached_stats(self):
        """Connect to Memcached and retrieve stats."""
        data = bytes()
        with socket.create_connection((self.config['host'],
                                       self.config['port']),
                                      timeout=self.config['timeout']) as s:
            s.sendall(b'stats\r\n')
            while True:
                buffer = bytearray(4096)
                bytes_received = s.recv_into(buffer)
                if bytes_received == 0:
                    # Remote host closed connection
                    break
                data += buffer
                if b'\r\nEND\r\n' in data:
                    # End of the stats command
                    break
        return data

    @staticmethod
    def config_sample():
        return '''
        # Memcached
        - type: Memcached
          checks:
            - type: bytes
              warn: 128M
              crit: 256M
            - type: used_percent
              warn: 80%
              crit: 90%
            - type: current_items
              warn: 10000
              crit: 20000
            - type: accepting_connections
          config:
            host: localhost
            port: 11211
        '''
