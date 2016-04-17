import unittest

from .context import sauna, mock


class PluginsTest(unittest.TestCase):

    def test_human_to_bytes(self):
        human_to_bytes = sauna.plugins.human_to_bytes
        self.assertEquals(0, human_to_bytes('0'))
        self.assertEquals(1000, human_to_bytes('1000'))
        self.assertEquals(1024, human_to_bytes('1K'))
        self.assertEquals(1024, human_to_bytes('1KiB'))
        self.assertEquals(1024, human_to_bytes('1KiO'))
        self.assertEquals(5242880, human_to_bytes('5M'))
        self.assertEquals(10737418240, human_to_bytes('10G'))

    def test_bytes_to_human(self):
        bytes_to_human = sauna.plugins.bytes_to_human
        self.assertEquals('0B', bytes_to_human(0))
        self.assertEquals('1000B', bytes_to_human(1000))
        self.assertEquals('1.0K', bytes_to_human(1024))
        self.assertEquals('5.0M', bytes_to_human(5*1024*1024))
        self.assertEquals('10.0G', bytes_to_human(10*1024*1024*1024))

    def test_strip_percent_sign(self):
        strip_percent_sign = sauna.plugins.Plugin._strip_percent_sign
        self.assertEquals(10, strip_percent_sign('10'))
        self.assertEquals(10, strip_percent_sign('10%'))
        self.assertEquals(-10, strip_percent_sign('-10%'))

    def test_strip_percent_sign_from_check_config(self):
        func = sauna.plugins.Plugin._strip_percent_sign_from_check_config
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
        self.assertDictEqual(expected_config, func(check_config))

    def test_get_threshold(self):
        func = sauna.plugins.Plugin.get_thresholds
        check_config = {
            'warn': 75,
            'crit': 95,
            'something_random': '10'
        }

        # Test without modifier
        self.assertTupleEqual((95, 75), func(check_config))

        # Test with modifier
        def double(number):
            return number * 2
        self.assertTupleEqual((190, 150), func(check_config, double))

    def test_value_to_status(self):
        less = sauna.plugins.Plugin._value_to_status_less
        more = sauna.plugins.Plugin._value_to_status_more
        status_ok = sauna.plugins.Plugin.STATUS_OK
        status_warn = sauna.plugins.Plugin.STATUS_WARN
        status_crit = sauna.plugins.Plugin.STATUS_CRIT

        # Test less, imagine this check is about used RAM in percent
        check_config = {
            'warn': 75,
            'crit': 95,
        }
        self.assertEquals(status_ok, less(10, check_config))
        self.assertEquals(status_warn, less(80, check_config))
        self.assertEquals(status_crit, less(100, check_config))

        # Test less, imagine this check is about free RAM in percent
        check_config = {
            'warn': 25,
            'crit': 5,
        }
        self.assertEquals(status_ok, more(50, check_config))
        self.assertEquals(status_warn, more(20, check_config))
        self.assertEquals(status_crit, more(2, check_config))

    def test_get_all_plugins(self):
        plugins = sauna.plugins.PluginRegister.all_plugins
        self.assertIsInstance(plugins, dict)
        self.assertGreater(len(plugins), 1)
        for plugin_name, plugin_info in plugins.items():
            self.assertIn('plugin_cls', plugin_info)
            self.assertIn('checks', plugin_info)
            self.assert_(issubclass(plugin_info['plugin_cls'],
                                    sauna.plugins.Plugin))
            self.assertIsInstance(plugin_info['checks'], dict)

    def test_get_plugin(self):
        load_plugin = sauna.plugins.PluginRegister.get_plugin('Load')
        self.assert_(issubclass(load_plugin['plugin_cls'],
                                sauna.plugins.Plugin))

        must_be_none = sauna.plugins.PluginRegister.get_plugin('Unknown')
        self.assertIsNone(must_be_none)


class PuppetAgentTest(unittest.TestCase):

    @mock.patch('sauna.plugins.ext.puppet_agent.time')
    def test_last_run_delta(self, mock_time):
        mock_time.time.return_value = 1460836285.4
        puppet_agent = sauna.plugins.ext.puppet_agent.PuppetAgent({})
        puppet_agent._last_run_summary = {
            'time': {
                'last_run': 1460836283
            }
        }
        self.assertTupleEqual(
            puppet_agent.last_run_delta({'warn': 10, 'crit': 20}),
            (sauna.plugins.Plugin.STATUS_OK, 'Puppet last ran 0:00:02 ago')
        )

        mock_time.time.return_value = 1460836295.4
        self.assertTupleEqual(
            puppet_agent.last_run_delta({'warn': 10, 'crit': 20}),
            (sauna.plugins.Plugin.STATUS_WARN, 'Puppet last ran 0:00:12 ago')
        )

    def test_failures(self):
        puppet_agent = sauna.plugins.ext.puppet_agent.PuppetAgent({})
        puppet_agent._last_run_summary = {
            'events': {
                'failure': 0
            }
        }
        self.assertTupleEqual(
            puppet_agent.failures({'warn': 1, 'crit': 2}),
            (sauna.plugins.Plugin.STATUS_OK, 'Puppet ran without trouble')
        )

        puppet_agent._last_run_summary['events']['failure'] = 1
        self.assertTupleEqual(
            puppet_agent.failures({'warn': 1, 'crit': 1}),
            (sauna.plugins.Plugin.STATUS_CRIT,
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
        puppet_agent = sauna.plugins.ext.puppet_agent.PuppetAgent({})
        self.assertEquals(puppet_agent._last_run_summary, None)
        self.assertDictEqual(puppet_agent.last_run_summary, expected)
        self.assertDictEqual(puppet_agent._last_run_summary, expected)
