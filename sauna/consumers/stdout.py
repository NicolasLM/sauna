from . import QueuedConsumer


class StdoutConsumer(QueuedConsumer):

    def _send(self, service_check):
        print(service_check)

    @staticmethod
    def config_sample():
        return '''
        # Just prints checks on the standard output
        Stdout:
        '''
