"""Тест ShadowROMRegion (итерация E3)"""
from modules import MemoryBus, RAMRegion, ShadowROMRegion

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
# ТЕСТ 1: Режим M1 (Радио-86РК)
# =============================================
print("\nТест 1: Режим M1 (Радио-86РК)")
print("-" * 50)

# ROM: JMP F800h (3 байта) + данные монитора
rom_data = {i: i for i in range(16)}  # 16 байт данных
bus = MemoryBus()
shadow = ShadowROMRegion(
    rom_data, low_addr=0x0000, high_addr=0xF800,
    mode=ShadowROMRegion.MODE_M1, action=ShadowROMRegion.ACTION_MOVE,
    m1_count=3, name="Monitor ROM"
)
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(shadow)  # ShadowROM регистрируется ПЕРЕД RAM
bus.register_memory(ram)

# После сброса ROM виден по 0x0000
check("ROM виден по 0x0000", bus.read(0x0000), 0x00)
check("Состояние LOW", shadow.state, ShadowROMRegion.STATE_LOW)

# Читаем 3 байта (размер JMP)
bus.read(0x0001)
bus.read(0x0002)
check("После 3 чтений ROM переключился", shadow.state, ShadowROMRegion.STATE_HIGH)

# ROM теперь виден по 0xF800
check("ROM виден по 0xF800", bus.read(0xF800), 0x00)
check("ROM не виден по 0x0000", shadow.contains(0x0000), False)

# RAM теперь доступен по 0x0000
bus.write(0x0000, 0xAA)
check("RAM доступен по 0x0000", bus.read(0x0000), 0xAA)

# Сброс возвращает ROM на 0x0000
shadow.reset()
check("После сброса ROM виден по 0x0000", bus.read(0x0000), 0x00)
check("Состояние LOW после сброса", shadow.state, ShadowROMRegion.STATE_LOW)

# =============================================
# ТЕСТ 2: Режим MEM_WRITE (переключение по записи)
# =============================================
print("\nТест 2: Режим MEM_WRITE")
print("-" * 50)

bus2 = MemoryBus()
shadow2 = ShadowROMRegion(
    rom_data, low_addr=0x0000, high_addr=0xF800,
    mode=ShadowROMRegion.MODE_MEM_WRITE, action=ShadowROMRegion.ACTION_MOVE,
    trigger_addr=0xE000, name="ShadowROM MEM_WRITE"
)
ram2 = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus2.register_memory(shadow2)
bus2.register_memory(ram2)

# ROM виден по 0x0000
check("ROM виден по 0x0000", bus2.read(0x0000), 0x00)

# Запись в триггерный адрес переключает ROM
bus2.write(0xE000, 0x01)
check("После записи в 0xE000 ROM переключился", shadow2.state, ShadowROMRegion.STATE_HIGH)
check("ROM виден по 0xF800", bus2.read(0xF800), 0x00)

# =============================================
# ТЕСТ 3: Режим IO_WRITE (переключение по записи в порт)
# =============================================
print("\nТест 3: Режим IO_WRITE")
print("-" * 50)

bus3 = MemoryBus()
shadow3 = ShadowROMRegion(
    rom_data, low_addr=0x0000, high_addr=0xF800,
    mode=ShadowROMRegion.MODE_IO_WRITE, action=ShadowROMRegion.ACTION_MOVE,
    trigger_port=0x80, name="ShadowROM IO_WRITE"
)
ram3 = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus3.register_memory(shadow3)
bus3.register_memory(ram3)

# ROM виден по 0x0000
check("ROM виден по 0x0000", bus3.read(0x0000), 0x00)

# Запись в порт переключает ROM
bus3.io_write(0x80, 0x01)
check("После записи в порт 0x80 ROM переключился", shadow3.state, ShadowROMRegion.STATE_HIGH)
check("ROM виден по 0xF800", bus3.read(0xF800), 0x00)

# =============================================
# ТЕСТ 4: Действие DISABLE (полное отключение)
# =============================================
print("\nТест 4: Действие DISABLE")
print("-" * 50)

bus4 = MemoryBus()
shadow4 = ShadowROMRegion(
    rom_data, low_addr=0x0000, high_addr=0xF800,
    mode=ShadowROMRegion.MODE_IO_WRITE, action=ShadowROMRegion.ACTION_DISABLE,
    trigger_port=0x80, name="ShadowROM DISABLE"
)
ram4 = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus4.register_memory(shadow4)
bus4.register_memory(ram4)

# ROM виден по 0x0000
check("ROM виден по 0x0000", bus4.read(0x0000), 0x00)

# Запись в порт полностью отключает ROM
bus4.io_write(0x80, 0x01)
check("После записи в порт 0x80 ROM отключён", shadow4.state, ShadowROMRegion.STATE_DISABLED)
check("ROM не виден по 0xF800", shadow4.contains(0xF800), False)
check("ROM не виден по 0x0000", shadow4.contains(0x0000), False)

# RAM доступен по 0x0000
bus4.write(0x0000, 0xBB)
check("RAM доступен по 0x0000", bus4.read(0x0000), 0xBB)

# Сброс возвращает ROM
shadow4.reset()
check("После сброса ROM виден по 0x0000", bus4.read(0x0000), 0x00)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ShadowROM ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")