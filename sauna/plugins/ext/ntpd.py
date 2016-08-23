import time
from datetime import timedelta
import os

from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('Ntpd')


@my_plugin.plugin()
class Ntpd(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'stats_dir': config.get('stats_dir', '/var/log/ntpstats')
        }
        self._last_loop_stats = None

    @property
    def last_loop_stats(self):
        loopstats_file = os.path.join(self.config['stats_dir'], 'loopstats')
        if not self._last_loop_stats:
            with open(loopstats_file) as f:
                last_line_items = f.readlines()[-1].split()
            self._last_loop_stats = {
                'timestamp': int(os.stat(loopstats_file).st_mtime),
                'offset': float(last_line_items[2])
            }
        return self._last_loop_stats

    @my_plugin.check()
    def last_sync_delta(self, check_config):
        current_time = int(time.time())
        delta = current_time - self.last_loop_stats['timestamp']
        status = self._value_to_status_less(delta, check_config)
        output = 'Ntp sync {} ago'.format(timedelta(seconds=delta))
        return status, output

    @my_plugin.check()
    def offset(self, check_config):
        status = self._value_to_status_less(
            abs(self.last_loop_stats['offset']), check_config
        )
        output = 'Last time offset: {0:.3f}s'.format(
            self.last_loop_stats['offset']
        )
        return status, output

    @staticmethod
    def config_sample():
        return '''
        # ntpd
        # Enable statistics in /etc/ntp.conf:
        # statsdir /var/log/ntpstats/
        - type: Ntpd
          checks:
            - type: offset
              warn: 0.500
              crit: 2.0
            # Last synchronization data available
            - type: last_sync_delta
              warn: 2800
              crit: 3600
        '''
