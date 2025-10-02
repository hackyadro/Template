import json
from umqtt.simple import MQTTClient

class Client:
    def __init__(self, client_id: str, mqtt_broker: str, port: int):
        self.client = MQTTClient(client_id, mqtt_broker, port = port)
        self.client.connect()
        self.client.set_callback(self._message_callback)
    
    def send_data(self, topic: str, data: dict[str, str]) -> bool:
        if not self.client:
            return False
            
        try:
            self.client.publish(topic, json.dumps(data))
            return True
        except:
            return False
        
    def subscribe(self, topic: str) -> bool:
        self.client.subscribe(topic)
    
    def _message_callback(self, topic: bytes, message: bytes):
        try:
            topic_str = topic.decode('utf-8')
            message_str = message.decode('utf-8')
            data = json.loads(message_str)
            print(topic_str, data)
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
    