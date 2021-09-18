import json
import re
from typing import Optional, Set, List

from sauna.consumers.base import BatchQueuedConsumer
from sauna.consumers import ConsumerRegister

my_consumer = ConsumerRegister('HomeAssistantMQTT')


status_to_name = {
    0: 'OK',
    1: 'Warning',
    2: 'Critical',
    3: 'Unknown'
}


@my_consumer.consumer()
class HomeAssistantMQTTConsumer(BatchQueuedConsumer):
    """Report checks to Home Assistant via MQTT.

    Uses the Home Assistant MQTT discovery functionnality to
    dynamically create sensors for each couple of host/check.
    The first time Sauna sees a new check for a host, it inserts
    a MQTT message on a well known topic that HA monitors with the
    configuration for the new sensor. Each host/check gets its own
    MQTT topic that HA starts subscribing to.

    Afterwards checks are just sent on their own topic.
    """

    def __init__(self, config):
        super().__init__(config)
        try:
            import paho.mqtt.publish as mqtt_publish
            self.mqtt_publish = mqtt_publish
        except ImportError:
            from ... import DependencyError
            raise DependencyError(self.__class__.__name__, 'paho-mqtt',
                                  'paho-mqtt', 'python3-paho-mqtt')
        self.config = {
            'hostname': config.get('hostname', 'localhost'),
            'port': config.get('port', 1883),
            'auth': config.get('auth', None)
        }
        self._configured_checks: Set[str] = set()

        from ... import __version__
        self._version = __version__

    def _to_safe_str(self, text: str) -> str:
        return re.sub('[^0-9a-zA-Z]+', '_', text)

    def _get_check_discovery(self, service_check) -> Optional[dict]:
        safe_hostname = self._to_safe_str(service_check.hostname)
        safe_name = self._to_safe_str(service_check.name)
        unique_id = f"sauna_{safe_hostname}_{safe_name}"
        if unique_id in self._configured_checks:
            return None

        self._configured_checks.add(unique_id)
        state_topic = f"sauna/{safe_hostname}/{safe_name}/state"
        return {
            "topic": f"homeassistant/sensor/{unique_id}/config",
            "retain": True,
            "qos": 1,
            "payload": json.dumps({
                "value_template": "{{ value_json.status }}",
                "state_topic": state_topic,
                "json_attributes_topic": state_topic,
                "device": {
                    "identifiers": [service_check.hostname],
                    "name": service_check.hostname,
                    "manufacturer": "Sauna",
                    "sw_version": f"Sauna {self._version}"
                },
                "name": f"{service_check.hostname} {service_check.name}",
                "unique_id": unique_id,
                "platform": "mqtt"
            })
        }

    def _send_batch(self, service_checks: list):
        msgs: List[dict] = list()
        pending_discovery_checks: Set[str] = set()

        for service_check in service_checks:

            safe_hostname = self._to_safe_str(service_check.hostname)
            safe_name = self._to_safe_str(service_check.name)
            unique_id = f"sauna_{safe_hostname}_{safe_name}"

            discovery_msg = self._get_check_discovery(service_check)
            if discovery_msg is not None:
                msgs.append(discovery_msg)
                pending_discovery_checks.add(unique_id)

            msgs.append({
                'topic': f"sauna/{safe_hostname}/{safe_name}/state",
                'retain': False,
                'qos': 0,
                'payload': json.dumps({
                    "status": status_to_name.get(service_check.status),
                    "output": service_check.output
                })
            })

        try:
            self.mqtt_publish.multiple(
                msgs=msgs,
                hostname=self.config['hostname'],
                port=self.config['port'],
                auth=self.config['auth']
            )
        except Exception:
            # Remove the discovery message that could not be sent so that
            # they will be recreated the next time they are seen.
            self._configured_checks.difference_update(pending_discovery_checks)
            raise

    @staticmethod
    def config_sample():
        return '''
        # Report checks to Home Assistant via MQTT
        - type: HomeAssistantMQTT
          hostname: localhost
          port: 1883
          auth:
            username: user
            password: pass
        '''
