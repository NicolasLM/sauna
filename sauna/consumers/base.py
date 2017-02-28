import time
import logging
from functools import reduce
from copy import deepcopy


class Consumer:

    def __init__(self, config):
        if config is None:
            config = {}
        self.stale_age = config.get('stale_age', 300)
        self.retry_delay = 10

    @property
    def logger(self):
        return logging.getLogger('sauna.' + self.__class__.__name__)

    @classmethod
    def logging(cls, lvl, message):
        """Log a message.

        Deprecated, use self.logger instead. Kept for backward compatibility
        """
        log = getattr(logging, lvl)
        message = '[{}] {}'.format(cls.__name__, message)
        log(message)

    def run(self, must_stop, queue):
        """Method to override in consumers."""
        raise NotImplemented()


class QueuedConsumer(Consumer):
    """Consumer that processes checks synchronously.

    QueuedConsumers wait for checks to appear on a queue. They process each
    check in order until the queue is empty.
    """
    def _send(self, service_check):
        """Method to override in consumers."""
        raise NotImplemented()

    def try_send(self, service_check, must_stop):

        while True:
            if must_stop.is_set():
                return
            if service_check.timestamp + self.stale_age < int(time.time()):
                self.logger.warning('Dropping check because it is too old')
                return
            try:
                self._send(service_check)
                self.logger.info('Check sent')
                return
            except Exception as e:
                self.logger.warning('Could not send check: {}'.format(e))
                if must_stop.is_set():
                    return
                self._wait_before_retry(must_stop)

    def _wait_before_retry(self, must_stop):
        self.logger.info('Waiting {}s before retry'.format(self.retry_delay))
        for i in range(self.retry_delay):
            if must_stop.is_set():
                return
            time.sleep(1)

    def run(self, must_stop, queue):
        from sauna import event_type
        while not must_stop.is_set():
            service_check = queue.get()
            if isinstance(service_check, event_type):
                continue
            self.logger.debug('Got check {}'.format(service_check))
            self.try_send(service_check, must_stop)
        self.logger.debug('Exited consumer thread')


class AsyncConsumer(Consumer):
    """Consumer that processes checks asynchronously.

    It is up to the consumer to read the checks when it needs to. No
    queueing is made.
    """

    @classmethod
    def get_current_status(cls):
        """Get the worse status of all check results.

        :returns: (status as str, code)
        :rtype: tuple
        """
        from sauna.plugins.base import Plugin
        from sauna import check_results_lock, check_results

        def reduce_status(accumulated, update_value):
            if update_value.status > Plugin.STATUS_CRIT:
                return accumulated
            return accumulated if accumulated > update_value.status else \
                update_value.status

        with check_results_lock:
            code = reduce(reduce_status, check_results.values(), 0)

        return Plugin.status_code_to_str(code), code

    @classmethod
    def get_checks_as_dict(cls):
        from sauna.plugins.base import Plugin
        from sauna import check_results_lock, check_results

        checks = {}
        with check_results_lock:
            for service_check in check_results.values():
                checks[service_check.name] = {
                    'status': Plugin.status_code_to_str(service_check.status),
                    'code': service_check.status,
                    'timestamp': service_check.timestamp,
                    'output': service_check.output
                }
        return deepcopy(checks)
