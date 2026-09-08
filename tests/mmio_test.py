"""
Тест MMIO механизма + вывод тестового сообщения
Проверяет:
1. MMIO регионы и маппинги
2. Запись тестового сообщения через видеопамять
3. Состояние системы
"""

# =============================================
# ЧАСТЬ 1: Информация о MMIO
# =============================================
bus = api.system.bus

print("=" * 60)
print("MMIO МЕХАНИЗМ — СТАТУС")
print("=" * 60)

print(f"\n📊 Статистика:")
print(f"   MMIO регионов: {len(bus._mmio_regions)}")
print(f"   MMIO маппингов: {len(bus._mmio_index)}")

if bus._mmio_regions:
    print(f"\n📋 Список MMIO регионов:")
    for i, region in enumerate(bus._mmio_regions, 1):
        print(f"\n   [{i}] Регион '{region.name}':")
        print(f"       Устройство: {region._device_name}")
        print(f"       Маппингов: {len(region.mappings)}")
        
        # Показываем первые 5 маппингов
        for j, (addr, port) in enumerate(region.mappings[:5], 1):
            print(f"       {j}. 0x{addr:04X} → порт 0x{port:02X}")
        
        if len(region.mappings) > 5:
            print(f"       ... и ещё {len(region.mappings) - 5} маппингов")

# =============================================
# ЧАСТЬ 2: Тестовое сообщение
# =============================================
print("\n" + "=" * 60)
print("ТЕСТОВОЕ СООБЩЕНИЕ")
print("=" * 60)

# Ищем устройство 8275 (Радио-86РК)
dev = None
for d in api.system.devices.values():
    if type(d).__name__ == 'I8275':
        dev = d
        break

if dev is None:
    print("❌ Устройство 8275 не найдено!")
else:
    print(f"\n✅ Устройство: {dev.name}")
    print(f"   Базовый порт: 0x{dev.base_port:02X}")
    print(f"   Адрес видеопамяти: 0x{dev.display_buffer_addr:04X}")
    print(f"   Размер экрана: {dev.chars_per_line}×{dev.lines_per_screen}")
    
    # Включаем отображение
    dev.display_enabled = True
    
    # Тестовое сообщение
    test_message = "MMIO TEST OK!"
    print(f"\n📝 Сообщение: '{test_message}'")
    
    # Записываем в видеопамять
    addr = dev.display_buffer_addr
    for i, ch in enumerate(test_message):
        code = ord(ch)
        bus.write(addr + i * 2, code)      # Символ
        bus.write(addr + i * 2 + 1, 0x08)  # Атрибут: яркость
    
    # Заполняем остаток пробелами
    total = dev.chars_per_line * dev.lines_per_screen
    for i in range(len(test_message), total):
        bus.write(addr + i * 2, 0x20)      # Пробел
        bus.write(addr + i * 2 + 1, 0x00)
    
    # Запускаем обновление через DMA
    dev._load_display_buffer()
    
    print(f"\n✅ Записано {len(test_message)} символов")
    print(f"   Буфер обновлён: {len(dev.display_buffer)} позиций")
    
    # Проверяем, что сообщение записалось корректно
    read_back = []
    for i in range(len(test_message)):
        idx = i
        if idx in dev.display_buffer:
            char, attr = dev.display_buffer[idx]
            read_back.append(chr(char) if 32 <= char <= 126 else '?')
        else:
            read_back.append(' ')
    
    read_message = ''.join(read_back)
    print(f"\n🔍 Проверка:")
    print(f"   Записано:  '{test_message}'")
    print(f"   Прочитано: '{read_message}'")
    
    if test_message == read_message:
        print(f"   ✅ Сообщения совпадают!")
    else:
        print(f"   ⚠️  Сообщения различаются")

# =============================================
# ЧАСТЬ 3: Итог
# =============================================
print("\n" + "=" * 60)
print("ИТОГ")
print("=" * 60)

if bus._mmio_index:
    print("\n✅ MMIO механизм работает")
    print(f"   Активных маппингов: {len(bus._mmio_index)}")
    
    # Показываем первые 3 адреса из индекса
    print(f"\n   Примеры маппингов:")
    for i, (addr, (device, port)) in enumerate(list(bus._mmio_index.items())[:3], 1):
        print(f"   {i}. Адрес 0x{addr:04X} → {device.name} порт 0x{port:02X}")
else:
    print("\n⚠️  MMIO индекс пуст — маппинги не настроены")

print(f"\n📺 Откройте окно устройства из Диспетчера")
print("=" * 60)