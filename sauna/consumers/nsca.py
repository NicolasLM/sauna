import socket
import struct
import binascii
from copy import deepcopy

from . import Consumer


class NSCAConsumer(Consumer):

    protocol_version = 3
    max_hostname_size = 64
    max_service_size = 128
    max_output_size = 4096

    init_payload_fmt = '!128sL'
    init_payload_size = struct.calcsize(init_payload_fmt)
    service_payload_fmt = '!hhIIh{}s{}s{}s'.format(
        max_hostname_size, max_service_size, max_output_size
    )
    service_payload_size = struct.calcsize(service_payload_fmt)

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'server': config.get('server', 'localhost'),
            'port': config.get('port', 5667),
            'timeout': config.get('timeout', 10)
        }

    def _recv_init_payload(self, s):
        init_payload = bytes()
        while len(init_payload) < self.init_payload_size:
            buffer = s.recv(self.init_payload_size - len(init_payload))
            if not buffer:
                init_payload += buffer
        return self._decode_init_payload(init_payload)

    def _decode_init_payload(self, init_payload):
        return struct.unpack(self.init_payload_fmt, init_payload)

    def _encode_service_payload(self, service_check):
        service_payload_list = [
            self.protocol_version,
            0,  # Padding
            0,  # Placeholder for CRC
            service_check.timestamp,
            service_check.status,
            service_check.hostname.encode('utf8'),
            service_check.name.encode('utf8'),
            service_check.output.encode('utf8')
        ]
        crc = binascii.crc32(struct.pack(self.service_payload_fmt,
                                         *service_payload_list))
        service_payload_list[2] = crc
        return struct.pack(self.service_payload_fmt, *service_payload_list)

    def _format_service_check(self, service_check):
        # C strings are null terminated, we need one extra char for each
        if len(service_check.hostname) > self.max_hostname_size - 1:
            raise ValueError('NSCA hostnames can be up to {} characters'.
                             format(self.max_hostname_size - 1))
        if len(service_check.name) > self.max_service_size - 1:
            raise ValueError('NSCA service names can be up to {} characters'.
                             format(self.max_service_size - 1))
        # Silently truncate output to its max length
        if len(service_check.output) > self.max_output_size - 1:
            service_check = deepcopy(service_check)
            truncate_output = self.max_output_size - 1
            service_check.output = service_check.output[:truncate_output]
        return service_check

    def _send(self, service_check):
        with socket.socket() as s:
            s.settimeout(self.config['timeout'])
            s.connect((self.config['server'], self.config['port']))
            # iv, timestamp = self._recv_init_payload(s)
            s.sendall(self._encode_service_payload(service_check))
        import time
        time.sleep(1)

    @staticmethod
    def config_sample():
        return '''
        # Send service check to a NSCA server
        # Only encryption method 0 (aka no encryption) is implemented
        # Max plugin output is 4096 bytes
        NSCA:
          server: receiver.shinken.tld
          port: 5667
          timeout: 10
        '''
