"""Проверка инверсии диапазона портов 8255 (Микро-80)"""
bus = api.system.bus
ppi = api.system.devices.get('PPI')

if ppi is None:
    print("❌ PPI не найден!")
    raise SystemExit

BASE = ppi.base_port
ppi.reset()

# 1. Проверяем карту инверсии
print(f"📋 _port_invert_map: {len(bus._port_invert_map)} записей")
for port in sorted(bus._port_invert_map.keys()):
    print(f"   порт 0x{port:02X} -> устройство получает 0x{bus._port_invert_map[port]:02X}")

# 2. Проверка записи управляющего слова через порт BASE (должен попасть в Control)
bus.io_write(BASE + 0, 0x80)
r1 = ppi.control == 0x80
print(f"\n{'✅' if r1 else '❌'} Запись в 0x{BASE:02X} -> control=0x{ppi.control:02X} (ожидалось 0x80)")

# 3. Проверка записи данных в порт BASE+3 (должен попасть в Port A)
bus.io_write(BASE + 3, 0xA5)
r2 = ppi.port_a == 0xA5
print(f"{'✅' if r2 else '❌'} Запись в 0x{BASE+3:02X} -> port_a=0x{ppi.port_a:02X} (ожидалось 0xA5)")

# 4. Проверка чтения: записываем в Control, читаем через порт BASE
val = bus.io_read(BASE + 0)
r3 = val == 0x80
print(f"{'✅' if r3 else '❌'} Чтение 0x{BASE:02X} -> 0x{val:02X} (ожидалось 0x80 из Control)")

# 5. Итог
print(f"\n{'='*40}")
if r1 and r2 and r3:
    print("✅ Инверсия диапазона портов работает!")
else:
    print("❌ Инверсия диапазона портов не работает")