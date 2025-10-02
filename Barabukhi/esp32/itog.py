import network
import time
import sys
import ujson


SSID = "Xiaomi_1360"
PASSWORD = "qwasd3rf"

map_name = None
beacons = []
freq = None
write_road = None
MAC_ADDRESS = None
JSON_PARSE_ERROR = "JSON parse error:"

def wifi_connect(ssid, pwd):
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    print("Connecting to Wi-Fi:", ssid)
    wifi.connect(ssid, pwd)

    connection_timeout = 2.5
    start = time.time()

    while not wifi.isconnected():
        if time.time() - start > connection_timeout:
            print("Failed to connect to Wi-Fi")
            break
        time.sleep(1)

    if wifi.isconnected():
        ip = wifi.ifconfig()[0]
        print("Connected to Wi-Fi!")
        print("IP address:", ip)
        return True

try:
    import urequests as requests
except ImportError:
    print("Error: urequests module not found. Install MicroPython urequests.")

def do_post(url, json_dict=None):
    import ujson
    try:
        print("HTTP POST:", url)
        body = ujson.dumps(json_dict) if json_dict else None

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        r = requests.post(url, data=body, headers=headers)
        print("Status:", r.status_code)
        text = r.text
        try:
            with open("last_response.txt", "w") as f:
                f.write(text)
        except Exception as e:
            print("Save error:", e)
        r.close()
        return r.status_code, text
    except Exception as e:
        print("POST failed:", e)
        return None, None

def mac_to_str(mac_bytes):
    try:
        return ':'.join('{:02X}'.format(b) for b in mac_bytes)
    except Exception:
        import ubinascii
        h = ubinascii.hexlify(mac_bytes).decode('utf-8')
        return ':'.join(h[i:i+2].upper() for i in range(0, len(h), 2))

def get_mac_address():
    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)
    mac = sta.config('mac')
    return mac_to_str(mac)

def set_mac_address():
    global MAC_ADDRESS
    
    MAC_ADDRESS = get_mac_address()
    print(f"Device MAC address: {MAC_ADDRESS}")
    return MAC_ADDRESS

def update_map():
    global map_name, beacons
    
    url_post = "http://192.168.31.211:8000/get_map"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)

    if status == 200 and body:
        print("update_map: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "map_name" in data:
                map_name = data["map_name"]
                print(f"Map name updated: {map_name}")
            
            if "beacons" in data and isinstance(data["beacons"], list):
                beacons = data["beacons"]
                print(f"Beacons list: {beacons}")
            
            return data
        except Exception as e:
            print("JSON parse error:", e)
            return None
    else:
        print(f"Failed to get map data. Status: {status}")
        return None

def update_freq():
    global freq
    
    url_post = "http://192.168.31.211:8000/get_freq"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)
    # status = 200
    # body = '{"freq": 1}'

    if status == 200 and body:
        print("update_freq: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "freq" in data:
                freq = data["freq"]
                print(f"Frequency updated: {freq}")
            
            return data
        except Exception as e:
            print(JSON_PARSE_ERROR, e)
            return None
    else:
        print(f"Failed to get freq data. Status: {status}")
        return None

def update_status_road():
    global write_road

    url_post = "http://192.168.31.211:8000/get_status_road"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)
    # status = 200
    # body = '{"write_road": true}'

    if status == 200 and body:
        print("update_status_road: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "write_road" in data:
                write_road = data["write_road"]
                print(f"Write road status updated: {write_road}")
            
            return data
        except Exception as e:
            print(JSON_PARSE_ERROR, e)
            return None
    else:
        print(f"Failed to get status_road data. Status: {status}")
        return None

def ping_server():
    """Пингует сервер для проверки изменений"""
    url_post = "http://192.168.31.211:8000/ping"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)

    if status == 200 and body:
        try:
            data = ujson.loads(body)
            
            if "change" in data and data["change"]:
                print("Changes detected on server!")
                
                if "change_list" in data and isinstance(data["change_list"], list):
                    change_list = data["change_list"]
                    print(f"Changed items: {change_list}")
                    
                    if "map" in change_list:
                        print("Updating map...")
                        update_map()
                    
                    if "freq" in change_list:
                        print("Updating frequency...")
                        update_freq()
                    
                    if "status" in change_list:
                        print("Updating status road...")
                        update_status_road()
                        
                    return True
                
            else:
                print("No changes on server")
                return False 
                
        except Exception as e:
            print(JSON_PARSE_ERROR, e)
            return None
    else:
        print(f"Failed to ping server. Status: {status}")
        return None

def run_pingator():
    """Запускает бесконечный цикл пингатора с интервалом 1 секунда"""
    print("Starting pingator...")
    ping_count = 0
    
    while True:
        try:
            ping_count += 1
            print(f"\n--- Ping #{ping_count} ---")
            
            result = ping_server()
            
            if result is True:
                print("Server data updated!")
            elif result is False:
                print("No updates needed")
            else:
                print("Ping failed")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nPingator stopped by user")
            break
        except Exception as e:
            print(f"Pingator error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    if not wifi_connect(SSID, PASSWORD):
        sys.exit(1)

    set_mac_address()
    update_map()
    update_freq()
    update_status_road()

    print("\n\n")
    print("Mac Address:", MAC_ADDRESS)
    print("Map Name:", map_name)
    print("Beacons:", beacons)
    print("Frequency:", freq)
    print("Write Road Status:", write_road)
    print("\n\n")
    
    run_pingator()