from umqtt.simple import MQTTClient

class MQTTClientWrapper:
    def __init__(self, client_id, broker, port):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.client = None

    def connect(self):
        try:
            self.client = MQTTClient(self.client_id, self.broker, port=self.port)
            self.client.connect()
            print("MQTT подключен к", self.broker)
        except Exception as e:
            print("Ошибка MQTT:", e)
            self.client = None
        return self.client is not None

    def publish(self, topic, payload):
        if not self.client:
            return False
        try:
            self.client.publish(topic, payload)
            return True
        except Exception as e:
            print("Ошибка publish:", e)
            return False
