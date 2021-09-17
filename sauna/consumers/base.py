from copy import deepcopy
from datetime import timedelta, datetime
from functools import reduce
import logging
from queue import Queue, Empty
import threading
import time


class Consumer:

    def __init__(self, config: dict):
        if config is None:
            config = {}
        self.stale_age = config.get('stale_age', 300)
        self.retry_delay = config.get('retry_delay', 10)
        self.max_retry = config.get('max_retry', -1)

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
        raise NotImplementedError()


class BatchQueuedConsumer(Consumer):
    """Consumer that processes checks synchronously in batches.

    BatchQueuedConsumers wait for checks to appear on a queue. They buffer the
    checks until enough of them are available. They then send all checks in a
    single batch to the remote service.
    """

    #: Maximum number of checks to send in a single batch.
    max_batch_size: int = 64

    #: Maximum amount of time to wait for the batch to be full before sending
    #: it.
    max_batch_delay: timedelta = timedelta(seconds=15)

    def _send(self, service_check):
        """Send one service checks.

        Method to override in consumers sending checks one by one.
        """
        raise NotImplementedError()

    def _send_batch(self, service_checks: list):
        """Send a batch of service checks.

        Method to override in consumers for actually sending batches, otherwise
        checks are sent one by one using `self._send`.
        """
        for service_check in service_checks:
            self._send(service_check)

    def try_send(self, service_checks: list, must_stop: threading.Event):
        try:
            last_service_check = service_checks[-1]
        except IndexError:
            return

        retry_count = 0
        while True:
            retry_count = retry_count + 1

            if last_service_check.timestamp + self.stale_age < time.time():
                self.logger.warning('Dropping batch because it is too old')
                return

            if self.max_retry != -1 and retry_count > self.max_retry:
                self.logger.warning('Dropping batch because '
                                    'max_retry has been reached')
                return

            try:
                self._send_batch(service_checks)
            except Exception as e:
                self.logger.warning('Could not send batch (attempt {}/{}): {}'
                                    .format(retry_count, self.max_retry, e))
                if must_stop.is_set():
                    return

                if self.max_retry == -1 or retry_count < self.max_retry:
                    self._wait_before_retry(must_stop)
            else:
                self.logger.info('Batch sent')
                return

    def _wait_before_retry(self, must_stop: threading.Event):
        self.logger.info('Waiting %s s before retry', self.retry_delay)
        must_stop.wait(timeout=self.retry_delay)

    def run(self, must_stop, queue: Queue):
        batch = list()
        batch_created_at = datetime.utcnow()

        while not must_stop.is_set():

            # Calculate how long to wait before the current batch
            # should be sent.
            if not batch:
                wait_timeout = None
            else:
                wait_timeout = (
                    batch_created_at + self.max_batch_delay - datetime.utcnow()
                ).total_seconds()
                if wait_timeout < 0:
                    wait_timeout = 0

            try:
                service_check = queue.get(timeout=wait_timeout)
            except Empty:
                pass
            else:
                if not isinstance(service_check, threading.Event):
                    self.logger.debug('Got check {}'.format(service_check))
                    if not batch:
                        # Current batch is empty, create a new one
                        batch.append(service_check)
                        batch_created_at = datetime.utcnow()
                    else:
                        # Current batch is not empty, just append the check
                        batch.append(service_check)

            # A batch should be sent if either:
            #   - the batch isfull
            #   - the first check has waited long enough in the batch
            #   - sauna is shutting down
            should_send_batch = (
                len(batch) >= self.max_batch_size
                or
                (batch_created_at + self.max_batch_delay) < datetime.utcnow()
                or
                must_stop.is_set()
            )
            if should_send_batch:
                self.try_send(batch, must_stop)
                batch = list()

        self.logger.debug('Exited consumer thread')


class QueuedConsumer(BatchQueuedConsumer):
    """Consumer that processes checks synchronously one by one.

    QueuedConsumers wait for checks to appear on a queue. They process each
    check one by one in order until the queue is empty.
    """

    max_batch_size = 1


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
