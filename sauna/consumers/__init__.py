import time
import logging


class Consumer:

    def __init__(self, config):
        if config is None:
            config = {}
        self.stale_age = config.get('stale_age', 300)
        self.retry_delay = 10

    def logging(self, lvl, message):
        log = getattr(logging, lvl)
        message = '[{}] {}'.format(self.__class__.__name__, message)
        log(message)

    def _send(self, service_check):
        raise NotImplemented()

    def try_send(self, service_check, must_stop):

        while True:
            if must_stop.is_set():
                return
            if service_check.timestamp + self.stale_age < int(time.time()):
                self.logging('warning', 'Dropping check because it is too old')
                return
            try:
                self._send(service_check)
                self.logging('info', 'Check sent')
                return
            except Exception as e:
                self.logging('warning', 'Could not send check: {}'.format(e))
                if must_stop.is_set():
                    return
                self._wait_before_retry(must_stop)

    def _wait_before_retry(self, must_stop):
        logging.info('Waiting {}s before retry'.format(self.retry_delay))
        for i in range(self.retry_delay):
            if must_stop.is_set():
                return
            time.sleep(1)


def get_consumer(consumer_name):
    if consumer_name == 'NSCA':
        from .nsca import NSCAConsumer
        return NSCAConsumer
    if consumer_name == 'HTTP':
        from .http import HTTPConsumer
        return HTTPConsumer
    if consumer_name == 'Stdout':
        from .stdout import StdoutConsumer
        return StdoutConsumer
    raise ValueError('Unknown consumer {}'.format(consumer_name))


def get_all_consumers():
    from .nsca import NSCAConsumer
    from .http import HTTPConsumer
    from .stdout import StdoutConsumer
    return NSCAConsumer, HTTPConsumer, StdoutConsumer
