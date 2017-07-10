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
        code = check_config.get('code', 200)
        content = check_config.get('content', '')

        try:
            r = self._do_http_request(check_config)
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

    def _do_http_request(self, check_config):
        method = check_config.get('method', 'GET').upper()
        timeout = check_config.get('timeout', 10000) / 1000
        verify_ca_crt = check_config.get('verify_ca_crt', True)
        data = check_config.get('data')
        json = check_config.get('json')
        headers = check_config.get('headers')
        params = check_config.get('params')
        auth = check_config.get('auth')
        cookies = check_config.get('cookies')
        allow_redirects = check_config.get('allow_redirects', True)
        url = check_config['url']

        return self.requests.request(method, url,
                                     verify=verify_ca_crt,
                                     timeout=timeout,
                                     data=data,
                                     json=json,
                                     headers=headers,
                                     params=params,
                                     auth=auth,
                                     cookies=cookies,
                                     allow_redirects=allow_redirects)

    @staticmethod
    def config_sample():
        return '''
        # Make an HTTP request
        # timeout, warn and crit are durations in milliseconds
        - type: HTTP
          checks:
            - type: request
              url: https://www.website.tld
              verify_ca_crt: true
              method: GET
              code: 200
              content: Welcome!
              timeout: 5000
              warn: 1000
              crit: 5000
        '''
