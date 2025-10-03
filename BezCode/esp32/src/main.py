import bluetooth
import time
from micropython import const
from bletools import *
from mynetwork import *
from mymqtt import *

count: dict[str, int] = {}
resout: dict[str, str] = {}
publisher: Client = None
stop = False

_IRQ_SCAN_RESULT = const(5)

_ADV_TYPE_SHORT_NAME = const(0x08)
_ADV_TYPE_COMPLETE_NAME = const(0x09)

def bt_irq(event, data):
    global count
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        beacon_addr = bytes(addr).hex()

        decoded_adv_data = decode_fields(adv_data)
        
        device_name = "Unknown"
        if decoded_adv_data.get(_ADV_TYPE_COMPLETE_NAME) != None:
            device_name = decoded_adv_data[_ADV_TYPE_COMPLETE_NAME].decode('ascii')
        elif decoded_adv_data.get(_ADV_TYPE_SHORT_NAME) != None:
            device_name = decoded_adv_data[_ADV_TYPE_SHORT_NAME].decode('ascii')

        if device_name == "Unknown" or "beacon" not in device_name:
            return
        
        if (resout.get(device_name) == None):
            resout[device_name] = rssi
            count[device_name] = 1
        else:
            resout[device_name] += rssi
            count[device_name] += 1

    
if __name__ == "__main__":
    wifissid = "vivo X200 Pro"
    password = "Oberon123"
    print(f"Connecting to {wifissid}...")
    wifiManager = WiFiManager(wifissid, password)
    if wifiManager.connect():
        print("Wi-Fi connected:", wifiManager.wlan.ifconfig())
    else:
        print("Can't connect to Wi-Fi")
        exit(1)

    print("Connecting to MQTT broker...")
    try:
        publisher = Client("ESP32_RSSI", "192.168.186.78", 1883)
    except:
        print("Can't connect to MQTT broker")
        exit(1)
    print("MQTT broker connected")

    ble = bluetooth.BLE()
    ble.active(True)
    ble.irq(bt_irq)

    print("Starting BLE scanner...")
    ble.gap_scan(0, 100000, 100000)

    try:
        while True:
            time.sleep(0.1)
            if len(resout) >= 4 and sum(count.values()) >= 15:
                resout = dict(map(lambda x: (x[0], x[1]/count[x[0]]), resout.items()))
                print(resout)
                publisher.send_data("ble/beacons/raw", resout)
                resout.clear()
                count.clear()
    except KeyboardInterrupt:
        print("Scan stopped by user")
        ble.gap_scan(None)
