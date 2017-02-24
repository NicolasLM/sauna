import socket

from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('SimpleDomain')


@my_plugin.plugin()
class SimpleDomain(Plugin):

    @my_plugin.check()
    def request(self, check_config):
        domain = check_config.get('domain')
        if check_config.get('ip_version') == 6:
            af = socket.AF_INET6
        elif check_config.get('ip_version') == 4:
            af = socket.AF_INET
        else:
            af = 0

        try:
            result = socket.getaddrinfo(domain, 0, af)
        except Exception as e:
            return Plugin.STATUS_CRIT, '{}'.format(e)

        ips = [ip[4][0] for ip in result]
        return (
            Plugin.STATUS_OK,
            'Domain was resolved with {}'.format(', '.join(ips))
        )

    @staticmethod
    def config_sample():
        return '''
        # Make a domain request,
        # crit if domain can't be resolved
        - type: SimpleDomain
          checks:
            - type: request
              domain: www.website.tld
              ip_version: 4 # 4 or 6; default is both

        '''
