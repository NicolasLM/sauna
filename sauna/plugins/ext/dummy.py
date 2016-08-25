from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('Dummy')


@my_plugin.plugin()
class Dummy(Plugin):

    @my_plugin.check()
    def dummy(self, check_config):
        return (check_config.get('status', 0),
                check_config.get('output', 'OK'))

    @staticmethod
    def config_sample():
        return '''
        # Fake checks that return the provided
        # status and output
        - type: Dummy
          checks:
            - type: dummy
              status: 0
              output: Everything is alright
        '''
