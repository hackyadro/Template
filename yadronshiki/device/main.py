import time, ujson as json
import config
from wifi import WiFiManager
from mqtt_client import MQTTClientWrapper
from ble_scanner import BLEScanner
from adv_parser import BeaconParser

class BeaconCollector:
    def __init__(self):
        self.wifi = WiFiManager(config.WIFI_SSID, config.WIFI_PASS)
        self.mqtt = MQTTClientWrapper(config.MQTT_CLIENT_ID, config.MQTT_BROKER, config.MQTT_PORT)
        self.scanner = BLEScanner()
        self.parser = BeaconParser()

    def run(self):
        if not self.wifi.connect():
            return
        if not self.mqtt.connect():
            return

        cycle = 0
        while True:
            cycle += 1
            print(f"\n--- Цикл #{cycle} ---")

            devices = self.scanner.scan(config.SCAN_DURATION_MS)
            print(f"Обнаружено {len(devices)} устройств")

            beacons = {}
            for addr, rssi, adv in devices:
                parsed = self.parser.adv_parse(adv)
                name = parsed.get("local_name")

                if not name or not name.startswith("beacon_"):
                    continue

                info = {"addr": addr, "rssi": int(rssi), "name": name}

                if parsed.get("manuf_data"):
                    ib = self.parser.parse_ibeacon(parsed["manuf_data"])
                    if ib:
                        info.update(ib)

                beacons[addr] = max([info, beacons.get(addr, {"rssi": -999})], key=lambda x: x["rssi"])

            if beacons:
                payload = {"ts": time.time(), "count": len(beacons), "beacons": list(beacons.values())}
                print(f"→ Отправка {len(beacons)} устройств в MQTT")
                self.mqtt.publish(config.MQTT_TOPIC, json.dumps(payload).encode())
            else:
                print("! Подходящих устройств не найдено")

            time.sleep(3)

if __name__ == "__main__":
    try:
        BeaconCollector().run()
    except KeyboardInterrupt:
        print("Остановка программы...")
