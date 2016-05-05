from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('HTTP')


@my_plugin.plugin()
class HTTP(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import requests
            self.requests = requests
        except ImportError:
            from ... import DependencyError
            raise DependencyError(self.__class__.__name__, 'requests',
                                  'requests', 'python3-requests')

    @my_plugin.check()
    def request(self, check_config):
        method = check_config.get('method', 'GET').upper()
        timeout = check_config.get('timeout', 10000) / 1000
        code = check_config.get('code', 200)
        content = check_config.get('content', '')

        try:
            r = self.requests.request(method, check_config['url'],
                                      timeout=timeout)
        except Exception as e:
            return Plugin.STATUS_CRIT, '{}'.format(e)

        if r.status_code != code:
            return (
                Plugin.STATUS_CRIT,
                'Got status code {} instead of {}'.format(r.status_code, code)
            )
        if content not in r.text:
            return (
                Plugin.STATUS_CRIT,
                'Content "{}" not in response'.format(content)
            )
        elapsed_ms = int(r.elapsed.microseconds / 1000)
        return (
            self._value_to_status_less(elapsed_ms, check_config),
            'HTTP {} in {} ms'.format(r.status_code, elapsed_ms)
        )

    @staticmethod
    def config_sample():
        return '''
        # Make an HTTP request
        # timeout, warn and crit are durations in milliseconds
        - type: HTTP
          checks:
            - type: request
              url: https://www.website.tld
              method: GET
              code: 200
              content: Welcome!
              timeout: 5000
              warn: 1000
              crit: 5000
        '''
