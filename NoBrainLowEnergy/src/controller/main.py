import time
import bluetooth
import json
from micropython import const

_IRQ_SCAN_RESULT = const(5)  # or const(4) / const( _IRQ_SCAN_RESULT ) depending on version
_IRQ_SCAN_DONE = const(6)

SCAN_WINDOW_US = 30000
CONFIG_FILE = "scan_config.json"
DEFAULT_FREQUENCY = 1.0  # Hz (1 scan per second)
MIN_FREQUENCY = 0.1  # Hz
MAX_FREQUENCY = 10.0  # Hz

_AD_TYPE_SHORT_NAME = const(0x08)
_AD_TYPE_COMPLETE_NAME = const(0x09)

# Global storage for discovered beacons
discovered_beacons = {}

scan_active = False

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
    discovered_beacons[addr_str] = {
        'rssi': rssi,
        'name': name,
        'last_seen': timestamp,
        'scan_count': discovered_beacons.get(addr_str, {}).get('scan_count', 0) + 1
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
        timestamp = time.time()
        
        if name and "beacon" in name.lower():
                update_beacon(addr_str, rssi, name, timestamp)
                # print("Beacon found - Device:", addr_str, "RSSI:", rssi, "Name:", name)

    elif event == _IRQ_SCAN_DONE:
        scan_active = False
        print("Scan done. Total beacons:", len(discovered_beacons))


def scan_loop(frequency):
    global scan_active
    ble.irq(bt_irq)
    
    scan_period_ms = get_scan_period_ms(frequency)
    scan_duration_ms = min(scan_period_ms - 10, 5000)  # Leave 10ms margin, max 5s scan
    
    print(f"Scanning at {frequency} Hz (period: {scan_period_ms}ms, duration: {scan_duration_ms}ms)")
    
    while True:
        if not scan_active:
            try:
                scan_active = True
                # Start scanning for the calculated duration
                ble.gap_scan(scan_duration_ms, SCAN_WINDOW_US, SCAN_WINDOW_US)
            except Exception as e:
                scan_active = False
                print("Scan start error:", e)
        else:
            pass

        # Wait for the remainder of the period
        time.sleep_ms(scan_period_ms)
        print_beacon_summary()


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
    
    # Load configuration
    frequency = load_config()
    print(f"Loaded scanning frequency: {frequency} Hz")
    
    # Start scanning
    scan_loop(frequency)

if __name__ == "__main__":
    main()
