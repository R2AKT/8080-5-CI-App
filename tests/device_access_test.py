"""Проверка регистрации портов после правки"""
bus = api.system.bus

print(f"📋 Всего портов в io_devices: {len(bus.io_devices)}")
print(f"\n📋 Карта портов:")
for port in sorted(bus.io_devices.keys()):
    dev = bus.io_devices[port]
    print(f"   порт 0x{port:02X} -> {dev.name} ({type(dev).__name__})")

# Проверка работы через прямой доступ
ppi = api.system.devices.get('PPI')
if ppi:
    ppi.reset()
    base = ppi.base_port
    # Запись управляющего слова
    bus.io_write(base + 3, 0x80)
    print(f"\n{'✅' if ppi.control == 0x80 else '❌'} Запись control через порт 0x{base+3:02X}: 0x{ppi.control:02X}")
    # Запись в порт A
    bus.io_write(base + 0, 0xA5)
    print(f"{'✅' if ppi.port_a == 0xA5 else '❌'} Запись port_a через порт 0x{base:02X}: 0x{ppi.port_a:02X}")
    # Чтение порта A
    val = bus.io_read(base + 0)
    print(f"{'✅' if val == 0xA5 else '❌'} Чтение port_a через порт 0x{base:02X}: 0x{val:02X}")