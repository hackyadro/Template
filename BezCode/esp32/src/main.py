import bluetooth
import time
from micropython import const
from bletools import *
from mynetwork import *
from mymqtt import *

resout: dict[str, str] = {}
publisher: Client = None
stop = False

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

_ADV_TYPE_SHORT_NAME = const(0x08)
_ADV_TYPE_COMPLETE_NAME = const(0x09)

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        beacon_addr = bytes(addr).hex()

        decoded_adv_data = decode_fields(adv_data)
        
        device_name = "Unknown"
        if decoded_adv_data.get(_ADV_TYPE_COMPLETE_NAME) != None:
            device_name = decoded_adv_data[_ADV_TYPE_COMPLETE_NAME].decode('ascii')
        elif decoded_adv_data.get(_ADV_TYPE_SHORT_NAME) != None:
            device_name = decoded_adv_data[_ADV_TYPE_SHORT_NAME].decode('ascii')

        if device_name == "Unknown":
            return
        
        resout[device_name] = rssi

    elif event == _IRQ_SCAN_DONE:
        # Автоматически перезапускаем сканирование
        print(resout)
        publisher.send_data("ble/beacons/raw", resout)
        resout.clear()
        if (stop):
            return
        ble.gap_scan(100, 100000, 100000)

        # for datatype, field in decoded_adv_data.items():
        #     print(f"{datatype}: {field}")

        # if (len(resout) >= 8):
            # buf = max(resout.items(), key = lambda x: x[1])[0] + " other: " + ", ".join(map(lambda x: x[0]+":"+str(x[1]), sorted(resout.items(), key = lambda x: x[0])))
            # print(buf)

    
if __name__ == "__main__":
    wifiManager = WiFiManager("wifi-ssid", "wifi-password")
    if wifiManager.connect():
        print("Wi-Fi connected:", wifiManager.wlan.ifconfig())
    else:
        print("Can't connect to Wi-Fi")

    print("Connecting to MQTT broker...")
    publisher = Client("ESP32_RSSI", "192.168.189.78", 1883)
    publisher.subscribe("ble/beacons/raw")
    print("MQTT broker connected")

    ble = bluetooth.BLE()
    ble.active(True)
    ble.irq(bt_irq)

    print("Starting BLE scanner...")
    ble.gap_scan(100, 100000, 100000)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop = True
        print("Scan stopped by user")
        ble.gap_scan(None)
