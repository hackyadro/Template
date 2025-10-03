import network
import socket
from umqtt.simple import MQTTClient
import ujson as json
import time


WIFI_SSID = "iPhone Матвей"
WIFI_PASSWORD = "77775555"

MQTT_BROKER = "172.20.10.6"
MQTT_PORT = 1883
MQTT_TOPIC = "indoor/scan/data"
CONFIG_TOPIC = "indoor/config"
CLIENT_ID = "esp32_client_01"

scan_duration = 1000
last_received_time = 0


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Подключаемся к Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Ждем подключения
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            print("Ожидание подключения...")
            time.sleep(1)
            timeout -= 1
            
        if not wlan.isconnected():
            print("Не удалось подключиться к Wi-Fi")
            return False

    print("Подключено к ", wlan.config('ssid'), "; ip: ", wlan.ifconfig()[0], sep='')
    return True


def mqtt_callback(topic, message):
    """Callback функция для входящих MQTT сообщений"""
    global scan_duration, last_received_time
    
    try:
        topic_str = topic.decode('utf-8')
        message_str = message.decode('utf-8')
        
        print(f"Получено сообщение: topic='{topic_str}', message='{message_str}'")
        
        # Проверяем, что это наш топик
        if topic_str == CONFIG_TOPIC:
            try:
                scan_duration = int(message_str)
                last_received_time = time.time()
                
                print(f"Установлено новое значение: {scan_duration}")
                
            except ValueError:
                print(f"Ошибка: сообщение '{message_str}' не является числом")
                
    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")


def connect_mqtt():
    """Подключение к MQTT брокеру"""
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.set_callback(mqtt_callback)
        client.connect()
        client.subscribe(CONFIG_TOPIC)
        print("Подключено к MQTT брокеру")
        return client
    except Exception as e:
        print("Ошибка подключения MQTT:", e)
        return None


def check_messages(client):
    """Проверка входящих сообщений без блокировки"""
    try:
        client.check_msg()
        return True
    except Exception as e:
        print(f"Ошибка проверки сообщений: {e}")
        return False


def publish_data(client, data):
    """Публикация данных в MQTT"""
    try:
        json_data = json.dumps(data)
        client.publish(MQTT_TOPIC, json_data)
        print("Данные отправлены:", json_data)
        return True
    except Exception as e:
        print("Ошибка публикации:", e)
        return False
