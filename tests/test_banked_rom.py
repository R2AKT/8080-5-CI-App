"""Тест BankedROMRegion"""
import sys
sys.path.insert(0, '.')
from modules import MemoryBus, BankedROMRegion

print("=" * 60)
print(" ТЕСТ BankedROMRegion")
print("=" * 60)

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

# === Подготовка данных банков ===
bank0 = {i: 0xA0 + i for i in range(16)}  # Банк 0: A0, A1, A2, ...
bank1 = {i: 0xB0 + i for i in range(16)}  # Банк 1: B0, B1, B2, ...
bank2 = {i: 0xC0 + i for i in range(16)}  # Банк 2: C0, C1, C2, ...

# === Тест 1: Создание через конструктор ===
print("\nТест 1: Создание через конструктор")
rom = BankedROMRegion(
    0x0000, 0x000F,
    banks=[bank0, bank1, bank2],
    switch_port=0x10,
    name="Test BankedROM"
)
bus = MemoryBus()
bus.register_memory(rom)

check("Чтение из банка 0 (offset 0)", bus.read(0x0000), 0xA0)
check("Чтение из банка 0 (offset 5)", bus.read(0x0005), 0xA5)

# === Тест 2: Переключение через IO-порт ===
print("\nТест 2: Переключение через IO-порт")
bus.io_write(0x10, 1)  # Переключаем на банк 1
check("Текущий банк после io_write(0x10, 1)", rom.current_bank, 1)
check("Чтение из банка 1 (offset 0)", bus.read(0x0000), 0xB0)
check("Чтение из банка 1 (offset 5)", bus.read(0x0005), 0xB5)

bus.io_write(0x10, 2)  # Переключаем на банк 2
check("Чтение из банка 2 (offset 0)", bus.read(0x0000), 0xC0)

# === Тест 3: Переключение с переполнением номера банка ===
print("\nТест 3: Переполнение номера банка")
bus.io_write(0x10, 5)  # 5 % 3 = 2
check("Банк при bank_num=5 (5%3=2)", rom.current_bank, 2)
bus.io_write(0x10, 3)  # 3 % 3 = 0
check("Банк при bank_num=3 (3%3=0)", rom.current_bank, 0)
check("Чтение из банка 0", bus.read(0x0000), 0xA0)

# === Тест 4: ROM не пишется ===
print("\nТест 4: ROM не пишется")
bus.write(0x0000, 0xFF)
check("ROM не изменился после записи", bus.read(0x0000), 0xA0)

# === Тест 5: Переключение через адрес памяти ===
print("\nТест 5: Переключение через адрес памяти")
rom2 = BankedROMRegion(
    0x0000, 0x000F,
    banks=[bank0, bank1],
    switch_addr=0x000F,  # Последний адрес окна — переключатель
    name="Test BankedROM 2"
)
bus2 = MemoryBus()
bus2.register_memory(rom2)

check("Начальный банк", rom2.current_bank, 0)
bus2.write(0x000F, 1)  # Запись по switch_addr переключает банк
check("Банк после записи по switch_addr", rom2.current_bank, 1)
check("Чтение из банка 1", bus2.read(0x0000), 0xB0)

# === Тест 6: load_bank ===
print("\nТест 6: load_bank")
rom3 = BankedROMRegion(0x0000, 0x000F, switch_port=0x20)
rom3.load_bank(0, [0x11, 0x22, 0x33])
rom3.load_bank(1, {0: 0x44, 1: 0x55})
rom3.num_banks = len(rom3.banks)

bus3 = MemoryBus()
bus3.register_memory(rom3)

check("Чтение из банка 0 (load_bank list)", bus3.read(0x0000), 0x11)
check("Чтение из банка 0 (offset 1)", bus3.read(0x0001), 0x22)
bus3.io_write(0x20, 1)
check("Чтение из банка 1 (load_bank dict)", bus3.read(0x0000), 0x44)
check("Чтение из банка 1 (offset 1)", bus3.read(0x0001), 0x55)

# === Тест 7: reset ===
print("\nТест 7: reset")
rom3.select_bank(1)
check("Банк до reset", rom3.current_bank, 1)
rom3.reset()
check("Банк после reset", rom3.current_bank, 0)

# === Тест 8: get_state ===
print("\nТест 8: get_state")
state = rom.get_state()
check("get_state current_bank", state["current_bank"], rom.current_bank)
check("get_state num_banks", state["num_banks"], 3)

# === Итоги ===
print("\n" + "=" * 60)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 60)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ BankedROMRegion ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")