from sauna.consumers.base import QueuedConsumer
from sauna.consumers import ConsumerRegister

my_consumer = ConsumerRegister('HTTP')


@my_consumer.consumer()
class HTTPConsumer(QueuedConsumer):

    def __init__(self, config):
        super().__init__(config)
        try:
            import requests
            self.requests = requests
        except ImportError:
            from .. import DependencyError
            raise DependencyError(self.__class__.__name__, 'requests',
                                  'requests', 'python3-requests')
        self.config = {
            'url': config.get('url', 'http://localhost'),
            'timeout': config.get('timeout', 60),
            'headers': config.get('headers', None)
        }

    def _send(self, service_check):
        data = {
            'timestamp': service_check.timestamp,
            'hostname': service_check.hostname,
            'service': service_check.name,
            'status': service_check.status,
            'output': service_check.output
        }
        response = self.requests.post(
            self.config['url'], timeout=self.config['timeout'],
            headers=self.config['headers'], json=data
        )
        response.raise_for_status()

    @staticmethod
    def config_sample():
        return '''
        # Posts a service check trough HTTP
        # Payload is serialized in JSON
        HTTP:
          url: http://server.tld/services
          timeout: 60
          headers:
            X-Auth-Token: XaiZevii0thaemaezaeJ
        '''
