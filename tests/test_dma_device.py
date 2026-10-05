"""Тест DMA память↔устройство (итерация 10.2 — дополнение)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
from modules.io import I8257

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: Память → устройство (режим WRITE)
# =============================================
print("\nТест 1: Память → устройство")
print("-" * 50)

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)

dma = I8257(base_port=0x00, name="DMA-0")
dma.set_memory_bus(bus)

# Записываем данные в память (источник)
test_data = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4]
for i, byte in enumerate(test_data):
    bus.write(0x1000 + i, byte)

# Программируем канал 0: адрес 0x1000, счётчик 5, режим WRITE
dma.io_write(0x0C, 0x00)  # Сброс Flip-Flop
dma.io_write(0x00, 0x00)  # Адрес канала 0, младший байт
dma.io_write(0x00, 0x10)  # Адрес канала 0, старший байт
dma.io_write(0x0C, 0x00)  # Сброс Flip-Flop
dma.io_write(0x01, 0x05)  # Счётчик канала 0, младший байт
dma.io_write(0x01, 0x00)  # Счётчик канала 0, старший байт

# Режим канала 0: WRITE (память → устройство)
dma.channels[0]["mode"] = I8257.MODE_WRITE

# Снимаем маску с канала 0
dma.mask_register = 0x0E

# Callback для приёма данных устройством
device_received = []
dma.on_device_write = lambda ch, data: device_received.append(data)

# Запуск
dma.request_dma(0)
check("HOLD активен", dma.hold_active, True)
check("Канал 0 активен", dma.channels[0]["enabled"], True)

# Выполняем передачу
dma.tick(5)

check("Передано 5 байт", len(device_received), 5)
check("Данные верны", device_received, test_data)

# =============================================
# ТЕСТ 2: Устройство → память (режим READ)
# =============================================
print("\nТест 2: Устройство → память")
print("-" * 50)

dma2 = I8257(base_port=0x00, name="DMA-1")  # ← ИЗМЕНЕНО: было 0x10
dma2.set_memory_bus(bus)

dma2.io_write(0x0C, 0x00)  # Сброс Flip-Flop
dma2.io_write(0x02, 0x00)  # Адрес канала 1, младший байт
dma2.io_write(0x02, 0x20)  # Адрес канала 1, старший байт
dma2.io_write(0x0C, 0x00)  # Сброс Flip-Flop
dma2.io_write(0x03, 0x03)  # Счётчик канала 1, младший байт
dma2.io_write(0x03, 0x00)  # Счётчик канала 1, старший байт

# Режим канала 1: READ (устройство → память)
dma2.channels[1]["mode"] = I8257.MODE_READ

# Снимаем маску с канала 1
dma2.mask_register = 0x0D

# Callback для предоставления данных от устройства
device_data = [0xB0, 0xB1, 0xB2]
read_index = [0]

def read_callback(ch):
    idx = read_index[0]
    read_index[0] += 1
    return device_data[idx] if idx < len(device_data) else 0xFF

dma2.on_device_read = read_callback

# Запуск
dma2.request_dma(1)
check("HOLD активен", dma2.hold_active, True)

# Выполняем передачу
dma2.tick(3)

check("Память 0x2000", bus.read(0x2000), 0xB0)
check("Память 0x2001", bus.read(0x2001), 0xB1)
check("Память 0x2002", bus.read(0x2002), 0xB2)

# =============================================
# ТЕСТ 3: Автоинкремент адреса
# =============================================
print("\nТест 3: Автоинкремент адреса")
print("-" * 50)

dma3 = I8257(base_port=0x00, name="DMA-2")
dma3.set_memory_bus(bus)

# Записываем данные в память
for i in range(8):
    bus.write(0x3000 + i, 0xC0 + i)

# Программируем канал 0
dma3.channels[0]["addr"] = 0x3000
dma3.channels[0]["count"] = 8
dma3.channels[0]["mode"] = I8257.MODE_WRITE
dma3.mask_register = 0x0E

device_received3 = []
dma3.on_device_write = lambda ch, data: device_received3.append(data)

dma3.request_dma(0)
dma3.tick(8)

check("Передано 8 байт", len(device_received3), 8)
check("Данные последовательны", device_received3, [0xC0 + i for i in range(8)])

# =============================================
# ТЕСТ 4: Завершение передачи и освобождение шины
# =============================================
print("\nТест 4: Завершение передачи")
print("-" * 50)

transfer_complete = []
dma3.on_transfer_complete = lambda ch: transfer_complete.append(ch)

dma3.channels[0]["addr"] = 0x3000
dma3.channels[0]["count"] = 2
dma3.channels[0]["mode"] = I8257.MODE_WRITE
dma3.mask_register = 0x0E

dma3.request_dma(0)
dma3.tick(3)

check("Передача завершена", len(transfer_complete) > 0, True)
check("HOLD освобождён", dma3.hold_active, False)
check("Канал отключён", dma3.channels[0]["enabled"], False)

# =============================================
# ТЕСТ 5: Маска канала блокирует запрос
# =============================================
print("\nТест 5: Маска канала")
print("-" * 50)

dma4 = I8257(base_port=0x00, name="DMA-2")
dma4.set_memory_bus(bus)

dma4.channels[0]["addr"] = 0x4000
dma4.channels[0]["count"] = 4
dma4.channels[0]["mode"] = I8257.MODE_WRITE
dma4.mask_register = 0x0F  # Все каналы замаскированы

dma4.request_dma(0)
check("Запрос заблокирован маской", dma4.hold_active, False)
check("Канал не активен", dma4.channels[0]["enabled"], False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ПАМЯТЬ↔УСТРОЙСТВО ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10.2 ПОЛНОСТЬЮ ЗАВЕРШЕНА!")
    print("    Покрыты все три режима:")
    print("    • Память ↔ Память (8237)")
    print("    • Память → Устройство (8257)")
    print("    • Устройство → Память (8257)")
    print("    Следующий шаг: 10.3 — WAIT-сигналы")
    print("    (AM9511, CF IDE → CPU)")
else:
    print(" ❌ Есть проваленные тесты.")
