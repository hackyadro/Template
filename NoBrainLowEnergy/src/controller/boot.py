import bluetooth
import machine


ble = bluetooth.BLE()
ble.active(True)
print("BLE active:", ble.active())

print("boot.py done")
