"""Тест I8257 / I8237 (итерация E4)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
from modules.io import IODevice, I8257, I8237

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}: {actual}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: 8257 — базовая настройка каналов
# =============================================
print("\nТест 1: 8257 — базовая настройка каналов")
print("-" * 50)

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)

dma = I8257(base_port=0x00)
dma.memory_bus = bus

# Настраиваем канал 0: адрес 0x10, счётчик 5, режим WRITE
dma.io_write(0x0C, 0x00)  # ← Сброс Flip-Flop
dma.io_write(0x00, 0x10)  # Адрес канала 0, младший байт

dma.io_write(0x0C, 0x00)  # ← Сброс Flip-Flop
dma.io_write(0x01, 0x05)  # Счётчик канала 0, младший байт

dma.io_write(0x08, 0x01)  # Режим: WRITE для канала 0

check("Адрес канала 0", dma.channels[0]["addr"], 0x10)
check("Счётчик канала 0", dma.channels[0]["count"], 0x05)
check("Режим канала 0", dma.channels[0]["mode"], I8257.MODE_WRITE)

# =============================================
# ТЕСТ 2: 8257 — передача память → устройство
# =============================================
print("\nТест 2: 8257 — передача память → устройство")
print("-" * 50)

# Записываем данные в память
for i in range(5):
    bus.write(0x10 + i, 0xA0 + i)

# Callback для записи в устройство
device_data = []
dma.on_device_write = lambda ch, data: device_data.append(data)

# Снимаем маску с канала 0
dma.mask_register = 0x0E  # Канал 0 не замаскирован

# Запрашиваем ПДП
hold_requested = []
dma.on_hold_request = lambda: hold_requested.append(True)
dma.request_dma(0)

check("HOLD запрошен", len(hold_requested), 1)
check("Канал 0 активен", dma.channels[0]["enabled"], True)

# Выполняем передачу
dma.tick(5)

check("Передано 5 байт", len(device_data), 5)
check("Данные верны", device_data, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4])

# =============================================
# ТЕСТ 3: 8257 — передача устройство → память
# =============================================
print("\nТест 3: 8257 — передача устройство → память")
print("-" * 50)

dma2 = I8257(base_port=0x10)
dma2.memory_bus = bus

# Настраиваем канал 1: адрес 0x20, счётчик 3, режим READ (устройство → память)
dma2.io_write(0x0C, 0x00)  # ← Сброс Flip-Flop
dma2.channels[1]["addr"] = 0x20
dma2.channels[1]["count"] = 3
dma2.channels[1]["mode"] = I8257.MODE_READ
dma2.mask_register = 0x0D  # Канал 1 не замаскирован

# Callback для чтения из устройства
device_read_data = [0xB0, 0xB1, 0xB2]
read_index = [0]
dma2.on_device_read = lambda ch: device_read_data[read_index[0] + 0] if read_index[0] < len(device_read_data) else 0xFF

def read_callback(ch):
    idx = read_index[0]
    read_index[0] += 1
    return device_read_data[idx] if idx < len(device_read_data) else 0xFF

dma2.on_device_read = read_callback

dma2.request_dma(1)
dma2.tick(3)

check("Память 0x20", bus.read(0x20), 0xB0)
check("Память 0x21", bus.read(0x21), 0xB1)
check("Память 0x22", bus.read(0x22), 0xB2)

# =============================================
# ТЕСТ 4: 8237 — память ↔ память
# =============================================
print("\nТест 4: 8237 — память ↔ память")
print("-" * 50)

dma3 = I8237(base_port=0x20)
dma3.memory_bus = bus

# Записываем данные в память источника
for i in range(4):
    bus.write(0x30 + i, 0xC0 + i)

# Настраиваем каналы
dma3.io_write(0x0C, 0x00)  # ← Сброс Flip-Flop
dma3.channels[0]["addr"] = 0x30  # Источник
dma3.channels[1]["addr"] = 0x40  # Приёмник
dma3.mask_register = 0x0C  # Каналы 0 и 1 не замаскированы

# Запрашиваем передачу память → память
dma3.request_mem_to_mem(0, 1, 4)
dma3.tick(4)

check("Память 0x40", bus.read(0x40), 0xC0)
check("Память 0x41", bus.read(0x41), 0xC1)
check("Память 0x42", bus.read(0x42), 0xC2)
check("Память 0x43", bus.read(0x43), 0xC3)

# =============================================
# ТЕСТ 5: 8237 — программный запуск цикла обмена
# =============================================
print("\nТест 5: 8237 — программный запуск цикла обмена")
print("-" * 50)

dma4 = I8237(base_port=0x30)
dma4.memory_bus = bus

# Записываем данные в память
for i in range(3):
    bus.write(0x50 + i, 0xD0 + i)

# Настраиваем канал 2: адрес 0x50, счётчик 3, режим WRITE
dma4.io_write(0x0C, 0x00)  # ← Сброс Flip-Flop
dma4.channels[2]["addr"] = 0x50
dma4.channels[2]["count"] = 3
dma4.channels[2]["mode"] = I8257.MODE_WRITE
dma4.mask_register = 0x0B  # Канал 2 не замаскирован

# Callback для записи в устройство
device_data2 = []
dma4.on_device_write = lambda ch, data: device_data2.append(data)

# Программный запуск
dma4.software_trigger(2)
dma4.tick(3)

check("Программный запуск работает", len(device_data2), 3)
check("Данные верны", device_data2, [0xD0, 0xD1, 0xD2])

# =============================================
# ТЕСТ 6: Наследование
# =============================================
print("\nТест 6: Наследование")
print("-" * 50)

check("I8237 наследует I8257", issubclass(I8237, I8257), True)
check("I8257 наследует IODevice", issubclass(I8257, IODevice), True)

# =============================================
# ТЕСТ 7: Сброс
# =============================================
print("\nТест 7: Сброс")
print("-" * 50)

dma4.reset()
check("Каналы сброшены", dma4.channels[0]["enabled"], False)
check("Маска сброшена", dma4.mask_register, 0x0F)
check("HOLD сброшен", dma4.hold_active, False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8257/I8237 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
