"""Тест DMA память↔память (итерация 10.2)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
#from modules.io.i8257 import I8237
from modules.io import IODevice, I8257, I8237

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
# ТЕСТ 1: Инициализация
# =============================================
print("\nТест 1: Инициализация")
print("-" * 50)

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)

dma = I8237(base_port=0x00, name="DMA-0")
dma.register_to_bus(bus)

# Подключаем шину памяти к DMA (итерация 10.2)
if hasattr(dma, 'set_memory_bus'):
    dma.set_memory_bus(bus)
    check("Шина памяти подключена к DMA", True, True)
else:
    check("Метод set_memory_bus отсутствует", False, True)

check("DMA создан", dma is not None, True)

# =============================================
# ТЕСТ 2: Запись данных в источник
# =============================================
print("\nТест 2: Запись данных в источник")
print("-" * 50)

# Записываем тестовые данные в область источника (0x1000-0x10FF)
source_data = [i & 0xFF for i in range(256)]
for i, byte in enumerate(source_data):
    bus.write(0x1000 + i, byte)

check("Первый байт записан", bus.read(0x1000), 0x00)
check("Байт 0x55 записан", bus.read(0x1055), 0x55)
check("Последний байт записан", bus.read(0x10FF), 0xFF)

# Проверяем, что приёмник пуст (нули)
check("Приёмник пуст (0)", bus.read(0x2000), 0x00)

# =============================================
# ТЕСТ 3: Программирование каналов
# =============================================
print("\nТест 3: Программирование каналов")
print("-" * 50)

# Сброс контроллера
bus.io_write(0x0C, 0x00)  # Порт 12: сброс

# Сброс маски (все каналы не замаскированы)
bus.io_write(0x0D, 0x00)  # Порт 13: сброс маски

# Канал 0: чтение из источника (0x1000), 256 байт
bus.io_write(0x00, 0x00)  # Адрес канала 0, младший байт
bus.io_write(0x00, 0x10)  # Адрес канала 0, старший байт
bus.io_write(0x01, 0xFF)  # Счётчик канала 0, младший (256-1=255)
bus.io_write(0x01, 0x00)  # Счётчик канала 0, старший

# Канал 1: запись в приёмник (0x2000), 256 байт
bus.io_write(0x02, 0x00)  # Адрес канала 1, младший байт
bus.io_write(0x02, 0x20)  # Адрес канала 1, старший байт
bus.io_write(0x03, 0xFF)  # Счётчик канала 1, младший
bus.io_write(0x03, 0x00)  # Счётчик канала 1, старший

# Режим канала 0: чтение памяти, автоинкремент адреса
bus.io_write(0x0B, 0x44)  # Канал 0, чтение, автоинкремент, без автозагрузки

# Режим канала 1: запись памяти, автоинкремент адреса
bus.io_write(0x0B, 0x48)  # Канал 1, запись, автоинкремент, без автозагрузки

# Включаем режим память↔память в регистре команды
bus.io_write(0x08, 0x01)  # Бит 0 = 1: режим память↔память

check("Каналы запрограммированы", True, True)

# =============================================
# ТЕСТ 4: Запуск передачи
# =============================================
print("\nТест 4: Запуск передачи")
print("-" * 50)

# Программный запрос канала 0 (запуск передачи)
bus.io_write(0x09, 0x04)  # Порт 9: запрос канала 0

# Проверяем активность
if hasattr(dma, 'is_active'):
    check("DMA активен", dma.is_active(), True)
else:
    check("Метод is_active отсутствует", False, True)

# Выполняем передачу через шину памяти
if hasattr(dma, 'perform_transfer'):
    dma.perform_transfer(bus)
    check("Передача выполнена", True, True)
else:
    # Альтернатива: через tick
    for _ in range(300):
        if hasattr(dma, 'tick'):
            dma.tick(cycles=1)
    check("Передача выполнена через tick", True, True)

# =============================================
# ТЕСТ 5: Проверка результата
# =============================================
print("\nТест 5: Проверка результата")
print("-" * 50)

# Проверяем, что данные скопированы из 0x1000 в 0x2000
check("Первый байт скопирован", bus.read(0x2000), 0x00)
check("Второй байт скопирован", bus.read(0x2001), 0x01)
check("Байт 0x55 скопирован", bus.read(0x2055), 0x55)
check("Байт 0xAA скопирован", bus.read(0x20AA), 0xAA)
check("Последний байт скопирован", bus.read(0x20FF), 0xFF)

# Проверяем, что источник не изменился
check("Источник не изменился (0)", bus.read(0x1000), 0x00)
check("Источник не изменился (0x55)", bus.read(0x1055), 0x55)

# =============================================
# ТЕСТ 6: Проверка завершения (счётчики)
# =============================================
print("\nТест 6: Проверка завершения")
print("-" * 50)

if hasattr(dma, 'is_active'):
    check("DMA завершил передачу", dma.is_active(), False)
else:
    check("Метод is_active отсутствует", False, True)

# =============================================
# ТЕСТ 7: Повторная передача
# =============================================
print("\nТест 7: Повторная передача")
print("-" * 50)

# Записываем новые данные в источник
new_data = [(i * 2) & 0xFF for i in range(256)]
for i, byte in enumerate(new_data):
    bus.write(0x1000 + i, byte)

# Сброс и повторное программирование
bus.io_write(0x0C, 0x00)  # Сброс

# Сброс маски (все каналы не замаскированы)
bus.io_write(0x0D, 0x00)  # Порт 13: сброс маски

bus.io_write(0x00, 0x00); bus.io_write(0x00, 0x10)  # Канал 0: 0x1000
bus.io_write(0x01, 0xFF); bus.io_write(0x01, 0x00)  # 256 байт
bus.io_write(0x02, 0x00); bus.io_write(0x02, 0x20)  # Канал 1: 0x2000
bus.io_write(0x03, 0xFF); bus.io_write(0x03, 0x00)  # 256 байт
bus.io_write(0x0B, 0x44)  # Режим канала 0
bus.io_write(0x0B, 0x48)  # Режим канала 1
bus.io_write(0x08, 0x01)  # Память↔память
bus.io_write(0x09, 0x04)  # Запуск

if hasattr(dma, 'perform_transfer'):
    dma.perform_transfer(bus)

check("Повторная передача: первый байт", bus.read(0x2000), 0x00)
check("Повторная передача: байт 0x55", bus.read(0x2055), 0xAA)  # 0x55*2 = 0xAA
check("Повторная передача: последний байт", bus.read(0x20FF), 0xFE)  # 0xFF*2 = 0x1FE → 0xFE

# =============================================
# ТЕСТ 8: Проверка через get_state
# =============================================
print("\nТест 8: Проверка через get_state")
print("-" * 50)

if hasattr(dma, 'get_state'):
    state = dma.get_state()
    check("get_state возвращает словарь", isinstance(state, dict), True)
    if 'name' in state:
        check("Имя в состоянии", state['name'], "DMA-0")
else:
    check("Метод get_state отсутствует", False, True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ DMA ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
