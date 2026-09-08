"""Тест BankedRegion"""
import sys
sys.path.insert(0, '.')
from modules.memory.memory_bus import IOBus, MemoryBus
from modules.memory.banked import BankedRegion
from modules.memory.shadow import ShadowROMRegion

print("=" * 60)
print(" ТЕСТ BankedRegion")
print("=" * 60)

# Создаём шину с банковой памятью
bus = MemoryBus()
banked = BankedRegion(0x0000, 0xFFFF, num_banks=4, switch_port=0x00, name="BankedRAM")
bus.register_memory(banked)

# Тест 1: Запись в банк 0
bus.write(0x0100, 0xAA)
assert bus.read(0x0100) == 0xAA, f"Ожидалось 0xAA, получено {bus.read(0x0100):02X}"
print("✅ Тест 1: Запись/чтение в банке 0")

# Тест 2: Переключение на банк 1 через IO-порт
bus.io_write(0x00, 1)  # Переключаем на банк 1
assert banked.current_bank == 1, f"Ожидался банк 1, получен {banked.current_bank}"
assert bus.read(0x0100) == 0x00, f"Банк 1 должен быть пуст, получено {bus.read(0x0100):02X}"
print("✅ Тест 2: Переключение на банк 1")

# Тест 3: Запись в банк 1
bus.write(0x0100, 0xBB)
assert bus.read(0x0100) == 0xBB, f"Ожидалось 0xBB, получено {bus.read(0x0100):02X}"
print("✅ Тест 3: Запись/чтение в банке 1")

# Тест 4: Возврат на банк 0
bus.io_write(0x00, 0)  # Возвращаемся на банк 0
assert bus.read(0x0100) == 0xAA, f"Банк 0 должен содержать 0xAA, получено {bus.read(0x0100):02X}"
print("✅ Тест 4: Возврат на банк 0")

# Тест 5: Переключение по адресу памяти
banked2 = BankedRegion(0x0000, 0xFFFF, num_banks=2, switch_addr=0xFFFE, name="BankedRAM2")
bus2 = MemoryBus()
bus2.register_memory(banked2)
bus2.write(0x0200, 0xCC)  # Запись в банк 0
bus2.write(0xFFFE, 1)      # Переключение на банк 1
assert banked2.current_bank == 1, f"Ожидался банк 1, получен {banked2.current_bank}"
assert bus2.read(0x0200) == 0x00, f"Банк 1 должен быть пуст"
print("✅ Тест 5: Переключение по адресу памяти")

# Тест 6: Карта памяти
mem_map = bus.get_memory_map()
assert len(mem_map) == 1
assert mem_map[0]["type"] == "BankedRegion"
assert mem_map[0]["current_bank"] == 0
assert mem_map[0]["num_banks"] == 4
print("✅ Тест 6: Карта памяти")

print("\n" + "=" * 60)
print(" ✅ ВСЕ ТЕСТЫ BankedRegion ПРОЙДЕНЫ!")
print("=" * 60)