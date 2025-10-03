import time
import ubluetooth
import network
from micropython import const
from secrets import secrets, mqtt_env, TARGET_BEACONS
from umqtt.simple import MQTTClient
import json
from KalmanFilter import SimpleKalmanRSSI
from machine import Pin

led = Pin(2, Pin.OUT)
# ------------------ connect wifi------------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print("Connecting to WiFi...")
wlan.connect(secrets["ssid"], secrets["password"])
while not wlan.isconnected():
    print(".", end="")
    time.sleep(1)
print("\nConnected!")
print("Network config:", wlan.ifconfig())


# ------------------ MQTT ------------------
CLIENT_ID = "esp32_client"
client = MQTTClient(
    CLIENT_ID,
    mqtt_env["broker"],
    port=mqtt_env["port"],
    user=mqtt_env.get("username"),
    password=mqtt_env.get("password")
)
client.connect()

# ------------------for calculations------------------
def normalize_mac(mac):
    return mac.replace(":", "").lower()

def median(lst):
    n = len(lst)
    if n == 0:
        return None
    s = sorted(lst)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    else:
        return s[mid]

def get_tx_power(adv_data):
    i = 0
    while i < len(adv_data):
        length = adv_data[i]
        if length == 0:
            break
        ad_type = adv_data[i + 1]
        if ad_type == 0x0A:  
            b = adv_data[i + 2]
            tx_power = b - 256 if b > 127 else b
            return tx_power
        i += length + 1
    return None

# ------------------ beacons ------------------
TARGET_MAP = {name: normalize_mac(mac) for name, mac in TARGET_BEACONS.items()}
beacon_data = {}
beacon_filters = {name: SimpleKalmanRSSI() for name in TARGET_BEACONS}
ema_rssi = {name: None for name in TARGET_BEACONS}
EMA_ALPHA = 0.2

REPORT_INTERVAL = 1

# ------------------BLE ------------------
ble = ubluetooth.BLE()
ble.active(True)
print("BLE active:", ble.active())

_IRQ_SCAN_RESULT = const(5)

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        nmac = "".join("{:02x}".format(b) for b in addr)
        for name, mac in TARGET_MAP.items():
            if mac[:-1] == nmac[:-1]:  
                if name not in beacon_data:
                    beacon_data[name] = []
                tx_power = get_tx_power(adv_data)
                filtered_rssi = beacon_filters[name].update(rssi)
                beacon_data[name].append((filtered_rssi, tx_power))

ble.irq(bt_irq)
ble.gap_scan(0, 30000, 30000, True)  # активный скан

# ------------------ Основной цикл ------------------
try:
    last_report = time.time()
    while True:
        now = time.time()
        if now - last_report >= REPORT_INTERVAL:
            print("---- RSSI Report ----")
            for name, samples in beacon_data.items():
                if samples:
                    rssi_values = [r for r, _ in samples]
                    tx_power = samples[0][1]
                    med_rssi = median(rssi_values)
                    # EMA после медианы
                    if ema_rssi[name] is None:
                        ema_rssi[name] = med_rssi
                    else:
                        ema_rssi[name] = EMA_ALPHA * med_rssi + (1 - EMA_ALPHA) * ema_rssi[name]

        

                    payload = json.dumps({
                        "beacon_name": name,
                        "avg_rssi": round(ema_rssi[name], 2),
                        "tx_power": int(tx_power)
                    })
                    client.publish(mqtt_env["topic"], payload)
                    print("Sent:", payload)
                    
                    led.on()
                    time.sleep(0.1)
                    led.off()
                else:
                    print(f"{name}: no data")
            print("---------------------\n")
            beacon_data.clear()
            last_report = now

except KeyboardInterrupt:
    ble.gap_scan(None)
    ble.active(False)
    print("BLE stopped by user")

except Exception as e:
    print("Scan failed:", e)
    ble.gap_scan(None)
    ble.active(False)
