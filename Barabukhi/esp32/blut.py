import ubluetooth
import time

# Настройки сканирования
SCAN_TIME = 0.05  # Время одного сканирования (короткое, т.к. опрашиваем часто)
POLL_FREQUENCY_HZ = 10  # Частота опроса BLE (фиксированная 10 Гц)
REPORT_FREQUENCY_HZ = 1  # Частота отправки данных (от 0.1 до 10 Гц)

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
        
        # 0x08 = Shortened Local Name, 0x09 = Complete Local Name
        if ad_type in (0x08, 0x09):
            name_bytes = bytes(adv_data[i + 2 : i + 1 + length])
            try:
                name = name_bytes.decode('utf-8')
                return name if name else None
            except UnicodeDecodeError:
                return None
        
        i += 1 + length
    
    return None

class BLEScanner:
    def __init__(self, poll_freq_hz=10, report_freq_hz=1.0):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.bt_irq)
        self.current_scan_devices = {}
        self.scan_complete = False
        self.scanning_active = False
        
        # Частота опроса (фиксированная 10 Гц)
        self.poll_freq_hz = poll_freq_hz
        self.poll_period = 1.0 / poll_freq_hz
        
        # Валидация частоты отчетов
        if report_freq_hz < 0.1:
            self.report_freq_hz = 0.1
        elif report_freq_hz > 10.0:
            self.report_freq_hz = 10.0
        else:
            self.report_freq_hz = report_freq_hz
            
        self.report_period = 1.0 / self.report_freq_hz  # Период между отправками данных
        
        # Буфер для накопления данных между отправками
        # Структура: {mac: {'name': str, 'rssi_values': [rssi1, rssi2, ...]}}
        self.accumulated_data = {}
        
    def bt_irq(self, event, data):
        if event == 5:  # _IRQ_SCAN_RESULT
            _, addr, _, rssi, adv_data = data
            mac = ':'.join('{:02X}'.format(b) for b in addr)
            
            device_name = decode_name(adv_data)
            
            if device_name and device_name in BEACONS:
                self.current_scan_devices[mac] = {
                    'name': device_name,
                    'rssi': rssi
                }
                
        elif event == 6:  # _IRQ_SCAN_DONE
            self.scan_complete = True
            self.scanning_active = False
    
    def poll_once(self, duration=SCAN_TIME):
        """Выполняет один быстрый опрос BLE (10 Гц)"""
        self.current_scan_devices.clear()
        self.scan_complete = False
        
        # Останавливаем предыдущее сканирование, если оно активно
        if self.scanning_active:
            try:
                self.ble.gap_scan(None)
                time.sleep(0.01)
            except OSError:
                pass
        
        # Запускаем сканирование
        try:
            self.scanning_active = True
            self.ble.gap_scan(int(duration * 1000), 30000, 30000, True)
        except OSError:
            # Если все еще занято, пропускаем этот опрос
            self.scanning_active = False
            return self.current_scan_devices.copy()
        
        # Ждем завершения сканирования
        timeout = duration + 0.5
        start_time = time.time()
        while not self.scan_complete:
            if time.time() - start_time > timeout:
                # Принудительно останавливаем сканирование при таймауте
                try:
                    self.ble.gap_scan(None)
                except OSError:
                    pass
                self.scanning_active = False
                break
            time.sleep(0.01)
        
        return self.current_scan_devices.copy()
    
    def accumulate_data(self, devices):
        """Накапливает RSSI значения для каждого устройства"""
        for mac, info in devices.items():
            if mac not in self.accumulated_data:
                self.accumulated_data[mac] = {
                    'name': info['name'],
                    'rssi_values': []
                }
            self.accumulated_data[mac]['rssi_values'].append(info['rssi'])
    
    def calculate_averages(self):
        """Вычисляет средние значения RSSI для всех устройств"""
        averaged_data = {}
        for mac, info in self.accumulated_data.items():
            if info['rssi_values']:
                avg_rssi = sum(info['rssi_values']) / len(info['rssi_values'])
                averaged_data[mac] = {
                    'name': info['name'],
                    'rssi': round(avg_rssi, 1),
                    'samples': len(info['rssi_values'])
                }
        return averaged_data
    
    def print_results(self, averaged_data, poll_count):
        """Выводит усредненные результаты пакетом"""
        if averaged_data:
            print(f"=== Отчет: {len(averaged_data)} устройств (опросов: {poll_count}) ===")
            # Сортируем по имени beacon'а
            sorted_items = sorted(averaged_data.items(), key=lambda x: x[1]['name'])
            for mac, info in sorted_items:
                print(f"{info['name']};{info['rssi']};{mac};samples={info['samples']}")
            print("=" * 50)
        else:
            print(f"=== Отчет: устройства не найдены (опросов: {poll_count}) ===")
    
    def run_continuous_scan(self):
        """Запускает непрерывное сканирование с опросом 10 Гц и отчетами по заданной частоте"""
        print(f"Частота опроса BLE: {self.poll_freq_hz} Гц")
        print(f"Частота отправки данных: {self.report_freq_hz} Гц")
        print(f"Период накопления данных: {self.report_period:.2f} сек")
        print("-" * 50)
        
        report_count = 0
        last_report_time = time.time()
        poll_count = 0
        
        while True:
            poll_start_time = time.time()
            
            # Выполняем быстрый опрос (10 Гц)
            devices = self.poll_once()
            poll_count += 1
            
            # Накапливаем данные
            self.accumulate_data(devices)
            
            # Проверяем, пора ли отправлять данные
            time_since_report = time.time() - last_report_time
            if time_since_report >= self.report_period:
                report_count += 1
                print(f"\nОтчет #{report_count}")
                
                # Вычисляем средние значения
                averaged_data = self.calculate_averages()
                
                # Выводим результаты
                self.print_results(averaged_data, poll_count)
                
                # Очищаем накопленные данные
                self.accumulated_data.clear()
                last_report_time = time.time()
                poll_count = 0

            # Соблюдаем частоту опроса 10 Гц
            elapsed = time.time() - poll_start_time
            sleep_time = max(0, self.poll_period - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

# Основной код
# Опрос всегда 10 Гц, отправка данных с заданной частотой
scanner = BLEScanner(poll_freq_hz=POLL_FREQUENCY_HZ, report_freq_hz=REPORT_FREQUENCY_HZ)
scanner.run_continuous_scan()