import utime  # type: ignore
import network  # type: ignore
import ubinascii  # type: ignore
import machine  # type: ignore
import bluetooth # type: ignore
from micropython import const  # type: ignore

try:
    import ujson as json  # type: ignore
except ImportError:  # pragma: no cover - fallback for standard json
    import json  # type: ignore

from umqtt.simple import MQTTClient  # type: ignore

ble = None

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

# noise mitigation defaults
DEFAULT_RSSI_CUTOFF = -85
MIN_RSSI_CUTOFF = -100
MAX_RSSI_CUTOFF = -40

DEFAULT_AGGREGATION_WINDOW_MS = 1000
MIN_AGGREGATION_WINDOW_MS = 100
MAX_AGGREGATION_WINDOW_MS = 10000

MEDIAN_OUTLIER_THRESHOLD_DB = 15

# Global storage for discovered beacons
discovered_beacons = {}

scan_active = False
aggregator = None  # type: ignore
current_scan_cycle = 0
previous_scan_cycle = -1


def advance_scan_cycle():
    """Advance the global scan cycle counter and notify the aggregator."""
    global current_scan_cycle, previous_scan_cycle, aggregator  # type: ignore
    previous_scan_cycle = current_scan_cycle
    current_scan_cycle = (current_scan_cycle + 1) & 0x7FFFFFFF
    if aggregator and hasattr(aggregator, "begin_cycle"):
        try:
            aggregator.begin_cycle(current_scan_cycle, previous_scan_cycle)
        except Exception:
            pass

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
        except Exception as exc:
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

        payload_beacons = []
        seen_addresses = set()
        global current_scan_cycle, previous_scan_cycle  # use latest cycle values

        for cycle_id in (current_scan_cycle, previous_scan_cycle):
            if cycle_id is None or cycle_id < 0:
                continue
            for addr, info in beacons.items():
                if addr in seen_addresses:
                    continue
                if info.get("last_cycle_seen") != cycle_id:
                    continue

                raw_count = info.get("raw_sample_count")
                filtered_count = info.get("samples_in_window")
                outlier_count = None
                if raw_count is not None and filtered_count is not None:
                    try:
                        outlier_count = max(0, int(raw_count) - int(filtered_count))
                    except (TypeError, ValueError):
                        outlier_count = None

                payload_beacons.append(
                    {
                        "address": addr,
                        "name": info.get("name"),
                        "rssi": info.get("rssi"),
                        "median_rssi": info.get("median_rssi"),
                        "min_rssi": info.get("min_rssi"),
                        "max_rssi": info.get("max_rssi"),
                        "samples_in_window": info.get("samples_in_window"),
                        "raw_sample_count": info.get("raw_sample_count"),
                        "outlier_samples": outlier_count,
                        "aggregation_window_ms": info.get("aggregation_window_ms"),
                        "rssi_cutoff": info.get("rssi_cutoff", DEFAULT_RSSI_CUTOFF),
                        "last_seen": info.get("last_seen"),
                        "scan_count": info.get("scan_count"),
                    }
                )
                seen_addresses.add(addr)

        if not payload_beacons:
            self._maybe_ping()
            return

        active_window = payload_beacons[0].get("aggregation_window_ms")
        active_cutoff = payload_beacons[0].get("rssi_cutoff", DEFAULT_RSSI_CUTOFF)
        active_threshold = MEDIAN_OUTLIER_THRESHOLD_DB
        try:
            if aggregator:
                active_window = aggregator.window_ms
                active_cutoff = aggregator.rssi_cutoff
                active_threshold = aggregator.median_threshold_db
        except NameError:
            pass

        envelope = {
            "device_id": self._device_id,
            "timestamp": utime.time(),
            "count": len(payload_beacons),
            "aggregation_window_ms": active_window,
            "rssi_cutoff": active_cutoff,
            "median_filter_threshold_db": active_threshold,
            "beacons": payload_beacons,
        }

        try:
            payload = json.dumps(envelope)
        except Exception as exc:
            print("Failed to encode aggregated payload:", exc)
            return

        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        try:
            client.publish(self.topic_bytes, payload)
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


class BeaconWindowAggregator:
    def __init__(self, window_ms=DEFAULT_AGGREGATION_WINDOW_MS, rssi_cutoff=DEFAULT_RSSI_CUTOFF):
        self._outlier_threshold_db = MEDIAN_OUTLIER_THRESHOLD_DB
        self._current_cycle_id = 0
        self._previous_cycle_id = -1
        self.configure(window_ms, rssi_cutoff)

    def configure(self, window_ms, rssi_cutoff):
        self._window_ms = self._clamp_window(window_ms)
        self._rssi_cutoff = self._clamp_cutoff(rssi_cutoff)
        self._synchronise_existing_entries()

    def begin_cycle(self, cycle_id, previous_cycle_id=None):
        if previous_cycle_id is None:
            previous_cycle_id = self._current_cycle_id
        self._previous_cycle_id = previous_cycle_id
        self._current_cycle_id = cycle_id

    @staticmethod
    def _clamp_window(window_ms):
        if window_ms is None:
            return DEFAULT_AGGREGATION_WINDOW_MS
        try:
            window_int = int(window_ms)
        except (TypeError, ValueError):
            window_int = DEFAULT_AGGREGATION_WINDOW_MS
        return max(MIN_AGGREGATION_WINDOW_MS, min(window_int, MAX_AGGREGATION_WINDOW_MS))

    @staticmethod
    def _clamp_cutoff(rssi_cutoff):
        if rssi_cutoff is None:
            return DEFAULT_RSSI_CUTOFF
        try:
            cutoff_int = int(rssi_cutoff)
        except (TypeError, ValueError):
            cutoff_int = DEFAULT_RSSI_CUTOFF
        return max(MIN_RSSI_CUTOFF, min(cutoff_int, MAX_RSSI_CUTOFF))

    def process(self, addr, rssi, name, timestamp_s):
        if not self._passes_filters(addr, rssi):
            return

        entry = discovered_beacons.get(addr)
        if not entry:
            entry = {
                "name": name or "unknown",
                "scan_count": 1,
                "last_seen": timestamp_s,
                "rssi_buffer": [],
                "last_cycle_seen": self._current_cycle_id,
            }
            discovered_beacons[addr] = entry
        else:
            entry["scan_count"] = entry.get("scan_count", 0) + 1
            if name and name != entry.get("name"):
                entry["name"] = name
            entry["last_cycle_seen"] = self._current_cycle_id

        now_ms = utime.ticks_ms()
        buffer = entry.setdefault("rssi_buffer", [])
        buffer.append({"timestamp_ms": now_ms, "rssi": rssi})
        self._prune_buffer(buffer, now_ms)

        if not self._apply_additional_filters(addr, buffer):
            return

        rssi_values = [sample["rssi"] for sample in buffer]
        rssi, filtered_values, median_rssi = self._denoise(rssi_values)
        if rssi is None:
            return

        entry.update({
            "rssi": float(rssi),
            "median_rssi": float(median_rssi) if median_rssi is not None else None,
            "min_rssi": float(min(filtered_values)),
            "max_rssi": float(max(filtered_values)),
            "samples_in_window": len(filtered_values),
            "raw_sample_count": len(rssi_values),
            "aggregation_window_ms": self._window_ms,
            "last_seen": timestamp_s,
            "rssi_cutoff": self._rssi_cutoff,
            "last_cycle_seen": self._current_cycle_id,
        })

    def _passes_filters(self, addr, rssi):  # pylint: disable=unused-argument
        return rssi >= self._rssi_cutoff

    def _apply_additional_filters(self, addr, buffer):  # pylint: disable=unused-argument
        # Placeholder for future noise filters (e.g., Kalman, Hampel). Currently a no-op.
        return True

    def _prune_buffer(self, buffer, now_ms):
        while buffer and utime.ticks_diff(now_ms, buffer[0]["timestamp_ms"]) > self._window_ms:
            buffer.pop(0)

    @property
    def window_ms(self):
        return self._window_ms

    @property
    def rssi_cutoff(self):
        return self._rssi_cutoff

    @property
    def median_threshold_db(self):
        return self._outlier_threshold_db

    def _median(self, values):
        if not values:
            return None
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2:
            return float(sorted_vals[mid])
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    def _denoise(self, values):
        if not values:
            return None, [], None

        median_value = self._median(values)
        if median_value is None:
            return None, [], None

        filtered = [v for v in values if abs(v - median_value) <= self._outlier_threshold_db]
        if not filtered:
            filtered = [median_value]

        denoised = sum(filtered) / len(filtered)
        return float(denoised), filtered, float(median_value)

    def _synchronise_existing_entries(self):
        if not discovered_beacons:
            return

        now_ms = utime.ticks_ms()
        current_time = utime.time()

        for addr in list(discovered_beacons.keys()):
            entry = discovered_beacons.get(addr)
            if not entry:
                continue

            buffer = entry.get("rssi_buffer") or []
            self._prune_buffer(buffer, now_ms)
            buffer[:] = [sample for sample in buffer if sample.get("rssi", 0) >= self._rssi_cutoff]

            if not buffer:
                discovered_beacons.pop(addr, None)
                continue

            rssi_values = [sample["rssi"] for sample in buffer]
            rssi, filtered_values, median_rssi = self._denoise(rssi_values)
            if rssi is None:
                discovered_beacons.pop(addr, None)
                continue

            entry.setdefault("last_cycle_seen", self._current_cycle_id)
            entry.update({
                "rssi": float(rssi),
                "median_rssi": float(median_rssi) if median_rssi is not None else None,
                "min_rssi": float(min(filtered_values)),
                "max_rssi": float(max(filtered_values)),
                "samples_in_window": len(filtered_values),
                "raw_sample_count": len(rssi_values),
                "aggregation_window_ms": self._window_ms,
                "rssi_cutoff": self._rssi_cutoff,
                "last_seen": entry.get("last_seen", current_time),
                "last_cycle_seen": entry.get("last_cycle_seen", self._current_cycle_id),
            })


def load_config():
    """Load scanning and aggregation settings from file with sane defaults."""
    raw = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                raw = loaded
    except (OSError, ValueError):
        pass

    frequency = raw.get('scan_frequency', DEFAULT_FREQUENCY)
    if frequency < MIN_FREQUENCY:
        frequency = MIN_FREQUENCY
    elif frequency > MAX_FREQUENCY:
        frequency = MAX_FREQUENCY

    cutoff = raw.get('rssi_cutoff', DEFAULT_RSSI_CUTOFF)
    cutoff = BeaconWindowAggregator._clamp_cutoff(cutoff)

    window_ms = raw.get('aggregation_window_ms', DEFAULT_AGGREGATION_WINDOW_MS)
    window_ms = BeaconWindowAggregator._clamp_window(window_ms)

    return {
        'scan_frequency': frequency,
        'rssi_cutoff': cutoff,
        'aggregation_window_ms': window_ms,
    }


def save_config(config):
    """Persist scanning and aggregation settings to file."""
    payload = {
        'scan_frequency': config.get('scan_frequency', DEFAULT_FREQUENCY),
        'rssi_cutoff': config.get('rssi_cutoff', DEFAULT_RSSI_CUTOFF),
        'aggregation_window_ms': config.get('aggregation_window_ms', DEFAULT_AGGREGATION_WINDOW_MS),
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(payload, f)
        return True
    except OSError:
        return False


def set_frequency(new_frequency):
    """Set new scanning frequency and save to config."""
    if MIN_FREQUENCY <= new_frequency <= MAX_FREQUENCY:
        config = load_config()
        config['scan_frequency'] = new_frequency
        if save_config(config):
            print(f"Frequency set to {new_frequency} Hz and saved to config.")
            return True
        else:
            print("Failed to save configuration.")
            return False
    else:
        print(f"Frequency must be between {MIN_FREQUENCY} and {MAX_FREQUENCY} Hz.")
        return False


def set_rssi_cutoff(new_cutoff):
    """Update RSSI cutoff and reconfigure aggregator if active."""
    cutoff = BeaconWindowAggregator._clamp_cutoff(new_cutoff)
    config = load_config()
    config['rssi_cutoff'] = cutoff
    if save_config(config):
        if aggregator:
            aggregator.configure(config['aggregation_window_ms'], cutoff)
        print(f"RSSI cutoff set to {cutoff} dBm and saved to config.")
        return True
    print("Failed to save RSSI cutoff configuration.")
    return False


def set_aggregation_window(new_window_ms):
    """Update aggregation window length (ms) and reconfigure aggregator if active."""
    window_ms = BeaconWindowAggregator._clamp_window(new_window_ms)
    config = load_config()
    config['aggregation_window_ms'] = window_ms
    if save_config(config):
        if aggregator:
            aggregator.configure(window_ms, config['rssi_cutoff'])
        print(f"Aggregation window set to {window_ms} ms and saved to config.")
        return True
    print("Failed to save aggregation window configuration.")
    return False


def update_beacon(addr_str, rssi, name, timestamp):
    """Update beacon information in storage."""
    global aggregator  # type: ignore
    if aggregator:
        aggregator.process(addr_str, rssi, name, timestamp)
        return

    entry = discovered_beacons.get(addr_str)

    if entry:
        entry['rssi'] = float(rssi)
        entry['median_rssi'] = float(rssi)
        entry['min_rssi'] = float(min(rssi, entry.get('min_rssi', rssi)))
        entry['max_rssi'] = float(max(rssi, entry.get('max_rssi', rssi)))
        entry['samples_in_window'] = entry.get('samples_in_window', 1) + 1
        entry['raw_sample_count'] = entry.get('raw_sample_count', 0) + 1
        entry['aggregation_window_ms'] = entry.get('aggregation_window_ms', DEFAULT_AGGREGATION_WINDOW_MS)
        entry['rssi_cutoff'] = entry.get('rssi_cutoff', DEFAULT_RSSI_CUTOFF)
        entry['name'] = name
        entry['last_seen'] = timestamp
        entry['scan_count'] = entry.get('scan_count', 0) + 1
        entry['last_cycle_seen'] = current_scan_cycle
    else:
        discovered_beacons[addr_str] = {
            'rssi': float(rssi),
            'median_rssi': float(rssi),
            'min_rssi': float(rssi),
            'max_rssi': float(rssi),
            'samples_in_window': 1,
            'raw_sample_count': 1,
            'aggregation_window_ms': DEFAULT_AGGREGATION_WINDOW_MS,
            'rssi_cutoff': DEFAULT_RSSI_CUTOFF,
            'name': name,
            'last_seen': timestamp,
            'scan_count': 1,
            'last_cycle_seen': current_scan_cycle,
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
    global ble
    
    ble.irq(bt_irq) # type: ignore

    scan_period_ms = max(get_scan_period_ms(frequency), 20)
    scan_duration_ms = min(max(scan_period_ms - 10, 20), 5000)

    print(f"Scanning at {frequency} Hz (period: {scan_period_ms}ms, duration: {scan_duration_ms}ms)")

    while True:
        if not scan_active:
            advance_scan_cycle()
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
    active_entries = []
    seen_addresses = set()
    for cycle_id in (current_scan_cycle, previous_scan_cycle):
        if cycle_id is None or cycle_id < 0:
            continue
        for addr, info in discovered_beacons.items():
            if addr in seen_addresses:
                continue
            if info.get('last_cycle_seen') != cycle_id:
                continue
            active_entries.append((addr, info))
            seen_addresses.add(addr)

    if not active_entries:
        print("No beacons discovered yet.")
        return
    
    print(f"\nDiscovered {len(active_entries)} beacon(s) in the last 2 cycles:")
    for addr, info in active_entries:
        name = info.get('name') or 'unknown'
        rssi = info.get('rssi')
        median_rssi = info.get('median_rssi')
        samples = info.get('samples_in_window') or info.get('scan_count')
        raw_samples = info.get('raw_sample_count') or samples
        outliers = None
        if raw_samples is not None and samples is not None:
            try:
                outliers = max(0, int(raw_samples) - int(samples))
            except (TypeError, ValueError):
                outliers = None
        if rssi is not None:
            median_part = f", median: {median_rssi:.1f}" if median_rssi is not None else ""
            outlier_part = f", outliers removed: {outliers}" if outliers is not None and outliers > 0 else ""
            print(
                f"  {name}: (denoised RSSI: {rssi:.1f}{median_part}, "
                f"samples: {samples}{outlier_part})"
            )
        else:
            latest_rssi = info.get('rssi')
            print(f"  {addr}: {name} (RSSI: {latest_rssi}, Scans: {info.get('scan_count')})")


def main():
    print("Starting BLE beacon scanner with configurable frequency")
    global ble
    ble = bluetooth.BLE()
    ble.active(True)
    print("BLE active:", ble.active())

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

    settings = load_config()
    frequency = settings['scan_frequency']

    global aggregator  # type: ignore
    aggregator = BeaconWindowAggregator(
        window_ms=settings['aggregation_window_ms'],
        rssi_cutoff=settings['rssi_cutoff'],
    )

    print(f"Loaded scanning frequency: {frequency} Hz")
    print(
        "Noise filter settings -> RSSI cutoff: {} dBm, aggregation window: {} ms".format(
            settings['rssi_cutoff'], settings['aggregation_window_ms']
        )
    )

    scan_loop(frequency, publisher)

if __name__ == "__main__":
    main()
