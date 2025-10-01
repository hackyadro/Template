import bluetooth
from micropython import const
import time
import network
from umqtt.simple import MQTTClient

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE   = const(6)
_ADV_TYPE_NAME = const(0x09)

_SCAN_FREQ = 100

MQTT_BROKER = "192.168.3.26"  
MQTT_PORT = 1883
MQTT_TOPIC = "beacons/rssi"  
CLIENT_ID = "beacon_publisher_01" 

ble = bluetooth.BLE()
ble.active(True)

beacons = {}
scan_done = False

def decode_name(adv_data):
    adv_bytes = bytes(adv_data)
    i = 0
    while i + 1 < len(adv_bytes):
        length = adv_bytes[i]
        if length == 0:
            break
        type = adv_bytes[i + 1]
        if type == _ADV_TYPE_NAME:
            return adv_bytes[i + 2 : i + 1 + length].decode("utf-8")
        i += 1 + length
    return None

def bt_irq(event, data):
    global beacons, scan_done
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        name = decode_name(adv_data)
        if name and name.startswith("beacon_"):
            if name not in beacons or rssi > beacons[name]:
                beacons[name] = rssi
    elif event == _IRQ_SCAN_DONE:
        scan_done = True

def scan_once(duration_ms=5000):
    global beacons, scan_done
    beacons = {}
    scan_done = False
    ble.irq(bt_irq)
    ble.gap_scan(duration_ms, 30000, 30000)
    
    while not scan_done:
        time.sleep_ms(_SCAN_FREQ)
    
    beacons_sorted = sorted(beacons.items(), key=lambda x: x[1], reverse=True)
    return [[name, rssi] for name, rssi in beacons_sorted]

def publish_beacons_data(beacons_data):
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.connect()
        
        if not beacons_data:
            data_str = "NO_BEACONS_FOUND"
            print("Маяки не найдены, отправляем сообщение об отсутствии")
        else:
            data_str = str(beacons_data).replace("'", '"')
            print(f"Найдено маяков: {len(beacons_data)}")
        
        client.publish(MQTT_TOPIC, data_str)
        print(f"Опубликовано в топик {MQTT_TOPIC}: {data_str}")
        
        client.disconnect()
        return True
        
    except Exception as e:
        print(f"Ошибка публикации: {e}")
        return False

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if not wlan.isconnected():
    print("Подключаемся к Wi-Fi...")
    wlan.connect('vaidy31', '88888888')
    
    for i in range(10):
        if wlan.isconnected():
            break
        print('Ожидание...')
        time.sleep(1)

if wlan.isconnected():
    print("Успешно подключено к Wi-Fi")
    print('IP адрес:', wlan.ifconfig()[0])
    
    while True:
        try:
            # Сканируем маяки
            beacons_data = scan_once(duration_ms=5000)
            
            # Публикуем данные (функция сама определит, есть маяки или нет)
            publish_beacons_data(beacons_data)
            
            # Пауза между сканированиями
            time.sleep(2)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)
else:
    print("Не удалось подключиться к Wi-Fi")