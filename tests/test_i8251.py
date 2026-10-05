"""Тест I8251 USART (итерация E5)"""
from modules.memory.memory_bus import MemoryBus
from modules.io import I8251

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
# ТЕСТ 1: Инициализация (Mode + Command)
# =============================================
print("\nТест 1: Инициализация (Mode + Command)")
print("-" * 50)

bus = MemoryBus()
usart = I8251(base_port=0x00)
usart.register_to_bus(bus)

check("Начальное состояние RESET", usart.state, I8251.STATE_RESET)

# Запись Mode Register
bus.io_write(0x00, 0x4E)  # Асинхронный, 8 бит, 16x baud
check("Состояние после Mode", usart.state, I8251.STATE_MODE)
check("Mode Register", usart.mode_register, 0x4E)

# Запись Command Register
bus.io_write(0x00, 0x37)  # Tx/Rx enable
check("Состояние после Command", usart.state, I8251.STATE_READY)
check("Command Register", usart.command_register, 0x37)

# =============================================
# ТЕСТ 2: Передача данных (Tx)
# =============================================
print("\nТест 2: Передача данных (Tx)")
print("-" * 50)

transmitted = []
usart.on_transmit = lambda data: transmitted.append(data)

bus.io_write(0x00, 0x55)  # Передача 0x55
check("Данные переданы", transmitted, [0x55])
check("TxRDY в статусе", bus.io_read(0x01) & 0x01, 0x01)

# =============================================
# ТЕСТ 3: Приём данных (Rx)
# =============================================
print("\nТест 3: Приём данных (Rx)")
print("-" * 50)

interrupts = []
usart.on_interrupt = lambda sig, active: interrupts.append((sig, active))

usart.receive_data(0xAA)
check("RxRDY в статусе", bus.io_read(0x01) & 0x02, 0x02)
check("RxRDY прерывание", interrupts[-1], ('RxRDY', True))

data = bus.io_read(0x00)
check("Прочитанные данные", data, 0xAA)
check("RxRDY сброшен после чтения", usart.rx_ready, False)

# =============================================
# ТЕСТ 4: Сброс
# =============================================
print("\nТест 4: Сброс")
print("-" * 50)

usart.reset()
check("Состояние после сброса", usart.state, I8251.STATE_RESET)
check("Mode после сброса", usart.mode_register, 0x00)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8251 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
