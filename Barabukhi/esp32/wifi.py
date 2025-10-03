# main.py (ASCII-friendly)
import network
import time

SSID = 'Keenetic-9990'   # -> replace with your SSID
PASSWORD = 'PnaFyiEF'  # -> replace with your password

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

print("Connecting to Wi-Fi:", SSID)
wifi.connect(SSID, PASSWORD)

timeout = 10
start = time.time()

while not wifi.isconnected():
    if time.time() - start > timeout:
        print("Failed to connect to Wi-Fi")
        break
    time.sleep(1)

if wifi.isconnected():
    ip = wifi.ifconfig()[0]
    print("Connected to Wi-Fi!")
    print("IP address:", ip)

