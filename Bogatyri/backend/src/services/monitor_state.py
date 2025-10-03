import threading
from src.models.schemas import BeaconConfig
from src.services.RSSISubscriber import MqttSensorSubscriber
from src.services.mqtt_publisher import mqtt_publish_lines


class MonitorState:
    def __init__(self, mqtt_subscriber: MqttSensorSubscriber, update_time_seconds: float = 1):
        self.update_time_seconds = update_time_seconds
        self.beacons = {}
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        self.mqtt_subscriber = mqtt_subscriber

    def set_update_time(self, update_time_seconds: float):
        self.update_time_seconds = update_time_seconds

    def add_beacons(self, beacons_list: list[BeaconConfig]):
        self.beacons = {beacon.name: (beacon.x, beacon.y) for beacon in beacons_list}

    def get_beacons(self):
        return self.beacons

    def _monitoring_loop(self):
        mqtt_publish_lines(self.mqtt_subscriber, self.update_time_seconds, stop_event=self._stop_event)

    def start_monitoring(self, update_time_seconds: float = 1):
        if self.is_running:
            print("Monitoring is already running")
            return
        self.is_running = True
        self.set_update_time(update_time_seconds)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        if not self.is_running:
            print("Monitoring is not running")
            return
        self.is_running = False
        self._stop_event.set()
        self._thread.join()
        print("Monitoring stopped.")
