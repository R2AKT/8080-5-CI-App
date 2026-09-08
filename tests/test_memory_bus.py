from modules.memory.memory_bus import MemoryBus, MemoryRegion

# Тест 1: Пустая шина
bus = MemoryBus()
assert bus.read(0x0000) == 0xFF, "Пустая шина должна возвращать 0xFF"

# Тест 2: Простой регион
class TestRAM(MemoryRegion):
    def __init__(self, start, end):
        super().__init__(start, end, "test_ram")
        self.data = {}
    def read(self, addr):
        return self.data.get(addr, 0xFF)
    def write(self, addr, value):
        self.data[addr] = value & 0xFF

ram = TestRAM(0x0000, 0xFFFF)
bus.register_memory(ram)
bus.write(0x0100, 0x55)
assert bus.read(0x0100) == 0x55, f"Ожидалось 0x55, получено {bus.read(0x0100):02X}"
assert bus.read_word(0x0100) == 0xFF55, "read_word little-endian"

# Тест 3: Карта памяти
mem_map = bus.get_memory_map()
assert len(mem_map) == 1
assert mem_map[0]["name"] == "test_ram"

print("✅ Все тесты MemoryBus пройдены!")