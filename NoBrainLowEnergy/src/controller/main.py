import utime  # type: ignore
import network  # type: ignore
import ubinascii  # type: ignore
import machine  # type: ignore
from micropython import const  # type: ignore

try:
    import ujson as json  # type: ignore
except ImportError:  # pragma: no cover - fallback for standard json
    import json  # type: ignore

from umqtt.simple import MQTTClient  # type: ignore

_IRQ_SCAN_RESULT = const(5)  # or const(4) / const( _IRQ_SCAN_RESULT ) depending on version
_IRQ_SCAN_DONE = const(6)

SCAN_WINDOW_US = 30000
CONFIG_FILE = "scan_config.json"
DEFAULT_FREQUENCY = 1.0  # Hz (1 scan per second)
MIN_FREQUENCY = 0.1  # Hz
MAX_FREQUENCY = 10.0  # Hz

MQTT_CONFIG_FILE = "mqtt_config.json"
MQTT_KEEPALIVE_SEC = 60
DEFAULT_TOPIC_TEMPLATE = "devices/{device_id}/beacons"
WIFI_CONNECT_TIMEOUT_MS = 20000

_AD_TYPE_SHORT_NAME = const(0x08)
_AD_TYPE_COMPLETE_NAME = const(0x09)

# Global storage for discovered beacons
discovered_beacons = {}

scan_active = False

def load_mqtt_config():
    try:
        with open(MQTT_CONFIG_FILE, "r") as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                return data
            print("MQTT config has unexpected format, skipping publisher.")
            return None
    except (OSError, ValueError) as exc:
        print("Unable to load MQTT config:", exc)
        return None


def ensure_wifi_connected(wifi_cfg, timeout_ms=WIFI_CONNECT_TIMEOUT_MS):
    if not wifi_cfg:
        return True

    ssid = wifi_cfg.get("ssid")
    if not ssid:
        return True

    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)

    if sta.isconnected():
        return True

    print("Connecting to Wi-Fi:", ssid)
    try:
        sta.connect(ssid, wifi_cfg.get("password", ""))
    except OSError as exc:
        print("Wi-Fi connection error:", exc)
        return False

    start = utime.ticks_ms()
    while not sta.isconnected() and utime.ticks_diff(utime.ticks_ms(), start) < timeout_ms:
        utime.sleep_ms(250)

    if sta.isconnected():
        try:
            print("Wi-Fi connected, IP:", sta.ifconfig()[0])
        except Exception:
            print("Wi-Fi connected")
        return True

    print("Wi-Fi connection timed out while preparing publisher.")
    return False


class BeaconPublisher:
    def __init__(self, mqtt_cfg):
        self._config = mqtt_cfg or {}
        self._broker = self._config.get("broker") or {}
        self._keepalive_sec = MQTT_KEEPALIVE_SEC
        self._device_id = ubinascii.hexlify(machine.unique_id()).decode()
        self.client_id = self._config.get("client_id") or "beacon-pub-" + self._device_id
        topic = DEFAULT_TOPIC_TEMPLATE.format(device_id=self._device_id)
        self.topic = topic
        self.topic_bytes = topic if isinstance(topic, bytes) else topic.encode("utf-8")
        self.client = None
        self._last_activity = utime.ticks_ms()

    def ensure_connected(self):
        if self.client:
            return True

        host = self._broker.get("host")
        if not host:
            print("MQTT broker host missing in configuration.")
            return False

        port = int(self._broker.get("port") or 1883)
        username = self._broker.get("username") or None
        password = self._broker.get("password") or None

        try:
            client = MQTTClient(
                self.client_id,
                host,
                port=port,
                user=username,
                password=password,
                keepalive=self._keepalive_sec,
            )
            client.connect()
            self.client = client
            self._touch()
            print("MQTT connected to {}:{} as {} (topic: {})".format(host, port, self.client_id, self.topic))
            return True
        except (OSError, ValueError) as exc:
            print("MQTT connection failed:", exc)
            self.client = None
            return False

    def publish_pending(self, beacons):
        if not self.ensure_connected():
            return

        if not beacons:
            self._maybe_ping()
            return

        client = self.client
        if not client:
            return

        dirty_entries = [
            (addr, info)
            for addr, info in beacons.items()
            if info.get("dirty")
        ]

        if not dirty_entries:
            self._maybe_ping()
            return

        payload_beacons = []
        for addr, info in dirty_entries:
            payload_beacons.append(
                {
                    "address": addr,
                    "name": info.get("name"),
                    "rssi": info.get("rssi"),
                    "last_seen": info.get("last_seen"),
                    "scan_count": info.get("scan_count"),
                }
            )

        envelope = {
            "device_id": self._device_id,
            "timestamp": utime.time(),
            "count": len(payload_beacons),
            "beacons": payload_beacons,
        }

        try:
            payload = json.dumps(envelope)
        except Exception as exc:
            print("Failed to encode aggregated payload:", exc)
            for _, info in dirty_entries:
                info["dirty"] = False # if we got here things are bad
            print("SILENT FAIL: Cleared dirty flags despite encoding failure.")
            return

        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        try:
            client.publish(self.topic_bytes, payload)
            for _, info in dirty_entries:
                info["dirty"] = False
            self._touch()
        except OSError as exc:
            print("MQTT publish failed:", exc)
            self.disconnect()

        self._maybe_ping()

    def disconnect(self):
        if not self.client:
            return
        try:
            self.client.disconnect()
        except Exception:
            pass
        self.client = None

    def _touch(self):
        self._last_activity = utime.ticks_ms()

    def _maybe_ping(self):
        if not self.client or self._keepalive_sec <= 0:
            return

        interval_ms = (self._keepalive_sec * 1000) // 2
        if utime.ticks_diff(utime.ticks_ms(), self._last_activity) < interval_ms:
            return

        try:
            self.client.ping()
            self._touch()
        except OSError as exc:
            print("MQTT ping failed:", exc)
            self.disconnect()


def load_config():
    """Load scanning frequency configuration from file, or use default."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            frequency = config.get('scan_frequency', DEFAULT_FREQUENCY)
            # Validate frequency range
            if frequency < MIN_FREQUENCY:
                frequency = MIN_FREQUENCY
            elif frequency > MAX_FREQUENCY:
                frequency = MAX_FREQUENCY
            return frequency
    except (OSError, ValueError, KeyError):
        # File doesn't exist or is corrupted, use default
        return DEFAULT_FREQUENCY


def save_config(frequency):
    """Save scanning frequency configuration to file."""
    try:
        config = {'scan_frequency': frequency}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except OSError:
        return False


def set_frequency(new_frequency):
    """Set new scanning frequency and save to config."""
    if MIN_FREQUENCY <= new_frequency <= MAX_FREQUENCY:
        if save_config(new_frequency):
            print(f"Frequency set to {new_frequency} Hz and saved to config.")
            return True
        else:
            print("Failed to save configuration.")
            return False
    else:
        print(f"Frequency must be between {MIN_FREQUENCY} and {MAX_FREQUENCY} Hz.")
        return False


def update_beacon(addr_str, rssi, name, timestamp):
    """Update beacon information in storage."""
    entry = discovered_beacons.get(addr_str)

    if entry:
        entry['rssi'] = rssi
        entry['name'] = name
        entry['last_seen'] = timestamp
        entry['scan_count'] = entry.get('scan_count', 0) + 1
        entry['dirty'] = True
    else:
        discovered_beacons[addr_str] = {
            'rssi': rssi,
            'name': name,
            'last_seen': timestamp,
            'scan_count': 1,
            'dirty': True,
        }


def get_scan_period_ms(frequency):
    """Convert frequency (Hz) to period in milliseconds."""
    return int(1000 / frequency)


def decode_name(adv_data):
    # adv_data might be bytes, bytearray, or memoryview
    # convert to bytes for safe slicing and decoding
    data = bytes(adv_data)
    i = 0
    length = len(data)
    while i < length:
        ad_len = data[i]
        if ad_len == 0:
            break
        ad_type = data[i + 1]
        # data payload is from i+2 up to i + ad_len
        if ad_type == _AD_TYPE_SHORT_NAME or ad_type == _AD_TYPE_COMPLETE_NAME:
            name_bytes = data[i + 2 : i + 1 + ad_len]
            try:
                return name_bytes.decode('utf-8')
            except UnicodeError:
                return name_bytes.decode('latin-1', 'ignore')
        i += 1 + ad_len
    return None


def bt_irq(event, data):
    global scan_active
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = ':'.join(['%02X' % b for b in addr])
        name = decode_name(adv_data)
        timestamp = utime.time()

        if name and "beacon" in name.lower():
            update_beacon(addr_str, rssi, name, timestamp)
            # print("Beacon found - Device:", addr_str, "RSSI:", rssi, "Name:", name)

    elif event == _IRQ_SCAN_DONE:
        scan_active = False
        print("Scan done. Total beacons:", len(discovered_beacons))


def scan_loop(frequency, publisher=None):
    global scan_active

    ble.irq(bt_irq) # type: ignore

    scan_period_ms = max(get_scan_period_ms(frequency), 20)
    scan_duration_ms = min(max(scan_period_ms - 10, 20), 5000)

    print(f"Scanning at {frequency} Hz (period: {scan_period_ms}ms, duration: {scan_duration_ms}ms)")

    while True:
        if not scan_active:
            try:
                scan_active = True
                ble.gap_scan(scan_duration_ms, SCAN_WINDOW_US, SCAN_WINDOW_US) # type: ignore
            except Exception as e:
                scan_active = False
                print("Scan start error:", e)
        # Allow short idle to avoid tight loop when scan already running
        utime.sleep_ms(scan_period_ms)
        print_beacon_summary()
        if publisher:
            publisher.publish_pending(discovered_beacons)


def print_beacon_summary():
    """Print summary of discovered beacons."""
    if not discovered_beacons:
        print("No beacons discovered yet.")
        return
    
    print(f"\nDiscovered {len(discovered_beacons)} beacon(s):")
    for addr, info in discovered_beacons.items():
        print(f"  {addr}: {info['name']} (RSSI: {info['rssi']}, Scans: {info['scan_count']})")


def main():
    print("Starting BLE beacon scanner with configurable frequency")

    mqtt_config = load_mqtt_config()
    publisher = None

    if not mqtt_config:
        print("MQTT configuration missing; running scanner offline.")
    else:
        if ensure_wifi_connected(mqtt_config.get("wifi")):
            try:
                publisher = BeaconPublisher(mqtt_config)
                # Attempt an early connection so failures appear before scanning
                publisher.ensure_connected()
            except RuntimeError as exc:
                print("Failed to initialise MQTT publisher:", exc)
                publisher = None
        else:
            print("Wi-Fi credentials invalid or network unreachable; MQTT publishing disabled.")

    frequency = load_config()
    print(f"Loaded scanning frequency: {frequency} Hz")

    scan_loop(frequency, publisher)

if __name__ == "__main__":
    main()
