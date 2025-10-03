import time
import bluetooth
import ubinascii
from micropython import const

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)


class BLEDeviceTracker:
    def __init__(self, scan_duration):
        self.bt = bluetooth.BLE()
        self.bt.active(True)
        self.bt.irq(self.bt_irq)

        self.scan_duration = scan_duration
        self.devices = {}

        self.scanning = False

    def decode_name(self, adv_data):
        i = 0
        name = None

        while i < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            if i + length >= len(adv_data):
                break
            ad_type = adv_data[i + 1]

            if ad_type == 0x08 or ad_type == 0x09:
                start = i + 2
                end = start + length - 1
                try:
                    name = bytes(adv_data[start:end]).decode('utf-8')
                except Exception:
                    name = None
                break
            i += length + 1
        return name

    def bt_irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            mac = ubinascii.hexlify(addr, ':').decode().upper()
            name = self.decode_name(adv_data)
            if name is None:
                return
            else:
                self.devices[mac] = {
                    'name': name,
                    'rssi': rssi
                }
        elif event == _IRQ_SCAN_DONE:
            self.scanning = False

    def start_scan(self):
        self.devices.clear()
        self.scanning = True
        self.bt.gap_scan(self.scan_duration, 0, 0, True)

    def print_devices(self):
        now = time.time()
        for mac, dev in self.devices.items():
            if(dev['name'] != 'Unknown'):
                print(f"\"{dev['name']}\" {-dev['rssi']}")
        print("")

    def run(self):
        while True:
            self.start_scan()
            while self.scanning:
                time.sleep_ms(100)
            self.print_devices()

def read_params():
    try:
        with open('params.txt', 'r') as f:
            val = f.read().strip()
            return int(val)
    except Exception:
        return 1000

if __name__ == '__main__':
    scan_duration = read_params()

    tracker = BLEDeviceTracker(scan_duration=scan_duration)
    tracker.run()
