class CommandRegister:
    all_commands = {}

    def command(self, **options):
        def decorator(func):
            command_name = options.pop('name', func.__name__)
            self.all_commands[command_name] = func
            return func
        return decorator

    @classmethod
    def get_command(cls, command_name):
        try:
            return cls.all_commands[command_name]
        except KeyError:
            return None
