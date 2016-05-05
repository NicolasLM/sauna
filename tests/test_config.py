import unittest
try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

from sauna import Sauna


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
