import os

from sauna.plugins import Plugin
from sauna.plugins import PluginRegister

my_plugin = PluginRegister('Load')


@my_plugin.plugin()
class Load(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self._load = None

    @my_plugin.check()
    def load1(self, check_config):
        return (self._value_to_status_less(self.load[0], check_config),
                'Load 1: {}'.format(self.load[0]))

    @my_plugin.check()
    def load5(self, check_config):
        return (self._value_to_status_less(self.load[1], check_config),
                'Load 5: {}'.format(self.load[1]))

    @my_plugin.check()
    def load15(self, check_config):
        return (self._value_to_status_less(self.load[2], check_config),
                'Load 15: {}'.format(self.load[2]))

    @property
    def load(self):
        if not self._load:
            self._load = os.getloadavg()
        return self._load

    @staticmethod
    def config_sample():
        return '''
        # Load average
        - type: Load
          checks:
            - type: load1
              warn: 2
              crit: 4
            - type: load5
              warn: 2
              crit: 4
            - type: load15
              warn: 2
              crit: 4
        '''
