import time
import bluetooth
from micropython import const

_IRQ_SCAN_RESULT = const(5)  # or const(4) / const( _IRQ_SCAN_RESULT ) depending on version
_IRQ_SCAN_DONE = const(6)

SCAN_WINDOW_US = 30000

_AD_TYPE_SHORT_NAME = const(0x08)
_AD_TYPE_COMPLETE_NAME = const(0x09)

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
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = ':'.join(['%02X' % b for b in addr])
        name = decode_name(adv_data)
        if name:
            if "beacon" in name.lower():
                print("Device:", addr_str, "RSSI:", rssi, "Name:", name)
        #else:
        #    print("Device:", addr_str, "RSSI:", rssi, "Name: <unknown>")
    elif event == _IRQ_SCAN_DONE:
        print("Scan done.\n\n")

def scan_loop():
    ble = bluetooth.BLE()
    ble.active(True)
    ble.irq(bt_irq)
    while True:
        try:
            # 0 for indefinite scanning
            ble.gap_scan(0, SCAN_WINDOW_US, SCAN_WINDOW_US) # same to have 100% duty cycle
        except Exception as e:
            print("Scan start error:", e)
        # Wait until scan completes (add margin)
        time.sleep_ms(SCAN_DURATION_MS + 100)
        # Optional small pause
        # time.sleep_ms(500)

def main():
    print("Starting BLE scan with name parsing")
    scan_loop()

if __name__ == "__main__":
    main()
