import time
import network
import usocket
import json
from bluetooth import BLE

# Настройки WiFi
WIFI_SSID = "POCO X6 Pro 5G"
WIFI_PASSWORD = "render228"
SERVER_IP = "10.237.37.238"
SERVER_PORT = 9999


class ESP32BluetoothScanner:
    def __init__(self):
        self.ble = BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        self.sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)

    def _irq(self, event, data):
        if event == 5:  # _IRQ_SCAN_RESULT
            addr_type, addr, adv_type, rssi, adv_data = data
            name, tx_power = self.parse_adv_data(adv_data)
            if name and tx_power:
                device_info = {"name": name, "rssi": rssi, "tx_power": tx_power}
                message = json.dumps(device_info)
                try:
                    self.sock.sendto(message.encode(), (SERVER_IP, SERVER_PORT))
                except Exception as e:
                    print(f"Failed to send UDP data: {e}")
        elif event == 6:  # _IRQ_SCAN_DONE
            print("Scan complete")

    def parse_adv_data(self, adv_data):
        i = 0
        name = None
        tx_power = None
        while i < len(adv_data):
            field_len = adv_data[i]
            if field_len == 0:
                break
            field_type = adv_data[i + 1]
            if field_type in (0x09, 0x08):
                name = bytes(adv_data[i + 2:i + field_len + 1]).decode()
            elif field_type == 0x0A:
                tx_power = signed_int_from_bytes(adv_data[i + 2:i + field_len + 1])
            i += field_len + 1
        return name, tx_power

    def scan(self):
        self.ble.gap_scan(10000000, 30000, 30000)
        time.sleep(100000)

def signed_int_from_bytes(data, byteorder='little'):
    """Convert bytes to signed integer for MicroPython compatibility"""
    if len(data) == 0:
        return 0
    
    # Convert to unsigned integer first
    result = 0
    if byteorder == 'little':
        for i, byte in enumerate(data):
            result |= byte << (i * 8)
    else:  # big endian
        for byte in data:
            result = (result << 8) | byte
    
    # Convert to signed if needed
    bit_length = len(data) * 8
    if result >= (1 << (bit_length - 1)):
        result -= (1 << bit_length)
    
    return result

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"Подключаемся к {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        for i in range(20):
            if wlan.isconnected():
                break
            print(".", end="")
            time.sleep(1)

    if wlan.isconnected():
        print(f"Connected: {wlan.ifconfig()[0]}")
        return True
    else:
        print("Failed to connect")
        return False


# Основной код
if __name__ == "__main__":
    if connect_wifi():
        scanner = ESP32BluetoothScanner()

        scanner.scan()

