import locale
import ssl
import socket
from datetime import datetime

from sauna.plugins import Plugin, PluginRegister

plugin = PluginRegister('SSL-CERT')


@plugin.plugin()
class SslCert(Plugin):

    @plugin.check()
    def validity(self, check_config):
        host = check_config['host']
        port = check_config.get('port', 443)
        cert_file = check_config.get('cert_file', None)
        min_valid_days = check_config.get('min_valid_days', 30)

        try:
            duration = self._get_cert_duration(host, port, cert_file)
        except Exception as ex:
            return (
                Plugin.STATUS_CRIT,
                'Unable to open an SSL connection to {}: {}'.format(host, ex)
            )

        status = Plugin.STATUS_OK
        if duration.days < min_valid_days:
            status = Plugin.STATUS_WARN

        return (
            status,
            'SSL certificate of {} valid for {}'.format(host, duration)
        )

    def _get_cert_duration(self, host, port, cert_file):
        context = self._get_ssl_context(cert_file)

        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                ssock.do_handshake()
                cert = ssock.getpeercert()
                # strftime is locale-dependent, but the certificate date is not
                until = self._parse_c_date(cert['notAfter'])
                now = datetime.utcnow()
                return until - now

    def _get_ssl_context(self, cert_file):
        # Use secure defaults, but only available with python 3.4+
        try:
            from ssl import create_default_context

            return create_default_context(cafile=cert_file)
        except ImportError:
            pass

        # Fallback for old python versions
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.verify_mode = ssl.CERT_REQUIRED

        if cert_file:
            context.load_verify_locations(cert_file, None, None)
        else:
            context.set_default_verify_paths()

        return context

    def _parse_c_date(self, datestring):
        old = locale.setlocale(locale.LC_ALL)

        try:
            locale.setlocale(locale.LC_ALL, 'C')
            return datetime.strptime(datestring, '%b %d %H:%M:%S %Y %Z')
        finally:
            locale.setlocale(locale.LC_ALL, old)

    @staticmethod
    def config_sample():
        return '''
        # Check that the SSL certificate of a host is valid and will remain
        # so for some time
        - type: SSL-CERT
          checks:
            - type: validity
              # Required
              host: my.server.net
              # Optional
              port: 886                     # Default: 443
              min_valid_days: 60            # Default: 30
              cert_file: /var/my_cert.crt   # Default: system certificates
        '''
