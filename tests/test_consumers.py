import unittest
import threading
import time

from .context import sauna, mock


class DumbConsumer(sauna.consumers.Consumer):

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
        consumers = sauna.consumers.get_all_consumers()
        self.assertIsInstance(consumers, tuple)
        self.assertGreater(len(consumers), 1)
        for consumer in consumers:
            self.assert_(issubclass(consumer, sauna.consumers.Consumer))

    def test_get_consumer(self):
        stdout_consumer = sauna.consumers.get_consumer('Stdout')
        self.assert_(issubclass(stdout_consumer, sauna.consumers.Consumer))
        with self.assertRaises(ValueError):
            sauna.consumers.get_consumer('Unknown')

    def test_consumer_send_success(self):
        must_stop = threading.Event()
        s = sauna.ServiceCheck(
            timestamp=int(time.time()),
            hostname='node-1.domain.tld',
            name='dumb_check',
            status=sauna.plugins.STATUS_OK,
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
            status=sauna.plugins.STATUS_OK,
            output='Check okay'
        )
        dumb_consumer = DumbConsumer({})
        dumb_consumer.fail_next = True
        dumb_consumer.try_send(s, must_stop)
        self.assertIs(s, dumb_consumer.last_service_check)
        self.assertEquals(2, dumb_consumer.times_called)

    @mock.patch('sauna.consumers.time')
    def test_wait_before_retry(self, time_mock):
        must_stop = threading.Event()
        stdout_consumer = sauna.consumers.get_consumer('Stdout')({})
        stdout_consumer._wait_before_retry(must_stop)
        time_mock.sleep.assert_called_with(1)
        self.assertEquals(time_mock.sleep.call_count,
                          stdout_consumer.retry_delay)


class ConsumerNSCATest(unittest.TestCase):

    def test_encrypt_xor(self):
        from sauna.consumers.nsca import encrypt_xor
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
        from sauna.consumers.nsca import NSCAConsumer
        nsca = NSCAConsumer({'encryption': 0})
        self.assertEquals(
            nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                          bytes.fromhex('5555')),
            bytes.fromhex('EEEE')
        )

    def test_xor_encryption(self):
        from sauna.consumers.nsca import NSCAConsumer
        nsca = NSCAConsumer({'encryption': 1, 'key': 'plop'})
        self.assertEquals(
            nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                          bytes.fromhex('5555')),
            bytes.fromhex('CBD7')
        )
