import unittest
import threading
import time

from .context import sauna, mock
from sauna.consumers.base import QueuedConsumer


class DumbConsumer(QueuedConsumer):

    times_called = 0
    fail_next = False
    last_service_check = None

    def _send(self, service_check):
        self.times_called += 1
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError('Send check failed')
        self.last_service_check = service_check

    def _wait_before_retry(self, must_stop):
        pass


class ConsumersTest(unittest.TestCase):

    def test_get_all_consumers(self):
        consumers = sauna.consumers.ConsumerRegister.all_consumers
        self.assertIsInstance(consumers, dict)
        self.assertGreater(len(consumers), 1)
        for consumer_name, consumer_info in consumers.items():
            self.assertIn('consumer_cls', consumer_info)
            self.assert_(issubclass(consumer_info['consumer_cls'],
                                    sauna.consumers.base.Consumer))

    def test_get_consumer(self):
        stdout_consumer = sauna.consumers.ConsumerRegister\
            .get_consumer('Stdout')
        self.assert_(issubclass(stdout_consumer['consumer_cls'],
                                sauna.consumers.base.Consumer))
        must_be_none = sauna.consumers.ConsumerRegister.get_consumer('Unknown')
        self.assertIsNone(must_be_none)

    def test_consumer_send_success(self):
        must_stop = threading.Event()
        s = sauna.ServiceCheck(
            timestamp=int(time.time()),
            hostname='node-1.domain.tld',
            name='dumb_check',
            status=sauna.plugins.Plugin.STATUS_OK,
            output='Check okay'
        )
        dumb_consumer = DumbConsumer({})
        dumb_consumer.try_send(s, must_stop)
        self.assertIs(s, dumb_consumer.last_service_check)

    def test_consumer_send_failure(self):
        must_stop = threading.Event()
        s = sauna.ServiceCheck(
            timestamp=int(time.time()),
            hostname='node-1.domain.tld',
            name='dumb_check',
            status=sauna.plugins.Plugin.STATUS_OK,
            output='Check okay'
        )
        dumb_consumer = DumbConsumer({})
        dumb_consumer.fail_next = True
        dumb_consumer.try_send(s, must_stop)
        self.assertIs(s, dumb_consumer.last_service_check)
        self.assertEquals(2, dumb_consumer.times_called)

    @mock.patch('sauna.consumers.base.time')
    def test_wait_before_retry(self, time_mock):
        must_stop = threading.Event()
        stdout_consumer = sauna.consumers.ConsumerRegister\
            .get_consumer('Stdout')['consumer_cls']({})
        stdout_consumer._wait_before_retry(must_stop)
        time_mock.sleep.assert_called_with(1)
        self.assertEquals(time_mock.sleep.call_count,
                          stdout_consumer.retry_delay)


class ConsumerNSCATest(unittest.TestCase):

    def test_encrypt_xor(self):
        from sauna.consumers.ext.nsca import encrypt_xor
        data = bytes.fromhex('0000')
        iv = bytes.fromhex('0000')
        key = bytes.fromhex('0000')
        self.assertEquals(encrypt_xor(data, iv, key), bytes.fromhex('0000'))

        data = bytes.fromhex('0000')
        iv = bytes.fromhex('FF')
        key = bytes.fromhex('00')
        self.assertEquals(encrypt_xor(data, iv, key), bytes.fromhex('FFFF'))

        data = bytes.fromhex('7DE8')
        iv = bytes.fromhex('8ECA')
        key = bytes.fromhex('E1D0')
        self.assertEquals(encrypt_xor(data, iv, key), bytes.fromhex('12F2'))

    def test_no_encryption(self):
        from sauna.consumers.ext.nsca import NSCAConsumer
        nsca = NSCAConsumer({'encryption': 0})
        self.assertEquals(
            nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                          bytes.fromhex('5555')),
            bytes.fromhex('EEEE')
        )

    def test_xor_encryption(self):
        from sauna.consumers.ext.nsca import NSCAConsumer
        nsca = NSCAConsumer({'encryption': 1, 'key': 'plop'})
        self.assertEquals(
            nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                          bytes.fromhex('5555')),
            bytes.fromhex('CBD7')
        )

    @mock.patch('sauna.consumers.ext.nsca.socket')
    def test_get_receivers_addresses(self, socket_mock):
        from sauna.consumers.ext.nsca import NSCAConsumer
        socket_mock.getaddrinfo.return_value = [
            (None, None, None, None, ('7.7.7.7', 5667)),
            (None, None, None, None, ('8.8.8.8', 5667)),
            (None, None, None, None, ('9.9.9.9', 5667))
        ]
        nsca = NSCAConsumer({})
        self.assertListEqual(nsca._get_receivers_addresses(),
                             ['7.7.7.7', '8.8.8.8', '9.9.9.9'])

        # Test with a already known good receiver
        nsca._last_good_receiver_address = '9.9.9.9'
        self.assertListEqual(nsca._get_receivers_addresses(),
                             ['9.9.9.9', '7.7.7.7', '8.8.8.8'])

    def test_send(self):
        from sauna.consumers.ext.nsca import NSCAConsumer
        nsca = NSCAConsumer({})
        nsca._get_receivers_addresses = lambda: ['7.7.7.7', '8.8.8.8']
        nsca._send_to_receiver = lambda x, y: None

        self.assertEqual(nsca._last_good_receiver_address, None)
        nsca._send(None)
        self.assertEqual(nsca._last_good_receiver_address, '7.7.7.7')

        def raise_socket_timeout(*args, **kwargs):
            import socket
            raise socket.timeout()

        nsca._send_to_receiver = raise_socket_timeout
        with self.assertRaises(IOError):
            nsca._send(None)
        self.assertEqual(nsca._last_good_receiver_address, '7.7.7.7')
