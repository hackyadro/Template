# ble_mqtt_beacons_fixed.py  (MicroPython для ESP32-S3)
import network
import time
import ujson as json
import ubinascii
from umqtt.simple import MQTTClient
try:
    import bluetooth
    BLE_MODULE = 'bluetooth'
except ImportError:
    from ubluetooth import BLE as bluetooth_BLE
    BLE_MODULE = 'ubluetooth'
    print("Используется ubluetooth модуль")

# --- Настройки (замени) ---
WIFI_SSID = "realme"
WIFI_PASS = "123456789"
MQTT_BROKER = "193.106.150.201"
MQTT_PORT = 1883
MQTT_CLIENT_ID = b"esp32-s3-ble"
MQTT_TOPIC = b"beacons/di	scovered"
SCAN_DURATION_MS = 10000  # 10 секунд

# --- WiFi подключение ---
def wifi_connect():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    if not wifi.isconnected():
        print("Подключаюсь к WiFi...")
        wifi.connect(WIFI_SSID, WIFI_PASS)
        timeout = 20
        while not wifi.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1
        print()
    if wifi.isconnected():
        print("WiFi подключен:", wifi.ifconfig())
        return wifi
    else:
        print("WiFi не подключился!")
        return None

# --- MQTT helpers ---
def mqtt_connect():
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.connect()
        print("MQTT подключен к", MQTT_BROKER)
        return client
    except Exception as e:
        print("Ошибка MQTT подключения:", e)
        return None

def mqtt_publish(client, topic, payload):
    if not client:
        return None
    try:
        client.publish(topic, payload)
        return client
    except Exception as e:
        print("Ошибка MQTT publish:", e)
        try:
            client.disconnect()
        except:
            pass
        # попытка переподключиться
        try:
            client = mqtt_connect()
            if client:
                client.publish(topic, payload)
        except Exception as e2:
            print("Повторный publish не удался:", e2)
    return client

# --- Разбор реклам-данных ---
def adv_parse(advertising_bytes):
    result = {"local_name": None, "manuf_data": None, "service_data": []}
    i = 0
    b = advertising_bytes
    while i < len(b) - 1:
        length = b[i]
        if length == 0 or i + length >= len(b):
            break
        ad_type = b[i + 1]
        data = b[i + 2 : i + 1 + length]
        
        if ad_type in (0x08, 0x09):  # Shortened or Complete Local Name
            try:
                result["local_name"] = data.decode('utf-8', 'ignore')
            except:
                pass
        elif ad_type == 0xFF:  # Manufacturer Specific Data
            result["manuf_data"] = data
        elif ad_type == 0x16:  # Service Data - 16-bit UUID
            if len(data) >= 2:
                uuid16 = data[0:2]
                svc = data[2:]
                result["service_data"].append((uuid16, svc))
        
        i += 1 + length
    return result

def parse_ibeacon(manuf):
    if manuf and len(manuf) >= 23:
        # Apple Company ID (0x004C) и iBeacon type (0x0215)
        if manuf[0:2] == b'\x4c\x00' and manuf[2:4] == b'\x02\x15':
            uuid = ubinascii.hexlify(manuf[4:20]).decode().upper()
            uuid = (uuid[0:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" +
                    uuid[16:20] + "-" + uuid[20:32])
            major = int.from_bytes(manuf[20:22], 'big')
            minor = int.from_bytes(manuf[22:24], 'big')
            tx = int.from_bytes(manuf[24:25], 'big', signed=True) if len(manuf) > 24 else None
            return {"type": "iBeacon", "uuid": uuid, "major": major, "minor": minor, "tx": tx}
    return None

def parse_eddystone(service_tuple):
    uuid16, svc = service_tuple
    # Eddystone UUID: 0xFEAA
    if uuid16 == b'\xaa\xfe':
        if len(svc) >= 1:
            frame = svc[0]
            frame_types = {0x00: "UID", 0x10: "URL", 0x20: "TLM", 0x30: "EID"}
            return {
                "type": "Eddystone",
                "frame_type": frame_types.get(frame, f"0x{frame:02x}"),
                "raw": ubinascii.hexlify(svc).decode()
            }
    return None

# --- BLE setup ---
print("\n=== Инициализация BLE ===")
print(f"Используется модуль: {BLE_MODULE}")

try:
    if BLE_MODULE == 'bluetooth':
        ble = bluetooth.BLE()
        IRQ_SCAN_RESULT = 5  # bluetooth.IRQ_SCAN_RESULT
        IRQ_SCAN_DONE = 6    # bluetooth.IRQ_SCAN_DONE
    else:
        ble = bluetooth_BLE()
        IRQ_SCAN_RESULT = 1  # const(1)
        IRQ_SCAN_DONE = 2    # const(2)
    
    ble.active(False)
    time.sleep_ms(100)
    ble.active(True)
    time.sleep_ms(100)
    
    print(f"BLE активирован: {ble.active()}")
    print(f"Конфигурация BLE: {ble.config('gap_name') if hasattr(ble, 'config') else 'N/A'}")
    
except Exception as e:
    print("ОШИБКА активации BLE:", e)
    import sys
    sys.print_exception(e)
    raise

scan_results = []
scan_in_progress = False
irq_call_count = 0

def bt_irq(event, data):
    global scan_in_progress, irq_call_count
    irq_call_count += 1
    
    if event == IRQ_SCAN_RESULT:
        # data: (addr_type, addr, adv_type, rssi, adv_data)
        addr_type, addr, adv_type, rssi, adv_data = data
        
        # Конвертируем адрес
        if isinstance(addr, bytes):
            addr_hex = ubinascii.hexlify(addr).decode().upper()
        else:
            addr_hex = ''.join([f'{b:02X}' for b in addr])
        
        addr_formatted = ':'.join([addr_hex[i:i+2] for i in range(0, len(addr_hex), 2)])
        
        # Конвертируем adv_data если нужно
        if not isinstance(adv_data, bytes):
            adv_data = bytes(adv_data)
        
        scan_results.append((addr_formatted, rssi, adv_data, addr_type, adv_type))
        
        # Живой вывод каждого 10-го устройства
        if len(scan_results) % 10 == 0:
            print(f"  ...найдено {len(scan_results)} устройств")
        
    elif event == IRQ_SCAN_DONE:
        scan_in_progress = False
        print(f"✓ Сканирование завершено | Всего IRQ вызовов: {irq_call_count} | Найдено устройств: {len(scan_results)}")

ble.irq(bt_irq)

# --- Основной цикл ---
def main():
    global scan_in_progress, irq_call_count
    
    # Подключаем WiFi и MQTT
    wifi = wifi_connect()
    if not wifi:
        print("Не могу продолжить без WiFi")
        return
    
    client = mqtt_connect()
    
    print("\n" + "="*50)
    print("Запуск мониторинга BLE маяков")
    print(f"Модуль BLE: {BLE_MODULE}")
    print(f"IRQ_SCAN_RESULT = {IRQ_SCAN_RESULT}")
    print(f"IRQ_SCAN_DONE = {IRQ_SCAN_DONE}")
    print("="*50 + "\n")
    
    # Тестовое сканирование
    print(">>> ТЕСТ: Запуск короткого сканирования (2 сек)")
    scan_results.clear()
    scan_in_progress = True
    irq_call_count = 0
    
    try:
        ble.gap_scan(2000, 30000, 30000)
        time.sleep(2.5)
        print(f"Тест завершен: найдено {len(scan_results)} устройств, IRQ вызовов: {irq_call_count}")
        
        if irq_call_count == 0:
            print("\n!!! IRQ callback НЕ ВЫЗЫВАЕТСЯ!")
            print("Возможные причины:")
            print("1. BLE не инициализирован правильно")
            print("2. Аппаратная проблема с BLE чипом")
            print("3. Конфликт с другими модулями")
            print("\nПопытка переинициализации...")
            
            ble.active(False)
            time.sleep(1)
            ble.active(True)
            time.sleep(1)
            ble.irq(bt_irq)
            time.sleep(0.5)
            
            # Повторный тест
            scan_results.clear()
            scan_in_progress = True
            irq_call_count = 0
            ble.gap_scan(2000, 30000, 30000)
            time.sleep(2.5)
            print(f"Повторный тест: найдено {len(scan_results)} устройств, IRQ вызовов: {irq_call_count}")
            
            if irq_call_count == 0:
                print("\n!!! КРИТИЧЕСКАЯ ОШИБКА: BLE не работает")
                print("Необходимо:")
                print("- Проверить прошивку MicroPython")
                print("- Проверить поддержку BLE в вашей версии ESP32-S3")
                print("- Попробовать другую плату")
                return
    
    except Exception as e:
        print(f"Ошибка тестового сканирования: {e}")
        import sys
        sys.print_exception(e)
        return
    
    print("\n>>> Начинаю основной цикл мониторинга\n")
    
    cycle = 0
    
    while True:
        cycle += 1
        print(f"\n--- Цикл #{cycle} ---")
        
        # Очищаем старые результаты
        scan_results.clear()
        scan_in_progress = True
        irq_call_count = 0
        
        # Запускаем сканирование
        try:
            print(f"Запуск BLE сканирования ({SCAN_DURATION_MS}мс)...")
            
            # Пробуем разные варианты вызова
            if BLE_MODULE == 'bluetooth':
                ble.gap_scan(SCAN_DURATION_MS, 30000, 30000, True)  # active scan
            else:
                ble.gap_scan(SCAN_DURATION_MS, 30000, 30000)
                
        except Exception as e:
            print(f"ОШИБКА gap_scan: {e}")
            import sys
            sys.print_exception(e)
            print("Перезапуск BLE...")
            try:
                ble.active(False)
                time.sleep_ms(200)
                ble.active(True)
                ble.irq(bt_irq)
                time.sleep(1)
            except Exception as e2:
                print(f"Ошибка перезапуска BLE: {e2}")
            continue
        
        # Ждём завершения с таймаутом
        start_time = time.ticks_ms()
        timeout_ms = SCAN_DURATION_MS + 3000
        
        while scan_in_progress:
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
                print("! Таймаут сканирования")
                try:
                    ble.gap_scan(None)  # stop scan
                except:
                    pass
                scan_in_progress = False
                break
            time.sleep_ms(100)
        
        # Обработка результатов
        if irq_call_count == 0:
            print("! IRQ НЕ вызывался - устройства не найдены или проблема с BLE")
        
        print(f"Обработка {len(scan_results)} устройств...")
        
        beacons = {}
        processed_count = 0
        
        for item in scan_results:
            addr_formatted, rssi, adv = item[0], item[1], item[2]
            addr_type = item[3] if len(item) > 3 else 0
            adv_type = item[4] if len(item) > 4 else 0
            
            processed_count += 1
            
            # Парсим advertising data
            parsed = adv_parse(adv)
            
            info = {
                "addr": addr_formatted,
                "rssi": int(rssi),
                "name": parsed.get("local_name"),
            }
            
            # Проверяем на iBeacon
            if parsed.get("manuf_data"):
                ib = parse_ibeacon(parsed["manuf_data"])
                if ib:
                    info.update(ib)
                    print(f"  iBeacon: {addr_formatted} | RSSI: {rssi} | UUID: {ib['uuid'][:8]}...")
                else:
                    # Неизвестный производитель
                    info["manuf_hex"] = ubinascii.hexlify(parsed["manuf_data"]).decode()
            
            # Проверяем на Eddystone
            for svc in parsed.get("service_data", []):
                ed = parse_eddystone(svc)
                if ed:
                    info.setdefault("services", []).append(ed)
                    print(f"  Eddystone: {addr_formatted} | RSSI: {rssi} | Type: {ed.get('frame_type')}")
            
            # Логируем все устройства
            if not info.get("type") and not info.get("services"):
                device_type = "Unknown"
                if info.get("name"):
                    device_type = f"Named: {info['name']}"
                print(f"  {device_type}: {addr_formatted} | RSSI: {rssi}")
            
            # Добавляем raw data для отладки
            info["raw_adv"] = ubinascii.hexlify(adv).decode()
            
            # Сохраняем лучший результат для каждого адреса
            if addr_formatted not in beacons or info["rssi"] > beacons[addr_formatted]["rssi"]:
                beacons[addr_formatted] = info
        
        # Отправка в MQTT
        payload_list = list(beacons.values())
        
        if payload_list:
            payload_dict = {
                "ts": time.time(),
                "count": len(payload_list),
                "beacons": payload_list
            }
            payload_json = json.dumps(payload_dict)
            
            print(f"\n→ Отправка {len(payload_list)} устройств в MQTT")
            client = mqtt_publish(client, MQTT_TOPIC, payload_json.encode())
        else:
            print("\n! Ни одного устройства не найдено")
        
        # Пауза перед следующим циклом
        print(f"Пауза 3 секунды...\n")
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nОстановка программы...")
        try:
            ble.gap_scan(None)
            ble.active(False)
        except:
            pass
    except Exception as e:
        print(f"\n\nКритическая ошибка: {e}")
        import sys
        sys.print_exception(e)
