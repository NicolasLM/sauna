import os

from sauna.plugins import PluginRegister
from sauna.plugins.base import PsutilPlugin

my_plugin = PluginRegister('Disk')


@my_plugin.plugin()
class Disk(PsutilPlugin):

    @my_plugin.check()
    def used_percent(self, check_config):
        check_config = self._strip_percent_sign_from_check_config(check_config)
        for part in self.psutil.disk_partitions(all=False):
            part_usage = self.psutil.disk_usage(part.mountpoint).percent
            status = self._value_to_status_less(part_usage, check_config)
            if status > 0:
                return (
                    status,
                    'Partition {} is full at {}%'.format(part.mountpoint,
                                                         part_usage)
                )
        return 0, 'Disk usage correct'

    @my_plugin.check()
    def used_inodes_percent(self, check_config):
        check_config = self._strip_percent_sign_from_check_config(check_config)
        for part in self.psutil.disk_partitions(all=False):
            s = os.statvfs(part.mountpoint)
            try:
                inodes_usage = int((s.f_files - s.f_favail) * 100 / s.f_files)
            except ZeroDivisionError:
                continue
            status = self._value_to_status_less(
                inodes_usage, check_config, self._strip_percent_sign
            )
            if status != self.STATUS_OK:
                return (
                    status,
                    'Partition {} uses {}% of inodes'.format(part.mountpoint,
                                                             inodes_usage)
                )
        return self.STATUS_OK, 'Inodes usage correct'

    @staticmethod
    def config_sample():
        return '''
        # Usage of disks
        Disk:
          checks:
            - type: used_percent
              warn: 80%
              crit: 90%
            - type: used_inodes_percent
              warn: 80%
              crit: 90%
        '''
