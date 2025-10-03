import bluetooth
from micropython import const
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
import time
import networking
from networking import connect_wifi, connect_mqtt, check_messages, publish_data

# Initialize Bluetooth
ble = bluetooth.BLE()
ble.active(True)

beacon_distance_dict = {}
output_distance = []
scan_finished = False


# Define a callback function for scan results
def bt_irq(event, data):
    global beacon_distance_dict
    global scan_finished
    
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        device_name = parse_ble_advertising_data(bytes(adv_data))
        if (device_name):
            if device_name in beacon_distance_dict:
                beacon_distance_dict[device_name].append(calculate_distance(rssi))
            else:
                beacon_distance_dict[device_name] = [calculate_distance(rssi)]
#                 print(f"Device found: {device_name} ({rssi})")
    elif event == _IRQ_SCAN_DONE:
        for item in sorted(beacon_distance_dict.items()):
            median = calculate_median(item[1])
            mad = calculate_mad(item[1], median) * 1.4826
            threshold = 2
            lower_bound = median - threshold * mad
            upper_bound = median + threshold * mad
            filtered_mad = [dist for dist in item[1] if lower_bound <= dist <= upper_bound]
            
            filtered = [dist for dist in item[1] if abs(dist - median) <= 3.0]
            
            if (len(filtered_mad) != 0):
                output_distance.append({"name": item[0], "distance": sum(filtered_mad) / len(filtered_mad)})
        beacon_distance_dict.clear()
        scan_finished = True
        
        
def parse_ble_advertising_data(data):
    index = 0
    device_name = None
    
    while index < len(data):
        # Читаем длину текущего AD-блока
        length = data[index]
        index += 1
        
        if length == 0:
            break
            
        # Читаем тип AD-блока
        ad_type = data[index]
        index += 1
        
        # Данные AD-блока (длина минус 1 байт типа)
        ad_data = data[index:index + length - 1]
        
        # Проверяем тип блока
        if ad_type == 0x09:  # Complete Local Name
            try:
                device_name = ad_data.decode('utf-8')
            except UnicodeDecodeError:
                device_name = ad_data.hex()
        
        # Переходим к следующему блоку
        index += length - 1
    
    return device_name


def calculate_distance(rssi, tx_power=-45, n=2.0):
    if rssi == 0:
        return -1.0  # Неверное значение
    
    ratio = (tx_power - rssi) / (10 * n)
    distance = 10 ** ratio
    return distance


def calculate_median(data):
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    if n % 2 == 1:
        return sorted_data[n // 2]
    else:
        mid1 = sorted_data[n // 2 - 1]
        mid2 = sorted_data[n // 2]
        return (mid1 + mid2) / 2


def calculate_mad(data_array, median_value):
    absolute_deviations = [abs(x - median_value) for x in data_array]
    return calculate_median(absolute_deviations)


def main():
    global output_distance, scan_finished
    
    if not connect_wifi():
        return
     
    client = connect_mqtt()
    if not client:
        return
    
    # Register the callback
    ble.irq(bt_irq)

    # Start scanning for devices
    while True:
        check_messages(client)
        output_distance.clear()
        scan_finished = False
        print("\n-------------------------------\n")
        ble.gap_scan(networking.scan_duration, 100000, 100000)
        while not scan_finished:
            time.sleep_ms(10)

        publish_data(client, {"beaconReadings": output_distance})
            
            
main()        
