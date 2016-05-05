from sauna.plugins.base import Plugin


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


class PluginRegister:
    all_plugins = {}

    def __init__(self, name):
        self.name = name
        self.plugin_class = None
        self.checks = {}

    def check(self, **options):
        def decorator(func):
            check_name = options.pop("name", func.__name__)
            self.checks[check_name] = func.__name__
            return func
        return decorator

    def plugin(self):
        def decorator(plugin_cls):
            self.plugin_class = plugin_cls
            # At this point all data should be set
            self.all_plugins[self.name] = {
                'plugin_cls': self.plugin_class,
                'checks': self.checks
            }
            return plugin_cls
        return decorator

    @classmethod
    def get_plugin(cls, name):
        try:
            return cls.all_plugins[name]
        except KeyError:
            return None
