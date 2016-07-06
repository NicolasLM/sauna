import os
import glob
from collections import namedtuple
from functools import reduce

from sauna.plugins import Plugin, PluginRegister


Sensor = namedtuple('Sensor', ['device_name', 'label', 'value'])

my_plugin = PluginRegister('Hwmon')


@my_plugin.plugin()
class Hwmon(Plugin):
    """Linux hardware monitoring plugin.

    This plugin crawls Linux's /sys/class/hwmon to find usable sensors. Be
    warned that this method is quite fragile since exotic hardware may present
    values that need offsets or conversions.

    A more solid approach could be to use lm-sensors, but:
    - it requires to install and configure lm-sensors
    - there is no proper python bindings to the library
    - parsing the output of 'sensors' is not fun nor efficient
    """

    @my_plugin.check()
    def temperature(self, check_config):
        dummy_sensor = Sensor(device_name='Dummy', label='Dummy', value=-1000)
        sensors = self._get_temperatures()
        if check_config.get('sensors'):
            sensors = [
                sensor for sensor in sensors
                if sensor.device_name in check_config.get('sensors', [])
            ]
        sensor = reduce(lambda x, y: x if x.value > y.value else y,
                        sensors,
                        dummy_sensor)
        if sensor is dummy_sensor:
            return self.STATUS_UNKNOWN, 'No sensor found'
        status = self._value_to_status_less(sensor.value, check_config)
        if status > self.STATUS_OK:
            return (
                status,
                'Sensor {}/{} {}°C'.format(sensor.device_name,
                                           sensor.label,
                                           sensor.value)
            )
        return self.STATUS_OK, 'Temperature okay ({}°C)'.format(sensor.value)

    @classmethod
    def _get_temperatures(cls):
        temperatures = list()
        for device in cls._get_devices():
            temperatures.extend(cls._process_device(device))
        return temperatures

    @classmethod
    def _get_devices(cls):
        base_path = '/sys/class/hwmon'
        devices = set()
        for file in os.listdir(base_path):
            file_path = os.path.join(base_path, file)
            if os.path.isfile(os.path.join(file_path, 'device', 'name')):
                devices.add(os.path.join(file_path, 'device'))
            else:
                devices.add(file_path)
        return devices

    @classmethod
    def _process_device(cls, device):
        sensors = list()
        with open(os.path.join(device, 'name')) as f:
            device_name = f.read().strip()
        pattern = 'temp*_input'
        for temp_file in glob.glob(os.path.join(device, pattern)):
            with open(temp_file) as f:
                temperature = int(int(f.read().strip())/1000)
            try:
                with open(temp_file.replace('input', 'label')) as f:
                    label = f.read().strip()
            except (OSError, IOError):
                label = None

            sensors.append(Sensor(device_name, label, temperature))

        return sensors

    @staticmethod
    def config_sample():
        return '''
        # Linux hardware monitoring
        - type: Hwmon
          checks:
            # Raise an alert if any sensor gets beyond a threshold
            - type: temperature
              warn: 65
              crit: 85
              # Optionally, only check some sensors
              sensors: ['acpitz', 'coretemp']
        '''
