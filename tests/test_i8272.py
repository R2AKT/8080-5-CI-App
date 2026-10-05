"""Тест I8272 FDC (итерация E5)"""
from modules.memory.memory_bus import MemoryBus
from modules.io.i8272 import I8272

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
# ТЕСТ 1: Инициализация и сброс
# =============================================
print("\nТест 1: Инициализация и сброс")
print("-" * 50)

bus = MemoryBus()
fdc = I8272(base_port=0xF0)
fdc.register_to_bus(bus)

check("Состояние IDLE", fdc.state, I8272.STATE_IDLE)
check("Выбран дисковод 0", fdc.selected_drive, 0)
check("4 дисковода", len(fdc.drives), 4)

# =============================================
# ТЕСТ 2: DOR — выбор дисковода
# =============================================
print("\nТест 2: DOR — выбор дисковода")
print("-" * 50)

# Включаем normal mode (бит 2) и выбираем дисковод 1
bus.io_write(0xF0, 0x04 | 0x01)  # DOR = 0x05
check("Выбран дисковод 1", fdc.selected_drive, 1)

# Включаем мотор дисковода 0
bus.io_write(0xF0, 0x04 | 0x00 | 0x10)  # DOR = 0x14
check("Мотор дисковода 0 включён", fdc.drives[0].motor_on, True)

# =============================================
# ТЕСТ 3: Specify
# =============================================
print("\nТест 3: Specify")
print("-" * 50)

# Команда Specify (0x03): SRT=3, HUT=1, HLT=16, ND=1 (PIO)
bus.io_write(0xF2, 0x03)  # Команда
bus.io_write(0xF2, 0x31)  # SRT=3, HUT=1
bus.io_write(0xF2, 0x21)  # HLT=16, ND=1

check("SRT установлен", fdc.srt, 3)
check("HUT установлен", fdc.hut, 1)
check("HLT установлен", fdc.hlt, 16)
check("Non-DMA mode", fdc.nd, 1)
check("Состояние IDLE после Specify", fdc.state, I8272.STATE_IDLE)

# =============================================
# ТЕСТ 4: Sense Drive Status
# =============================================
print("\nТест 4: Sense Drive Status")
print("-" * 50)

# Вставляем диск в дисковод 0
fdc.insert_disk(0)

# Выбираем дисковод 0
bus.io_write(0xF0, 0x04 | 0x00)  # DOR = 0x04

# Команда Sense Drive Status (0x04)
bus.io_write(0xF2, 0x04)  # Команда
bus.io_write(0xF2, 0x00)  # Параметр (дисковод 0)

# Читаем результат
status = bus.io_read(0xF2)
check("Дисковод готов (бит 7=0)", bool(status & 0x80), False)
check("Дорожка 0 (бит 4=1)", bool(status & 0x10), True)

# =============================================
# ТЕСТ 5: Запись и чтение данных (PIO mode)
# =============================================
print("\nТест 5: Запись и чтение данных (PIO mode)")
print("-" * 50)

# Запись данных на диск
# Команда Write Data (0x05)
bus.io_write(0xF2, 0x05)  # Команда
bus.io_write(0xF2, 0x00)  # Параметр 1 (дисковод, головка)
bus.io_write(0xF2, 0x00)  # Цилиндр 0
bus.io_write(0xF2, 0x00)  # Головка 0
bus.io_write(0xF2, 0x01)  # Сектор 1
bus.io_write(0xF2, 0x02)  # Размер сектора: 512 байт (N=2)
bus.io_write(0xF2, 0x12)  # Последний сектор на дорожке
bus.io_write(0xF2, 0x1B)  # GPL
bus.io_write(0xF2, 0xFF)  # DTL

check("Состояние EXECUTION", fdc.state, I8272.STATE_EXECUTION)

# Записываем 512 байт данных
for i in range(512):
    bus.io_write(0xF2, i & 0xFF)

# Проверяем, что данные записаны на диск
drive = fdc.drives[0]
sector_data = drive.read_sector(0, 0, 1)
check("Данные записаны (первый байт)", sector_data[0], 0x00)
check("Данные записаны (байт 100)", sector_data[100], 100)
check("Данные записаны (последний байт)", sector_data[511], 0xFF)

# Читаем результат (7 байт)
for i in range(7):
    result = bus.io_read(0xF2)

check("Состояние IDLE после результата", fdc.state, I8272.STATE_IDLE)

# =============================================
# ТЕСТ 6: Чтение данных (PIO mode)
# =============================================
print("\nТест 6: Чтение данных (PIO mode)")
print("-" * 50)

# Команда Read Data (0x06)
bus.io_write(0xF2, 0x06)  # Команда
bus.io_write(0xF2, 0x00)  # Параметр 1
bus.io_write(0xF2, 0x00)  # Цилиндр 0
bus.io_write(0xF2, 0x00)  # Головка 0
bus.io_write(0xF2, 0x01)  # Сектор 1
bus.io_write(0xF2, 0x02)  # Размер сектора: 512 байт
bus.io_write(0xF2, 0x12)  # Последний сектор
bus.io_write(0xF2, 0x1B)  # GPL
bus.io_write(0xF2, 0xFF)  # DTL

check("Состояние EXECUTION", fdc.state, I8272.STATE_EXECUTION)

# Читаем 512 байт данных
read_data = []
for i in range(512):
    read_data.append(bus.io_read(0xF2))

check("Данные прочитаны (первый байт)", read_data[0], 0x00)
check("Данные прочитаны (байт 100)", read_data[100], 100)
check("Данные прочитаны (последний байт)", read_data[511], 0xFF)

# Читаем результат (7 байт)
for i in range(7):
    result = bus.io_read(0xF2)

check("Состояние IDLE после результата", fdc.state, I8272.STATE_IDLE)

# =============================================
# ТЕСТ 7: Seek и Recalibrate
# =============================================
print("\nТест 7: Seek и Recalibrate")
print("-" * 50)

# Команда Seek (0x0F): цилиндр 10
bus.io_write(0xF2, 0x0F)  # Команда
bus.io_write(0xF2, 0x00)  # Параметр (дисковод 0)
bus.io_write(0xF2, 0x0A)  # Цилиндр 10

check("Головка на цилиндре 10", fdc.drives[0].cylinder, 10)
check("Не на дорожке 0", fdc.drives[0].track0, False)
check("IRQ ожидает", fdc.pending_irq, True)

# Sense Interrupt Status (0x08)
bus.io_write(0xF2, 0x08)  # Команда
st0 = bus.io_read(0xF2)
cyl = bus.io_read(0xF2)
check("ST0: Seek End (бит 5)", bool(st0 & 0x20), True)
check("Цилиндр в результате", cyl, 10)
check("IRQ сброшен", fdc.pending_irq, False)

# Команда Recalibrate (0x07)
bus.io_write(0xF2, 0x07)  # Команда
bus.io_write(0xF2, 0x00)  # Параметр (дисковод 0)

check("Головка на цилиндре 0", fdc.drives[0].cylinder, 0)
check("На дорожке 0", fdc.drives[0].track0, True)

# =============================================
# ТЕСТ 8: Version (8272A)
# =============================================
print("\nТест 8: Version (8272A)")
print("-" * 50)

bus.io_write(0xF2, 0x10)  # Команда Version
version = bus.io_read(0xF2)
check("Версия 8272A (0x90)", version, 0x90)

# =============================================
# ТЕСТ 9: Read ID
# =============================================
print("\nТест 9: Read ID")
print("-" * 50)

# Устанавливаем позицию головки
fdc.drives[0].cylinder = 5
fdc.drives[0].head = 1
fdc.drives[0].sector = 3

bus.io_write(0xF2, 0x0A)  # Команда Read ID
bus.io_write(0xF2, 0x00)  # Параметр

# Читаем результат (7 байт)
st0 = bus.io_read(0xF2)
st1 = bus.io_read(0xF2)
st2 = bus.io_read(0xF2)
cyl = bus.io_read(0xF2)
head = bus.io_read(0xF2)
sec = bus.io_read(0xF2)
n = bus.io_read(0xF2)

check("Цилиндр в ID", cyl, 5)
check("Головка в ID", head, 1)
check("Сектор в ID", sec, 3)
check("Размер сектора (N=2)", n, 2)

# =============================================
# ТЕСТ 10: Форматирование и извлечение диска
# =============================================
print("\nТест 10: Форматирование и извлечение диска")
print("-" * 50)

fdc.insert_disk(0)
check("Диск вставлен", fdc.drives[0].ready, True)

# Форматируем дорожку 0
fdc.drives[0].cylinder = 0
bus.io_write(0xF2, 0x0D)  # Команда Format Track
bus.io_write(0xF2, 0x00)  # Параметр 1
bus.io_write(0xF2, 0x00)  # Головка
bus.io_write(0xF2, 0x12)  # Секторов на дорожку
bus.io_write(0xF2, 0x02)  # Размер сектора
bus.io_write(0xF2, 0x54)  # GPL

check("Дорожка отформатирована", (0, 0, 1) in fdc.drives[0].data, True)

fdc.eject_disk(0)
check("Диск извлечён", fdc.drives[0].ready, False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8272 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
