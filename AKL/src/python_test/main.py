from bluetooth import BLE
import ubinascii
import time

# IRQ константы в MicroPython для BLE (ESP32)
_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6

def decode_name(adv_data: bytes) -> str | None:
    # Разбор TLV формата рекламанных данных (AD structures)
    i = 0
    L = len(adv_data)
    while i + 1 < L:
        length = adv_data[i]
        if length == 0:
            break
        ad_type = adv_data[i + 1]
        # 0x09 = Complete Local Name, 0x08 = Shortened Local Name
        if ad_type == 0x09 or ad_type == 0x08:
            start = i + 2
            end = start + (length - 1)
            try:
                return adv_data[start:end].decode('utf-8', 'ignore')
            except:
                return None
        i += 1 + length
    return None

ble = BLE()

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        # data = (addr_type, addr, adv_type, rssi, adv_data)
        addr_type, addr, adv_type, rssi, adv_data = data
        # addr — bytes like b'\x11\x22\x33\x44\x55\x66'
        mac = ':'.join('{:02x}'.format(b) for b in addr[::-1])  # иногда нужен reverse
        name = decode_name(adv_data) or ''
        adv_hex = ubinascii.hexlify(adv_data).decode()
        print(f"{mac}  RSSI:{rssi}  NAME:'{name}'  ADV:{adv_hex}")
    elif event == _IRQ_SCAN_DONE:
        print("Scan finished")

# Инициализация и запуск
ble.active(True)
ble.irq(bt_irq)

print("Start scanning for 5 seconds...")
ble.gap_scan(5000, 30000, 30000) 
time.sleep(6)
ble.active(False)
print("Done.")
