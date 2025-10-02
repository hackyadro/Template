import network
import time
import sys
import ujson
import urequests as requests
import ubinascii

SSID = "Xiaomi_1360"
PASSWORD = "qwasd3rf"

BEACONSDATA = [
  [{"name": "beacon_1", "signal": -63.3}, {"name": "beacon_2", "signal": -57.9}, {"name": "beacon_3", "signal": -66.8}, {"name": "beacon_4", "signal": -76.2}, {"name": "beacon_5", "signal": -76.8}, {"name": "beacon_6", "signal": -78.0}, {"name": "beacon_7", "signal": -93.5}],
  [{"name": "beacon_1", "signal": -61.0}, {"name": "beacon_2", "signal": -47.0}, {"name": "beacon_3", "signal": -73.0}, {"name": "beacon_4", "signal": -81.6}, {"name": "beacon_5", "signal": -73.0}, {"name": "beacon_6", "signal": -82.2}, {"name": "beacon_7", "signal": -95.5}],
  [{"name": "beacon_1", "signal": -62.1}, {"name": "beacon_2", "signal": -47.7}, {"name": "beacon_3", "signal": -61.5}, {"name": "beacon_4", "signal": -77.6}, {"name": "beacon_5", "signal": -66.9}, {"name": "beacon_6", "signal": -76.0}, {"name": "beacon_7", "signal": -94.5}],
  [{"name": "beacon_1", "signal": -54.0}, {"name": "beacon_2", "signal": -45.3}, {"name": "beacon_3", "signal": -66.2}, {"name": "beacon_4", "signal": -76.5}, {"name": "beacon_5", "signal": -68.8}, {"name": "beacon_6", "signal": -77.0}, {"name": "beacon_7", "signal": -95.0}],
  [{"name": "beacon_1", "signal": -53.8}, {"name": "beacon_2", "signal": -46.0}, {"name": "beacon_3", "signal": -67.0}, {"name": "beacon_4", "signal": -80.0}, {"name": "beacon_5", "signal": -71.0}, {"name": "beacon_6", "signal": -79.6}, {"name": "beacon_7", "signal": -93.7}],
  [{"name": "beacon_1", "signal": -61.0}, {"name": "beacon_2", "signal": -53.8}, {"name": "beacon_3", "signal": -65.0}, {"name": "beacon_4", "signal": -78.8}, {"name": "beacon_5", "signal": -70.0}, {"name": "beacon_6", "signal": -74.2}, {"name": "beacon_7", "signal": -92.0}],
  [{"name": "beacon_1", "signal": -67.0}, {"name": "beacon_2", "signal": -58.0}, {"name": "beacon_3", "signal": -60.5}, {"name": "beacon_4", "signal": -70.7}, {"name": "beacon_5", "signal": -79.0}, {"name": "beacon_6", "signal": -74.3}, {"name": "beacon_7", "signal": -93.0}],
  [{"name": "beacon_1", "signal": -73.2}, {"name": "beacon_2", "signal": -69.7}, {"name": "beacon_3", "signal": -57.0}, {"name": "beacon_4", "signal": -72.7}, {"name": "beacon_5", "signal": -75.4}, {"name": "beacon_6", "signal": -73.5}, {"name": "beacon_7", "signal": -93.0}],
  [{"name": "beacon_1", "signal": -70.5}, {"name": "beacon_2", "signal": -59.8}, {"name": "beacon_3", "signal": -55.2}, {"name": "beacon_4", "signal": -68.5}, {"name": "beacon_5", "signal": -67.8}, {"name": "beacon_6", "signal": -74.7}, {"name": "beacon_7", "signal": -89.0}],
  [{"name": "beacon_1", "signal": -77.2}, {"name": "beacon_2", "signal": -71.6}, {"name": "beacon_3", "signal": -49.0}, {"name": "beacon_4", "signal": -72.8}, {"name": "beacon_5", "signal": -66.4}, {"name": "beacon_6", "signal": -71.8}, {"name": "beacon_7", "signal": -91.0}],
  [{"name": "beacon_1", "signal": -77.2}, {"name": "beacon_2", "signal": -72.6}, {"name": "beacon_3", "signal": -48.6}, {"name": "beacon_4", "signal": -72.5}, {"name": "beacon_5", "signal": -62.7}, {"name": "beacon_6", "signal": -73.9}, {"name": "beacon_7", "signal": -90.1}],
  [{"name": "beacon_1", "signal": -70.0}, {"name": "beacon_2", "signal": -73.0}, {"name": "beacon_3", "signal": -48.3}, {"name": "beacon_4", "signal": -69.0}, {"name": "beacon_5", "signal": -63.8}, {"name": "beacon_6", "signal": -78.7}, {"name": "beacon_7", "signal": -87.3}],
  [{"name": "beacon_1", "signal": -76.8}, {"name": "beacon_2", "signal": -73.8}, {"name": "beacon_3", "signal": -50.4}, {"name": "beacon_4", "signal": -73.8}, {"name": "beacon_5", "signal": -66.8}, {"name": "beacon_6", "signal": -73.3}, {"name": "beacon_7", "signal": -85.2}],
  [{"name": "beacon_1", "signal": -77.4}, {"name": "beacon_2", "signal": -76.2}, {"name": "beacon_3", "signal": -56.0}, {"name": "beacon_4", "signal": -70.0}, {"name": "beacon_5", "signal": -74.0}, {"name": "beacon_6", "signal": -81.0}, {"name": "beacon_7", "signal": -88.3}],
  [{"name": "beacon_1", "signal": -76.9}, {"name": "beacon_2", "signal": -74.0}, {"name": "beacon_3", "signal": -60.8}, {"name": "beacon_4", "signal": -67.1}, {"name": "beacon_5", "signal": -60.0}, {"name": "beacon_6", "signal": -75.7}, {"name": "beacon_7", "signal": -91.5}],
  [{"name": "beacon_1", "signal": -79.2}, {"name": "beacon_2", "signal": -70.3}, {"name": "beacon_3", "signal": -59.7}, {"name": "beacon_4", "signal": -64.3}, {"name": "beacon_5", "signal": -65.3}, {"name": "beacon_6", "signal": -67.8}, {"name": "beacon_7", "signal": -82.5}],
  [{"name": "beacon_1", "signal": -82.3}, {"name": "beacon_2", "signal": -82.3}, {"name": "beacon_3", "signal": -67.0}, {"name": "beacon_4", "signal": -64.0}, {"name": "beacon_5", "signal": -69.2}, {"name": "beacon_6", "signal": -71.2}, {"name": "beacon_7", "signal": -88.5}],
  [{"name": "beacon_1", "signal": -78.0}, {"name": "beacon_2", "signal": -86.0}, {"name": "beacon_3", "signal": -71.5}, {"name": "beacon_4", "signal": -59.0}, {"name": "beacon_5", "signal": -55.0}, {"name": "beacon_6", "signal": -71.8}, {"name": "beacon_7", "signal": -88.2}],
  [{"name": "beacon_1", "signal": -83.0}, {"name": "beacon_2", "signal": -81.4}, {"name": "beacon_3", "signal": -69.3}, {"name": "beacon_4", "signal": -60.7}, {"name": "beacon_5", "signal": -54.3}, {"name": "beacon_6", "signal": -64.3}, {"name": "beacon_7", "signal": -82.3}],
  [{"name": "beacon_1", "signal": -83.2}, {"name": "beacon_2", "signal": -83.0}, {"name": "beacon_3", "signal": -76.0}, {"name": "beacon_4", "signal": -65.4}, {"name": "beacon_5", "signal": -65.0}, {"name": "beacon_6", "signal": -70.5}, {"name": "beacon_7", "signal": -88.2}],
  [{"name": "beacon_1", "signal": -86.0}, {"name": "beacon_2", "signal": -83.3}, {"name": "beacon_3", "signal": -74.1}, {"name": "beacon_4", "signal": -72.4}, {"name": "beacon_5", "signal": -58.0}, {"name": "beacon_6", "signal": -63.2}, {"name": "beacon_7", "signal": -83.5}],
  [{"name": "beacon_1", "signal": -84.8}, {"name": "beacon_2", "signal": -80.7}, {"name": "beacon_3", "signal": -72.5}, {"name": "beacon_4", "signal": -74.0}, {"name": "beacon_5", "signal": -53.5}, {"name": "beacon_6", "signal": -61.0}, {"name": "beacon_7", "signal": -83.3}],
  [{"name": "beacon_1", "signal": -86.6}, {"name": "beacon_2", "signal": -83.4}, {"name": "beacon_3", "signal": -72.2}, {"name": "beacon_4", "signal": -75.0}, {"name": "beacon_5", "signal": -46.0}, {"name": "beacon_6", "signal": -57.8}, {"name": "beacon_7", "signal": -80.2}],
  [{"name": "beacon_1", "signal": -85.0}, {"name": "beacon_2", "signal": -89.5}, {"name": "beacon_3", "signal": -71.0}, {"name": "beacon_4", "signal": -79.0}, {"name": "beacon_5", "signal": -44.2}, {"name": "beacon_6", "signal": -59.0}, {"name": "beacon_7", "signal": -81.0}],
  [{"name": "beacon_1", "signal": -82.6}, {"name": "beacon_2", "signal": -84.3}, {"name": "beacon_3", "signal": -69.2}, {"name": "beacon_4", "signal": -74.7}, {"name": "beacon_5", "signal": -60.7}, {"name": "beacon_6", "signal": -62.0}, {"name": "beacon_7", "signal": -83.0}],
  [{"name": "beacon_1", "signal": -73.0}, {"name": "beacon_2", "signal": -79.0}, {"name": "beacon_3", "signal": -64.0}, {"name": "beacon_4", "signal": -75.5}, {"name": "beacon_5", "signal": -51.0}, {"name": "beacon_6", "signal": -80.0}, {"name": "beacon_7", "signal": -82.3}],
  [{"name": "beacon_1", "signal": -75.0}, {"name": "beacon_2", "signal": -81.3}, {"name": "beacon_3", "signal": -62.2}, {"name": "beacon_4", "signal": -78.0}, {"name": "beacon_5", "signal": -62.3}, {"name": "beacon_6", "signal": -58.6}, {"name": "beacon_7", "signal": -79.4}],
  [{"name": "beacon_1", "signal": -77.0}, {"name": "beacon_2", "signal": -88.6}, {"name": "beacon_3", "signal": -64.5}, {"name": "beacon_4", "signal": -75.5}, {"name": "beacon_5", "signal": -55.8}, {"name": "beacon_6", "signal": -53.8}, {"name": "beacon_7", "signal": -76.2}],
  [{"name": "beacon_1", "signal": -82.4}, {"name": "beacon_2", "signal": -82.8}, {"name": "beacon_3", "signal": -73.0}, {"name": "beacon_4", "signal": -80.3}, {"name": "beacon_5", "signal": -52.3}, {"name": "beacon_6", "signal": -57.3}, {"name": "beacon_7", "signal": -75.3}],
  [{"name": "beacon_1", "signal": -82.7}, {"name": "beacon_2", "signal": -77.8}, {"name": "beacon_3", "signal": -69.0}, {"name": "beacon_4", "signal": -76.8}, {"name": "beacon_5", "signal": -55.3}, {"name": "beacon_6", "signal": -52.2}, {"name": "beacon_7", "signal": -74.8}],
  [{"name": "beacon_1", "signal": -84.2}, {"name": "beacon_2", "signal": -83.6}, {"name": "beacon_3", "signal": -75.4}, {"name": "beacon_4", "signal": -80.2}, {"name": "beacon_5", "signal": -57.7}, {"name": "beacon_6", "signal": -58.8}, {"name": "beacon_7", "signal": -75.2}],
  [{"name": "beacon_1", "signal": -85.0}, {"name": "beacon_2", "signal": -82.7}, {"name": "beacon_3", "signal": -68.2}, {"name": "beacon_4", "signal": -84.8}, {"name": "beacon_5", "signal": -64.5}, {"name": "beacon_6", "signal": -58.8}, {"name": "beacon_7", "signal": -64.5}],
  [{"name": "beacon_1", "signal": -81.0}, {"name": "beacon_2", "signal": -79.7}, {"name": "beacon_3", "signal": -72.3}, {"name": "beacon_4", "signal": -80.0}, {"name": "beacon_5", "signal": -60.5}, {"name": "beacon_6", "signal": -52.8}, {"name": "beacon_7", "signal": -56.0}],
  [{"name": "beacon_1", "signal": -88.3}, {"name": "beacon_2", "signal": -86.0}, {"name": "beacon_3", "signal": -81.3}, {"name": "beacon_4", "signal": -85.3}, {"name": "beacon_5", "signal": -57.8}, {"name": "beacon_6", "signal": -48.0}, {"name": "beacon_7", "signal": -62.8}],
  [{"name": "beacon_1", "signal": -92.0}, {"name": "beacon_2", "signal": -92.2}, {"name": "beacon_3", "signal": -80.5}, {"name": "beacon_4", "signal": -85.0}, {"name": "beacon_5", "signal": -70.3}, {"name": "beacon_6", "signal": -44.7}, {"name": "beacon_7", "signal": -58.7}],
  [{"name": "beacon_1", "signal": -90.8}, {"name": "beacon_2", "signal": -95.0}, {"name": "beacon_3", "signal": -80.0}, {"name": "beacon_4", "signal": -87.6}, {"name": "beacon_5", "signal": -72.6}, {"name": "beacon_6", "signal": -44.0}, {"name": "beacon_7", "signal": -62.0}],
  [{"name": "beacon_1", "signal": -95.5}, {"name": "beacon_2", "signal": -94.0}, {"name": "beacon_3", "signal": -87.8}, {"name": "beacon_4", "signal": -92.7}, {"name": "beacon_5", "signal": -70.9}, {"name": "beacon_6", "signal": -46.0}, {"name": "beacon_7", "signal": -59.3}],
  [{"name": "beacon_1", "signal": -96.0}, {"name": "beacon_2", "signal": -97.0}, {"name": "beacon_3", "signal": -84.3}, {"name": "beacon_4", "signal": -90.8}, {"name": "beacon_5", "signal": -81.2}, {"name": "beacon_6", "signal": -55.8}, {"name": "beacon_7", "signal": -58.2}],
  [{"name": "beacon_1", "signal": -99.5}, {"name": "beacon_2", "signal": -95.0}, {"name": "beacon_3", "signal": -90.3}, {"name": "beacon_4", "signal": -96.3}, {"name": "beacon_5", "signal": -79.4}, {"name": "beacon_6", "signal": -53.6}, {"name": "beacon_7", "signal": -49.0}],
  [{"name": "beacon_3", "signal": -90.0}, {"name": "beacon_4", "signal": -93.7}, {"name": "beacon_5", "signal": -81.2}, {"name": "beacon_6", "signal": -54.4}, {"name": "beacon_7", "signal": -46.4}],
  [{"name": "beacon_3", "signal": -92.3}, {"name": "beacon_5", "signal": -84.7}, {"name": "beacon_6", "signal": -60.1}, {"name": "beacon_7", "signal": -46.3}],
  [{"name": "beacon_3", "signal": -93.3}, {"name": "beacon_5", "signal": -83.8}, {"name": "beacon_6", "signal": -63.2}, {"name": "beacon_7", "signal": -35.6}],
  [{"name": "beacon_3", "signal": -91.8}, {"name": "beacon_4", "signal": -98.0}, {"name": "beacon_5", "signal": -82.3}, {"name": "beacon_6", "signal": -66.7}, {"name": "beacon_7", "signal": -42.0}],
  [{"name": "beacon_1", "signal": -100.0}, {"name": "beacon_3", "signal": -89.8}, {"name": "beacon_4", "signal": -97.0}, {"name": "beacon_5", "signal": -82.5}, {"name": "beacon_6", "signal": -60.6}, {"name": "beacon_7", "signal": -47.2}],
  [{"name": "beacon_2", "signal": -96.0}, {"name": "beacon_3", "signal": -91.2}, {"name": "beacon_4", "signal": -93.0}, {"name": "beacon_5", "signal": -73.6}, {"name": "beacon_6", "signal": -57.2}, {"name": "beacon_7", "signal": -52.5}],
  [{"name": "beacon_1", "signal": -95.5}, {"name": "beacon_2", "signal": -97.0}, {"name": "beacon_3", "signal": -88.0}, {"name": "beacon_4", "signal": -92.2}, {"name": "beacon_5", "signal": -75.6}, {"name": "beacon_6", "signal": -54.7}, {"name": "beacon_7", "signal": -57.9}],
  [{"name": "beacon_1", "signal": -85.0}, {"name": "beacon_2", "signal": -91.0}, {"name": "beacon_3", "signal": -83.0}, {"name": "beacon_4", "signal": -84.0}, {"name": "beacon_5", "signal": -59.5}, {"name": "beacon_6", "signal": -51.0}, {"name": "beacon_7", "signal": -56.4}],
  [{"name": "beacon_1", "signal": -84.8}, {"name": "beacon_2", "signal": -84.0}, {"name": "beacon_3", "signal": -77.9}, {"name": "beacon_4", "signal": -85.5}, {"name": "beacon_5", "signal": -57.7}, {"name": "beacon_6", "signal": -48.2}, {"name": "beacon_7", "signal": -60.9}]
]
INDEX_NOW = 0

map_name = None
beacons = []
freq = None
write_road = None
MAC_ADDRESS = None
JSON_PARSE_ERROR = "JSON parse error:"

HOST_ADDRESS = "http://192.168.31.181:8000"

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
        # print("IP address:", ip)
        return True

def do_post(url, json_dict=None):
    try:
        body = ujson.dumps(json_dict) if json_dict else None
        # print("HTTP POST:", url, body)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        r = requests.post(url, data=body, headers=headers)
        # print("Status:", r.status_code)
        text = r.text
        # try:
            # with open("last_response.txt", "w") as f:
                # f.write(text)
        # except Exception as e:
            # print("Save error:", e)
        r.close()
        return r.status_code, text
    except Exception as e:
        # print("POST failed:", e)
        return None, None

def mac_to_str(mac_bytes):
    try:
        return ':'.join('{:02X}'.format(b) for b in mac_bytes)
    except Exception:
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
    # print(f"Device MAC address: {MAC_ADDRESS}")
    return MAC_ADDRESS

def update_map():
    global map_name, beacons
    
    url_post = HOST_ADDRESS + "/get_map"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)

    if status == 200 and body:
        # print("update_map: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "map_name" in data:
                map_name = data["map_name"]
                # print(f"Map name updated: {map_name}")
            
            if "beacons" in data and isinstance(data["beacons"], list):
                beacons = data["beacons"]
                # print(f"Beacons list: {beacons}")
            
            return data
        except Exception as e:
            # print("JSON parse error:", e)
            return None
    else:
        # print(f"Failed to get map data. Status: {status}")
        return None

def update_freq():
    global freq
    
    url_post = HOST_ADDRESS + "/get_freq"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)
    # status = 200
    # body = '{"freq": 1}'

    if status == 200 and body:
        # print("update_freq: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "freq" in data:
                freq = data["freq"]
                # print(f"Frequency updated: {freq}")
            
            return data
        except Exception as e:
            # print(JSON_PARSE_ERROR, e)
            return None
    else:
        # print(f"Failed to get freq data. Status: {status}")
        return None

def update_status_road():
    global write_road

    url_post = HOST_ADDRESS + "/get_status_road"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)
    # status = 200
    # body = '{"write_road": true}'

    if status == 200 and body:
        # print("update_status_road: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "write_road" in data:
                write_road = data["write_road"]
                # print(f"Write road status updated: {write_road}")
            
            return data
        except Exception as e:
            # print(JSON_PARSE_ERROR, e)
            return None
    else:
        # print(f"Failed to get status_road data. Status: {status}")
        return None

def ping_server():
    """Пингует сервер для проверки изменений"""
    url_post = HOST_ADDRESS + "/ping"
    payload = {"mac": MAC_ADDRESS}
    status, body = do_post(url_post, json_dict=payload)

    if status == 200 and body:
        try:
            data = ujson.loads(body)
            
            if "change" in data and data["change"]:
                # print("Changes detected on server!")
                
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
                # print("No changes on server")
                return False 
                
        except Exception as e:
            print(JSON_PARSE_ERROR, e)
            return None
    else:
        # print(f"Failed to ping server. Status: {status}")
        return None

def run_pingator():
    """Запускает бесконечный цикл пингатора с интервалом 1 секунда"""
    # print("Starting pingator...")
    ping_count = 0
    
    while True:
        try:
            ping_count += 1
            # print(f"\n--- Ping #{ping_count} ---")
            
            result = ping_server()

            send_signal()
            
            # if result is True:
            #     # print("Server data updated!")
            # elif result is False:
            #     # print("No updates needed")
            # else:
            #     # print("Ping failed")
            
        except KeyboardInterrupt:
            # print("\nPingator stopped by user")
            break
        except Exception as e:
            # print(f"Pingator error: {e}")
            time.sleep(1)

def send_signal():
    global INDEX_NOW

    url_post = HOST_ADDRESS + "/send_signal"
    current_beacon_data = BEACONSDATA[INDEX_NOW]

    for beacon in current_beacon_data:
        beacon["signal"] = int(beacon["signal"])
    payload = {"mac": MAC_ADDRESS,"map_name": map_name, "list": current_beacon_data}
    INDEX_NOW += 1

    if INDEX_NOW >= len(BEACONSDATA):
        INDEX_NOW = 0
    status, body = do_post(url_post, json_dict=payload)

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