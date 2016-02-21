import unittest

from .context import sauna


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
        status_ok = sauna.plugins.STATUS_OK
        status_warn = sauna.plugins.STATUS_WARN
        status_crit = sauna.plugins.STATUS_CRIT

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
        plugins = sauna.plugins.get_all_plugins()
        self.assertIsInstance(plugins, tuple)
        self.assertGreater(len(plugins), 1)
        for plugin in plugins:
            self.assert_(issubclass(plugin, sauna.plugins.Plugin))

    def test_get_plugin(self):
        load_plugin = sauna.plugins.get_plugin('Load')
        self.assert_(issubclass(load_plugin, sauna.plugins.Plugin))
        with self.assertRaises(ValueError):
            sauna.plugins.get_plugin('Unknown')
