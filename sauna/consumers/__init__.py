class ConsumerRegister:
    all_consumers = {}

    def __init__(self, name):
        self.name = name
        self.consumer_class = None

    def consumer(self):
        def decorator(plugin_cls):
            self.consumer_class = plugin_cls
            self.all_consumers[self.name] = {
                'consumer_cls': self.consumer_class
            }
            return plugin_cls
        return decorator

    @classmethod
    def get_consumer(cls, name):
        try:
            return cls.all_consumers[name]
        except KeyError:
            return None
