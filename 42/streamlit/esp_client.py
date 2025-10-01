from micropython import const
import bluetooth, network, ujson, time
import urequests as requests

WIFI_SSID = "YOUR_SSID"
WIFI_PWD  = "YOUR_PASS"
SERVER_URL = "http://192.168.1.100:8000/rssi"  # ваш сервер

# карта MAC -> логическое имя из standart.beacons
TARGETS = {
    "a4:c1:38:xx:xx:01": "beacon_1",
    "a4:c1:38:xx:xx:02": "beacon_2",
    # ...
}

_IRQ_SCAN_RESULT   = const(5)
_IRQ_SCAN_COMPLETE = const(6)

# ---- Wi-Fi ----
w = network.WLAN(network.STA_IF); w.active(True); w.connect(WIFI_SSID, WIFI_PWD)
t0 = time.ticks_ms()
while not w.isconnected():
    if time.ticks_diff(time.ticks_ms(), t0) > 15000:
        raise RuntimeError("Wi-Fi timeout")
    time.sleep_ms(200)

# ---- BLE ----
ble = bluetooth.BLE(); ble.active(True)

# аккумулируем RSSI по окну
rssi_sum = {}  # mac -> (sum, count)

def on_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        mac = ":".join(["%02x" % b for b in bytes(addr)])
        if mac in TARGETS:
            s, c = rssi_sum.get(mac, (0, 0))
            rssi_sum[mac] = (s + rssi, c + 1)

ble.irq(on_irq)

WINDOW_MS = 500  # окно усреднения RSSI
PERIOD_MS = 500  # период отправки (2 Гц; можно 100..10000)
while True:
    # одно окно сканирования
    rssi_sum.clear()
    ble.gap_scan(WINDOW_MS, 30000, 30000, True)  # active scan
    time.sleep_ms(WINDOW_MS + 50)  # ждём завершения

    # готовим усреднённые RSSI
    readings = []
    for mac, (s, c) in rssi_sum.items():
        name = TARGETS[mac]
        avg = s / c
        readings.append({"name": name, "rssi": avg})

    # отправляем на сервер
    try:
        payload = {"ts": time.ticks_ms(), "readings": readings}
        requests.post(SERVER_URL, json=payload, timeout=5)
    except Exception as e:
        # сеть могла отвалиться — просто попробуем снова в следующий период
        pass

    time.sleep_ms(PERIOD_MS)
