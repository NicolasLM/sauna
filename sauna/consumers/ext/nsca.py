import socket
import struct
import binascii
from copy import deepcopy
import itertools

from sauna.consumers.base import QueuedConsumer
from sauna.consumers import ConsumerRegister

my_consumer = ConsumerRegister('NSCA')


def encrypt_xor(data, iv, key):
    for i in (iv, key):
        i = itertools.cycle(i)
        data = bytes(x ^ y for x, y in zip(data, i))
    return data


@my_consumer.consumer()
class NSCAConsumer(QueuedConsumer):

    protocol_version = 3
    max_hostname_size = 64
    max_service_size = 128
    max_output_size = 4096

    init_payload_fmt = '!128sL'
    init_payload_size = struct.calcsize(init_payload_fmt)
    service_payload_fmt = '!hhIIh{}s{}s{}sh'.format(
        max_hostname_size, max_service_size, max_output_size
    )
    service_payload_size = struct.calcsize(service_payload_fmt)

    encryption_functions = {
        0: lambda x, y, z: x,
        1: encrypt_xor
    }

    def __init__(self, config):
        super().__init__(config)
        self.config = {
            'server': config.get('server', 'localhost'),
            'port': config.get('port', 5667),
            'timeout': config.get('timeout', 10),
            'encryption': config.get('encryption', 0),
            'key': config.get('key', '').encode('ascii'),
        }
        self._last_good_receiver_address = None

    def _recv_init_payload(self, s):
        init_payload = bytes()
        while len(init_payload) < self.init_payload_size:
            buffer = s.recv(self.init_payload_size - len(init_payload))
            if buffer:
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
            service_check.output.encode('utf8'),
            0  # Padding
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

    def _encrypt_service_payload(self, service_payload, iv):
        try:
            encryption_mode = self.config['encryption']
            encryption_function = self.encryption_functions[encryption_mode]
        except KeyError:
            raise ValueError('Encryption mode not supported')
        data = encryption_function(service_payload, iv, self.config['key'])
        return data

    def _get_receivers_addresses(self):
        """Retrieve all the addresses associated with a hostname.

        It will return in priority the address of the last known receiver which
        accepted the previous check.
        """
        receivers = socket.getaddrinfo(
            self.config['server'], self.config['port'],
            proto=socket.IPPROTO_TCP
        )
        # Only keep the actual address
        addresses = [r[4][0] for r in receivers]
        try:
            addresses.remove(self._last_good_receiver_address)
            addresses = [self._last_good_receiver_address] + addresses
        except ValueError:
            pass
        return addresses

    def _send_to_receiver(self, service_check, receiver_address):
        with socket.socket() as s:
            s.settimeout(self.config['timeout'])
            s.connect((receiver_address, self.config['port']))
            iv, timestamp = self._recv_init_payload(s)
            service_payload = self._encode_service_payload(service_check)
            s.sendall(self._encrypt_service_payload(service_payload, iv))

    def _send(self, service_check):
        for receiver_address in self._get_receivers_addresses():
            try:
                self._send_to_receiver(service_check, receiver_address)
                self._last_good_receiver_address = receiver_address
                return
            except OSError as e:
                self.logger.info('Could not send check to receiver {}: '
                                 '{}'.format(receiver_address, e))
        raise IOError('No receiver accepted the check')

    @staticmethod
    def config_sample():
        return '''
        # Send service check to a NSCA server
        # Only encryption methods 0 and 1 are supported
        # Max plugin output is 4096 bytes
        - type: NSCA
          server: receiver.shinken.tld
          port: 5667
          timeout: 10
          encryption: 1
          key: verylongkey
        '''
