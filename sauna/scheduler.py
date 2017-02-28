import time
import fractions
from functools import reduce
from logging import getLogger

logger = getLogger(__name__)


class Scheduler:

    def __init__(self, jobs):
        """
        Create a new Scheduler.

        >>> s = Scheduler([Job(1, max, 100, 200)])
        >>> for jobs in s:
        ...    time.sleep(s.tick_duration)

        :param jobs: Sequence of jobs to schedule
        """
        periodicities = {job.periodicity for job in jobs}
        self.tick_duration = reduce(lambda x, y: fractions.gcd(x, y),
                                    periodicities)
        self._ticks = self.find_minimum_ticks_required(self.tick_duration,
                                                       periodicities)
        self._jobs = jobs
        self._current_tick = 0
        logger.debug('Scheduler has {} ticks, each one is {} seconds'.
                     format(self._ticks, self.tick_duration))

    @staticmethod
    def find_minimum_ticks_required(tick_duration, periodicities):
        """Find the minimum number of ticks required to execute all jobs
        at once."""
        ticks = 1
        for periodicity in reversed(sorted(periodicities)):
            if ticks % periodicity != 0:
                ticks *= int(periodicity / tick_duration)
        return ticks

    def __iter__(self):
        return self

    def __next__(self):
        jobs = [job for job in self._jobs
                if ((self._current_tick * self.tick_duration)
                    % job.periodicity) == 0
                ]
        if jobs:
            logger.debug('Tick {}, scheduled {}'.
                         format(self._current_tick, jobs))
        self._current_tick += 1
        if self._current_tick >= self._ticks:
            self._current_tick = 0
        for job in jobs:
            job()
        return jobs

    def run(self):
        """Shorthand for iterating over all jobs forever.

        >>> print_time = lambda: print(time.time())
        >>> s = Scheduler([Job(1, print_time)])
        >>> s.run()
        1470146095.0748773
        1470146096.076028
        """
        for _ in self:
            time.sleep(self.tick_duration)


class Job:

    def __init__(self, periodicity, func, *func_args, **func_kwargs):
        """
        Create a new Job to be scheduled and run periodically.

        :param periodicity: Number of seconds to wait between job runs
        :param func: callable that perform the job action
        :param func_args: arguments of the callable
        :param func_kwargs: keyword arguments of the callable
        """
        if not callable(func):
            raise ValueError('func attribute must be callable')
        self.periodicity = periodicity
        self.func = func
        self.func_args = func_args
        self.func_kwargs = func_kwargs

    def __repr__(self):
        try:
            name = self.func.__name__
        except AttributeError:
            name = 'unknown'
        return '<Job {} every {} seconds>'.format(name,
                                                  self.periodicity)

    def __call__(self, *args, **kwargs):
        self.func(*self.func_args, **self.func_kwargs)
