from sauna.plugins import Plugin, human_to_bytes, bytes_to_human,\
    PluginRegister

my_plugin = PluginRegister('Redis')


@my_plugin.plugin()
class Redis(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import redis
            self.redis = redis
        except ImportError:
            from .. import DependencyError
            raise DependencyError(self.__class__.__name__, 'redis-py',
                                  'redis', 'python3-redis')
        self._redis_info = None

    @my_plugin.check()
    def used_memory(self, check_config):
        status = self._value_to_status_less(
            self.redis_info['used_memory'], check_config, human_to_bytes
        )
        output = 'Used memory: {}'.format(self.redis_info['used_memory_human'])
        return status, output

    @my_plugin.check()
    def used_memory_rss(self, check_config):
        status = self._value_to_status_less(
            self.redis_info['used_memory_rss'], check_config, human_to_bytes
        )
        output = 'Used memory RSS: {}'.format(
            bytes_to_human(self.redis_info['used_memory_rss'])
        )
        return status, output

    @property
    def redis_info(self):
        if not self._redis_info:
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 6379)
            r = self.redis.StrictRedis(host=host, port=port)
            self._redis_info = r.info()
        return self._redis_info

    @staticmethod
    def config_sample():
        return '''
        # Redis
        Redis:
          checks:
            - type: used_memory
              warn: 128M
              crit: 1024M
            - type: used_memory_rss
              warn: 128M
              crit: 1024M
          config:
            host: localhost
            port: 6379
        '''
