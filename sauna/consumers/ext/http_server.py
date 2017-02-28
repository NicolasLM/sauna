import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from logging import getLogger

from sauna.consumers.base import AsyncConsumer
from sauna.consumers import ConsumerRegister
from sauna import __version__

logger = getLogger('sauna.HTTPServerConsumer')
my_consumer = ConsumerRegister('HTTPServer')


class StoppableHTTPServer(HTTPServer):
    """HTTPServer that stops itself when receiving a threading.Event"""

    def __init__(self, must_stop, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._must_stop = must_stop

    def service_actions(self):
        """Called by the serve_forever() loop.

        Check if Sauna requested the server to shutdown.
        It cannot call self.shutdown() because the server does not run in
        a separated thread.
        """
        if self._must_stop.is_set():
            self._BaseServer__shutdown_request = True


@my_consumer.consumer()
class HTTPServerConsumer(AsyncConsumer):

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'port': config.get('port', 8080),
            'address': config.get('address', '')  # listen on all interfaces
        }

    def run(self, must_stop, *args):
        http_server = StoppableHTTPServer(
            must_stop,
            (self.config['address'], self.config['port']),
            Handler
        )
        http_server.serve_forever()
        self.logger.debug('Exited consumer thread')

    @staticmethod
    def config_sample():
        return '''
        # HTTP Server that exposes sauna status as a REST API
        - type: HTTPServer
          port: 8080
        '''


class NotFoundError(Exception):
    pass


class Handler(BaseHTTPRequestHandler):

    server_version = 'Sauna/' + __version__

    def do_GET(self):
        data = self.generate_response()
        self.wfile.write(data)

    def do_HEAD(self):
        self.generate_response()

    def generate_response(self):
        try:
            content = self.get_content_from_path()
            code = 200
        except NotFoundError:
            content = {'error': 'Resource not found'}
            code = 404
        data = json.dumps(content).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        return data

    def get_content_from_path(self):
        if self.path == '/':
            status, code = HTTPServerConsumer.get_current_status()
            return {
                'status': status,
                'code': code,
                'checks': HTTPServerConsumer.get_checks_as_dict()
            }
        else:
            raise NotFoundError()

    def log_message(self, format, *args):
        logger.debug('{} {}'.format(self.address_string(), format % args))
