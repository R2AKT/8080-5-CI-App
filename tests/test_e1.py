"""Тест E1: шина памяти"""
import sys
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from modules.memory.memory_bus import MemoryBus, RAMRegion, ROMRegion

# Тест 1: RAM
bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)
bus.write(0x0100, 0x55)
assert bus.read(0x0100) == 0x55, f"RAM: ожидалось 0x55, получено {bus.read(0x0100):02X}"
print("✅ RAM: запись/чтение OK")

# Тест 2: ROM не пишется
bus2 = MemoryBus()
rom = ROMRegion(0x0000, 0x0FFF, data={0x0000: 0xC3, 0x0001: 0x00, 0x0002: 0x10}, name="ROM")
bus2.register_memory(rom)
assert bus2.read(0x0000) == 0xC3, "ROM: чтение OK"
bus2.write(0x0000, 0xFF)
assert bus2.read(0x0000) == 0xC3, "ROM: запись игнорируется"
print("✅ ROM: чтение OK, запись игнорируется")

# Тест 3: RAM + ROM на шине
bus3 = MemoryBus()
rom3 = ROMRegion(0x0000, 0x0FFF, data={0x0000: 0xC3}, name="ROM")
ram3 = RAMRegion(0x1000, 0xFFFF, name="RAM")
bus3.register_memory(rom3)
bus3.register_memory(ram3)
assert bus3.read(0x0000) == 0xC3, "ROM по 0x0000"
bus3.write(0x1000, 0xAA)
assert bus3.read(0x1000) == 0xAA, "RAM по 0x1000"
print("✅ RAM + ROM на шине OK")

# Тест 4: read_word / write_word
bus3.write_word(0x2000, 0x1234)
assert bus3.read_word(0x2000) == 0x1234, "write_word/read_word OK"
print("✅ read_word/write_word OK")

# Тест 5: get_memory_map
mmap = bus3.get_memory_map()
assert len(mmap) == 2, f"Ожидалось 2 региона, получено {len(mmap)}"
assert mmap[0]["name"] == "ROM"
assert mmap[1]["name"] == "RAM"
print("✅ get_memory_map OK")

# Тест 6: RAM с внешним dict (mem_data)
mem_data = {0x0000: 0x3E, 0x0001: 0x55}
bus4 = MemoryBus()
ram4 = RAMRegion(0x0000, 0xFFFF, data=mem_data, name="RAM")
bus4.register_memory(ram4)
assert bus4.read(0x0000) == 0x3E, "Чтение из mem_data"
bus4.write(0x0002, 0x76)
assert mem_data[0x0002] == 0x76, "Запись в mem_data через шину"
print("✅ RAM с внешним dict OK")

print("\n✅ ВСЕ ТЕСТЫ E1 ПРОЙДЕНЫ!")
