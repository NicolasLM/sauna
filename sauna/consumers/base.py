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
        self.logging('info',
                     'Waiting {}s before retry'.format(self.retry_delay))
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
            self.logging(
                'debug',
                'Got check {}'.format(service_check)
            )
            self.try_send(service_check, must_stop)
        self.logging('debug', 'Exited consumer thread')


class AsyncConsumer(Consumer):
    """Consumer that processes checks asynchronously.

    It is up to the consumer to read the checks when it needs to. No
    queueing is made.
    """
    pass
