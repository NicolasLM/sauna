from collections import namedtuple
import threading
import queue
import logging
import time
import socket
import os
import textwrap
import signal

from sauna import plugins, consumers

__version__ = '0.0.3'

ServiceCheck = namedtuple('ServiceCheck',
                          ['timestamp', 'hostname', 'name',
                           'status', 'output'])

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


def read_config(config_file):
    # importing yaml here because dependency is not installed
    # when fetching __version__ from setup.py
    import yaml

    try:
        with open(config_file) as f:
            return yaml.safe_load(f)
    except OSError as e:
        print('Cannot read configuration file {}: {}'
              .format(config_file, e))
        exit(1)


class Sauna:

    def __init__(self, config=None):
        if config is None:
            config = {}
        self.config = config

        self.must_stop = threading.Event()
        self._consumers_queues = []

    @classmethod
    def assemble_config_sample(cls, path):
        sample = '---\nperiodicity: 120\nhostname: node-1.domain.tld\n'

        sample += '\nconsumers:\n'
        consumers_sample = ''
        for c in consumers.get_all_consumers():
            consumers_sample += textwrap.dedent(c.config_sample())
        sample += consumers_sample.replace('\n', '\n  ')

        sample += '\nplugins:\n'
        plugins_sample = ''
        for p in plugins.get_all_plugins():
            plugins_sample += textwrap.dedent(p.config_sample())
        sample += plugins_sample.replace('\n', '\n  ')

        file_path = os.path.join(path, 'sauna-sample.yml')
        with open(file_path, 'w') as f:
            f.write(sample)

        return file_path

    @property
    def hostname(self):
        return self.config.get('hostname', socket.getfqdn())

    @property
    def periodicity(self):
        return self.config.get('periodicity', 120)

    def get_checks_name(self):
        checks = self.get_all_checks()
        return [check.name for check in checks]

    def get_all_checks(self):
        checks = []
        deps_error = []
        for plugin_name, plugin_data in self.config['plugins'].items():

            # Load plugin
            try:
                Plugin = plugins.get_plugin(plugin_name)
            except ValueError as e:
                print(str(e))
                exit(1)

            # Configure plugin
            try:
                plugin = Plugin(plugin_data.get('config', {}))
            except DependencyError as e:
                deps_error.append(str(e))
                continue

            # Launch plugin checks
            for check in plugin_data['checks']:
                check_func = getattr(plugin, check['type'])

                if not check_func:
                    print('Unknown check {} on plugin {}'.format(check['type'],
                                                                 plugin_name))
                    exit(1)

                check_name = (check.get('name') or '{}_{}'.format(
                    plugin_name, check['type']
                ).lower())

                checks.append(plugins.Check(check_name, check_func, check))
        if deps_error:
            for error in deps_error:
                print(error)
            exit(1)
        return checks

    def launch_all_checks(self, hostname):
        for check in self.get_all_checks():

            try:
                status, output = check.run_check()
            except Exception as e:
                logging.warning('Could not run check {}: {}'.format(
                    check.name, str(e)
                ))
                status = 3
                output = str(e)
            s = ServiceCheck(
                timestamp=int(time.time()),
                hostname=hostname,
                name=check.name,
                status=status,
                output=output
            )
            yield s

    def run_producer(self):
        while True:
            for service_check in self.launch_all_checks(self.hostname):
                logging.debug(
                    'Pushing to main queue: {}'.format(service_check))
                self.send_data_to_consumers(service_check)
            if self.must_stop.wait(timeout=self.periodicity):
                break
        logging.debug('Exited producer thread')

    def run_consumer(self, consumer_name, consumer_config, consumer_queue):
        logging.debug(
            'Running {} with {}'.format(consumer_name, consumer_config))
        try:
            consumer = consumers.get_consumer(consumer_name)(consumer_config)
        except DependencyError as e:
            print(str(e))
            exit(1)

        while not self.must_stop.is_set():
            service_check = consumer_queue.get()
            if isinstance(service_check, event_type):
                continue
            logging.debug(
                '[{}] Got check {}'.format(consumer_name, service_check))
            consumer.try_send(service_check, self.must_stop)
        logging.debug('Exited consumer {} thread'.format(consumer_name))

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

        consumers = []
        for consumer_name, consumer_config in self.config['consumers'].items():
            consumer_queue = queue.Queue()
            self._consumers_queues.append(consumer_queue)

            consumer = threading.Thread(
                name='consumer_{}'.format(consumer_name),
                target=self.run_consumer,
                args=(consumer_name, consumer_config, consumer_queue)
            )
            consumer.start()
            consumers.append(consumer)

        signal.signal(signal.SIGTERM, self.term_handler)
        signal.signal(signal.SIGINT, self.term_handler)

        producer.join()
        self.term_handler()

        for consumer in consumers:
            consumer.join()

        logging.debug('Exited main thread')
