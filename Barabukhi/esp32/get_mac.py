import network
import time

def mac_to_str(mac_bytes):
    """Преобразует байты MAC в строку вида XX:XX:XX:XX:XX:XX"""
    try:
        return ':'.join('{:02X}'.format(b) for b in mac_bytes)
    except Exception:
        import ubinascii
        h = ubinascii.hexlify(mac_bytes).decode('utf-8')
        return ':'.join(h[i:i+2].upper() for i in range(0, len(h), 2))

def get_mac_address():
    """Возвращает MAC-адрес STA интерфейса в виде строки"""
    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)
        # time.sleep(0.001)
    mac = sta.config('mac')
    return mac_to_str(mac)


# Пример использования
if __name__ == "__main__":
    print("MAC:", get_mac_address())