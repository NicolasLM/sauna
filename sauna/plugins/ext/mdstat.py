from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('MDStat')


@my_plugin.plugin()
class MDStat(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import pymdstat
            self.pymdstat = pymdstat
        except ImportError:
            from ... import DependencyError
            raise DependencyError(self.__class__.__name__, 'pymdstat',
                                  'pymdstat')
        self._md_stats = None

    @property
    def md_stats(self):
        if not self._md_stats:
            self._md_stats = self.pymdstat.MdStat().get_stats()
        return self._md_stats

    @my_plugin.check()
    def status(self, check_config):
        if not self.md_stats['arrays']:
            return self.STATUS_UNKNOWN, 'No RAID array detected'

        for array_name, array_infos in self.md_stats['arrays'].items():
            if array_infos['status'] != 'active':
                return self.STATUS_CRIT, '{} is in status {}'.format(
                    array_name, array_infos['status']
                )
            if array_infos['used'] != array_infos['available']:
                return self.STATUS_CRIT, '{} uses {}/{} devices'.format(
                    array_name, array_infos['used'], array_infos['available']
                )

        return self.STATUS_OK, 'All arrays are healthy'

    @staticmethod
    def config_sample():
        return '''
        # Linux MD RAID arrays
        - type: MDStat
          checks:
            - type: status
        '''
