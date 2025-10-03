# main.py
# Wi-Fi + HTTP GET/POST helper for MicroPython (ESP32-S3)
# ASCII-friendly prints

import network
import time
import sys

SSID = "iPhone (Владимир)"
PASSWORD = "12345678"

# -------- Wi-Fi connect --------
def wifi_connect(ssid, pwd, timeout=15):
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    print("Connecting to Wi-Fi:", SSID)
    wifi.connect(SSID, PASSWORD)

    timeout = 10
    start = time.time()

    while not wifi.isconnected():
        if time.time() - start > timeout:
            print("Failed to connect to Wi-Fi")
            break
        time.sleep(1)

    if wifi.isconnected():
        ip = wifi.ifconfig()[0]
        print("Connected to Wi-Fi!")
        print("IP address:", ip)
        return True


# -------- Import urequests --------
try:
    import urequests as requests  # type: ignore
except ImportError:
    print("Error: urequests module not found. Install MicroPython urequests.")

def do_post(url, json_dict=None):
    import ujson
    try:
        print("HTTP POST:", url)
        body = ujson.dumps(json_dict) if json_dict else None
        headers = {"Content-Type": "application/json"} if json_dict else None
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

# -------- Example usage --------
if __name__ == "__main__":
    # Connect to Wi-Fi
    if not wifi_connect(SSID, PASSWORD, timeout=15):
        sys.exit(1)

    # Example GET
    # url_get = "https://api.ipify.org?format=json"
    # status, body = do_get(url_get)
    # if body:
    #     print("GET response head:", body[:200])

    # Example POST
    url_post = "http://q1zin-nsu.ru/ping.php"
    payload = {"mac": "4A:E3:50:9E:E3:62"}
    status, body = do_post(url_post, json_dict=payload)
    if body:
        print("POST response head:", body[:200])

    print("Done.")
