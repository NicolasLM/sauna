import socket

from sauna.plugins import (Plugin, PluginRegister)

my_plugin = PluginRegister('TCP')


@my_plugin.plugin()
class Tcp(Plugin):

    @my_plugin.check()
    def request(self, check_config):
        try:
            with socket.create_connection((check_config['host'],
                                           check_config['port']),
                                          timeout=check_config['timeout']):
                pass
        except Exception as e:
            return Plugin.STATUS_CRIT, "{}".format(e)
        else:
            return Plugin.STATUS_OK, "OK"

    @staticmethod
    def config_sample():
        return '''
        # Tcp
        - type: TCP
          checks:
            - type: request
              host: localhost
              port: 11211
              timeout: 5
        '''
