import network
import time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect(self) -> bool:
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print(f'Подключение к {self.ssid}...')
            self.wlan.connect(self.ssid, self.password)
            
            for i in range(20):
                if self.wlan.isconnected():
                    break
                time.sleep(1)
                
        return self.wlan.isconnected()
    
    def get_ip(self):
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None