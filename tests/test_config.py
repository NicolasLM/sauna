import copy
import unittest
try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

import yaml

from sauna import Sauna, _merge_config


class ConfigTest(unittest.TestCase):

    def test_dict_conf(self):
        dict_conf = {
            "plugins": {
                "Disk": {
                    "config": {
                        "myconf": "myvalue"
                    },
                    "checks": [
                        {
                            "type": "used_percent",
                            "warn": "80%",
                            "crit": "90%"
                        }
                    ]
                }
            }
        }
        expected_result = [
            {
                'type': 'Disk',
                "config": {
                    "myconf": "myvalue"
                },
                "checks": [
                    {
                        "type": "used_percent",
                        "warn": "80%",
                        "crit": "90%"
                    }
                ]
            }
        ]
        sauna = Sauna(config=dict_conf)
        self.assertEqual(sauna.plugins_checks, expected_result)

    def test_list_conf(self):
        list_conf = {
            "plugins": [
                {
                    'type': 'Disk',
                    "config": {
                        "myconf": "myvalue"
                    },
                    "checks": [
                        {
                            "type": "used_percent",
                            "warn": "80%",
                            "crit": "90%"
                        }
                    ]
                }
            ]
        }

        sauna = Sauna(config=list_conf)
        self.assertEqual(sauna.plugins_checks, list_conf['plugins'])

    def test_complex_dict_conf(self):
        dict_conf = {
            "plugins": {
                "Disk": {
                    "config": {
                        "myconf": "myvalue"
                    },
                    "checks": [
                        {
                            "type": "used_percent",
                            "warn": "80%",
                            "crit": "90%"
                        },
                        {
                            "type": "used_percent",
                            "warn": "80%",
                            "crit": "90%"
                        }
                    ]
                },
                "Memory": {
                    "config": {
                        "myconf": "myvalue"
                    },
                    "checks": [
                        {
                            "type": "used_percent",
                            "warn": "80%",
                            "crit": "90%"
                        },
                    ]
                }
            }
        }
        expected_result = [
            {
                'type': 'Disk',
                "config": {
                    "myconf": "myvalue"
                },
                "checks": [
                    {
                        "type": "used_percent",
                        "warn": "80%",
                        "crit": "90%"
                    },
                    {
                        "type": "used_percent",
                        "warn": "80%",
                        "crit": "90%"
                    }
                ]
            },
            {
                "type": "Memory",
                "config": {
                    "myconf": "myvalue"
                },
                "checks": [
                    {
                        "type": "used_percent",
                        "warn": "80%",
                        "crit": "90%"
                    },
                ]
            }
        ]
        sauna = Sauna(config=dict_conf)
        self.assertEqual(len(sauna.plugins_checks), len(expected_result))
        for elem in sauna.plugins_checks:
            self.assertIn(elem, expected_result, 'missing element')

    def test_consumers_dict_conf(self):
        dict_conf = {
            'consumers': {
                'NSCA': {
                    'foo': 'bar'
                },
                'Stdout': None
            }
        }
        expected_result = [
            {
                'type': 'NSCA',
                'foo': 'bar'
            },
            {
                'type': 'Stdout',
            }
        ]
        sauna = Sauna(config=dict_conf)
        for r in expected_result:
            self.assertTrue(r in sauna.consumers)

    def test_consumers_list_conf(self):
        list_conf = {
            'consumers': [
                {
                    'type': 'NSCA',
                    'foo': 'bar'
                },
                {
                    'type': 'Stdout',
                }
            ]
        }
        sauna = Sauna(config=list_conf)
        for r in list_conf['consumers']:
            self.assertTrue(r in sauna.consumers)

    def test_merge_config(self):
        original = {
            'periodicity': 60,
            'consumers': {
                'Stdout': {}
            },
            'plugins': [
                {
                   'type': 'Disk',
                   "config": {
                       "myconf": "myvalue"
                   },
                   "checks": [
                       {
                           "type": "used_percent",
                           "warn": "80%",
                           "crit": "90%"
                       },
                       {
                           "type": "used_percent",
                           "warn": "80%",
                           "crit": "90%"
                       }
                   ]
                }
            ]
        }

        # Not changing anthing
        expected = copy.deepcopy(original)
        _merge_config(original, {})
        self.assertDictEqual(original, expected)

        # Adding a consumer
        expected['consumers']['NSCA'] = {}
        _merge_config(original, {'consumers': {'NSCA': {}}})
        self.assertDictEqual(original, expected)

        # Adding a plugin
        expected['plugins'].append({'type': 'Load'})
        _merge_config(original, {'plugins': [{'type': 'Load'}]})
        self.assertDictEqual(original, expected)

        # Adding a root property
        expected['hostname'] = 'host-1.domain.tld'
        _merge_config(original, {'hostname': 'host-1.domain.tld'})
        self.assertDictEqual(original, expected)

        # Appending to a non existent list
        expected['extra_plugins'] = ['/opt/plugins1', '/opt/plugins2']
        _merge_config(original,
                      {'extra_plugins': ['/opt/plugins1', '/opt/plugins2']})
        self.assertDictEqual(original, expected)

    def test_assemble_config_sample(self):
        mock_open = mock.mock_open()
        sauna_instance = Sauna()
        with mock.patch('builtins.open', mock_open):
            sauna_instance.assemble_config_sample('/foo')
        mock_open.assert_called_once_with('/foo/sauna-sample.yml', 'w')
        f = mock_open()
        generated_yaml_string = f.write.call_args[0][0]
        # Will raise a yaml error if generated content is not valid yaml
        yaml.safe_load(generated_yaml_string)

    def test_conf_with_concurrency_instantiates_threadpool(self):
        original = {
            'periodicity': 60,
            'concurrency': 5,
            'consumers': {
                'Stdout': {}
            },
            'plugins': []
        }
        sauna = Sauna(config=original)
        self.assertIsNotNone(sauna._thread_pool)

    def test_conf_without_concurrency_no_threadpool(self):
        original = {
            'periodicity': 60,
            'consumers': {
                'Stdout': {},
            },
            'plugins': []
        }
        sauna = Sauna(config=original)
        self.assertIsNone(sauna._thread_pool)
