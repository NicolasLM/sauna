from sauna.plugins import Plugin, human_to_bytes, bytes_to_human,\
    PluginRegister

my_plugin = PluginRegister('Disque')


@my_plugin.plugin()
class Disque(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import redis
            self.redis = redis
        except ImportError:
            from ... import DependencyError
            raise DependencyError(self.__class__.__name__, 'redis-py',
                                  'redis', 'python3-redis')
        self._disque_info = None

    @my_plugin.check()
    def used_memory(self, check_config):
        status = self._value_to_status_less(
            self.disque_info['used_memory'], check_config, human_to_bytes
        )
        output = 'Used memory: {}'.format(
            self.disque_info['used_memory_human'])
        return status, output

    @my_plugin.check()
    def used_memory_rss(self, check_config):
        status = self._value_to_status_less(
            self.disque_info['used_memory_rss'], check_config, human_to_bytes
        )
        output = 'Used memory RSS: {}'.format(
            bytes_to_human(self.disque_info['used_memory_rss'])
        )
        return status, output

    @property
    def disque_info(self):
        if not self._disque_info:
            r = self.redis.StrictRedis(**self.config)
            self._disque_info = r.info()
        return self._disque_info

    @my_plugin.check()
    def qlen(self, check_config):
        r = self.redis.StrictRedis(**self.config)
        num_items = r.execute_command('QLEN', check_config['key'])
        status = self._value_to_status_less(num_items, check_config)
        output = '{} items in key {}'.format(num_items, check_config['key'])
        return status, output

    @staticmethod
    def config_sample():
        return '''
        # Disque, an in-memory, distributed job queue
        # This is a Redis fork, https://github.com/antirez/disque
        - type: Disque
          checks:
            - type: used_memory
              warn: 128M
              crit: 1024M
            - type: used_memory_rss
              warn: 128M
              crit: 1024M
            # Check the size of a queue
            - type: qlen
              key: my-queue
              warn: 10
              crit: 20
          config:
            host: localhost
            port: 7711
        '''
