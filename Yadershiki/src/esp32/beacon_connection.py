import bluetooth
from micropython import const
import time

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE   = const(6)
_ADV_TYPE_NAME = const(0x09)  # Complete Local Name

ble = bluetooth.BLE()
ble.active(True)

# словарь {имя: rssi}
beacons = {}
scan_done = False

def decode_name(adv_data):
    adv_bytes = bytes(adv_data)
    i = 0
    while i + 1 < len(adv_bytes):
        length = adv_bytes[i]
        if length == 0:
            break
        type = adv_bytes[i + 1]
        if type == _ADV_TYPE_NAME:
            return adv_bytes[i + 2 : i + 1 + length].decode("utf-8")
        i += 1 + length
    return None

def bt_irq(event, data):
    global beacons, scan_done
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        name = decode_name(adv_data)
        if name and name.startswith("beacon_"):
            if name not in beacons or rssi > beacons[name]:
                beacons[name] = rssi
    elif event == _IRQ_SCAN_DONE:
        scan_done = True

def scan_once(duration_ms=5000):
    """Запускает сканирование и возвращает список [имя, rssi], отсортированный по близости"""
    global beacons, scan_done
    beacons = {}
    scan_done = False
    ble.irq(bt_irq)
    ble.gap_scan(duration_ms, 30000, 30000)
    
    # ждём окончания
    while not scan_done:
        time.sleep_ms(100)
    
    beacons_sorted = sorted(beacons.items(), key=lambda x: x[1], reverse=True)
    result = [[name, rssi] for name, rssi in beacons_sorted]
    return result
