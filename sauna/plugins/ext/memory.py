from sauna.plugins.base import PsutilPlugin
from sauna.plugins import human_to_bytes, bytes_to_human, PluginRegister

my_plugin = PluginRegister('Memory')


@my_plugin.plugin()
class Memory(PsutilPlugin):

    def __init__(self, config):
        super().__init__(config)
        self._virtual_memory = None
        self._swap_memory = None

    @my_plugin.check()
    def available(self, check_config):
        available = self.virtual_memory.available
        return (
            self._value_to_status_more(available, check_config,
                                       human_to_bytes),
            'Memory available: {}'.format(bytes_to_human(available))
        )

    @my_plugin.check()
    def used_percent(self, check_config):
        used_percent = self.virtual_memory.percent
        check_config = self._strip_percent_sign_from_check_config(check_config)
        return (
            self._value_to_status_less(used_percent, check_config),
            'Memory used: {}%'.format(used_percent)
        )

    @my_plugin.check()
    def swap_used_percent(self, check_config):
        swap_used_percent = self.swap_memory.percent
        check_config = self._strip_percent_sign_from_check_config(check_config)
        return (
            self._value_to_status_less(swap_used_percent, check_config),
            'Swap used: {}%'.format(swap_used_percent)
        )

    @property
    def virtual_memory(self):
        if not self._virtual_memory:
            self._virtual_memory = self.psutil.virtual_memory()
        return self._virtual_memory

    @property
    def swap_memory(self):
        if not self._swap_memory:
            self._swap_memory = self.psutil.swap_memory()
        return self._swap_memory

    @staticmethod
    def config_sample():
        return '''
        # System memory
        Memory:
          checks:
            - type: available
              warn: 6G
              crit: 2G
            - type: used_percent
              warn: 80%
              crit: 90%
            - type: swap_used_percent
              warn: 50%
              crit: 70%
        '''
