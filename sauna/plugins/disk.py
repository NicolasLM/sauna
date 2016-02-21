from . import PsutilPlugin


class DiskPlugin(PsutilPlugin):

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

    @staticmethod
    def config_sample():
        return '''
        # Usage of disks
        Disk:
          checks:
            - type: used_percent
              warn: 80%
              crit: 90%
        '''
