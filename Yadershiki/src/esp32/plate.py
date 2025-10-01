import network
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if not wlan.isconnected():
    print("Пытаемся подключиться")
    wlan.connect('vaidy31', '88888888')
    
    for i in range(10):
        if wlan.isconnected():
            break
        print('Ожидание...')
        time.sleep(1)

if wlan.isconnected():
    print("Мы смогли. Ура")
    print('Сетевые настройки:', wlan.ifconfig())
    
    try:
        import urequests
        print("urequests доступен")
        
        ip_address = "192.168.3.26:8080"
        response = urequests.get(f"http://{ip_address}")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.close()
        
    except ImportError:
        print("urequests не установлен")

else:
    print("Не удалось подключиться")
    
