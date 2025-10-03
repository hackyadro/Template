from models import BLData, bl_list_to_json
from umqtt.simple import MQTTClient
import ujson
MQTT_BROKER = "5.35.88.189"   # публичный брокер
MQTT_PORT   = 1883
CLIENT_ID   = "esp32_micropython"
TOPIC       = "test/beacons"

client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)

def mqtt_connect():
    attempts = 5
    is_connected = False
    for i in range(attempts):
        try:
            client.connect()
            is_connected = True
            break
        except:
            pass
    if is_connected:
        print("Подключено к MQTT:", MQTT_BROKER)
    else:
        raise Exception("No connect to MQTT")
    
def mqtt_send_bldata(data: list[BLData]):
    json_res = bl_list_to_json(data)

    client.publish(TOPIC, json_res)
    #print("Отправлено:", json_res)
    
def connect_mqtt():
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
    client.connect()
    print("Подключено к MQTT:", MQTT_BROKER)
    return client
