import uasyncio as asyncio
from bluetooth import BLE
from collections import deque
from umqtt.robust import MQTTClient
import ujson
import time

# === Настройки MQTT ===
MQTT_BROKER = "192.168.98.124"
MQTT_PORT = 1883
MQTT_TOPIC = "hakaton/board"
CLIENT_ID = "esp32_board"

# === BLE ===
_IRQ_SCAN_RESULT = 5
ble = BLE()
ble.active(True)
queue = deque((), 200)
flag = asyncio.ThreadSafeFlag()

# Словарь для устройств: mac -> (rssi, name, tx, last_send_time)
devices = {}

# MQTT клиент
client = MQTTClient(client_id=CLIENT_ID, server=MQTT_BROKER, port=MQTT_PORT, keepalive=30)
client.connect(clean_session=True)
client.set_callback(lambda t, m: print(f"MQTT recv: {m.decode()} from {t.decode()}"))
client.subscribe(MQTT_TOPIC)
client.subscribe(f"{MQTT_TOPIC}/command")
print("MQTT подключение установлено и темы подписаны")

# === BLE IRQ ===
def _bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        queue.append((addr_type, bytes(addr), adv_type, rssi, bytes(adv_data)))
        flag.set()

ble.irq(_bt_irq)

# === Парсинг BLE данных ===
def _parse_adv(adv_data: bytes):
    i = 0
    name = None
    tx = None
    L = len(adv_data)
    while i < L:
        length = adv_data[i]
        if length == 0:
            break
        if i + length >= L + 1:
            break
        ad_type = adv_data[i + 1]
        value = adv_data[i + 2: i + 1 + length]
        if ad_type == 0x09:
            try:
                name = value.decode("utf-8", "replace")
            except:
                name = value
        elif ad_type == 0x0A and len(value) >= 1:
            tx = int.from_bytes(value[:1], "little", True)
            if (tx > 127):
                tx -= 256
        i += length + 1
    return name, tx

def _addr_to_str(addr_bytes):
    return ":".join("{:02x}".format(b) for b in reversed(addr_bytes))

# === Настройки частоты обновления ===
UPDATE_INTERVAL_MS = 25  # ~40 Гц

# === BLE сканер + MQTT с ограничением частоты ===
async def scanner_mqtt():
    ble.gap_scan(0, 30000, 30000)  # бесконечное сканирование
    print("🔍 Вечное сканирование BLE запущено")
    while True:
        await flag.wait()
        while queue:
            addr_type, addr, adv_type, rssi, adv_data = queue.popleft()
            name, tx = _parse_adv(adv_data)
            if not name:
                continue  # игнорируем устройства без имени
            mac = _addr_to_str(addr)
            now = time.ticks_ms()
            last_send = devices.get(mac, (None, None, None, 0))[3]
            if time.ticks_diff(now, last_send) >= UPDATE_INTERVAL_MS:
                devices[mac] = (rssi, name, tx, now)
                payload = ujson.dumps({
                    "mac": mac,
                    "rssi": rssi,
                    "tx_power": tx,
                    "name": name
                })
                try:
                    client.publish(MQTT_TOPIC, payload)
                except Exception as e:
                    print("Ошибка MQTT:", e)

# === Главная корутина ===
async def main_loop():
    asyncio.create_task(scanner_mqtt())
    while True:
        try:
            client.check_msg()  # проверка входящих MQTT сообщений
        except Exception as e:
            print("Ошибка MQTT check_msg:", e)
        await asyncio.sleep(0.001)  # 10 мс цикл проверки

# === Запуск ===
try:
    asyncio.run(main_loop())
finally:
    try:
        asyncio.new_event_loop()
    except:
        pass
