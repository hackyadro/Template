import ubinascii, time
from adv_parser import BeaconParser

try:
    import bluetooth
    BLE = bluetooth.BLE()
    IRQ_SCAN_RESULT, IRQ_SCAN_DONE = 5, 6
except ImportError:
    from ubluetooth import BLE as BLE
    BLE = BLE()
    IRQ_SCAN_RESULT, IRQ_SCAN_DONE = 1, 2

class BLEScanner:
    def __init__(self):
        self.ble = BLE
        self.results = []
        self.scan_in_progress = False
        self.ble.irq(self._irq)

    def _irq(self, event, data):
        if event == IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            addr_hex = ubinascii.hexlify(addr).decode().upper()
            addr_fmt = ':'.join([addr_hex[i:i+2] for i in range(0, len(addr_hex), 2)])
            self.results.append((addr_fmt, rssi, bytes(adv_data)))
        elif event == IRQ_SCAN_DONE:
            self.scan_in_progress = False

    def scan(self, duration_ms):
        self.results.clear()
        self.scan_in_progress = True
        self.ble.gap_scan(duration_ms, 30000, 30000)

        start = time.ticks_ms()
        while self.scan_in_progress:
            if time.ticks_diff(time.ticks_ms(), start) > duration_ms + 3000:
                self.ble.gap_scan(None)
                self.scan_in_progress = False
                break
            time.sleep_ms(100)

        return self.results
