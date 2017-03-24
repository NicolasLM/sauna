import unittest
import threading
import socket
import os
try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

from sauna import Sauna, ServiceCheck
from sauna.consumers import base, ConsumerRegister
from sauna.consumers.ext import nsca
from sauna.consumers.ext.http_server.html import get_check_html


class DumbConsumer(base.QueuedConsumer):

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
        Sauna.import_submodules('sauna.consumers.ext')
        consumers = ConsumerRegister.all_consumers
        self.assertIsInstance(consumers, dict)
        self.assertGreater(len(consumers), 1)
        for consumer_name, consumer_info in consumers.items():
            self.assertIn('consumer_cls', consumer_info)
            self.assert_(issubclass(consumer_info['consumer_cls'],
                                    base.Consumer))

    def test_get_consumer(self):
        stdout_consumer = ConsumerRegister.get_consumer('Stdout')
        self.assert_(issubclass(stdout_consumer['consumer_cls'],
                                base.Consumer))
        must_be_none = ConsumerRegister.get_consumer('Unknown')
        self.assertIsNone(must_be_none)

    @mock.patch('sauna.consumers.base.time')
    def test_consumer_send_success(self, time_mock):
        time_mock.time.return_value = 1461363313
        must_stop = threading.Event()
        s = ServiceCheck(
            timestamp=1461363313,
            hostname='node-1.domain.tld',
            name='dumb_check',
            status=0,
            output='Check okay'
        )
        dumb_consumer = DumbConsumer({})
        dumb_consumer.try_send(s, must_stop)
        self.assertIs(s, dumb_consumer.last_service_check)

    @mock.patch('sauna.consumers.base.time')
    def test_consumer_send_failure(self, time_mock):
        time_mock.time.return_value = 1461363313
        must_stop = threading.Event()
        s = ServiceCheck(
            timestamp=1461363313,
            hostname='node-1.domain.tld',
            name='dumb_check',
            status=0,
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
        stdout_consumer = (ConsumerRegister.
                           get_consumer('Stdout')['consumer_cls']({}))
        stdout_consumer._wait_before_retry(must_stop)
        time_mock.sleep.assert_called_with(1)
        self.assertEquals(time_mock.sleep.call_count,
                          stdout_consumer.retry_delay)

    def test_get_current_status(self):
        foo = ServiceCheck(timestamp=42, hostname='server1',
                           name='foo', status=0, output='foo out')
        bar = ServiceCheck(timestamp=42, hostname='server1',
                           name='bar', status=1, output='bar out')
        with mock.patch.dict('sauna.check_results'):
            self.assertEquals(base.AsyncConsumer.get_current_status(),
                              ('OK', 0))
        with mock.patch.dict('sauna.check_results', foo=foo):
            self.assertEquals(base.AsyncConsumer.get_current_status(),
                              ('OK', 0))
        with mock.patch.dict('sauna.check_results', foo=foo, bar=bar):
            self.assertEquals(base.AsyncConsumer.get_current_status(),
                              ('WARNING', 1))

    def test_get_checks_as_dict(self):
        foo = ServiceCheck(timestamp=42, hostname='server1',
                           name='foo', status=0, output='foo out')
        bar = ServiceCheck(timestamp=42, hostname='server1',
                           name='bar', status=1, output='bar out')
        with mock.patch.dict('sauna.check_results', foo=foo, bar=bar):
            self.assertDictEqual(base.AsyncConsumer.get_checks_as_dict(), {
                'foo': {
                    'status': 'OK',
                    'code': 0,
                    'timestamp': 42,
                    'output': 'foo out'
                },
                'bar': {
                    'status': 'WARNING',
                    'code': 1,
                    'timestamp': 42,
                    'output': 'bar out'
                }
            })


class ConsumerNSCATest(unittest.TestCase):

    def setUp(self):
        self.nsca = nsca.NSCAConsumer({})

    def test_encrypt_xor(self):
        encrypt_xor = nsca.encrypt_xor
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
        self.nsca.config['encryption'] = 0
        self.assertEquals(
            self.nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                               bytes.fromhex('5555')),
            bytes.fromhex('EEEE')
        )

    def test_xor_encryption(self):
        self.nsca.config.update({'encryption': 1, 'key': b'plop'})
        self.assertEquals(
            self.nsca._encrypt_service_payload(bytes.fromhex('EEEE'),
                                               bytes.fromhex('5555')),
            bytes.fromhex('CBD7')
        )

    @mock.patch('sauna.consumers.ext.nsca.socket')
    def test_get_receivers_addresses(self, socket_mock):
        socket_mock.getaddrinfo.return_value = [
            (None, None, None, None, ('7.7.7.7', 5667)),
            (None, None, None, None, ('8.8.8.8', 5667)),
            (None, None, None, None, ('9.9.9.9', 5667))
        ]
        self.assertListEqual(self.nsca._get_receivers_addresses(),
                             ['7.7.7.7', '8.8.8.8', '9.9.9.9'])

        # Test with an already known good receiver
        self.nsca._last_good_receiver_address = '9.9.9.9'
        self.assertListEqual(self.nsca._get_receivers_addresses(),
                             ['9.9.9.9', '7.7.7.7', '8.8.8.8'])

    def test_send(self):
        self.nsca._get_receivers_addresses = lambda: ['7.7.7.7', '8.8.8.8']
        self.nsca._send_to_receiver = lambda x, y: None

        self.assertEqual(self.nsca._last_good_receiver_address, None)
        self.nsca._send(None)
        self.assertEqual(self.nsca._last_good_receiver_address, '7.7.7.7')

        def raise_socket_timeout(*args, **kwargs):
            raise socket.timeout()

        self.nsca._send_to_receiver = raise_socket_timeout
        with self.assertRaises(IOError):
            self.nsca._send(None)
        self.assertEqual(self.nsca._last_good_receiver_address, '7.7.7.7')


class ConsumerHTTPTest(unittest.TestCase):
    @mock.patch('sauna.consumers.base.AsyncConsumer.get_checks_as_dict')
    def test_escape_html(self, m_get_checks_as_dict):
        os.environ['TZ'] = 'UTC'
        m_get_checks_as_dict.return_value = {
            '<h1>test</h1>': {
                    'status': 'Warning',
                    'code': 1,
                    'timestamp': 12345678,
                    'output': "<script>test</script>"
            }
        }
        html_check = get_check_html()
        self.assertEqual(
            html_check,
            '<tr><td>&lt;h1&gt;test&lt;/h1&gt;</td>'
            '<td><span class="st st_1">Warning</span></td>'
            '<td>&lt;script&gt;test&lt;/script&gt;</td>'
            '<td>1970-05-23 21:21:18</td></tr>')
