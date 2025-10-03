# show_info.py — печатает имя/информацию платы и MAC-адрес(а)
import network
import os
import time

def mac_to_str(mac_bytes):
    try:
        return ':'.join('{:02X}'.format(b) for b in mac_bytes)
    except Exception:
        # fallback: try decode hex
        try:
            import ubinascii
            h = ubinascii.hexlify(mac_bytes).decode('utf-8')
            return ':'.join(h[i:i+2].upper() for i in range(0, len(h), 2))
        except Exception:
            return str(mac_bytes)

print("=== Device info ===")
try:
    u = os.uname()
    # os.uname() fields may vary; show all
    print("sysname:", getattr(u, "sysname", u[0]))
    print("nodename:", getattr(u, "nodename", u[1]))
    print("release:", getattr(u, "release", u[2]))
    print("version:", getattr(u, "version", u[3]))
    print("machine:", getattr(u, "machine", u[4]))
except Exception as e:
    print("os.uname() not available:", e)

# STA MAC
try:
    sta = network.WLAN(network.STA_IF)
    # ensure interface exists; do not force-activate network if you don't want
    if not sta.active():
        sta.active(True)
        # short wait for hw to initialize
        time.sleep(0.1)
    mac_sta = sta.config('mac')
    print("MAC (STA):", mac_to_str(mac_sta))
    if sta.isconnected():
        print("IP (STA):", sta.ifconfig()[0])
    else:
        print("IP (STA): not connected")
except Exception as e:
    print("STA MAC read error:", e)

# AP MAC (only if interface present)
try:
    ap = network.WLAN(network.AP_IF)
    if ap.active():
        mac_ap = ap.config('mac')
        print("MAC (AP):", mac_to_str(mac_ap))
        print("IP (AP):", ap.ifconfig()[0])
    else:
        print("AP interface inactive (no AP MAC shown)")
except Exception as e:
    print("AP MAC read error:", e)

print("===================")
