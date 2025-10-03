import network
import time
import json
import machine
import bluetooth
from machine import unique_id
try:
    from umqtt.robust import MQTTClient
except ImportError:
    from umqtt.simple import MQTTClient


# НАСТРОЙКИ

WIFI_SSID = "naut_2"
WIFI_PASS = "FFFFFFFF"

BROKER = "10.175.95.190"
PORT = 1883
MQTT_USER = "42"
MQTT_PASS = "123123"

# ---------------------------------------------------


DEVICE_ID = "esp32-" + "".join("{:02x}".format(b) for b in unique_id())
TOPIC_DATA = b"devices/esp32/telemetry"
TOPIC_STATUS = b"devices/esp32/status"

BEACON_PREFIX = "beacon_"
SCAN_DURATION_S = 2

SEQ = 0


def wifi_connect():
    sta = network.WLAN(network.STA_IF)

    if not sta.active():
        sta.active(True)

    if not sta.isconnected():
        print("Connecting to WiFi...")

        sta.connect(WIFI_SSID, WIFI_PASS)
        t0 = time.ticks_ms()

        while not sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 15000:
                raise RuntimeError("WiFi connect timeout")
            time.sleep_ms(200)

    print("WiFi:", sta.ifconfig())
    return sta


def mqtt_connect():
    client = MQTTClient(
        client_id=DEVICE_ID,
        server=BROKER,
        port=PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        keepalive=30
    )

    try:
        client.set_last_will(TOPIC_STATUS, b"offline", retain=False, qos=1)
    except TypeError:
        client.set_last_will(TOPIC_STATUS, b"offline", retain=False)

    client.connect()
    client.publish(TOPIC_STATUS, b"online", retain=False)

    print("Connected to MQTT broker:", BROKER)
    return client


def scan_beacons(ble):
    found = {}

    def ble_irq(event, data):
        if event == 5:  # _IRQ_SCAN_RESULT
            addr, rssi, payload = bytes(data[1]), data[3], data[4]
            n, name = 0, None

            while n + 1 < len(payload):
                field_len = payload[n]

                if field_len == 0:
                    break
                if payload[n + 1] == 0x09:
                    try:
                        name = bytes(payload[n+2:n+field_len+1]).decode("utf-8")
                    except:
                        pass
                    break
                n += field_len + 1

            if name and name.startswith(BEACON_PREFIX):
                found[addr] = (name, rssi)

    ble.irq(ble_irq)
    ble.gap_scan(SCAN_DURATION_S * 100, 30000, 30000)
    time.sleep(SCAN_DURATION_S / 10)
    ble.gap_scan(None)  # остановить скан

    return [{"name": n, "rssi": r} for n, r in found.values()]


def main():
    sta = wifi_connect()
    client = mqtt_connect()
    ble = bluetooth.BLE()
    ble.active(True)

    global SEQ
    while True:
        try:
            if not sta.isconnected():
                print("Wi-Fi lost, reboot...")
                time.sleep(5)
                machine.reset()

            SEQ += 1
            beacons = scan_beacons(ble)
            data = {
                "device_id": DEVICE_ID,
                "seq": SEQ,
                "ip": sta.ifconfig()[0],
                "uptime_s": time.ticks_ms() // 1000,
                "beacons": beacons
            }
            payload = json.dumps(data)
            client.publish(TOPIC_DATA, payload)

            print("Published:", payload)
            time.sleep(0.05)  # задержка перед новым сканом
        except Exception as e:
            print("Error:", e)

            try:
                client.disconnect()
            except:
                pass

            client = None
            time.sleep(5)
            client = mqtt_connect()

main()