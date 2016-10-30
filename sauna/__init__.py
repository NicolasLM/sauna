from collections import namedtuple
import threading
import queue
import logging
import time
import socket
import os
import textwrap
import signal
import importlib
import pkgutil
import re
import sys
import glob
import functools

from sauna import plugins, consumers
from sauna.plugins.base import Check
from sauna.consumers.base import QueuedConsumer
from sauna.consumers import ConsumerRegister
from sauna.plugins import PluginRegister
from sauna.scheduler import Scheduler, Job

__version__ = '0.0.15'

ServiceCheck = namedtuple('ServiceCheck',
                          ['timestamp', 'hostname', 'name',
                           'status', 'output'])

# Global dict containing the last status of each check
# Needs to hold a lock to access it
check_results = {}
check_results_lock = threading.Lock()

try:
    # In Python 3.2 threading.Event is a factory function
    # the real class lives in threading._Event
    event_type = threading._Event
except AttributeError:
    event_type = threading.Event


class DependencyError(Exception):

    def __init__(self, plugin, dep_name, pypi='', deb=''):
        self.msg = '{} depends on {}. It can be installed with:\n'.format(
            plugin, dep_name
        )
        if pypi:
            self.msg = '{}    pip install {}\n'.format(self.msg, pypi)
        if deb:
            self.msg = '{}    apt-get install {}\n'.format(self.msg, deb)

    def __str__(self):
        return self.msg


def _merge_config(original, included):
    """Add properties from a dict to another dict.

    :param original: dict to update
    """
    for key, value in included.items():
        if isinstance(value, list):
            try:
                original[key].extend(value)
            except KeyError:
                original[key] = value
        elif isinstance(value, dict):
            try:
                original[key].update(value)
            except KeyError:
                original[key] = value
        else:
            original[key] = value


def read_config(config_file):
    # importing yaml here because dependency is not installed
    # when fetching __version__ from setup.py
    import yaml

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
    except OSError as e:
        print('Cannot read configuration file {}: {}'
              .format(config_file, e))
        exit(1)

    for config_file_included in glob.glob(config.get('include', '')):
        config_included = read_config(config_file_included)
        _merge_config(config, config_included)

    return config


class Sauna:

    def __init__(self, config=None):
        if config is None:
            config = {}
        self.config = config
        self.must_stop = threading.Event()
        self._consumers_queues = []
        self.import_submodules(__name__ + '.plugins.ext')
        self.import_submodules(__name__ + '.consumers.ext')
        for extra_plugin_path in self.config.get('extra_plugins', []):
            self.import_directory_modules(extra_plugin_path)

    @classmethod
    def assemble_config_sample(cls, path):
        sample = '---\nperiodicity: 120\nhostname: node-1.domain.tld\n'

        sample += '\nconsumers:\n'
        consumers_sample = ''
        for _, consumer_info in ConsumerRegister.all_consumers.items():
            if hasattr(consumer_info['consumer_cls'], 'config_sample'):
                consumers_sample += textwrap.dedent(
                    consumer_info['consumer_cls'].config_sample()
                )
        sample += consumers_sample.replace('\n', '\n  ')

        sample += '\nplugins:\n'
        plugins_sample = ''
        for _, plugin_info in PluginRegister.all_plugins.items():
            if hasattr(plugin_info['plugin_cls'], 'config_sample'):
                plugins_sample += textwrap.dedent(
                    plugin_info['plugin_cls'].config_sample()
                )
        sample += plugins_sample.replace('\n', '\n  ')

        file_path = os.path.join(path, 'sauna-sample.yml')
        with open(file_path, 'w') as f:
            f.write(sample)

        return file_path

    @property
    @functools.lru_cache()
    def hostname(self):
        # socket.getfqdn can be a very long call
        # make sure to only call it when absolutely necessary
        # that's why a cache is used and dict.get() is avoided
        try:
            return self.config['hostname']
        except KeyError:
            return socket.getfqdn()

    @property
    def periodicity(self):
        return self.config.get('periodicity', 120)

    @property
    def plugins_checks(self):
        plugins = []
        if type(self.config['plugins']) is dict:
            for plugin_name, plugin_data in self.config['plugins'].items():
                plugin_data.update({'type': plugin_name})
                plugins.append(plugin_data)
        elif type(self.config['plugins']) is list:
            plugins = self.config['plugins']
        else:
            print('Invalid configuration, plugins must be a list or a dict')
            exit(1)
        return plugins

    @property
    def consumers(self):
        consumers = []
        if type(self.config['consumers']) is dict:
            for cons_name, cons_data in self.config['consumers'].items():
                # Consumer Stdout doesn't need configuration
                if cons_data is None:
                    cons_data = {}
                cons_data.update({'type': cons_name})
                consumers.append(cons_data)
        elif type(self.config['consumers']) is list:
            consumers = self.config['consumers']
        else:
            print('Invalid configuration, consumers must be a list or a dict')
            exit(1)
        return consumers

    def get_active_checks_name(self):
        checks = self.get_all_active_checks()
        return [check.name for check in checks]

    def get_all_available_consumers(self):
        return_consumers = []
        for plugin_name, _ in ConsumerRegister.all_consumers.items():
            return_consumers.append(plugin_name)

        return return_consumers

    def get_all_available_checks(self):
        checks = {}
        for plugin_name, data in PluginRegister.all_plugins.items():
            checks[plugin_name] = []
            for check in data['checks']:
                checks[plugin_name].append(check)
        return checks

    def get_all_active_checks(self):
        checks = []
        deps_error = []
        for plugin_data in self.plugins_checks:
            plugin_name = plugin_data['type']
            # Load plugin
            plugin_info = PluginRegister.get_plugin(plugin_name)
            if not plugin_info:
                print('Plugin {} does not exist'.format(plugin_name))
                exit(1)

            # Configure plugin
            try:
                plugin = plugin_info['plugin_cls'](
                    plugin_data.get('config', {})
                )
            except DependencyError as e:
                deps_error.append(str(e))
                continue

            # Launch plugin checks
            for check in plugin_data['checks']:
                func_name = plugin_info['checks'].get(check['type'])
                if func_name is None:
                    print('Unknown check {} on plugin {}'.format(check['type'],
                                                                 plugin_name))
                    exit(1)
                check_func = getattr(plugin, func_name)

                # An empty string is a valid check name
                check_name = check.get(
                    'name',
                    '{}_{}'.format(plugin_name, check['type'])
                ).lower()

                check_periodicity = (check.get('periodicity') or
                                     self.periodicity)

                checks.append(Check(check_name, check_periodicity,
                                    check_func, check))
        if deps_error:
            for error in deps_error:
                print(error)
            exit(1)

        # Check duplicate name
        names = [check.name for check in checks]
        duplicates_names = {name: names.count(name)
                            for name in names if names.count(name) > 1}
        for name, count in duplicates_names.items():
            print("check name {} was found {} times, please add name"
                  " field to theses checks".format(name, count))
        if duplicates_names:
            exit(1)
        return checks

    def launch_all_checks(self):
        """Run once every single check."""
        for check in self.get_all_active_checks():
            yield self.launch_check(check)

    def launch_and_publish_checks_with_periodicity(self, periodicity):
        """Run once every check matching the given periodicity.

        Sends the result of each check to the queues and shared dict.
        """
        checks = filter(lambda x: x.periodicity == periodicity,
                        self.get_all_active_checks())
        for check in checks:
            service_check = self.launch_check(check)
            logging.debug('Pushing to consumers: {}'.
                          format(service_check.name))
            self.send_data_to_consumers(service_check)
            with check_results_lock:
                check_results[service_check.name] = service_check

    def launch_check(self, check):
        try:
            status, output = check.run_check()
        except Exception as e:
            logging.warning('Could not run check {}: {}'.format(
                check.name, str(e)
            ))
            status = 3
            output = str(e)
        return ServiceCheck(
            timestamp=int(time.time()),
            hostname=self.hostname,
            name=check.name,
            status=status,
            output=output
        )

    def run_producer(self):
        periodicities = {check.periodicity
                         for check in self.get_all_active_checks()}
        jobs = [Job(p, self.launch_and_publish_checks_with_periodicity, p)
                for p in periodicities]
        logging.info('Running checks with interval: {}'
                     .format(str(periodicities)))
        scheduler = Scheduler(jobs)

        for _ in scheduler:
            if self.must_stop.wait(timeout=scheduler.tick_duration):
                break
        logging.debug('Exited producer thread')

    def term_handler(self, *args):
        """Notify producer and consumer that they should stop."""
        if not self.must_stop.is_set():
            self.must_stop.set()
            self.send_data_to_consumers(self.must_stop)
            logging.info('Exiting...')

    def send_data_to_consumers(self, data):
        for queue in self._consumers_queues:
            queue.put(data)

    def launch(self):
        # Start producer and consumer threads
        producer = threading.Thread(
            name='producer', target=self.run_producer
        )
        producer.start()

        consumers_threads = []
        for consumer_data in self.consumers:

            consumer_name = consumer_data['type']

            consumer_info = ConsumerRegister.get_consumer(consumer_name)
            if not consumer_info:
                print('Plugin {} does not exist'.format(consumer_name))
                exit(1)

            try:
                consumer = consumer_info['consumer_cls'](consumer_data)
            except DependencyError as e:
                print(str(e))
                exit(1)

            if isinstance(consumer, QueuedConsumer):
                consumer_queue = queue.Queue()
                self._consumers_queues.append(consumer_queue)
            else:
                consumer_queue = None

            consumer_thread = threading.Thread(
                name='consumer_{}'.format(consumer_name),
                target=consumer.run,
                args=(self.must_stop, consumer_queue)
            )

            consumer_thread.start()
            consumers_threads.append(consumer_thread)
            logging.debug(
                'Running consumer {}'.format(consumer_name)
            )

        signal.signal(signal.SIGTERM, self.term_handler)
        signal.signal(signal.SIGINT, self.term_handler)

        producer.join()
        self.term_handler()

        for consumer_thread in consumers_threads:
            consumer_thread.join()

        logging.debug('Exited main thread')

    @classmethod
    def import_submodules(cls, entity):
        """Import packages and/or modules."""
        entity = importlib.import_module(entity)
        try:
            for _, name, is_pkg in pkgutil.walk_packages(entity.__path__):
                if not name.startswith('_') and is_pkg is False:
                    full_name = entity.__name__ + '.' + name
                    importlib.import_module(full_name)
        except AttributeError:
            pass

    @classmethod
    def import_directory_modules(cls, path):
        """Import all modules from a filesystem directory."""
        try:
            entries = os.listdir(path)
        except OSError as e:
            logging.error('Cannot load plugins from {}: {}'.format(path, e))
            return
        logging.info('Loading extra plugins from {}'.format(path))
        sys.path.append(path)
        for entry in entries:
            if not os.path.isfile(os.path.join(path, entry)):
                continue
            regexp_result = re.search(r'(.+)\.py$', entry)
            if regexp_result:
                logging.debug('Loading {}'.format(regexp_result.groups()[0]))
                cls.import_submodules(regexp_result.groups()[0])
