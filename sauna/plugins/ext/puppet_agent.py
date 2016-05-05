import time
from datetime import timedelta

from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('PuppetAgent')


@my_plugin.plugin()
class PuppetAgent(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'summary_path': config.get(
                'summary_path',
                '/var/lib/puppet/state/last_run_summary.yaml'
            )
        }
        self._last_run_summary = None

    @property
    def last_run_summary(self):
        import yaml
        if not self._last_run_summary:
            with open(self.config['summary_path']) as f:
                self._last_run_summary = yaml.safe_load(f)
        return self._last_run_summary

    @my_plugin.check()
    def last_run_delta(self, check_config):
        current_time = int(time.time())
        last_run_time = self.last_run_summary['time']['last_run']
        delta = current_time - last_run_time
        status = self._value_to_status_less(delta, check_config)
        output = 'Puppet last ran {} ago'.format(timedelta(seconds=delta))
        return status, output

    @my_plugin.check()
    def failures(self, check_config):
        failures = self.last_run_summary['events']['failure']
        status = self._value_to_status_less(failures, check_config)
        if failures:
            output = 'Puppet last run had {} failure(s)'.format(failures)
        else:
            output = 'Puppet ran without trouble'
        return status, output

    @staticmethod
    def config_sample():
        return '''
        # Puppet agent
        # sauna user must be able to read:
        # /var/lib/puppet/state/last_run_summary.yaml
        - type: PuppetAgent
          checks:
            - type: last_run_delta
              warn: 3600
              crit: 14400
            - type: failures
              warn: 1
              crit: 1
        '''
