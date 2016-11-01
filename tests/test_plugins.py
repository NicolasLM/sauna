import unittest

try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

from sauna.plugins import (human_to_bytes, bytes_to_human, Plugin,
                           PluginRegister)
from sauna.plugins.ext import (puppet_agent, postfix, memcached, processes,
                               hwmon, mdstat, ntpd, dummy, http_json)
import requests_mock


class PluginsTest(unittest.TestCase):
    def test_human_to_bytes(self):
        self.assertEquals(0, human_to_bytes('0'))
        self.assertEquals(1000, human_to_bytes('1000'))
        self.assertEquals(1024, human_to_bytes('1K'))
        self.assertEquals(1024, human_to_bytes('1KiB'))
        self.assertEquals(1024, human_to_bytes('1KiO'))
        self.assertEquals(5242880, human_to_bytes('5M'))
        self.assertEquals(10737418240, human_to_bytes('10G'))

    def test_bytes_to_human(self):
        self.assertEquals('0B', bytes_to_human(0))
        self.assertEquals('1000B', bytes_to_human(1000))
        self.assertEquals('1.0K', bytes_to_human(1024))
        self.assertEquals('5.0M', bytes_to_human(5 * 1024 * 1024))
        self.assertEquals('10.0G', bytes_to_human(10 * 1024 * 1024 * 1024))

    def test_strip_percent_sign(self):
        self.assertEquals(10, Plugin._strip_percent_sign('10'))
        self.assertEquals(10, Plugin._strip_percent_sign('10%'))
        self.assertEquals(-10, Plugin._strip_percent_sign('-10%'))

    def test_strip_percent_sign_from_check_config(self):
        check_config = {
            'warn': '75%',
            'crit': 95,
            'something_random': '10'
        }
        expected_config = {
            'warn': 75,
            'crit': 95,
            'something_random': '10'
        }
        self.assertDictEqual(
            expected_config,
            Plugin._strip_percent_sign_from_check_config(check_config)
        )

    def test_get_threshold(self):
        check_config = {
            'warn': 75,
            'crit': 95,
            'something_random': '10'
        }

        # Test without modifier
        self.assertTupleEqual((95, 75), Plugin.get_thresholds(check_config))

        # Test with modifier
        def double(number):
            return number * 2

        self.assertTupleEqual(
            (190, 150),
            Plugin.get_thresholds(check_config, double)
        )

    def test_value_to_status(self):
        less = Plugin._value_to_status_less
        more = Plugin._value_to_status_more

        # Test less, imagine this check is about used RAM in percent
        check_config = {
            'warn': 75,
            'crit': 95,
        }
        self.assertEquals(Plugin.STATUS_OK, less(10, check_config))
        self.assertEquals(Plugin.STATUS_WARN, less(80, check_config))
        self.assertEquals(Plugin.STATUS_CRIT, less(100, check_config))

        # Test less, imagine this check is about free RAM in percent
        check_config = {
            'warn': 25,
            'crit': 5,
        }
        self.assertEquals(Plugin.STATUS_OK, more(50, check_config))
        self.assertEquals(Plugin.STATUS_WARN, more(20, check_config))
        self.assertEquals(Plugin.STATUS_CRIT, more(2, check_config))

    def test_get_all_plugins(self):
        plugins = PluginRegister.all_plugins
        self.assertIsInstance(plugins, dict)
        self.assertGreater(len(plugins), 1)
        for plugin_name, plugin_info in plugins.items():
            self.assertIn('plugin_cls', plugin_info)
            self.assertIn('checks', plugin_info)
            self.assert_(issubclass(plugin_info['plugin_cls'], Plugin))
            self.assertIsInstance(plugin_info['checks'], dict)

    def test_get_plugin(self):
        import sauna
        sauna.Sauna.import_submodules('sauna.plugins.ext')
        load_plugin = PluginRegister.get_plugin('Load')
        self.assert_(issubclass(load_plugin['plugin_cls'], Plugin))
        self.assertIsNone(PluginRegister.get_plugin('Unknown'))

    def test_status_code_to_str(self):
        self.assertEquals(Plugin.status_code_to_str(Plugin.STATUS_OK), 'OK')
        self.assertEquals(
            Plugin.status_code_to_str(Plugin.STATUS_WARN), 'WARNING'
        )
        self.assertEquals(
            Plugin.status_code_to_str(Plugin.STATUS_CRIT), 'CRITICAL'
        )
        self.assertEquals(
            Plugin.status_code_to_str(Plugin.STATUS_UNKNOWN), 'UNKNOWN'
        )
        self.assertEquals(
            Plugin.status_code_to_str(42), 'UNKNOWN'
        )


class PuppetAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = puppet_agent.PuppetAgent({})

    @mock.patch('sauna.plugins.ext.puppet_agent.time')
    def test_last_run_delta(self, mock_time):
        mock_time.time.return_value = 1460836285.4
        self.agent._last_run_summary = {
            'time': {
                'last_run': 1460836283
            }
        }
        self.assertTupleEqual(
            self.agent.last_run_delta({'warn': 10, 'crit': 20}),
            (Plugin.STATUS_OK, 'Puppet last ran 0:00:02 ago')
        )

        mock_time.time.return_value = 1460836295.4
        self.assertTupleEqual(
            self.agent.last_run_delta({'warn': 10, 'crit': 20}),
            (Plugin.STATUS_WARN, 'Puppet last ran 0:00:12 ago')
        )

    def test_failures(self):
        self.agent._last_run_summary = {
            'events': {
                'failure': 0
            }
        }
        self.assertTupleEqual(
            self.agent.failures({'warn': 1, 'crit': 2}),
            (Plugin.STATUS_OK, 'Puppet ran without trouble')
        )

        self.agent._last_run_summary['events']['failure'] = 1
        self.assertTupleEqual(
            self.agent.failures({'warn': 1, 'crit': 1}),
            (Plugin.STATUS_CRIT,
             'Puppet last run had 1 failure(s)')
        )

    @mock.patch('builtins.open')
    def test_get_last_run_summary(self, mock_open):
        class ContextManager:
            def __enter__(self):
                return '''
---
  time:
    last_run: 1460836283
  events:
    failure: 0
    success: 1
    total: 1
'''

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_open.return_value = ContextManager()
        expected = {
            'time': {
                'last_run': 1460836283
            },
            'events': {
                'failure': 0,
                'success': 1,
                'total': 1,
            }
        }
        self.assertEquals(self.agent._last_run_summary, None)
        self.assertDictEqual(self.agent.last_run_summary, expected)
        self.assertDictEqual(self.agent._last_run_summary, expected)


class PostfixTest(unittest.TestCase):
    def setUp(self):
        self.postfix = postfix.Postfix({})

    def test_get_queue_size(self):
        self.postfix._mailq_output = 'Mail queue is empty\n'
        self.assertEqual(self.postfix._get_queue_size(), 0)

        self.postfix._mailq_output = (
            'postqueue: fatal: Queue report unavailable '
            '- mail system is down\n'
        )
        with self.assertRaises(Exception):
            self.postfix._get_queue_size()

        self.postfix._mailq_output = '''
        -Queue ID- --Size-- ----Arrival Time---- -Sender/Recipient-------
89B3CC02*       436 Tue Apr 19 09:21:31  user@host
                                         user2@host

-- 0 Kbytes in 1 Request.
'''
        self.assertEqual(self.postfix._get_queue_size(), 1)

        self.postfix._mailq_output = '-- 105 Kbytes in 25 Requests.\n'
        self.assertEqual(self.postfix._get_queue_size(), 25)

    def test_queue_size(self):
        self.postfix._get_queue_size = lambda: 5
        self.assertTupleEqual(
            self.postfix.queue_size({'warn': 10, 'crit': 20}),
            (Plugin.STATUS_OK, '5 mail(s) in queue')
        )
        self.assertTupleEqual(
            self.postfix.queue_size({'warn': 1, 'crit': 20}),
            (Plugin.STATUS_WARN, '5 mail(s) in queue')
        )
        self.assertTupleEqual(
            self.postfix.queue_size({'warn': 1, 'crit': 2}),
            (Plugin.STATUS_CRIT, '5 mail(s) in queue')
        )


class MemcachedTest(unittest.TestCase):
    def setUp(self):
        self.memcached = memcached.Memcached({})

    def test_bytes(self):
        self.memcached._stats = {'bytes': 1024}
        self.assertTupleEqual(
            self.memcached.bytes({'warn': '2K', 'crit': '4K'}),
            (Plugin.STATUS_OK, 'Memcached memory: 1.0K')
        )
        self.assertTupleEqual(
            self.memcached.bytes({'warn': '512', 'crit': '4K'}),
            (Plugin.STATUS_WARN, 'Memcached memory: 1.0K')
        )
        self.memcached._stats = {'bytes': 100000}
        self.assertTupleEqual(
            self.memcached.bytes({'warn': '512', 'crit': '4K'}),
            (Plugin.STATUS_CRIT, 'Memcached memory: 97.7K')
        )

    def test_used_percent(self):
        self.memcached._stats = {'bytes': 512, 'limit_maxbytes': 1024}
        self.assertTupleEqual(
            self.memcached.used_percent({'warn': '40%', 'crit': '80%'}),
            (Plugin.STATUS_WARN, 'Memcached memory used: 50% of 1.0K')
        )

    def test_current_items(self):
        self.memcached._stats = {'curr_items': 100}
        self.assertTupleEqual(
            self.memcached.current_items({'warn': 50, 'crit': 200}),
            (Plugin.STATUS_WARN, 'Memcached holds 100 items')
        )

    def test_accepting_connections(self):
        self.memcached._stats = {'accepting_conns': 1}
        self.assertTupleEqual(
            self.memcached.accepting_connections({}),
            (Plugin.STATUS_OK, 'Memcached is accepting connections')
        )
        self.memcached._stats = {'accepting_conns': 0}
        self.assertTupleEqual(
            self.memcached.accepting_connections({}),
            (Plugin.STATUS_CRIT, 'Memcached is not accepting connections')
        )

    def test_raw_stats_to_dict(self):
        data = b'''STAT pid 8509
STAT accepting_conns 1
STAT bytes 70
STAT curr_items 1
END
'''
        self.assertDictEqual(
            self.memcached._raw_stats_to_dict(data),
            {
                'pid': 8509,
                'accepting_conns': 1,
                'bytes': 70,
                'curr_items': 1
            }
        )


class ProcessesTest(unittest.TestCase):
    def setUp(self):
        Processes = processes.Processes
        Processes.__init__ = lambda *args, **kwargs: None
        self.processes = Processes({})
        self.processes.psutil = mock.Mock()

    def test_count(self):
        self.processes.psutil.pids.return_value = [1, 2, 3]
        self.assertTupleEqual(
            self.processes.count({'warn': 5, 'crit': 10}),
            (Plugin.STATUS_OK, '3 processes')
        )
        self.assertTupleEqual(
            self.processes.count({'warn': 1, 'crit': 10}),
            (Plugin.STATUS_WARN, '3 processes')
        )
        self.assertTupleEqual(
            self.processes.count({'warn': 1, 'crit': 2}),
            (Plugin.STATUS_CRIT, '3 processes')
        )

    def test_zombies(self):
        class Process:
            def __init__(self, status='sleeping'):
                self._status = status

            def status(self):
                return self._status

        self.processes.psutil.process_iter.return_value = [
            Process('sleeping'),
            Process('zombie'),
            Process('sleeping'),
        ]
        self.assertTupleEqual(
            self.processes.zombies({'warn': 1, 'crit': 10}),
            (Plugin.STATUS_WARN, '1 zombies')
        )

    def test_count_running_processes(self):
        class Process:
            def __init__(self, cmdline):
                self._cmdline = cmdline

            def cmdline(self):
                return self._cmdline

        self.processes.psutil.process_iter.return_value = [
            Process(['/bin/bash']),
            Process(['/bin/bash']),
            Process(['/usr/sbin/sshd', '-D']),
        ]

        check_config = {'exec': '/bin/bash'}
        self.assertEqual(
            self.processes._count_running_processes(check_config), 2
        )
        check_config = {'exec': '/usr/sbin/sshd'}
        self.assertEqual(
            self.processes._count_running_processes(check_config), 1
        )
        check_config = {'exec': '/usr/sbin/sshd', 'args': '-D'}
        self.assertEqual(
            self.processes._count_running_processes(check_config), 1
        )
        check_config = {'exec': '/usr/sbin/sshd', 'args': '-D -a'}
        self.assertEqual(
            self.processes._count_running_processes(check_config), 0
        )
        check_config = {'exec': '/usr/bin/pulseaudio'}
        self.assertEqual(
            self.processes._count_running_processes(check_config), 0
        )

    def test_running_without_nb(self):
        check_config = {'exec': 'bash'}
        self.processes._count_running_processes = lambda *args, **kwargs: 0
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_CRIT, 'Process bash not running')
        )

        self.processes._count_running_processes = lambda *args, **kwargs: 1
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_OK, 'Process bash is running')
        )

        self.processes._count_running_processes = lambda *args, **kwargs: 2
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_OK, 'Process bash is running')
        )

    def test_running_with_nb(self):
        check_config = {'exec': 'bash', 'nb': 2}
        self.processes._count_running_processes = lambda *args, **kwargs: 0
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_CRIT, 'Process bash not running')
        )

        self.processes._count_running_processes = lambda *args, **kwargs: 1
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_WARN, 'Process bash is running 1 times')
        )

        self.processes._count_running_processes = lambda *args, **kwargs: 2
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_OK, 'Process bash is running')
        )

        self.processes._count_running_processes = lambda *args, **kwargs: 3
        self.assertTupleEqual(
            self.processes.running(check_config),
            (Plugin.STATUS_WARN, 'Process bash is running 3 times')
        )

    def test_required_args_are_in_cmdline(self):
        self.assertTrue(self.processes._required_args_are_in_cmdline(
            [], ['/usr/sbin/sshd', '-D']
        ))
        self.assertTrue(self.processes._required_args_are_in_cmdline(
            ['-D'], ['/usr/sbin/sshd', '-D']
        ))
        self.assertFalse(self.processes._required_args_are_in_cmdline(
            ['-a'], ['/usr/sbin/sshd', '-D']
        ))
        self.assertFalse(self.processes._required_args_are_in_cmdline(
            ['-a', '-D'], ['/usr/sbin/sshd', '-D']
        ))


class HwmonPluginTest(unittest.TestCase):
    def setUp(self):
        self.hwmon = hwmon.Hwmon({})

    def test_no_temperature(self):
        self.hwmon._get_temperatures = lambda: []
        self.assertTupleEqual(
            self.hwmon.temperature({'warn': 20, 'crit': 40}),
            (Plugin.STATUS_UNKNOWN, 'No sensor found')
        )

    def test_temperature(self):
        self.hwmon._get_temperatures = lambda: [
            hwmon.Sensor('Core', '1', 25),
            hwmon.Sensor('Core', '2', 40),
            hwmon.Sensor('Core', '3', 20),
            hwmon.Sensor('Core', '4', 26)
        ]
        self.assertTupleEqual(
            self.hwmon.temperature({'warn': 50, 'crit': 60}),
            (Plugin.STATUS_OK, 'Temperature okay (40°C)')
        )
        self.assertTupleEqual(
            self.hwmon.temperature({'warn': 20, 'crit': 40}),
            (Plugin.STATUS_CRIT, 'Sensor Core/2 40°C')
        )

    def test_filter_sensors_temperature(self):
        self.hwmon._get_temperatures = lambda: [
            hwmon.Sensor('Core', '1', 25),
            hwmon.Sensor('Buggy', 'sensor', 9999),
        ]
        self.assertTupleEqual(
            self.hwmon.temperature({'warn': 50, 'crit': 60,
                                    'sensors': ['Core']}),
            (Plugin.STATUS_OK, 'Temperature okay (25°C)')
        )

    @mock.patch('os.listdir')
    @mock.patch('os.path.isfile')
    def test_get_devices(self, isfile_mock, listdir_mock):
        isfile_mock.return_value = False
        listdir_mock.return_value = ['hwmon1', 'hwmon2']
        self.assertSetEqual(
            self.hwmon._get_devices(),
            {'/sys/class/hwmon/hwmon1', '/sys/class/hwmon/hwmon2'}
        )
        isfile_mock.return_value = True
        self.assertSetEqual(
            self.hwmon._get_devices(),
            {'/sys/class/hwmon/hwmon1/device',
             '/sys/class/hwmon/hwmon2/device'}
        )


class MDStatPluginTest(unittest.TestCase):
    def setUp(self):
        self.mdstat = mdstat.MDStat({})

    def test_no_arrays(self):
        self.mdstat._md_stats = {'arrays': {}, 'personalities': []}
        self.assertTupleEqual(
            self.mdstat.status({}),
            (Plugin.STATUS_UNKNOWN, 'No RAID array detected')
        )

    def test_single_healthy_array(self):
        self.mdstat._md_stats = {
            'arrays': {
                'md0': {
                    'available': '2',
                    'components': {'sda1': '0', 'sdb1': '1'},
                    'config': 'UU',
                    'status': 'active',
                    'type': 'raid1',
                    'used': '2'
                }
            },
            'personalities': ['raid1']
        }
        self.assertTupleEqual(
            self.mdstat.status({}),
            (Plugin.STATUS_OK, 'All arrays are healthy')
        )

    def test_bad_status_array(self):
        self.mdstat._md_stats = {
            'arrays': {
                'md0': {
                    'available': '2',
                    'components': {'sda1': '0', 'sdb1': '1'},
                    'config': 'UU',
                    'status': 'inactive',
                    'type': 'raid1',
                    'used': '2'
                }
            },
            'personalities': ['raid1']
        }
        self.assertTupleEqual(
            self.mdstat.status({}),
            (Plugin.STATUS_CRIT, 'md0 is in status inactive')
        )

    def test_bad_device_nb_array(self):
        self.mdstat._md_stats = {
            'arrays': {
                'md0': {
                    'available': '2',
                    'components': {'sda1': '0', 'sdb1': '1'},
                    'config': 'UU',
                    'status': 'active',
                    'type': 'raid1',
                    'used': '1'
                }
            },
            'personalities': ['raid1']
        }
        self.assertTupleEqual(
            self.mdstat.status({}),
            (Plugin.STATUS_CRIT, 'md0 uses 1/2 devices')
        )


class NtpdPluginTest(unittest.TestCase):
    def setUp(self):
        self.ntpd = ntpd.Ntpd({})

    def test_positive_offset(self):
        self.ntpd._last_loop_stats = {
            'offset': 0.1
        }
        self.assertTupleEqual(
            self.ntpd.offset({'warn': 0.2, 'crit': 0.4}),
            (Plugin.STATUS_OK, 'Last time offset: 0.100s')
        )
        self.assertTupleEqual(
            self.ntpd.offset({'warn': 0.1, 'crit': 0.4}),
            (Plugin.STATUS_WARN, 'Last time offset: 0.100s')
        )
        self.assertTupleEqual(
            self.ntpd.offset({'warn': 0.01, 'crit': 0.04}),
            (Plugin.STATUS_CRIT, 'Last time offset: 0.100s')
        )

    def test_negative_offset(self):
        self.ntpd._last_loop_stats = {
            'offset': -0.04
        }
        self.assertTupleEqual(
            self.ntpd.offset({'warn': 0.02, 'crit': 0.5}),
            (Plugin.STATUS_WARN, 'Last time offset: -0.040s')
        )

    @mock.patch('sauna.plugins.ext.ntpd.time')
    def test_delta(self, mock_time):
        mock_time.time.return_value = 1471940731
        self.ntpd._last_loop_stats = {
            'timestamp': 1471940731
        }
        self.assertTupleEqual(
            self.ntpd.last_sync_delta({'warn': 60, 'crit': 300}),
            (Plugin.STATUS_OK, 'Ntp sync 0:00:00 ago')
        )

        mock_time.time.return_value = 1471950731
        self.assertTupleEqual(
            self.ntpd.last_sync_delta({'warn': 60, 'crit': 300}),
            (Plugin.STATUS_CRIT, 'Ntp sync 2:46:40 ago')
        )


class DummyPluginTest(unittest.TestCase):
    def setUp(self):
        self.dummy = dummy.Dummy({})

    def test_dummy(self):
        self.assertTupleEqual(
            self.dummy.dummy({}),
            (Plugin.STATUS_OK, 'OK')
        )
        self.assertTupleEqual(
            self.dummy.dummy({'status': 1}),
            (Plugin.STATUS_WARN, 'OK')
        )
        self.assertTupleEqual(
            self.dummy.dummy({'output': 'Alright'}),
            (Plugin.STATUS_OK, 'Alright')
        )


@requests_mock.Mocker()
class HttpJsonPluginTest(unittest.TestCase):
    def setUp(self):
        self.plugin = http_json.HTTPJSON({})

        def make_conf(c):
            base = {'warn': 60, 'crit': 300, 'url': 'http://mo.ck/foo'}
            base.update(c)
            return base

        self.config = make_conf

    def test_success(self, m):
        conf = self.config({'expect': 'bar'})
        m.get(conf['url'], text='bar')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_OK)

    def test_success_regex(self, m):
        conf = self.config({'expect': '.*not a (pipe|bar)'})
        m.get(conf['url'], text='This is not a pipe')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_OK)

    def test_success_jsonpath(self, m):
        conf = self.config({'expect': 'spam', 'success_jsonpath': '$.foo.bar'})
        m.get(conf['url'], text='{"foo": {"bar": "spam"}}')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_OK)

    def test_success_jsonpath_multiple(self, m):
        conf = self.config(
            {'expect': 'spam', 'success_jsonpath': '$.foo.[a,b]'})
        m.get(conf['url'], text='{"foo": {"a": "not spam", "b": "spam"}}')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_OK)

    def test_success_jsonpath_regex(self, m):
        conf = self.config(
            {'expect': '.*pam', 'success_jsonpath': '$.foo.bar'})
        m.get(conf['url'], text='{"foo": {"bar": "not spam"}}')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_OK)

    def test_fail_code(self, m):
        conf = self.config({'expect': 'ok', 'code': 200})
        m.get(conf['url'], text='ok', status_code=250)
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_CRIT)
        self.assertEqual(msg, 'Got status code 250 instead of 200')

    def test_fail_json(self, m):
        conf = self.config({'expect': 'ok', 'success_jsonpath': '$.dummy'})
        m.get(conf['url'], text='{"missing": "bracket"')
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_CRIT)

    def test_fail_jsonpath(self, m):
        conf = self.config(
            {'expect': 'ok', 'error_jsonpath': '$.[id,message]'})
        m.get(conf['url'], text='{"id": 123, "message": "An error"}',
              status_code=400)
        status, msg = self.plugin.request(conf)
        self.assertEqual(status, Plugin.STATUS_CRIT)
        self.assertIn('message: An error', msg)
        self.assertIn('id: 123', msg)
