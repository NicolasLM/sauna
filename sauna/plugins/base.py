import copy
import logging


class Plugin:
    """Base class to implement check plugins.

    Most methods use a check_config dict that mostly defines thresholds.
    It looks like:
    check_config = {
        'warn': '80%',
        'crit': '90%',
        'other_data': 'something'
    }
    """

    STATUS_OK = 0
    STATUS_WARN = 1
    STATUS_CRIT = 2
    STATUS_UNKNOWN = 3

    def __init__(self, config):
        if config is None:
            config = {}
        self.config = config

    @property
    def logger(self):
        return logging.getLogger('sauna.' + self.__class__.__name__)

    @classmethod
    def get_thresholds(cls, check_config, modifier=None):
        critical_threshold = check_config['crit']
        if modifier:
            critical_threshold = modifier(critical_threshold)
        warning_threshold = check_config['warn']
        if modifier:
            warning_threshold = modifier(warning_threshold)
        return critical_threshold, warning_threshold

    @classmethod
    def _value_to_status_less(cls, value, check_config, modifier=None):
        """Return an error when the value should be less than threshold."""
        critical, warning = cls.get_thresholds(check_config, modifier)
        if value >= critical:
            return cls.STATUS_CRIT
        elif value >= warning:
            return cls.STATUS_WARN
        else:
            return cls.STATUS_OK

    @classmethod
    def _value_to_status_more(cls, value, check_config, modifier=None):
        """Return an error when the value should be more than threshold."""
        critical, warning = cls.get_thresholds(check_config, modifier)
        if value <= critical:
            return cls.STATUS_CRIT
        elif value <= warning:
            return cls.STATUS_WARN
        else:
            return cls.STATUS_OK

    @classmethod
    def _strip_percent_sign(cls, value):
        try:
            return int(value)
        except ValueError:
            return int(value.split('%')[0])

    @classmethod
    def _strip_percent_sign_from_check_config(cls, check_config):
        check_config = copy.deepcopy(check_config)
        check_config['warn'] = cls._strip_percent_sign(check_config['warn'])
        check_config['crit'] = cls._strip_percent_sign(check_config['crit'])
        return check_config

    @classmethod
    def status_code_to_str(cls, status_code):
        if status_code == Plugin.STATUS_OK:
            return 'OK'
        elif status_code == Plugin.STATUS_WARN:
            return 'WARNING'
        elif status_code == Plugin.STATUS_CRIT:
            return 'CRITICAL'
        else:
            return 'UNKNOWN'


class Check:
    def __init__(self, name, periodicity, check_func, config):
        self.name = name
        self.periodicity = periodicity
        self.check_func = check_func
        self.config = config

    def run_check(self):
        return self.check_func(self.config)


class PsutilPlugin(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            from .. import DependencyError
            raise DependencyError(self.__class__.__name__, 'psutil',
                                  'psutil', 'python3-psutil')
