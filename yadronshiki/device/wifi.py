import network, time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)

    def connect(self, timeout=15):
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print("Подключаюсь к WiFi...")
            self.wlan.connect(self.ssid, self.password)

            while not self.wlan.isconnected() and timeout > 0:
                print(".", end="")
                time.sleep(1)
                timeout -= 1
            print()

        if self.wlan.isconnected():
            print("WiFi подключен:", self.wlan.ifconfig())
            return True
        print("Ошибка подключения WiFi")
        return False
