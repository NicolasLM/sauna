import unittest
try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

from sauna.scheduler import Scheduler, Job


class SchedulerTest(unittest.TestCase):

    def test_scheduler_3_jobs(self):
        """
        Test scheduler with 3 jobs, one every 1, 2 and 3 seconds.

        0   1   2   3   4   5
        ---------------------
        |   |   |   |   |   |
        A   A   A   A   A   A
        B       B       B
        C           C
        """
        mock1, mock2, mock3 = mock.Mock(), mock.Mock(), mock.Mock()
        ja, jb, jc = Job(1, mock1), Job(2, mock2), Job(3, mock3)
        s = Scheduler([ja, jb, jc])

        self.assertEqual(s.tick_duration, 1)
        self.assertEqual(s._ticks, 6)

        self.assertListEqual(next(s), [ja, jb, jc])
        self.assertListEqual(next(s), [ja])
        self.assertListEqual(next(s), [ja, jb])
        self.assertListEqual(next(s), [ja, jc])
        self.assertListEqual(next(s), [ja, jb])
        self.assertListEqual(next(s), [ja])

        self.assertEqual(mock1.call_count, 6)
        self.assertEqual(mock2.call_count, 3)
        self.assertEqual(mock3.call_count, 2)

    def test_scheduler_2_jobs(self):
        """Jobs every 1 and 5 min."""
        ja, jb = Job(60, lambda: None), Job(300, lambda: None)
        s = Scheduler([ja, jb])

        self.assertEqual(s.tick_duration, 60)
        self.assertEqual(s._ticks, 5)

        self.assertListEqual(next(s), [ja, jb])
        for _ in range(4):
            self.assertListEqual(next(s), [ja])
        self.assertListEqual(next(s), [ja, jb])

    def test_number_of_ticks(self):
        self.assertEqual(
            Scheduler.find_minimum_ticks_required(1, {13, 15}),
            195
        )
        self.assertEqual(
            Scheduler.find_minimum_ticks_required(1, {5, 13, 1, 15}),
            195
        )


class JobTest(unittest.TestCase):

    def test_execute_job(self):
        mock1 = mock.Mock()
        job = Job(10, mock1, 'foo', 1, bar='baz')
        job()
        self.assertTrue(mock1.called)
        self.assertEqual(str(mock1.call_args), "call('foo', 1, bar='baz')")

    def test_non_callable_job(self):
        with self.assertRaises(ValueError):
            Job(10, 'foo')
