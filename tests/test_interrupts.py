"""Тест системы прерываний (итерация 10.1)"""
from modules.system import ComputerSystem

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
# ТЕСТ 1: Прерывание от устройства
# =============================================
print("\nТест 1: Прерывание от устройства")
print("-" * 50)

toml_config = """
[system]
name = "IRQ Test"

[[memory]]
type = "ram"
start = 0x0000
end = 0xFFFF
name = "RAM"

[[devices]]
type = "i8253"
name = "PIT-0"
base_port = 0x04
irq_vector = 0xCF
"""

system = ComputerSystem()
system.load_from_toml_string(toml_config, name="irq_test")

# Эмулятор не подключён, но проверим конфигурацию
pit = system.get_device("PIT-0")
check("PIT-0 найден", pit is not None, True)

# Проверка вектора из конфигурации
vector = system._get_interrupt_vector("PIT-0", pit)
check("Вектор из конфигурации", vector, 0xCF)

# =============================================
# ТЕСТ 2: Вектор по умолчанию
# =============================================
print("\nТест 2: Вектор по умолчанию")
print("-" * 50)

toml_config2 = """
[system]
name = "IRQ Default"

[[memory]]
type = "ram"
start = 0x0000
end = 0xFFFF
name = "RAM"

[[devices]]
type = "i8253"
name = "PIT-0"
base_port = 0x04
"""

system2 = ComputerSystem()
system2.load_from_toml_string(toml_config2, name="irq_default")

pit2 = system2.get_device("PIT-0")
vector2 = system2._get_interrupt_vector("PIT-0", pit2)
check("Вектор по умолчанию (RST 7)", vector2, 0xFF)

# =============================================
# ТЕСТ 3: Обработка прерывания в эмуляторе
# =============================================
print("\nТест 3: Обработка прерывания в эмуляторе")
print("-" * 50)

from i8080_emulator import I8080Emulator

mem = {
    0x0000: 0x00,  # NOP
    0x0001: 0x00,  # NOP
    0x0038: 0xC3,  # JMP 0x0100 (по адресу RST 7)
    0x0039: 0x00,
    0x003A: 0x01,
    0x0100: 0x76,  # HLT
}

emu = I8080Emulator(mem)
emu.reset()
emu.sp = 0xFFFE
emu.int_enabled = True  # EI выполнен

# Запрашиваем прерывание с вектором RST 7 (0xFF)
emu.request_interrupt(0xFF)
check("Прерывание ожидает", emu.has_pending_interrupt(), True)

# Обрабатываем прерывание
result = emu._handle_interrupt()
check("Прерывание обработано", result, True)
check("PC = 0x0038 (RST 7)", emu.pc, 0x0038)
check("Прерывания запрещены", emu.int_enabled, False)

# =============================================
# ТЕСТ 4: Прерывание запрещено (DI)
# =============================================
print("\nТест 4: Прерывание запрещено (DI)")
print("-" * 50)

emu2 = I8080Emulator(mem)
emu2.reset()
emu2.sp = 0xFFFE
emu2.int_enabled = False  # DI выполнен

emu2.request_interrupt(0xFF)
check("Прерывание ожидает", emu2.has_pending_interrupt(), True)

result2 = emu2._handle_interrupt()
check("Прерывание НЕ обработано (DI)", result2, False)
check("PC не изменился", emu2.pc, 0x0000)

# =============================================
# ТЕСТ 5: Проверка прерываний в ComputerSystem
# =============================================
print("\nТест 5: Проверка прерываний в ComputerSystem")
print("-" * 50)

system3 = ComputerSystem()
system3.load_from_toml_string(toml_config, name="irq_check")

emu3 = I8080Emulator(mem)
emu3.reset()
system3.connect_cpu(emu3)

# Имитируем прерывание от PIT
pit3 = system3.get_device("PIT-0")
pit3.irq_flag = True  # Флаг прерывания

# Проверяем прерывания
system3.check_interrupts()
check("Прерывание передано в CPU", emu3.has_pending_interrupt(), True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ПРЕРЫВАНИЙ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10.1 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
