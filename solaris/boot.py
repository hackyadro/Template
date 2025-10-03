import time
import machine
import network

# === НАСТРОЙКИ WiFi ===
WIFI_SSID = 'asyakwtd'
WIFI_PASSWORD = 'bbsp2858'

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Подключаемся к WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1
            print(".", end="")
    if wlan.isconnected():
        print("\nWiFi подключен! IP:", wlan.ifconfig()[0])
        return True
    else:
        print("\nОшибка подключения к WiFi!")
        return False

# Подключаемся к WiFi
if not connect_wifi():
    print("Нет WiFi, перезагрузка...")
    time.sleep(5)
    machine.reset()

# Загружаем основной скрипт
try:
    import main
except Exception as e:
    print("Ошибка при загрузке main.py:", e)
    time.sleep(10)
    machine.reset()
