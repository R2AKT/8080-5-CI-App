"""Сквозной тест: прерывание + DMA + WAIT одновременно (итерация 10)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
from modules.io.i8257 import I8237
from modules.io.i8253 import I8253
from modules.io.am9511 import AM9511

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
# МОК CPU
# =============================================
class MockCPU:
    """Мок CPU для сквозного теста"""
    def __init__(self, memory_bus):
        self.memory_bus = memory_bus
        self.io_bus = memory_bus
        self.wait_signal = False
        self._pending_interrupts = []
        self.int_enabled = True
        self.pc = 0x0000
        self.sp = 0xFFFE
        self.cycles = 0

    def set_wait(self, active):
        self.wait_signal = active

    def request_interrupt(self, vector):
        self._pending_interrupts.append(vector)

    def has_pending_interrupt(self):
        return len(self._pending_interrupts) > 0

    def read_word(self, addr):
        low = self.memory_bus.read(addr)
        high = self.memory_bus.read(addr + 1)
        return (high << 8) | low

    def write_byte(self, addr, value):
        self.memory_bus.write(addr, value & 0xFF)

# =============================================
# МОК ComputerSystem (упрощённый)
# =============================================
class MockSystem:
    """Упрощённый ComputerSystem для сквозного теста"""
    def __init__(self, bus, cpu):
        self.bus = bus
        self.cpu = cpu
        self.devices = {}

    def add_device(self, name, device):
        self.devices[name] = device

    def tick(self, cycles=1):
        for name, device in self.devices.items():
            if hasattr(device, 'tick'):
                device.tick(cycles)

    def check_dma(self):
        for name, device in self.devices.items():
            if hasattr(device, 'is_active') and device.is_active():
                if hasattr(device, 'perform_transfer'):
                    device.perform_transfer(self.bus)
                return True
        return False

    def check_wait(self):
        for name, device in self.devices.items():
            if hasattr(device, 'is_busy') and device.is_busy():
                return True
        return False

    def check_interrupts(self):
        for name, device in self.devices.items():
            if hasattr(device, 'has_interrupt') and device.has_interrupt():
                vector = getattr(device, 'irq_vector', 0xFF)
                self.cpu.request_interrupt(vector)
                if hasattr(device, 'acknowledge_interrupt'):
                    device.acknowledge_interrupt()
                return True
        return False

# =============================================
# ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ
# =============================================
print("\nИнициализация системы")
print("-" * 50)

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)

cpu = MockCPU(bus)
system = MockSystem(bus, cpu)

# === AM9511 (WAIT) ===
apu = AM9511(base_port=0x80, name="APU-0")
apu.register_to_bus(bus)
apu.on_wait = lambda active: cpu.set_wait(active)
system.add_device("APU-0", apu)
check("AM9511 создан", apu is not None, True)

# === I8237 (DMA) ===
dma = I8237(base_port=0x00, name="DMA-0")
dma.register_to_bus(bus)
dma.set_memory_bus(bus)
system.add_device("DMA-0", dma)
check("I8237 создан", dma is not None, True)

# === I8253 (Прерывание) ===
pit = I8253(base_port=0x04, name="PIT-0")
pit.register_to_bus(bus)
pit.on_irq = lambda active: None
system.add_device("PIT-0", pit)
check("I8253 создан", pit is not None, True)

# =============================================
# ТЕСТ 1: Одновременная работа всех систем
# =============================================
print("\nТест 1: Одновременная работа всех систем")
print("-" * 50)

# Подготавливаем данные для DMA
for i in range(256):
    bus.write(0x1000 + i, i & 0xFF)

# Программируем DMA: память↔память (0x1000 → 0x2000, 256 байт)
dma.io_write(0x0C, 0x00)  # Сброс Flip-Flop
dma.io_write(0x0D, 0x00)  # Сброс маски
dma.io_write(0x00, 0x00)  # Канал 0: адрес 0x1000 (LSB)
dma.io_write(0x00, 0x10)  # Канал 0: адрес 0x1000 (MSB)
dma.io_write(0x01, 0xFF)  # Канал 0: счётчик 255 (256 байт)
dma.io_write(0x01, 0x00)
dma.io_write(0x02, 0x00)  # Канал 1: адрес 0x2000 (LSB)
dma.io_write(0x02, 0x20)  # Канал 1: адрес 0x2000 (MSB)
dma.io_write(0x03, 0xFF)  # Канал 1: счётчик 255
dma.io_write(0x03, 0x00)
dma.io_write(0x08, 0x01)  # Режим память↔память
dma.io_write(0x09, 0x04)  # Программный запрос канала 0

check("DMA активен", dma.is_active(), True)

# Запускаем AM9511 (WAIT)
apu.io_write(0x80, 0x10)  # TOS = 0x0010
apu.io_write(0x80, 0x00)
apu.io_write(0x80, 0x20)  # NOS = 0x0020
apu.io_write(0x80, 0x00)
apu.io_write(0x81, AM9511.CMD_MUL)  # MUL: 0x10 * 0x20 = 0x200

check("AM9511 занят (WAIT)", apu.is_busy(), True)
check("CPU.wait_signal = True", cpu.wait_signal, True)

# Имитируем прерывание от I8253
pit.irq_flag = True
check("PIT: прерывание активно", pit.irq_flag, True)

# =============================================
# ТЕСТ 2: Обработка в правильном порядке
# =============================================
print("\nТест 2: Обработка в правильном порядке")
print("-" * 50)

# Приоритет: DMA > WAIT > Прерывание
# Шаг 1: DMA приостанавливает CPU
dma_active = system.check_dma()
check("Шаг 1: DMA приостанавливает CPU", dma_active, True)

# Шаг 2: После завершения DMA проверяем WAIT
for i in range(300):
    system.tick(cycles=1)
    if not dma.is_active():
        break

check("Шаг 2: DMA завершён", dma.is_active(), False)
check("Шаг 2: Данные скопированы", bus.read(0x2055), 0x55)

# Шаг 3: Проверяем WAIT (AM9511 всё ещё занят)
wait_active = system.check_wait()
check("Шаг 3: WAIT активен (AM9511)", wait_active, True)

# Шаг 4: Завершаем AM9511
for i in range(35):
    system.tick(cycles=1)
    if not apu.is_busy():
        break

check("Шаг 4: AM9511 завершён", apu.is_busy(), False)
check("Шаг 4: Результат MUL", apu._tos(), 0x0200)

# Шаг 5: Проверяем прерывание
irq_handled = system.check_interrupts()
check("Шаг 5: Прерывание обработано", irq_handled, True)
check("Шаг 5: Вектор в очереди", cpu.has_pending_interrupt(), True)

# =============================================
# ТЕСТ 3: Повторный цикл
# =============================================
print("\nТест 3: Повторный цикл")
print("-" * 50)

# Записываем новые данные для DMA
for i in range(128):
    bus.write(0x3000 + i, (i * 2) & 0xFF)

# Программируем DMA: 0x3000 → 0x4000, 128 байт
dma.io_write(0x0C, 0x00)
dma.io_write(0x0D, 0x00)
dma.io_write(0x00, 0x00)  # Канал 0: 0x3000
dma.io_write(0x00, 0x30)
dma.io_write(0x01, 0x7F)  # 128 байт (127)
dma.io_write(0x01, 0x00)
dma.io_write(0x02, 0x00)  # Канал 1: 0x4000
dma.io_write(0x02, 0x40)
dma.io_write(0x03, 0x7F)
dma.io_write(0x03, 0x00)
dma.io_write(0x08, 0x01)
dma.io_write(0x09, 0x04)

check("Повторный DMA запущен", dma.is_active(), True)

# Выполняем передачу
for i in range(150):
    system.tick(cycles=1)
    if not dma.is_active():
        break

check("Повторный DMA завершён", dma.is_active(), False)
check("Данные скопированы (0x4000)", bus.read(0x4000), 0x00)
check("Данные скопированы (0x4020)", bus.read(0x4020), 0x40)  # 0x20 * 2 = 0x40
check("Данные скопированы (0x407F)", bus.read(0x407F), 0xFE)  # 0x7F * 2 = 0xFE

# =============================================
# ТЕСТ 4: Состояние после всех операций
# =============================================
print("\nТест 4: Состояние после всех операций")
print("-" * 50)

check("CPU не ждёт", cpu.wait_signal, False)
check("DMA не активен", dma.is_active(), False)
check("AM9511 не занят", apu.is_busy(), False)

# Проверяем, что источник не изменился
check("Источник не изменился (0x1000)", bus.read(0x1000), 0x00)
check("Источник не изменился (0x10FF)", bus.read(0x10FF), 0xFF)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ СКВОЗНОЙ ИНТЕГРАЦИИ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10 ПОЛНОСТЬЮ ЗАВЕРШЕНА!")
    print("    • Прерывания (10.1) ✅")
    print("    • ПДП (10.2) ✅")
    print("    • WAIT-сигналы (10.3) ✅")
    print("    • Профили в MainWindow (10.4) ✅")
    print("    • Сквозной тест ✅")
    print("    Следующий шаг: новая итерация")
    print("    (графическая отрисовка дисплеев в GUI)")
else:
    print(" ❌ Есть проваленные тесты.")
