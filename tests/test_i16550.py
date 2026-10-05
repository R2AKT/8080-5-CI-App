"""Тест I16550 UART (итерация E5)"""
from modules.memory.memory_bus import MemoryBus
from modules.io import I16550

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
# ТЕСТ 1: Инициализация и DLAB
# =============================================
print("\nТест 1: Инициализация и DLAB")
print("-" * 50)

bus = MemoryBus()
uart = I16550(base_port=0x00)
uart.register_to_bus(bus)

# Устанавливаем делитель (DLAB=1)
bus.io_write(0x03, 0x80)  # LCR: DLAB=1
check("DLAB установлен", uart.dlab, True)

bus.io_write(0x00, 0x0C)  # DLL = 12 (9600 baud при 1.8432 MHz)
bus.io_write(0x01, 0x00)  # DLM = 0
check("DLL записан", uart.dll, 0x0C)
check("DLM записан", uart.dlm, 0x00)

# Настройка формата данных (DLAB=0)
bus.io_write(0x03, 0x03)  # LCR: 8 бит, без паритета
check("DLAB сброшен", uart.dlab, False)
check("LCR записан", uart.lcr, 0x03)

# =============================================
# ТЕСТ 2: Передача данных (Tx)
# =============================================
print("\nТест 2: Передача данных (Tx)")
print("-" * 50)

transmitted = []
uart.on_transmit = lambda data: transmitted.append(data)

bus.io_write(0x00, 0x55)  # THR = 0x55
check("Данные переданы", transmitted, [0x55])
check("LSR: THR Empty", bool(uart.lsr & I16550.LSR_THRE), True)

# =============================================
# ТЕСТ 3: Приём данных (Rx)
# =============================================
print("\nТест 3: Приём данных (Rx)")
print("-" * 50)

interrupts = []
uart.on_interrupt = lambda active: interrupts.append(active)

uart.receive_data(0xAA)
check("LSR: Data Ready", bool(uart.lsr & I16550.LSR_DR), True)

data = bus.io_read(0x00)  # RBR
check("Прочитанные данные", data, 0xAA)
check("LSR: Data Ready сброшен", bool(uart.lsr & I16550.LSR_DR), False)

# =============================================
# ТЕСТ 4: FIFO буферы
# =============================================
print("\nТест 4: FIFO буферы")
print("-" * 50)

# Включаем FIFO
bus.io_write(0x02, 0x01)  # FCR: FIFO enable
check("FIFO включены", uart.fifo_enabled, True)

# Записываем несколько байтов в Rx FIFO
uart.receive_bytes([0x11, 0x22, 0x33])
check("Rx FIFO размер", len(uart.rx_fifo), 3)

# Читаем последовательно
check("Rx FIFO[0]", bus.io_read(0x00), 0x11)
check("Rx FIFO[1]", bus.io_read(0x00), 0x22)
check("Rx FIFO[2]", bus.io_read(0x00), 0x33)
check("Rx FIFO пуст", len(uart.rx_fifo), 0)

# =============================================
# ТЕСТ 5: Прерывания
# =============================================
print("\nТест 5: Прерывания")
print("-" * 50)

uart2 = I16550(base_port=0x10)
bus2 = MemoryBus()
uart2.register_to_bus(bus2)

interrupts2 = []
uart2.on_interrupt = lambda active: interrupts2.append(active)

# Включаем Rx прерывание
bus2.io_write(0x11, 0x01)  # IER: Rx enable
check("IER записан", uart2.ier, 0x01)

# Приём данных вызывает прерывание
uart2.receive_data(0x42)
check("Прерывание активно", uart2.has_interrupt(), True)

# Чтение IIR
iir = bus2.io_read(0x12)
check("IIR: Rx Data Available", iir, I16550.INT_RX)

# =============================================
# ТЕСТ 6: Scratch Register
# =============================================
print("\nТест 6: Scratch Register")
print("-" * 50)

bus.io_write(0x07, 0xAB)
check("SCR записан", bus.io_read(0x07), 0xAB)

# =============================================
# ТЕСТ 7: Сброс
# =============================================
print("\nТест 7: Сброс")
print("-" * 50)

uart.reset()
check("LCR после сброса", uart.lcr, 0x00)
check("IER после сброса", uart.ier, 0x00)
check("LSR после сброса (THRE|TEMT)", uart.lsr, I16550.LSR_THRE | I16550.LSR_TEMT)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I16550 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
