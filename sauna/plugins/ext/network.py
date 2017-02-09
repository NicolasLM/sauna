import time

from sauna.plugins.base import PsutilPlugin
from sauna.plugins import human_to_bytes, bytes_to_human, PluginRegister

my_plugin = PluginRegister('Network')


@my_plugin.plugin()
class Network(PsutilPlugin):

    def __init__(self, config):
        super().__init__(config)

    @my_plugin.check()
    def upload_data_speed(self, check_config):
        ul, _, _, _ = self.get_network_data(
            interface=check_config['interface'])
        ul = round(ul, 2)

        return (
            self._value_to_status_less(ul, check_config, human_to_bytes),
            'Upload speed: {}/s'.format(bytes_to_human(ul))
        )

    @my_plugin.check()
    def download_data_speed(self, check_config):
        _, dl, _, _ = self.get_network_data(
            interface=check_config['interface'])
        dl = round(dl, 2)
        return (
            self._value_to_status_less(dl, check_config, human_to_bytes),
            'Download speed: {}/s'.format(bytes_to_human(dl))
        )

    @my_plugin.check()
    def upload_packet_speed(self, check_config):
        _, _, ul, _ = self.get_network_data(
            interface=check_config['interface'])
        ul = round(ul, 2)
        return (
            self._value_to_status_less(ul, check_config),
            'Upload : {} p/s'.format(ul)
        )

    @my_plugin.check()
    def download_packet_speed(self, check_config):
        _, _, _, dl = self.get_network_data(
            interface=check_config['interface'])
        dl = round(dl, 2)
        return (
            self._value_to_status_less(dl, check_config),
            'Download : {} p/s'.format(dl)
        )

    def get_network_data(self, interface='eth0', delay=1):
        t0 = time.time()
        counter = self.psutil.net_io_counters(pernic=True)[interface]
        first_values = (counter.bytes_sent, counter.bytes_recv,
                        counter.packets_sent, counter.packets_recv)

        time.sleep(delay)
        counter = self.psutil.net_io_counters(pernic=True)[interface]
        t1 = time.time()
        last_values = (counter.bytes_sent, counter.bytes_recv,
                       counter.packets_sent, counter.packets_recv)
        kb_ul, kb_dl, p_ul, p_dl = [
            (last - first) / (t1 - t0)
            for last, first in zip(last_values, first_values)
        ]
        return kb_ul, kb_dl, p_ul, p_dl

    @staticmethod
    def config_sample():
        return '''
  - type: Network

    checks:
      - type: upload_data_speed
        interface: em1
        # Crit if download > 2MB/s
        warn: 500K
        crit: 2M
      - type: download_data_speed
        interface: em1
        # Warn if upload > 500KB/s
        warn: 500K
        crit: 2M
      - type: upload_packet_speed
        interface: em1
        # Values are in packet/s
        warn: 500
        crit: 2000
      - type: download_packet_speed
        interface: em1
        # Values are in packet/s
        warn: 500
        crit: 2000
        '''
