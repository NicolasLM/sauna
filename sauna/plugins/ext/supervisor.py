import xmlrpc.client
import http.client
import socket

from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('Supervisor')


@my_plugin.plugin()
class Supervisor(Plugin):

    def __init__(self, config):
        super().__init__(config)

        serverurl = config.get('serverurl', 'unix:///var/run/supervisor.sock')
        timeout = config.get('timeout', 5)
        if serverurl.startswith('unix://'):
            serverurl = serverurl.replace('unix://', '', 1)
            # xmlrpc.client does not support Unix sockets, so we must provide
            # a custom transport layer
            transport = UnixStreamTransport(serverurl, timeout=timeout)
            server = xmlrpc.client.ServerProxy('http://noop',
                                               transport=transport)
        else:
            transport = CustomHTTPTransport(timeout=timeout)
            server = xmlrpc.client.ServerProxy(serverurl, transport=transport)

        rpc_namespace = config.get('rpc_namespace', 'supervisor')
        self.supervisor = getattr(server, rpc_namespace)
        self.supervisor_addr = serverurl

    @my_plugin.check()
    def service(self, check_config):
        try:
            service = check_config['service']
        except KeyError:
            raise KeyError('A name parameter is required for Supervisor '
                           'service checks')
        states_threshold = self._get_states_threshold(check_config)

        try:
            service_info = self.supervisor.getProcessInfo(service)
        except Exception as ex:
            raise Exception('Error while contacting Supervisor at {}: {}'
                            .format(self.supervisor_addr, ex))

        service_state = service_info['statename']
        status = self._get_status(service_state, states_threshold)

        return status, 'Service {} {}'.format(service, service_state)

    @my_plugin.check()
    def services(self, check_config):
        states_threshold = self._get_states_threshold(check_config)
        whitelist = check_config.get('whitelist', [])
        blacklist = check_config.get('blacklist', [])

        def service_enabled(name):
            if blacklist and name in blacklist:
                return False
            if whitelist and name not in whitelist:
                return False
            return True

        try:
            service_infos = self.supervisor.getAllProcessInfo()
        except Exception as ex:
            raise Exception('Error while contacting Supervisor at {}: {}'
                            .format(self.supervisor_addr, ex))

        service_states = {info['name']: info['statename']
                          for info in service_infos
                          if service_enabled(info['name'])}
        service_statuses = {name: self._get_status(state, states_threshold)
                            for name, state in service_states.items()}

        status_priority = [Plugin.STATUS_OK, Plugin.STATUS_UNKNOWN,
                           Plugin.STATUS_WARN, Plugin.STATUS_CRIT]
        status_priority = {s: i for i, s in enumerate(status_priority)}

        global_status = Plugin.STATUS_OK
        for status in service_statuses.values():
            if status_priority[status] > status_priority[global_status]:
                global_status = status

        faulty_services = [name for name, status in service_statuses.items()
                           if status != Plugin.STATUS_OK]
        if faulty_services:
            msg = 'Found {} services out of {} with incorrect state: '\
                  .format(len(faulty_services), len(service_statuses)) +\
                  ', '.join('{} is {}'.format(name, service_states[name])
                            for name in faulty_services)
        else:
            msg = 'All {} services OK'.format(len(service_statuses))

        return global_status, msg

    @staticmethod
    def _get_status(state, states_threshold):
        status_name = states_threshold.get(state, 'UNKNOWN')
        status = getattr(Plugin, 'STATUS_' + status_name,
                         Plugin.STATUS_UNKNOWN)
        return status

    @staticmethod
    def _get_states_threshold(check_config):
        user_threshold = check_config.get('states', {})
        states_threshold = {
            'STARTING': 'OK',
            'RUNNING': 'OK',
            'BACKOFF': 'WARN',
            'STOPPING': 'WARN',
            'STOPPED': 'CRIT',
            'FATAL': 'CRIT'
            # Other states are translated to unknown
        }
        states_threshold.update({a.upper(): b.upper()
                                 for a, b in user_threshold.items()})
        return states_threshold

    @staticmethod
    def config_sample():
        return '''
        # Monitor services of a Supervisor instance
        # Each check can monitor one Supervisor process (type 'service') or all
        # of them (type 'services')
        # The serverurl option should be the same as the one from the
        # Supervisor config, with optional credentials added for HTTP(S)
        - type: Supervisor    # Minimal config to check local services
          checks:
            - type: services
        - type: Supervisor
          config:
            serverurl: unix:///var/run/supervisor.sock  # Same as default
          checks:
            - type: service
              name: supervisor_foo
              service: foo
              states:
                STOPPED: OK  # Allowed: UNKOWN, OK, WARN and CRIT (default)
            - type: services
              name: supervisor_services
              blacklist: [foo]
        - type: Supervisor
          config:
            serverurl: http://bob:pa$$word@example.com:9001/RPC2
            rpc_namespace: ubervisor    # Default is supervisor
            timeout: 10                 # Default is 5s
          checks:
            - type: services
              name: ubervisor_services
              whitelist: [bar,spam]
        '''


# Thanks to Adaptation (http://stackoverflow.com/a/23837147)
class UnixStreamHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.host)
        self.sock = sock


class UnixStreamTransport(xmlrpc.client.Transport):
    def __init__(self, socket_path, **conn_kwargs):
        self.socket_path = socket_path
        self._conn_kwargs = conn_kwargs
        super(UnixStreamTransport, self).__init__()

    def make_connection(self, host):
        return UnixStreamHTTPConnection(self.socket_path, **self._conn_kwargs)


class CustomHTTPTransport(xmlrpc.client.Transport):
    def __init__(self, **conn_kwargs):
        self._conn_kwargs = conn_kwargs
        super(CustomHTTPTransport, self).__init__()

    def make_connection(self, host):
        # return an existing connection if possible. This allows
        # HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        self._connection = (
            host,
            http.client.HTTPConnection(chost, **self._conn_kwargs)
        )
        return self._connection[1]
