# forked from http.py to match icinga Rest API
from sauna.consumers.base import QueuedConsumer
from sauna.consumers import ConsumerRegister

my_consumer = ConsumerRegister('HTTP-icinga')


@my_consumer.consumer()
class HTTPIcingaConsumer(QueuedConsumer):

    def __init__(self, config):
        super().__init__(config)
        try:
            import requests
            self.requests = requests
        except ImportError:
            from ... import DependencyError
            raise DependencyError(self.__class__.__name__, 'requests',
                                  'requests', 'python3-requests')
        self.config = {
            'url': config.get('url', 'http://localhost'),
            'timeout': config.get('timeout', 60),
            'headers': config.get('headers', None)
        }

    def _send(self, service_check):
        data = {
            "filter": (
                "host.name==\"" + service_check.hostname +
                "\" && service.name==\"" + service_check.name + "\""
            ),
            "exit_status": service_check.status,
            "plugin_output": service_check.output,
            "type": "Service"
        }
        response = self.requests.post(
            self.config['url'], timeout=self.config['timeout'],
            headers=self.config['headers'], json=data
        )
        response.raise_for_status()

    @staticmethod
    def config_sample():
        return '''
        # Posts a service check trough HTTP to Icinga
        # Payload is serialized in JSON
        - type: HTTP-icinga
          url: http://icinga.host:5665/v1/actions/process-check-result
          timeout: 60
          headers:
            accept: application/json
            authorization: ICINGA_BASIC
        '''
