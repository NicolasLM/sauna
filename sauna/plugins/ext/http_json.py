from sauna.plugins import Plugin, PluginRegister
from sauna.plugins.ext.http import HTTP
from sauna import DependencyError
import re
import json

my_plugin = PluginRegister('HTTP-JSON')


@my_plugin.plugin()
class HTTPJSON(HTTP):
    def __init__(self, config):
        super().__init__(config)
        try:
            import jsonpath_rw as jsonpath
            self.jsonpath = jsonpath
        except ImportError:
            raise DependencyError(self.__class__.__name__, 'jsonpath_rw',
                                  pypi='jsonpath-rw')

    @my_plugin.check()
    def request(self, check_config):
        code = check_config.get('code', 200)
        expect = check_config.get('expect', None)

        try:
            r = self._do_http_request(check_config)
        except Exception as e:
            return Plugin.STATUS_CRIT, '{}'.format(e)

        if r.status_code != code:
            return (
                Plugin.STATUS_CRIT,
                self._error_message(
                    'Got status code {} instead of {}'.format(
                        r.status_code, code),
                    r, check_config)
            )

        if expect is not None:
            regex = re.compile(expect)
            if 'success_jsonpath' in check_config:
                finder = self.jsonpath.parse(check_config['success_jsonpath'])
                try:
                    data = json.loads(r.text)
                except ValueError as ex:
                    return (
                        Plugin.STATUS_CRIT,
                        self._error_message(
                            'Fail to parse response as JSON: {}'.format(ex),
                            r, check_config)
                    )
                matches = finder.find(data)
                found = any(regex.match(str(match.value)) for match in matches)
            else:
                found = bool(regex.match(r.text))

            if not found:
                return (
                    Plugin.STATUS_CRIT,
                    self._error_message(
                        'Could not find expected result ({})'.format(expect),
                        r, check_config)
                )

        elapsed_ms = int(r.elapsed.microseconds / 1000)
        return (
            self._value_to_status_less(elapsed_ms, check_config),
            'HTTP {} in {} ms'.format(r.status_code, elapsed_ms)
        )

    def _error_message(self, msg, r, check_config):
        error_jsonpath = check_config.get('error_jsonpath', None)
        if error_jsonpath is None:
            return msg
        try:
            data = json.loads(r.text)
        except ValueError:
            return msg
        finder = self.jsonpath.parse(error_jsonpath)
        matches = finder.find(data)
        for m in matches:
            msg += ', {}: {}'.format(m.path, m.value)
        return msg

    @staticmethod
    def config_sample():
        return '''
        # Make an HTTP request and parse the result as JSON
        # timeout, warn and crit are durations in milliseconds
        # If success_jsonpath is undefined, the whole response
        # is matched against the expect regex
        # If error_jsonpath is defined, all matches within the
        # response are returned with the check result
        - type: HTTP-JSON
          checks:
            - type: request
              url: https://www.website.tld/status
              verify_ca_crt: false
              method: GET
              code: 200
              success_jsonpath: '$.status'
              expect: (ok|OK)
              error_jsonpath: '$.message'
              timeout: 5000
              warn: 1000
              crit: 5000
        '''
