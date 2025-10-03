import network
import time
import bluetooth
import time

SSID = "TECNO POVA 5"        # имя твоей сети Wi-Fi
PASSWORD = "nhezynyfut58dnv"  # пароль от Wi-Fi

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)  # режим "клиент"
    wlan.active(True)

    if not wlan.isconnected():
        print("Подключаюсь к Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        for i in range(20):  # ждем до 20 секунд
            if wlan.isconnected():
                break
            time.sleep(1)

    if wlan.isconnected():
        print("Успешно!")
        print("IP config:", wlan.ifconfig())
    else:
        print("Ошибка подключения")

connect_wifi()

ble = bluetooth.BLE()
ble.active(True)

devices = {}  # словарь: mac -> (rssi, name)

def scan_callback(addr_type, addr, adv_type, rssi, adv_data):
    mac = ":".join("%02x" % b for b in addr)   # MAC адрес
    # пытаемся вытащить имя из рекламных данных
    name = None
    try:
        name = adv_data.decode("utf-8")
    except:
        pass
    devices[mac] = (rssi, name)

print("Сканирую устройства 10 секунд...")
ble.gap_scan(10000, 30000, 30000, scan_callback)  # 10 секунд
time.sleep(12)  # ждём пока сканирование завершится
print("Сканирование завершено.\n")

# выводим список найденных устройств
if devices:
    print("Найденные устройства:")
    for mac, (rssi, name) in devices.items():
        print(f"MAC: {mac}, RSSI: {rssi}, Имя: {name}")
else:
    print("Устройств не найдено.")

