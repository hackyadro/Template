import network
import time
import sys
import ujson
import urequests as requests
import ubinascii
import ubluetooth

SSID = "iPhone (Владимир)"
PASSWORD = "12345678"

map_name = None
beacons = []
freq = None
write_road = None
MAC_ADDRESS = None
JSON_PARSE_ERROR = "JSON parse error:"

HOST_ADDRESS = "http://10.145.244.78:8000"

# BLE scanning and reporting config
SCAN_TIME = 0.05  # seconds per scan burst
POLL_FREQUENCY_HZ = 5  # fixed BLE scan rate

# Names of beacons we accept from BLE advertisements
BEACONS = {
    "beacon_1",
    "beacon_2",
    "beacon_3",
    "beacon_4",
    "beacon_5",
    "beacon_6",
    "beacon_7",
    "beacon_8",
}

def decode_name(adv_data):
    if not adv_data or len(adv_data) == 0:
        return None
    i = 0
    while i < len(adv_data):
        length = adv_data[i]
        if length == 0:
            break
        if i + length >= len(adv_data):
            break
        ad_type = adv_data[i + 1]
        if ad_type in (0x08, 0x09):  # Shortened/Complete Local Name
            name_bytes = bytes(adv_data[i + 2 : i + 1 + length])
            try:
                name = name_bytes.decode('utf-8')
                return name if name else None
            except Exception:
                return None
        i += 1 + length
    return None

class BLEScanner:
    def __init__(self, poll_freq_hz=10):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.bt_irq)
        self.current_scan_devices = {}
        self.scan_complete = False
        self.scanning_active = False
        self.poll_freq_hz = poll_freq_hz
        self.poll_period = 1.0 / poll_freq_hz
        # accumulated structure: {mac: {'name': str, 'rssi_values': [..]}}
        self.accumulated_data = {}

    def bt_irq(self, event, data):
        if event == 5:
            _, addr, _, rssi, adv_data = data
            mac = ':'.join('{:02X}'.format(b) for b in addr)
            device_name = decode_name(adv_data)
            if device_name and device_name in BEACONS:
                self.current_scan_devices[mac] = {
                    'name': device_name,
                    'rssi': rssi
                }
        elif event == 6:
            self.scan_complete = True
            self.scanning_active = False

    def poll_once(self, duration=SCAN_TIME):
        self.current_scan_devices.clear()
        self.scan_complete = False
        if self.scanning_active:
            try:
                self.ble.gap_scan(None)
                time.sleep(0.01)
            except OSError:
                pass
        try:
            self.scanning_active = True
            self.ble.gap_scan(int(duration * 1000), 30000, 30000, True)
        except OSError:
            self.scanning_active = False
            return self.current_scan_devices.copy()
        timeout = duration + 0.5
        start_time = time.time()
        while not self.scan_complete:
            if time.time() - start_time > timeout:
                try:
                    self.ble.gap_scan(None)
                except OSError:
                    pass
                self.scanning_active = False
                break
            time.sleep(0.01)
        return self.current_scan_devices.copy()

    def accumulate_data(self, devices):
        for mac, info in devices.items():
            if mac not in self.accumulated_data:
                self.accumulated_data[mac] = {
                    'name': info['name'],
                    'rssi_values': []
                }
            self.accumulated_data[mac]['rssi_values'].append(info['rssi'])

    def calculate_averages(self):
        averaged_data = {}
        for mac, info in self.accumulated_data.items():
            vals = info.get('rssi_values') or []
            if vals:
                avg_rssi = sum(vals) / len(vals)
                averaged_data[mac] = {
                    'name': info['name'],
                    'rssi': avg_rssi,
                    'samples': len(vals)
                }
        return averaged_data

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
        print("HTTP POST:", url, body)
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
    except Exception:
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
        except Exception:
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

    if status == 200 and body:
        # print("update_freq: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "freq" in data:
                freq = data["freq"]
                # print(f"Frequency updated: {freq}")
            
            return data
        except Exception:
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

    if status == 200 and body:
        # print("update_status_road: POST response head:", body[:200])
        try:
            data = ujson.loads(body)
            
            if "write_road" in data:
                write_road = data["write_road"]
                # print(f"Write road status updated: {write_road}")
            
            return data
        except Exception:
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

def send_signal_with_list(beacon_list):
    url_post = HOST_ADDRESS + "/send_signal"
    payload = {"mac": MAC_ADDRESS, "map": map_name, "list": beacon_list}
    status, body = do_post(url_post, json_dict=payload)
    # print("!!!! ", status, body)

def current_report_period():
    """Compute report period from global freq with bounds [0.1, 10] Hz."""
    try:
        f = float(freq) if freq is not None else 1.0
    except Exception:
        f = 1.0
    if f < 0.1:
        f = 0.1
    if f > 10.0:
        f = 10.0
    return 1.0 / f

def run_main_loop():
    """Main loop: scan at 10Hz, ping each 1s, send_signal at 'freq' Hz."""
    scanner = BLEScanner(poll_freq_hz=POLL_FREQUENCY_HZ)
    last_ping_time = time.time()
    last_report_time = time.time()

    while True:
        try:
            loop_start = time.time()

            # 10 Hz BLE polling
            devices_found = scanner.poll_once()
            scanner.accumulate_data(devices_found)

            # Ping every 1 second
            if time.time() - last_ping_time >= 1.0:
                ping_server()
                last_ping_time = time.time()

            # Send signal at configured freq
            report_period = current_report_period()
            if time.time() - last_report_time >= report_period:
                averaged = scanner.calculate_averages()
                if averaged:
                    # Transform to backend payload
                    beacon_list = []
                    for _mac, info in averaged.items():
                        beacon_list.append({
                            "name": info['name'],
                            "signal": info['rssi'],
                            "samples": int(info.get('samples', 0))
                            })
                    send_signal_with_list(beacon_list)
                # reset accumulation window regardless
                scanner.accumulated_data.clear()
                last_report_time = time.time()

            # sleep to maintain ~10Hz polling
            elapsed = time.time() - loop_start
            sleep_time = max(0, scanner.poll_period - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            break
        except Exception:
            # backoff a bit on error
            time.sleep(0.1)

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
    
    run_main_loop()