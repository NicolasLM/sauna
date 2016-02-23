import copy

STATUS_OK = 0
STATUS_WARN = 1
STATUS_CRIT = 2
STATUS_UNKNOWN = 3


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

    def __init__(self, config):
        if config is None:
            config={}
        self.config = config

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
            return STATUS_CRIT
        elif value >= warning:
            return STATUS_WARN
        else:
            return STATUS_OK

    @classmethod
    def _value_to_status_more(cls, value, check_config, modifier=None):
        """Return an error when the value should be more than threshold."""
        critical, warning = cls.get_thresholds(check_config, modifier)
        if value <= critical:
            return STATUS_CRIT
        elif value <= warning:
            return STATUS_WARN
        else:
            return STATUS_OK

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


def get_plugin(plugin_name):
    if plugin_name == 'Load':
        from .load import LoadPlugin
        return LoadPlugin
    if plugin_name == 'Memory':
        from .memory import MemoryPlugin
        return MemoryPlugin
    if plugin_name == 'Disk':
        from .disk import DiskPlugin
        return DiskPlugin
    if plugin_name == 'Command':
        from .command import CommandPlugin
        return CommandPlugin
    if plugin_name == 'Redis':
        from .redis import RedisPlugin
        return RedisPlugin
    if plugin_name == 'Processes':
        from .processes import ProcessesPlugin
        return ProcessesPlugin
    raise ValueError('Unknown plugin {}'.format(plugin_name))


def get_all_plugins():
    from .load import LoadPlugin
    from .memory import MemoryPlugin
    from .disk import DiskPlugin
    from .command import CommandPlugin
    from .redis import RedisPlugin
    from .processes import ProcessesPlugin
    return (LoadPlugin, MemoryPlugin, DiskPlugin, CommandPlugin, RedisPlugin,
            ProcessesPlugin)


def bytes_to_human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def human_to_bytes(size):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    size = size.upper()
    for i, s in enumerate(symbols):
        if s in size:
            base = int(size.split(s)[0])
            return base * (1024 ** (i+1))
    return int(size)
