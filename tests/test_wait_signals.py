"""Тест WAIT-сигналов (итерация 10.3)"""
from modules.system import ComputerSystem
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
# ТЕСТ 1: Базовый WAIT от AM9511
# =============================================
print("\nТест 1: Базовый WAIT от AM9511")
print("-" * 50)

toml_config = """
[system]
name = "WAIT Test"

[[memory]]
type = "ram"
start = 0x0000
end = 0xFFFF
name = "RAM"

[[devices]]
type = "am9511"
name = "APU-0"
base_port = 0x80
"""

system = ComputerSystem()
system.load_from_toml_string(toml_config, name="wait_test")

apu = system.get_device("APU-0")
check("AM9511 найден", apu is not None, True)
check("Режим WAIT", apu.sync_mode, AM9511.MODE_WAIT)

# =============================================
# ТЕСТ 2: WAIT-сигнал при операции
# =============================================
print("\nТест 2: WAIT-сигнал при операции")
print("-" * 50)

wait_events = []
apu.on_wait = lambda active: wait_events.append(active)

# PUSH двух операндов
apu.io_write(0x80, 0x10)  # LSB
apu.io_write(0x80, 0x00)  # MSB → TOS = 0x0010
apu.io_write(0x80, 0x20)  # LSB
apu.io_write(0x80, 0x00)  # MSB → NOS = 0x0020

# Запуск MUL
apu.io_write(0x81, AM9511.CMD_MUL)

check("WAIT активен после команды", apu.busy, True)
check("on_wait(True) вызван", len(wait_events) > 0 and wait_events[-1], True)
check("is_busy() = True", apu.is_busy(), True)

# =============================================
# ТЕСТ 3: Операция завершается через tick
# =============================================
print("\nТест 3: Операция завершается через tick")
print("-" * 50)

# MUL занимает 30 тактов
for i in range(30):
    apu.tick(cycles=1)
    if not apu.busy:
        break

check("Операция завершена", apu.busy, False)
check("on_wait(False) вызван", len(wait_events) >= 2 and wait_events[-1], False)
check("is_busy() = False", apu.is_busy(), False)

# Проверяем результат MUL: 0x0010 * 0x0020 = 0x00000200
check("TOS (low) = 0x0200", apu._tos(), 0x0200)
check("NOS (high) = 0x0000", apu._nos(), 0x0000)

# =============================================
# ТЕСТ 4: CPU останавливается при WAIT
# =============================================
print("\nТест 4: CPU останавливается при WAIT")
print("-" * 50)

# Создаём простой CPU-мок
class MockCPU:
    def __init__(self):
        self.wait_signal = False
        self.memory_bus = None
        self.io_bus = None
    def set_wait(self, active):
        self.wait_signal = active

cpu = MockCPU()
system.connect_cpu(cpu)

# Запускаем MUL
apu.io_write(0x80, 0x05)
apu.io_write(0x80, 0x00)
apu.io_write(0x80, 0x03)
apu.io_write(0x80, 0x00)
apu.io_write(0x81, AM9511.CMD_MUL)

check("CPU.wait_signal = True", cpu.wait_signal, True)
check("system.check_wait() = True", system.check_wait(), True)

# Выполняем такты до завершения
for _ in range(35):
    system.tick(cycles=1)

check("CPU.wait_signal = False", cpu.wait_signal, False)
check("system.check_wait() = False", system.check_wait(), False)

# =============================================
# ТЕСТ 5: Несколько операций подряд
# =============================================
print("\nТест 5: Несколько операций подряд")
print("-" * 50)

apu.reset()
wait_count = [0]
apu.on_wait = lambda active: wait_count.__setitem__(0, wait_count[0] + 1) if active else None

# PUSH 2 и 3
apu.io_write(0x80, 0x02); apu.io_write(0x80, 0x00)
apu.io_write(0x80, 0x03); apu.io_write(0x80, 0x00)

# ADD (быстрая операция)
apu.io_write(0x81, AM9511.CMD_ADD)
check("ADD: busy", apu.busy, True)

apu.tick(10)
check("ADD: завершён", apu.busy, False)
check("ADD: результат 5", apu._tos(), 5)

# PUSH 10 и 2 для DIV
apu.io_write(0x80, 0x0A); apu.io_write(0x80, 0x00)
apu.io_write(0x80, 0x02); apu.io_write(0x80, 0x00)

# DIV (медленная операция)
apu.io_write(0x81, AM9511.CMD_DIV)
check("DIV: busy", apu.busy, True)

for _ in range(35):
    apu.tick(cycles=1)
    if not apu.busy:
        break

check("DIV: завершён", apu.busy, False)
check("DIV: частное 5", apu._nos(), 5)
check("DIV: остаток 0", apu._tos(), 0)

# =============================================
# ТЕСТ 6: Проверка через get_state
# =============================================
print("\nТест 6: Проверка через get_state")
print("-" * 50)

state = apu.get_state()
check("get_state: busy", state.get("busy", None), False)
check("get_state: sync_mode", state.get("sync_mode", None), "WAIT")

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ WAIT-СИГНАЛОВ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10.3 ЗАВЕРШЕНА (для AM9511)!")
    print("    Следующий шаг: WAIT для CF IDE")
else:
    print(" ❌ Есть проваленные тесты.")
