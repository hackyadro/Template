import bluetooth
import time
import json
from micropython import const
from bletools import *
from mynetwork import *
from umqtt.simple import MQTTClient

count: dict[str, int] = {}
resout: dict[str, float] = {}

scan_hz: float = 1
programm_status = 0

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

def mqtt_message_callback(topic: bytes, message: bytes):
        global scan_hz
        global programm_status
        print(f"recieve mqtt msg from {topic}\n{message}")
        try:
            if topic == b"navigation/route/control":
                data = json.loads(message.decode())
                if data["command"] == "start_routing":
                    programm_status = 1
                    scan_hz = float(data["hz"])
                elif data["command"] == "end_routing":
                    programm_status = 0
                else:
                    print(f"Unknown command: {data["command"]}")
                    return
            else:
                print(f"Unknown topic {topic}")
        except Exception as e:
            print(f"Error while mqtt msg handling: {e}")

def main():
    global resout
    global count

    config_data: dict[str, str] = None
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)

    print(f"Connecting to {config_data["wifissid"]}...")
    wifiManager = WiFiManager(config_data["wifissid"], config_data["wifipasswd"])
    if wifiManager.connect():
        print("Wi-Fi connected:", wifiManager.wlan.ifconfig())
    else:
        print("Can't connect to Wi-Fi")
        return

    print("Connecting to MQTT broker...")
    try:
        client = MQTTClient("ESP32_RSSI", config_data["server_ip"], 1883)
        client.connect()
        client.set_callback(mqtt_message_callback)
        client.subscribe("navigation/route/control")
    except Exception as e:
        print(f"Can't connect to MQTT broker: {e}")
        return
    
    print("MQTT broker connected")

    client.wait_msg()

    ble = bluetooth.BLE()
    ble.active(True)
    ble.irq(bt_irq)

    print("Starting BLE scanner...")
    timings = int(100000*(1/scan_hz))
    ble.gap_scan(0, timings, timings)

    try:
        while True:
            time.sleep(0.1)
            if len(resout) >= 4:
                resout = dict(map(lambda x: (x[0], x[1]/count[x[0]]), resout.items()))
                print(resout)
                client.publish(b"ble/beacons/raw", json.dumps(resout).encode())
                resout.clear()
                count.clear()
    except KeyboardInterrupt:
        print("Programm stopped by user")
        ble.gap_scan(None)
    
if __name__ == "__main__":
    main()
