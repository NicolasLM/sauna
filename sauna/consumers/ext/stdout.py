from sauna.consumers.base import QueuedConsumer
from sauna.consumers import ConsumerRegister

my_consumer = ConsumerRegister('Stdout')


@my_consumer.consumer()
class StdoutConsumer(QueuedConsumer):

    def _send(self, service_check):
        print(service_check)

    @staticmethod
    def config_sample():
        return '''
        # Just prints checks on the standard output
        Stdout:
        '''
