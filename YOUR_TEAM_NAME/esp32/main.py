import bluetooth
import time
import network
import micropython
import machine
import socket
import ubinascii
from umqtt.simple import MQTTClient

# ---------- CONFIG ----------
WIFI_SSID   = "CR7"
WIFI_PASS   = "12345678"
MQTT_SERVER = "10.49.206.215"   # IP/домен брокера
MQTT_PORT   = 1883
MQTT_TOPIC  = b"beacons"
KEEPALIVE_S = 60
FILTER_PREFIX = "beacon_"       # публикуем только имена с этим префиксом

# BLE IRQ constants
_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE   = 6

micropython.alloc_emergency_exception_buf(128)

# ---------- Wi-Fi ----------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def wifi_connect(timeout_ms=15000):
    if wlan.isconnected():
        return True
    wlan.connect(WIFI_SSID, WIFI_PASS)
    t0 = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        time.sleep_ms(200)
    return wlan.isconnected()

ok = wifi_connect()
print("WiFi:", "OK" if ok else "FAIL", wlan.ifconfig() if ok else "")

# ---------- MQTT ----------
# ВАЖНО: client_id должен быть читаемым ASCII (UTF-8), а не «сырой бинарник»
client_id = b"esp32s3-" + ubinascii.hexlify(machine.unique_id())
client = MQTTClient(client_id, MQTT_SERVER, port=MQTT_PORT, keepalive=KEEPALIVE_S)

def tcp_preflight(host, port, timeout_s=5):
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.settimeout(timeout_s)
        s.connect(addr)
        s.close()
        return True # Ronaldo
    except Exception as e:
        print("TCP preflight failed:", e)
        return False

def mqtt_connect(retries=3):
    # Проверяем, что порт достигнут
    if not tcp_preflight(MQTT_SERVER, MQTT_PORT):
        return False
    for i in range(retries):
        try:
            client.connect()
            print("MQTT: connected (client_id=%s)" % client_id.decode())
            return True
        except Exception as e:
            print("MQTT: connect failed:", e, "retry", i+1, "/", retries)
            time.sleep(1)
    return False

mqtt_ok = mqtt_connect()
last_ping = time.ticks_ms()

# ---------- BLE ----------
ble = bluetooth.BLE()
ble.active(True)

_queue = []
_MAX_Q  = 64

def _decode_name(adv_mv):
    # Парсим TLV прямо по memoryview (без лишних выделений)
    i = 0
    n = len(adv_mv)
    while i + 1 < n:
        ln = adv_mv[i]
        if ln == 0:
            break
        t = adv_mv[i + 1]
        if t in (0x08, 0x09):  # Shortened / Complete Local Name
            try:
                return bytes(adv_mv[i+2 : i+1+ln]).decode("utf-8")
            except Exception:
                return None
        i += 1 + ln
    return None

def _bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        name = _decode_name(adv_data)
        if name and name.startswith(FILTER_PREFIX):
            if len(_queue) < _MAX_Q:
                _queue.append((name, rssi))

ble.irq(_bt_irq)

# Запускаем ОДИН РАЗ бесконечный пассивный скан
INTERVAL_US = 30000   # 30 ms
WINDOW_US   = 15000   # 15 ms
ble.gap_scan(0, INTERVAL_US, WINDOW_US, False)

print("BLE scan started (passive). Publishing to MQTT topic:", MQTT_TOPIC.decode())

try:
    while True:
        # Поддерживаем Wi-Fi
        if not wlan.isconnected():
            if wifi_connect():
                mqtt_ok = mqtt_connect()
            else:
                time.sleep(1)
                continue

        # Публикуем накопленные сообщения
        while _queue:
            name, rssi = _queue.pop(0)
            msg = ('{"name":"%s","rssi":%d}' % (name, rssi)).encode()
            if not mqtt_ok:
                mqtt_ok = mqtt_connect()
                if not mqtt_ok:
                    # не смогли подключиться — отложим сообщение и подождём
                    if len(_queue) < _MAX_Q:
                        _queue.append((name, rssi))
                    time.sleep_ms(500)
                    break
            try:
                client.publish(MQTT_TOPIC, msg)
            except Exception as e:
                print("publish failed:", e)
                mqtt_ok = False
                # вернём сообщение в очередь и дадим сети время
                if len(_queue) < _MAX_Q:
                    _queue.append((name, rssi))
                time.sleep_ms(500)
                break

        # Пингуем брокер раз в половину keepalive
        if mqtt_ok and time.ticks_diff(time.ticks_ms(), last_ping) > (KEEPALIVE_S * 1000) // 2:
            try:
                client.ping()
            except Exception as e:
                print("ping failed:", e)
                mqtt_ok = False
            last_ping = time.ticks_ms()

        time.sleep_ms(100)

except KeyboardInterrupt:
    print("Stopping...")
finally:
    try:
        ble.gap_scan(0)
    except Exception:
        pass
