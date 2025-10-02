import machine  # type: ignore
import bluetooth # type: ignore
import network  # type: ignore
import usocket as socket  # type: ignore
import utime as time_mod  # type: ignore
import ujson as json  # type: ignore

ticks_ms = time_mod.ticks_ms
ticks_diff = time_mod.ticks_diff
sleep_ms = time_mod.sleep_ms
sleep = time_mod.sleep

CONFIG_FILE = "mqtt_config.json"
AP_SSID = "DeviceSetup"
AP_PASSWORD = "setup123"
AP_CHANNEL = 6
CONNECT_TIMEOUT_SEC = 20

# --- file utils unchanged ---
def load_config():
    try:
        with open(CONFIG_FILE, "r") as fp:
            data = json.load(fp)
            return data if isinstance(data, dict) else None
    except OSError:
        return None
    except ValueError:
        return None


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as fp:
            json.dump(config, fp)
        print("Configuration saved to", CONFIG_FILE)
        return True
    except OSError as exc:
        print("Failed to save configuration:", exc)
        return False

# --- wifi connect: keep loop short so REPL can run ---
def connect_to_wifi(wifi_config):
    if not wifi_config:
        return False

    ssid = wifi_config.get("ssid")
    password = wifi_config.get("password", "")

    if not ssid:
        print("No SSID provided in configuration.")
        return False

    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)

    if sta.isconnected():
        # some ports have config('ssid'); guard in try.
        try:
            current = sta.config('ssid')
        except Exception:
            current = None
        if current == ssid:
            print("Already connected to Wi-Fi:", ssid)
            return True
        try:
            sta.disconnect()
        except Exception:
            pass

    print("Connecting to Wi-Fi:", ssid)
    try:
        sta.connect(ssid, password)
    except OSError as exc:
        print("Failed to start Wi-Fi connection:", exc)
        return False

    start = ticks_ms()
    timeout = CONNECT_TIMEOUT_SEC * 1000
    # use short sleeps to avoid blocking too long
    while not sta.isconnected():
        if ticks_diff(ticks_ms(), start) > timeout:
            print("Wi-Fi connection timed out.")
            return False
        # small yield to keep REPL responsive
        sleep_ms(100)
    try:
        print("Wi-Fi connected, IP:", sta.ifconfig()[0])
    except Exception:
        print("Wi-Fi connected")
    return True

# --- helpers for parsing ---
def url_decode(value):
    if value is None:
        return ""

    result = []
    i = 0
    length = len(value)
    while i < length:
        char = value[i]
        if char == '+':
            result.append(' ')
            i += 1
        elif char == '%' and i + 2 < length:
            try:
                result.append(chr(int(value[i + 1:i + 3], 16)))
                i += 3
            except ValueError:
                result.append(char)
                i += 1
        else:
            result.append(char)
            i += 1
    return ''.join(result)


def parse_post_data(body):
    params = {}
    if not body:
        return params

    pairs = body.split('&')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key] = url_decode(value.replace('\r', '').replace('\n', ''))
    return params

# --- HTML renderer unchanged (kept for clarity) ---
def render_form(existing_config=None, message=""):
    wifi_cfg = (existing_config or {}).get("wifi", {})
    broker_cfg = (existing_config or {}).get("broker", {})

    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Setup MQTT Publisher</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#f7f7f7; margin:0; padding:0; }}
    .container {{ max-width: 420px; margin: 40px auto; background:#fff; padding:24px; border-radius:12px; box-shadow:0 6px 24px rgba(0,0,0,0.1); }}
    h1 {{ font-size:1.4rem; margin-bottom:16px; }}
    label {{ display:block; margin-top:12px; font-weight:600; }}
    input {{ width:100%; padding:10px; margin-top:6px; border:1px solid #ccc; border-radius:8px; box-sizing:border-box; }}
    button {{ width:100%; padding:12px; margin-top:20px; background:#2563eb; color:#fff; border:none; border-radius:8px; font-size:1rem; cursor:pointer; }}
    button:hover {{ background:#1d4ed8; }}
    .message {{ margin-top:12px; color:#047857; font-weight:600; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>MQTT Publisher Setup</h1>
    {message}
    <form method=\"POST\">
      <label for=\"wifi_ssid\">Wi-Fi SSID</label>
      <input id=\"wifi_ssid\" name=\"wifi_ssid\" value=\"{wifi_ssid}\" required>

      <label for=\"wifi_password\">Wi-Fi Password</label>
      <input id=\"wifi_password\" name=\"wifi_password\" value=\"{wifi_password}\" type=\"password\">

      <label for=\"broker_host\">Mosquitto Host</label>
      <input id=\"broker_host\" name=\"broker_host\" value=\"{broker_host}\" required>

      <label for=\"broker_port\">Mosquitto Port</label>
      <input id=\"broker_port\" name=\"broker_port\" value=\"{broker_port}\" type=\"number\" min=\"1\" max=\"65535\" required>

      <label for=\"broker_login\">Broker Username</label>
      <input id=\"broker_login\" name=\"broker_login\" value=\"{broker_login}\">

      <label for=\"broker_password\">Broker Password</label>
      <input id=\"broker_password\" name=\"broker_password\" value=\"{broker_password}\" type=\"password\">

      <button type=\"submit\">Save &amp; Apply</button>
    </form>
  </div>
</body>
</html>
"""
    message_html = f"<div class=\"message\">{message}</div>" if message else ""

    return html.format(
        message=message_html,
        wifi_ssid=wifi_cfg.get("ssid", ""),
        wifi_password=wifi_cfg.get("password", ""),
        broker_host=broker_cfg.get("host", ""),
        broker_port=broker_cfg.get("port", ""),
        broker_login=broker_cfg.get("username", ""),
        broker_password=broker_cfg.get("password", "")
    )

# --- safer send_response: make attempts and always close client ---
def send_response(client, body, status="200 OK"):
    try:
        if isinstance(body, (bytes, bytearray)):
            body_bytes = body
        else:
            body_bytes = str(body).encode("utf-8")

        headers = (
            "HTTP/1.1 {}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(status, len(body_bytes))

        try:
            client.setblocking(True)
        except Exception:
            pass

        client.send(headers)
        if body_bytes:
            client.send(body_bytes)
    except Exception as exc:
        print("send_response error:", exc)
    finally:
        try:
            client.close()
        except Exception:
            pass

# --- non-blocking recv with timeout to avoid indefinite blocking ---
def recv_request_nonblocking(client, timeout_ms=4000, chunk_size=1024):
    """
    Read from non-blocking socket until header/body separator found or timeout.
    Returns bytes (possibly empty).
    """
    start = ticks_ms()
    data = b""
    header = None
    body = b""
    content_len = None
    sent_continue = False

    try:
        client.setblocking(False)
    except Exception:
        pass

    while True:
        if header is not None:
            if content_len is None:
                break
            if len(body) >= content_len:
                break

        if ticks_diff(ticks_ms(), start) > timeout_ms:
            break

        try:
            part = client.recv(chunk_size)
        except OSError:
            sleep_ms(20)
            continue

        if not part:
            if header is None or content_len is None or len(body) >= (content_len or 0):
                break
            sleep_ms(20)
            continue

        data += part

        if header is None and b"\r\n\r\n" in data:
            header, body = data.split(b"\r\n\r\n", 1)
            header_lines = header.split(b"\r\n")

            if not sent_continue:
                for line in header_lines:
                    lower_line = line.lower()
                    if lower_line.startswith(b"expect:") and b"100-continue" in lower_line:
                        try:
                            try:
                                client.setblocking(True)
                            except Exception:
                                pass
                            client.send(b"HTTP/1.1 100 Continue\r\n\r\n")
                            try:
                                client.setblocking(False)
                            except Exception:
                                pass
                        except Exception as exc:
                            print("Failed to send 100-continue:", exc)
                        sent_continue = True
                        break

            for line in header_lines:
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_len = int(line.split(b":", 1)[1].strip())
                    except Exception:
                        content_len = 0
                    break

            if content_len is None:
                break

        elif header is not None and content_len is not None:
            body = data.split(b"\r\n\r\n", 1)[1]

    try:
        client.setblocking(True)
    except Exception:
        pass

    return data

# --- configuration portal with non-blocking accept + recv ---
def start_config_portal(existing_config=None):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:
        ap.config(essid=AP_SSID, password=AP_PASSWORD, channel=AP_CHANNEL)
    except Exception:
        # older ports may not accept channel/psk combos, try simpler config
        ap.config(essid=AP_SSID, password=AP_PASSWORD)

    print("Access point active on SSID:", AP_SSID)
    try:
        print("AP IP:", ap.ifconfig()[0])
    except Exception:
        pass

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    sock = socket.socket()
    # allow quick reuse on some ports
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    sock.bind(addr)
    sock.listen(1)
    # set non-blocking so accept() won't block indefinitely
    sock.setblocking(False)
    print("HTTP configuration portal listening on port 80 (non-blocking)")

    stored_config = existing_config or {}

    try:
        while True:
            try:
                client, remote_addr = sock.accept()
            except OSError:
                # no client waiting; yield to REPL and continue
                sleep_ms(30)
                continue

            print("Client connected from", remote_addr)
            try:
                # read request in a non-blocking manner with a short timeout
                raw = recv_request_nonblocking(client, timeout_ms=3000)
                if not raw:
                    # nothing received within timeout or client closed
                    try:
                        client.close()
                    except Exception:
                        pass
                    continue

                # split header/body (safe even if no body)
                try:
                    header, body = raw.split(b"\r\n\r\n", 1)
                except ValueError:
                    header = raw
                    body = b""

                # get method safely
                parts = header.split(b" ", 2)
                method = parts[0] if parts else b"GET"

                if method == b"POST":
                    # decode body as percent-encoded form data
                    body_str = body.decode("utf-8", "ignore")
                    params = parse_post_data(body_str)
                    print("Received configuration:", params)

                    new_config = {
                        "wifi": {
                            "ssid": params.get("wifi_ssid", ""),
                            "password": params.get("wifi_password", "")
                        },
                        "broker": {
                            "host": params.get("broker_host", ""),
                            "port": int(params.get("broker_port", "1883") or 1883),
                            "username": params.get("broker_login", ""),
                            "password": params.get("broker_password", "")
                        }
                    }

                    if not new_config["wifi"]["ssid"] or not new_config["broker"]["host"]:
                        body_html = render_form(new_config, message="Wi-Fi SSID and Broker Host are required.")
                        send_response(client, body_html)
                        continue

                    if save_config(new_config):
                        stored_config = new_config
                        body_html = render_form(new_config, message="Configuration saved! Device will reboot shortly.")
                        send_response(client, body_html)

                        # attempt to connect (non-fatal if it fails)
                        try:
                            connect_to_wifi(new_config.get("wifi"))
                        except Exception as exc:
                            print("Wi-Fi connection after saving failed:", exc)

                        # small delay then restart
                        sleep(1)
                        print("Restarting device to apply configuration...")
                        machine.reset()
                    else:
                        body_html = render_form(new_config, message="Failed to save configuration. Please try again.")
                        send_response(client, body_html)

                else:
                    body_html = render_form(stored_config)
                    send_response(client, body_html)

            except Exception as exc:
                # keep the portal up if a client or parsing error happens
                print("Error while serving client:", exc)
                try:
                    client.close()
                except Exception:
                    pass
                continue

    except KeyboardInterrupt:
        # allow user to break to REPL on Ctrl-C
        print("Configuration portal interrupted by user (KeyboardInterrupt). Shutting down portal.")
    finally:
        try:
            sock.close()
        except Exception:
            pass
        # optionally deactivate AP if you want REPL to reclaim network
        try:
            ap.active(False)
        except Exception:
            pass

# --- main unchanged except we call portal ---
def main():
    config = load_config()
    ble = bluetooth.BLE()
    ble.active(True)
    print("BLE active:", ble.active())

    if config and connect_to_wifi(config.get("wifi")):
        print("Boot configuration succeeded. Broker details available for publisher.")
        return

    print("Starting configuration access point...")
    start_config_portal(config)


if __name__ == "__main__":
    main()
